# R4 Execution Readiness

```text
status = PASS
```

R4 的 scientific protocol、measurement implementation、以及 execution-side
operational hardening 已经全部 closure；**6/6 model cache 完整**且
**6/6 synthetic preflight PASS**。因此 execution readiness 可以宣告 PASS。

```text
R4 EXECUTION READINESS = PASS

FORMAL R4 EXECUTION = NOT YET AUTHORIZED
```

`NOT YET AUTHORIZED` 的原因 **不是** 技术 blocker，而是流程：

```text
本轮 operational hardening / readiness commit
尚未经 human / ChatGPT review
尚未 push 到 remote
```

review → normal push → remote SHA 核对 → explicit execution authorization
之后，才可以开始第一条 real study forward。

---

## 1. Gate-by-gate audit

| # | gate | status | evidence |
|---|---|---|---|
| 1 | models closed | PASS | 6-model registry frozen（4 current + 2 legacy），exact revisions |
| 2 | population frozen | PASS | `R4_POPULATION_FREEZE.md`；4 manifests |
| 3 | fixed-event frozen | PASS | anchor protocol `r4-fixed-event-anchor-deterministic-source-index-hash` v1 |
| 4 | measurement contract frozen | PASS | `R4_MEASUREMENT_EXECUTION_CONTRACT.json` `7b126d30…` FROZEN |
| 5 | measurement runner engineering pass | PASS | 87 tests（run twice，identical）；determinism verified |
| 6 | calibration semantics frozen | PASS | `R4_CALIBRATION_FAMILY_FREEZE.md` |
| 7 | calibration implementation provenance closed | PASS | `R4_CALIBRATION_FAMILY_IMPLEMENTATION_ENGINEERING.md` |
| 8 | inference semantics frozen | PASS | `R4_INFERENCE_MULTIPLICITY_FREEZE.json` `dcbb7ac9…` |
| 9 | inference implementation provenance closed | PASS | `R4_INFERENCE_IMPLEMENTATION_PROVENANCE_CLOSURE.md` |
| 10 | predictor semantics frozen | PASS | `R4_PREDICTOR_FREEZE.json` `c856fcc1…` |
| 11 | predictor implementation provenance closed | PASS | `R4_PREDICTOR_IMPLEMENTATION_PROVENANCE_CLOSURE.md` |
| 12 | final protocol frozen | PASS | `R4_FINAL_PROTOCOL_FREEZE.json` `d1b56d70…` |
| 13 | execution manifest frozen | PASS | `R4_EXECUTION_MANIFEST_FREEZE.json` `f32381c5…` |
| 14 | clone-instance revalidated | PASS | `R4_CLONE_INSTANCE_AUDIT.md` |
| 15 | environment compatible | PASS | 6/6 required models present at exact revisions |
| 16 | six-model synthetic preflight | PASS | 6/6 PASS；`R4_EXECUTION_READINESS_REVALIDATION.md` |
| 17 | crash-safe resume hardened | PASS | `R4_MEASUREMENT_RESUME_POLICY.md`；`R4_MEASUREMENT_OPERATIONAL_HARDENING.md` |
| 18 | single-writer / no-retry semantics | PASS | 16 crash-injection tests |
| 19 | all tests pass | PASS | full suite `2245 passed, 4 skipped`；exit 0 |
| 20 | worktree clean | PASS | see final report |
| 21 | no outcomes accessed | PASS | outcome firewall intact |

---

## 2. Model cache (was the single blocker)

上一版 readiness 的唯一 blocker 是：

```text
BLOCKER = legacy model cache missing (2/6)
```

现在已解除。`/root/rivermind-data/hf-cache/hub` 六个 snapshot 全部就位：

