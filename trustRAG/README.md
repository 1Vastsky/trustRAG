# TrustRAG

这是一个最小可运行的可验证去中心化 RAG 聚合 Demo，核心链路包括：

- Pedersen 承诺（投票隐藏）
- Shamir `(t, n)` 秘密分享（`s/r`）
- 委员会节点汇总 share（通过 SPDZ runner 接口）
- Python 侧阈值 BLS 聚合签名
- 链上聚合结果校验（承诺乘积一致性 + 委员会 attestation）

## 1. 环境要求

- macOS / Linux
- Python 3.9+
- Node.js 18+（建议）
- npm

## 2. 安装依赖

```bash
cd /Users/chehaotian/TrustRAG/trustRAG

# Python
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install fastapi uvicorn httpx pytest py-ecc web3 eth-account eth-abi eth-tester py-evm

# Node / Hardhat
npm install --cache .npm-cache
```

## 3. 启动文档后端（可选）

```bash
cd /Users/chehaotian/TrustRAG/trustRAG
source .venv/bin/activate
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

接口：

- `GET /docs`：返回 CSV 中全部文档
- `GET /doc/{doc_id}`：返回指定文档
- Swagger：`http://127.0.0.1:8000/api-docs`

## 3.1 启动委员会节点服务（可选）

```bash
cd /Users/chehaotian/TrustRAG/trustRAG
source .venv/bin/activate
PYTHONPATH=. python3 scripts/start_committee_nodes.py --n 4
```

默认会启动：

- 节点1：`http://127.0.0.1:9001`
- 节点2：`http://127.0.0.1:9002`
- 节点3：`http://127.0.0.1:9003`
- 节点4：`http://127.0.0.1:9004`

## 3.2 接口文档

### A. 文档服务（`backend.main`）

Base URL：`http://127.0.0.1:8000`  
Swagger：`/api-docs`

1. `GET /docs`

- 说明：返回所有文档（来源 `backend/docs.csv`）。
- 请求示例：

```bash
curl http://127.0.0.1:8000/docs
```

- 响应示例：

```json
{
  "docs": [
    {"doc_id": "doc1", "text": "Hello this is a demo document."},
    {"doc_id": "doc2", "text": "Another doc sentence."}
  ]
}
```

2. `GET /doc/{doc_id}`

- 说明：按 `doc_id` 查询文档。
- 路径参数：`doc_id`（文档 ID，如 `doc1`）。
- 请求示例：

```bash
curl http://127.0.0.1:8000/doc/doc1
```

- 成功响应示例（200）：

```json
{"doc_id":"doc1","text":"Hello this is a demo document."}
```

- 失败响应示例（404）：

```json
{"detail":"doc_id 'missing' not found"}
```

### B. 委员会节点服务（`backend.committee`）

Base URL（示例节点1）：`http://127.0.0.1:9001`  
Swagger（示例节点1）：`http://127.0.0.1:9001/api-docs`

1. `GET /health`

- 说明：检查节点存活状态。
- 请求示例：

```bash
curl http://127.0.0.1:9001/health
```

- 响应示例：

```json
{"status":"ok","node_id":"1"}
```

2. `POST /share`

- 说明：提交某投票人在该节点的 `s/r` share。
- 请求体：

```json
{
  "rid": 1,
  "doc_id": "doc1",
  "voter_id": "v1",
  "s_share": {"x": 1, "y": 123},
  "r_share": {"x": 1, "y": 456}
}
```

- 请求示例：

```bash
curl -X POST http://127.0.0.1:9001/share \
  -H "Content-Type: application/json" \
  -d '{"rid":1,"doc_id":"doc1","voter_id":"v1","s_share":{"x":1,"y":123},"r_share":{"x":1,"y":456}}'
```

- 响应示例：

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

3. `GET /shares/{rid}/{doc_id}`

- 说明：查看当前节点已存储 shares（调试用）。
- 请求示例：

```bash
curl http://127.0.0.1:9001/shares/1/doc1
```

- 响应示例：

```json
{
  "node_id": "1",
  "rid": 1,
  "doc_id": "doc1",
  "count": 1,
  "voter_ids": ["v1"],
  "shares": {
    "v1": {
      "s_share": {"x": 1, "y": 123},
      "r_share": {"x": 1, "y": 456}
    }
  }
}
```

4. `POST /trigger/{rid}/{doc_id}`

- 说明：触发该节点对本地 shares 做聚合，输出节点级 `(S_share, R_share)`。
- 请求示例：

```bash
curl -X POST http://127.0.0.1:9001/trigger/1/doc1
```

- 成功响应示例（有 shares）：

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

- 无数据响应示例：

```json
{
  "node_id": "1",
  "rid": 1,
  "doc_id": "doc1",
  "status": "no shares",
  "stored_count": 0
}
```

## 4. 运行测试

```bash
cd /Users/chehaotian/TrustRAG/trustRAG
source .venv/bin/activate
PYTHONPATH=. python3 -m pytest -q
```

## 5. 编译合约

```bash
cd /Users/chehaotian/TrustRAG/trustRAG
npx hardhat compile
```

## 6. 运行端到端仿真（推荐）

```bash
cd /Users/chehaotian/TrustRAG/trustRAG
source .venv/bin/activate
PYTHONPATH=. python3 scripts/simulate.py
```

成功时会输出类似结果：

- `Expected S=... , Expected R=...`
- `SPDZ output S=... , R=...`
- `Contract verification success=True`
- `Weight (S/vote_count)=...`
- `Doc doc1: ...`

## 7. 目录说明

- `backend/`：后端服务与密码学模块
- `contracts/`：Solidity 合约 `DataChain.sol`
- `mpc/`：SPDZ 程序与 runner 脚本
- `scripts/simulate.py`：完整本地仿真入口
- `test/`：单元测试

## 8. 说明与限制

- 为保持本地最小可运行，BLS 阈值验证在 Python 侧完成；链上校验委员会 ECDSA attestation。
- 当前 `mpc/run_spdz.sh` 为本地可运行的 runner 包装接口，可替换为真实 MP-SPDZ 执行流程。
- Demo 侧重“可验证聚合链路”，非生产级安全实现。
