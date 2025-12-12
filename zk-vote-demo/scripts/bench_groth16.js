// scripts/bench_groth16.js
const fs = require("fs");
const path = require("path");
const { performance } = require("perf_hooks");
const snarkjs = require("snarkjs");
const circomlibjs = require("circomlibjs"); // 用于 Poseidon

// 这里要和 vote.circom 里的 depth 一致
const MERKLE_DEPTH = 8;

async function buildInput() {
  const poseidon = await circomlibjs.buildPoseidon();
  const F = poseidon.F;


  const leaf = 123n;
  const sk_i = 456n;
  const rid = 789n;
  const s_i = 7n;   // score
  const r_i = 11n;  // commitment randomness
  const S_max = 10n;
  const doc_id = 12345n; 


  // Merkle 路径：全部 sibling = 0，pathIndex = 0
  const pathElements = Array(MERKLE_DEPTH).fill(0n);
  const pathIndex = Array(MERKLE_DEPTH).fill(0);

  // 用同样的 Poseidon 规则构造 root
  let cur = leaf;
  for (let i = 0; i < MERKLE_DEPTH; i++) {
    const left = cur;
    const right = pathElements[i];
    cur = F.toObject(poseidon([left, right]));
  }
  const Root_reg = cur;

  // Nullifier = Poseidon(sk_i, rid)
  const Null_i = F.toObject(poseidon([sk_i, rid]));

  // Commitment = Poseidon(s_i, r_i)
  const Com_i = F.toObject(poseidon([s_i, r_i]));

  // 构造 witness 输入对象（字段名要和 circom 电路里的 signal input 对上）
  const input = {
    Root_reg: Root_reg.toString(),
    Com_i: Com_i.toString(),
    Null_i: Null_i.toString(),
    rid: rid.toString(),
    S_max: S_max.toString(),
    doc_id: doc_id.toString(),
    s_i: s_i.toString(),
    r_i: r_i.toString(),
    sk_i: sk_i.toString(),
    leaf: leaf.toString(),
    pathElements: pathElements.map((x) => x.toString()),
    pathIndex: pathIndex,
  };

  return input;
}

async function main() {
  const wasmPath = path.join(__dirname, "..", "build", "vote_js", "vote.wasm");
  const zkeyPath = path.join(__dirname, "..", "build", "vote_final.zkey");

  if (!fs.existsSync(wasmPath) || !fs.existsSync(zkeyPath)) {
    console.error("❌ 找不到 vote.wasm 或 vote_final.zkey，请先完成编译和 setup。");
    process.exit(1);
  }

  const input = await buildInput();

  const runs = 10; // 连续跑多少次，按需调整
  let times = [];

  console.log("Groth16 证明生成时间基准测试 (runs =", runs, ")");

  // 先做一次 warm-up
  console.log("⚙️  Warm-up...");
  await snarkjs.groth16.fullProve(input, wasmPath, zkeyPath);

  for (let i = 0; i < runs; i++) {
    const t0 = performance.now();
    const { proof, publicSignals } = await snarkjs.groth16.fullProve(
      input,
      wasmPath,
      zkeyPath
    );
    const t1 = performance.now();
    const dt = t1 - t0;
    times.push(dt);
    console.log(`Run #${i + 1}: ${dt.toFixed(2)} ms`);
  }

  const avg =
    times.reduce((acc, x) => acc + x, 0) / (times.length || 1);
  console.log("=======================================");
  console.log(
    `Groth16 fullProve 平均时间: ${avg.toFixed(2)} ms`
  );
  console.log("=======================================");
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