```text
models--allenai--Olmo-3-7B-Instruct       @ 6e5971d9eba42665f5bd5a0fcf047f299ce1dccc
models--tiiuae--Falcon-H1-7B-Instruct     @ 41e72f27effbab80cd45b6e884688452253a3686
models--ibm-granite--granite-4.0-h-tiny   @ 791e0d3d28c86e106c9b6e0b4cecdee0375b6124
models--Qwen--Qwen3.5-9B                  @ c202236235762e1c871ad0ccb60c8ee5ba337b9a
models--openbmb--MiniCPM5-2B              @ 12a3808a956f869c767195e9266b59c4d21d92e2
models--Qwen--Qwen3.5-2B                  @ 15852e8c16360a2fea060d615a32b45270f8a8fc
```

两个 legacy snapshot 按 human 决定（KEEP legacy secondary cells /
DO NOT revise frozen plan / COMPLETE exact pinned caches）补齐：

```text
openbmb/MiniCPM5-2B  model-00000-of-00001.safetensors
  size   5033557096
  sha256 14fb8e7f0a18d53d1f239773758bf581cee7e456a4523a54622c3a245b64402c

Qwen/Qwen3.5-2B      model.safetensors-00001-of-00001.safetensors
  size   4548221488
  sha256 aa33250c4fc64891ddfaba3a314fd9542ea371843c387178b425fbcc5ed680b1
```

两个 sha256 都与对应 pinned revision 的 tree metadata 中记录的
`lfs_sha256` 精确一致；无 `*.incomplete` 残留。

缓存补齐只改变了 **传输通道**（hf-mirror 限速，改用 gitcode 的
exact-revision 路径），**没有**改变任何 model id / revision / 文件内容。

---

## 3. What is now proven

```text
6/6 models preflighted with exactly 2 synthetic forwards each
  olmo-3-7b-instruct        PASS
  falcon-h1-7b-instruct     PASS
  granite-4-0-h-tiny        PASS
  qwen3-5-9b                PASS
  minicpm5-2b               PASS
  qwen3-5-2b                PASS

exact revisions + model classes + verbalizer ids match the frozen registry
raw-evidence determinism verified (byte-identical across processes)
crash-safe resume semantics verified (16 crash-injection tests)
```

---

## 4. Accepted known risks (fail-closed, no semantic change)

```text
B-beta primary N456 TRAIN 若出现 exact raw score 0 或 1
  => BETA_FIT_INELIGIBLE_ENDPOINT
  => dependent B-beta secondary extension result may be INCOMPLETE
  => no clipping / no fallback / no N912 rescue of primary N456 status

exact LogLoss 是 SECONDARY
  calibrated q == 0/1 被保留
  相反 realized label 可能产生 +infinity
  +infinity 是合法的 frozen secondary outcome state
  => no epsilon clipping / no cap / no row deletion

isotonic N456/N912
  N456 仍是 primary；N912 是 predeclared nested robustness
  N912 不能 rescue N456

multi-worker
  formal path = single worker per cell
  MULTI-WORKER = NOT AUTHORIZED
```

---

## 5. Status

```text
R4 MEASUREMENT EXECUTION CONTRACT = FROZEN
R4 MEASUREMENT IMPLEMENTATION ENGINEERING = PASS
R4 MEASUREMENT IMPLEMENTATION PROVENANCE CLOSURE CANDIDATE = PASS
R4 FINAL INTEGRATED PROTOCOL = FROZEN
R4 EXECUTION MANIFEST = FROZEN

R4 CLONE-INSTANCE REVALIDATION = PASS
R4 LEGACY MODEL CACHE = COMPLETE
R4 SIX-MODEL SYNTHETIC PREFLIGHT = 6/6 PASS
R4 MEASUREMENT CRASH-SAFE RESUME HARDENING = PASS

R4 EXECUTION READINESS = PASS

FORMAL R4 EXECUTION = NOT YET AUTHORIZED
AWAITING HUMAN / CHATGPT FINAL REVIEW, REMOTE PUSH,
AND EXPLICIT EXECUTION AUTHORIZATION
```
