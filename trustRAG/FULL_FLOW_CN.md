# TrustRAG 完整请求流程（打分 -> `w_j` -> 结束）

本文档给出当前代码实现下，一次完整流程的接口请求路径。  
目标：从用户打分开始，最终得到文档权重 `w_j`，并完成本轮流程。

---

## 1. 参与方与入口

- 文档服务（HTTP）：`http://127.0.0.1:8000`
- 委员会节点（HTTP）：
  - `http://127.0.0.1:9001`
  - `http://127.0.0.1:9002`
  - `http://127.0.0.1:9003`
  - `http://127.0.0.1:9004`
- 链上合约（JSON-RPC + `DataChain.sol`）：
  - 本地常见 RPC：`http://127.0.0.1:8545`
  - 关键方法：`submitVote`、`submitAggregate`、`voteCount`、`aggregatedS`、`aggregatedVoteCount`

---

## 2. 请求路径总览（时序）

1. 客户端读取文档：`GET /doc/{doc_id}`
2. 用户本地打分：得到 `s_i`（例如 0~50）与随机盲值 `r_i`
3. 客户端本地计算承诺：`C_i = g^s_i * h^r_i mod P`
4. 客户端调用链上：`DataChain.submitVote(docId, rid, C_i)`
5. 客户端本地做 Shamir 分片：`(s_i,r_i) -> n 份 shares`
6. 客户端向每个委员会节点发送 share：`POST /share`
7. 聚合方向 `t` 个委员会节点触发本地聚合：`POST /trigger/{rid}/{doc_id}`
8. 聚合方收集 `t` 份 `(S_share, R_share)` 后重建 `S, R`
9. 聚合方查询链上票数：`DataChain.voteCount(docId, rid)`
10. 聚合方离线生成并聚合阈值 BLS 签名 `sigma`，再准备 committee attestation
11. 聚合方调用链上：`DataChain.submitAggregate(docId, rid, S, R, voteCount, sigma, attestations)`
12. 客户端/聚合方查询链上结果：`aggregatedS`、`aggregatedVoteCount`
13. 计算文档权重：`w_j = S_j / voteCount_j`
14. （可选）再读文档文本：`GET /doc/{doc_id}`，返回“文本 + 权重”
15. 本轮结束

---

## 3. 各步骤接口明细

## 3.1 读取文档（可选）

### 请求

```bash
curl http://127.0.0.1:8000/doc/doc1
```

### 响应

```json
{"doc_id":"doc1","text":"Hello this is a demo document."}
```

---

## 3.2 用户打分与承诺（本地计算）

本地输入：

- `rid = 1`
- `doc_id = "doc1"`
- `s_i`：用户打分
- `r_i`：随机盲值

本地计算：

- `C_i = commit(s_i, r_i)`

此步骤不走 HTTP，请求发生在下一步链上提交。

---

## 3.3 提交投票承诺到链上

调用合约方法（通过 JSON-RPC 发送交易）：

- `DataChain.submitVote(docId, rid, C_i)`

效果：

- `productCommitment[docId][rid]` 累乘更新
- `voteCount[docId][rid] += 1`

---

## 3.4 将 `(s_i, r_i)` 分片并发送给委员会

每个节点一份 share，请求路径如下（以节点 1 为例）：

### 请求

```bash
curl -X POST http://127.0.0.1:9001/share \
  -H "Content-Type: application/json" \
  -d '{
    "rid": 1,
    "doc_id": "doc1",
    "voter_id": "v1",
    "s_share": {"x": 1, "y": 123},
    "r_share": {"x": 1, "y": 456}
  }'
```

### 响应

```json
{
  "ok": true,
  "node_id": "1",
  "rid": 1,
  "doc_id": "doc1",
  "voter_id": "v1",
  "stored_count": 1
}
```

同理发送到 `9002/9003/9004`。

---

## 3.5 触发委员会节点聚合本地 shares

聚合方对至少 `t` 个节点请求：

### 请求

```bash
curl -X POST http://127.0.0.1:9001/trigger/1/doc1
```

### 响应（示例）

```json
{
  "node_id": "1",
  "rid": 1,
  "doc_id": "doc1",
  "status": "ok",
  "stored_count": 20,
  "share": {"x": 1, "s_y": 210, "r_y": 111852486},
  "field_prime": 170141183460469231731687303715884105727
}
```

说明：

- `share.s_y`、`share.r_y` 是该节点对所有投票 share 的本地汇总结果
- 聚合方收集到 `t` 份后，可重建全局 `S, R`

---

## 3.6 重建 `S, R` + 生成签名（离线）

离线步骤（无 HTTP）：

1. 使用 `t` 份 `S_share` 重建 `S`
2. 使用 `t` 份 `R_share` 重建 `R`
3. 查询链上 `voteCount`
4. 对消息 `m = H(rid, doc_id, S, R, voteCount)` 做阈值 BLS 部分签名与聚合，得到 `sigma`
5. 生成 committee attestation（当前实现链上校验该 attestation）

---

## 3.7 提交聚合结果到链上

调用合约方法：

- `DataChain.submitAggregate(docId, rid, S, R, voteCount, sigma, attestations)`

链上校验要点：

- `voteCount` 一致性
- committee attestation 数量达到阈值
- Pedersen 一致性：`g^S * h^R == productCommitment[docId][rid]`

通过后保存：

- `aggregatedS[docId][rid]`
- `aggregatedR[docId][rid]`
- `aggregatedVoteCount[docId][rid]`

---

## 3.8 获取 `w_j` 并结束

查询链上：

- `S_j = aggregatedS(docId, rid)`
- `N_j = aggregatedVoteCount(docId, rid)`

计算：

- `w_j = S_j / N_j`

可选再请求文档：

```bash
curl http://127.0.0.1:8000/doc/doc1
```

输出建议：

- `doc_id`
- `doc_text`
- `S_j`
- `N_j`
- `w_j`

至此本轮流程结束。

---

## 4. 一次完整流程的最简执行方式

当前项目已经提供一键仿真入口，内部会按上述路径自动完成全部请求与链上调用：

```bash
cd /Users/chehaotian/TrustRAG/trustRAG
source .venv/bin/activate
PYTHONPATH=. python3 scripts/simulate.py
```

看到 `Contract verification success=True` 且打印 `Weight (S/vote_count)=...` 即表示完整流程成功结束。
