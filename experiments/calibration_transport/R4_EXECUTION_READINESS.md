# R4 Execution Readiness

```text
status = BLOCKED
```

R4 的 scientific protocol 与 measurement implementation 已经 closure；但 **model
cache 不完整**，因此 **不能** 宣告 execution readiness PASS。

```text
R4 EXECUTION READINESS = BLOCKED

FORMAL R4 EXECUTION = NOT AUTHORIZED
```

---

## 1. Gate-by-gate audit

| # | gate | status | evidence |
|---|---|---|---|
| 1 | models closed | PASS | 6-model registry frozen（4 current + 2 legacy），exact revisions |
| 2 | population frozen | PASS | `R4_POPULATION_FREEZE.md`；4 manifests |
| 3 | fixed-event frozen | PASS | anchor protocol `r4-fixed-event-anchor-deterministic-source-index-hash` v1 |
| 4 | measurement contract frozen | PASS | `R4_MEASUREMENT_EXECUTION_CONTRACT.json` `7b126d30…` FROZEN |
| 5 | measurement runner engineering pass | PASS | 71 tests；determinism verified；preflight 4/6 PASS |
| 6 | calibration semantics frozen | PASS | `R4_CALIBRATION_FAMILY_FREEZE.md` |
| 7 | calibration implementation provenance closed | PASS | `R4_CALIBRATION_FAMILY_IMPLEMENTATION_ENGINEERING.md` |
| 8 | inference semantics frozen | PASS | `R4_INFERENCE_MULTIPLICITY_FREEZE.json` `dcbb7ac9…` |
| 9 | inference implementation provenance closed | PASS | `R4_INFERENCE_IMPLEMENTATION_PROVENANCE_CLOSURE.md` |
| 10 | predictor semantics frozen | PASS | `R4_PREDICTOR_FREEZE.json` `c856fcc1…` |
| 11 | predictor implementation provenance closed | PASS | `R4_PREDICTOR_IMPLEMENTATION_PROVENANCE_CLOSURE.md` |
| 12 | final protocol frozen | PASS | `R4_FINAL_PROTOCOL_FREEZE.json` `d1b56d70…` |
| 13 | execution manifest frozen | PASS | `R4_EXECUTION_MANIFEST_FREEZE.json` `f32381c5…` |
| 14 | environment compatible | **BLOCKED** | 2/6 required models absent from the local HF cache |
| 15 | worktree clean | PASS | see final report |
| 16 | all tests pass | PASS | full suite exit 0 |
| 17 | no outcomes accessed | PASS | outcome firewall intact |

---

## 2. The single blocker

```text
BLOCKER = legacy model cache missing
```

required by the frozen R4 grid but **absent** locally：

```text
openbmb/MiniCPM5-2B          @ 12a3808a956f869c767195e9266b59c4d21d92e2
Qwen/Qwen3.5-2B              @ 15852e8c16360a2fea060d615a32b45270f8a8fc
```

`/root/rivermind-data/hf-cache/hub` 现有 snapshot：

```text
models--allenai--Olmo-3-7B-Instruct
models--tiiuae--Falcon-H1-7B-Instruct
models--ibm-granite--granite-4.0-h-tiny
models--Qwen--Qwen3.5-9B
```

本任务禁止下载（§12）且禁止跳过模型后宣称 ready（§43），因此：

```text
MEASUREMENT_PREFLIGHT_BLOCKER = legacy model cache missing (2/6)
```

这是 **operational** blocker，不是 implementation failure，也不是科学变更。

---

## 3. What is already proven

```text
4/6 models preflighted with exactly 2 synthetic forwards each
  olmo-3-7b-instruct        PASS
  falcon-h1-7b-instruct     PASS
  granite-4-0-h-tiny        PASS
  qwen3-5-9b                PASS

exact revisions + model classes + verbalizer ids match the frozen registry
raw-evidence determinism verified (byte-identical across processes)
```

---

## 4. Required to lift the blocker

（human / ChatGPT 决定，不在本任务范围内）

```text
option 1: populate the local HF cache with the two legacy models at their
          exact frozen revisions, then re-run --synthetic-preflight
option 2: amend the frozen R4 execution plan to drop the legacy secondary cells
          (scientific decision, NOT an engineering decision)
```

本任务 **不** 执行其中任何一个。

---

## 5. Status

```text
R4 MEASUREMENT EXECUTION CONTRACT = FROZEN
R4 MEASUREMENT IMPLEMENTATION ENGINEERING = PASS
R4 MEASUREMENT IMPLEMENTATION PROVENANCE CLOSURE CANDIDATE = PASS
R4 FINAL INTEGRATED PROTOCOL = FROZEN
R4 EXECUTION MANIFEST = FROZEN

R4 EXECUTION READINESS = BLOCKED (legacy model cache missing)

FORMAL R4 EXECUTION = NOT YET AUTHORIZED
AWAITING EXPLICIT HUMAN / CHATGPT EXECUTION AUTHORIZATION
```
