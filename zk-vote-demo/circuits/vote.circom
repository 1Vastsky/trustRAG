pragma circom 2.1.6;

// 你需要安装 circomlib(circom 版本)，然后根据实际路径调整 include
include "node_modules/circomlib/circuits/poseidon.circom";
include "node_modules/circomlib/circuits/comparators.circom";

// 简单的 Poseidon Merkle 树成员证明
template MerkleMembership(depth) {
    // 这里的 root 只是子电路的输入，在顶层 main 里决定是否 public
    signal input root;

    // “私有”输入：circom2 里直接写 signal input 即可
    signal input leaf;
    signal input pathElements[depth];
    signal input pathIndex[depth]; // 0 / 1

    component hashers[depth];
    signal cur[depth + 1];
    signal left[depth];
    signal right[depth];
    signal leftDiff[depth];
    signal rightDiff[depth];

    cur[0] <== leaf;

    for (var i = 0; i < depth; i++) {
        // pathIndex 必须是 0/1
        pathIndex[i] * (pathIndex[i] - 1) === 0;
        hashers[i] = Poseidon(2);

        // pathIndex[i] == 0: (cur, sibling)
        // pathIndex[i] == 1: (sibling, cur)
        leftDiff[i] <== pathElements[i] - cur[i];
        rightDiff[i] <== cur[i] - pathElements[i];

        left[i] <== cur[i] + pathIndex[i] * leftDiff[i];
        right[i] <== pathElements[i] + pathIndex[i] * rightDiff[i];

        hashers[i].inputs[0] <== left[i];
        hashers[i].inputs[1] <== right[i];

        cur[i + 1] <== hashers[i].out;
    }

    // 约束根
    root === cur[depth];
}

// 源链 Vote 电路：membership + nullifier + commitment + range
template VoteCircuit(depth) {
    // ------------ 公共输入（在 main 里设为 public） ------------
    signal input Root_reg;     // 成员 Merkle root
    signal input Com_i;        // 承诺（这里用 Poseidon）
    signal input Null_i;       // nullifier = Poseidon(sk, rid)
    signal input rid;          // round id
    signal input S_max;        // 最大得分

    // ------------ 私有输入（witness） ------------
    signal input s_i;             // 投票得分
    signal input r_i;             // 承诺随机数
    signal input sk_i;            // 成员 secret key
    signal input leaf;            // 叶子（比如成员 pk 的哈希）
    signal input pathElements[depth];
    signal input pathIndex[depth];

    // -------- (1) 成员资格证明：Merkle membership --------
    component mm = MerkleMembership(depth);
    mm.root <== Root_reg;
    mm.leaf <== leaf;

    for (var i = 0; i < depth; i++) {
        mm.pathElements[i] <== pathElements[i];
        mm.pathIndex[i]    <== pathIndex[i];
    }

    // -------- (2) nullifier = Poseidon(sk_i, rid) --------
    component poseNull = Poseidon(2);
    poseNull.inputs[0] <== sk_i;
    poseNull.inputs[1] <== rid;
    Null_i === poseNull.out;

    // -------- (3) 承诺：这里用 Poseidon(s_i, r_i) 代替 Pedersen --------
    component poseCom = Poseidon(2);
    poseCom.inputs[0] <== s_i;
    poseCom.inputs[1] <== r_i;
    Com_i === poseCom.out;

    // -------- (4) range check: 0 <= s_i <= S_max --------
    // 使用 LessThan：检查 s_i < S_max + 1
    // 要求 S_max < 2^n
    component lt = LessThan(16); // 16 bit，按需调大
    lt.in[0] <== s_i;
    lt.in[1] <== S_max + 1;
    lt.out === 1;

    // 限制 S_max 也处于 16 bit，避免溢出
    component sMaxRange = LessThan(16);
    sMaxRange.in[0] <== S_max;
    sMaxRange.in[1] <== 1 << 16;
    sMaxRange.out === 1;
}

// 主电路
template Main(depth) {
    // 顶层的输入
    signal input Root_reg;
    signal input Com_i;
    signal input Null_i;
    signal input rid;
    signal input S_max;
    signal input doc_id;    // 公共输入，标识这条 vote 评分的是哪一个文档


    signal input s_i;
    signal input r_i;
    signal input sk_i;
    signal input leaf;
    signal input pathElements[depth];
    signal input pathIndex[depth];

    component vote = VoteCircuit(depth);

    // 直接透传所有输入
    vote.Root_reg <== Root_reg;
    vote.Com_i    <== Com_i;
    vote.Null_i   <== Null_i;
    vote.rid      <== rid;
    vote.S_max    <== S_max;

    vote.s_i      <== s_i;
    vote.r_i      <== r_i;
    vote.sk_i     <== sk_i;
    vote.leaf     <== leaf;

    for (var i = 0; i < depth; i++) {
        vote.pathElements[i] <== pathElements[i];
        vote.pathIndex[i]    <== pathIndex[i];
    }
}

// 在这里声明哪些输入是 public 的
component main {public [Root_reg, Com_i, Null_i, rid, S_max, doc_id]} = Main(8);
// 想调节 Merkle 深度，把 8 改成别的数即可，比如 16
