# R4 Measurement Implementation Provenance Closure (Candidate)

```text
status : IMPLEMENTATION PROVENANCE CLOSURE CANDIDATE
```

本文件是 **candidate**，不是 human final closure。它记录 R4 formal measurement
implementation 的可审计 provenance。

本任务期间 **没有** 产生或读取任何正式 study outcome：

```text
NO real R4 CAT probability
NO real R4 OVR probability
NO real model logits on study rows
NO calibration fit
NO Brier / LogLoss
NO transport outcome
NO predictor value / correlation
NO official R4 result
```

---

## 1. Artifact hash closure

| artifact | path | lines | sha256 |
|---|---|---|---|
| measurement contract (JSON) | `experiments/calibration_transport/R4_MEASUREMENT_EXECUTION_CONTRACT.json` | 479 | `c9d61ed3011a3d42c1455c8e6ff1c724d80a5ceebc2f507992e371d661e15e52` |
| measurement contract (MD) | `experiments/calibration_transport/R4_MEASUREMENT_EXECUTION_CONTRACT.md` | 418 | `7beb1e36192a286ea8410fe01111c746d74ea55130601a154d2830840644e401` |
| environment contract | `experiments/calibration_transport/R4_MEASUREMENT_EXECUTION_ENVIRONMENT.md` | 130 | `e794bddef9c909a7502fc6badd04f4805e350464aee0a34efb1fbacc858b01fd` |
| raw-evidence layer | `experiments/calibration_transport/r4_raw_evidence.py` | 452 | `12f1f037f0400dc7cbbf73e9f014e2ab735a341690e0431273281bdb6afe7dac` |
| measurement runner | `experiments/calibration_transport/run_r4_measurements.py` | 1028 | `2f6d59a06b1dbe869dfd1ec29e174d4246819e2d07ccb681db9fd6c681cc0601` |
| measurement tests | `tests/test_r4_measurements.py` | 1032 | `f36ddc56c11ab2587a8c74fd09e6db1345ffd3a2d3871334631a919bee337066` |
| engineering doc | `experiments/calibration_transport/R4_MEASUREMENT_IMPLEMENTATION_ENGINEERING.md` | 451 | `07375014742efc8a684db69e0f385d8c95830e42e792d9afbc7e11561548285f` |

```text
measurement_contract_fingerprint = 7b126d300e774cb44d2c47fcb12513865d03c2b08ffd03a5ce409b2ea976e1e5
measurement_contract_status      = FROZEN
```

---

## 2. Synthetic unit tests

```text
python -m py_compile experiments/calibration_transport/r4_raw_evidence.py \
    experiments/calibration_transport/run_r4_measurements.py \
    tests/test_r4_measurements.py          -> PASS
ruff check (同上三个文件)                   -> PASS
pytest -q tests/test_r4_measurements.py    -> 71 passed
```

覆盖：

```text
CAT probability extraction
OVR probability extraction
fixed D_i
all anchor positions (0/1/2/3)
exactly two calls per item
failure independence (CAT-first, OVR-second)
non-designated OVR guard
verbalizer id verification
evidence serialization
evidence validation
population registry
legacy-MMLU domain rejection
N456/N912 row registry
determinism
frozen-authority / amended-candidate consistency
```

配套 R4 suites：

```text
tests/test_r4_measurements.py tests/test_r4_predictor.py
tests/test_r4_inference.py tests/test_r4_calibration_families.py
-> 308 passed
```

全仓：

```text
pytest -q -p no:randomly -> exit 0 (2233 collected)
```

---

## 3. Real-model synthetic preflight

synthetic-only（无 frozen study row，无 MMLU/HellaSwag/MedMCQA 题目）。

```text
python experiments/calibration_transport/run_r4_measurements.py \
    --synthetic-preflight --device cuda:0
```

| model | class | adapter | CAT ids | yes / no | forwards | status |
|---|---|---|---|---|---|---|
| olmo-3-7b-instruct | `Olmo3ForCausalLM` | transformers_backend | 32/33/34/35 | 9891 / 2201 | 2 | PASS |
| falcon-h1-7b-instruct | `FalconH1ForCausalLM` | transformers_backend | 1068/1069/1070/1071 | 5763 / 3257 | 2 | PASS |
| granite-4-0-h-tiny | `GraniteMoeHybridForCausalLM` | transformers_backend | 32/33/34/35 | 9891 / 2201 | 2 | PASS |
| qwen3-5-9b | `Qwen3_5ForCausalLM` | qwen35_text | 32/33/34/35 | 9405 / 2083 | 2 | PASS |
| minicpm5-2b | — | transformers_backend | — | — | 0 | BLOCKED (`R4ModelCacheMissing`) |
| qwen3-5-2b | — | qwen35_text | — | — | 0 | BLOCKED (`R4ModelCacheMissing`) |

每个 PASS 模型：

```text
exact revision resolved
actual class / tokenizer class recorded
verbalizer ids == frozen registry
CAT finite normalized probability
OVR finite normalized probability
forward count = 2
```

### 3.1 Legacy cache blocker（operational）

```text
/root/rivermind-data/hf-cache/hub/models--openbmb--MiniCPM5-2B/snapshots   -> absent
/root/rivermind-data/hf-cache/hub/models--Qwen--Qwen3.5-2B/snapshots       -> absent
```

`/root/rivermind-data/hf-cache/hub` 只有 4 个 snapshot（Olmo、Falcon、
granite-4.0-h-tiny、Qwen3.5-9B）。本任务禁止下载（§12），也禁止跳过模型后宣称
ready（§43），因此：

```text
MEASUREMENT_PREFLIGHT_BLOCKER = legacy model cache missing (2/6)
```

这是 **operational** blocker，不是 implementation failure，也不是科学变更。

---

## 4. Raw-evidence determinism

相同 fully-synthetic input，两个独立进程：

```text
SYNTHETIC_R4_RAW_EVIDENCE_STATE_SHA256 = 2c3a714571d6a2b6d6064fe14843af61586f14c4fee22bc0384a71b89fc2b17d
evidence_fingerprint                    = 7fa1723d5508f4bf499b467e51366c1dfe54c8f1af148643caf37d5e86750ef5
planned rows = 4 / CAT forwards = 4 / OVR forwards = 4 / total forwards = 8
```

canonical evidence bytes 与 evidence fingerprint 完全一致。

实现依据：wall-clock timing 被排除出 fingerprinted artifact（只在 stderr 报告）。

---

## 5. Formal outcome firewall

```text
formal study forward        : NOT RUN
real CAT / OVR probability  : NOT PRODUCED / NOT READ
calibration fit             : NOT RUN
Brier / LogLoss             : NOT COMPUTED
transport outcome           : NOT COMPUTED
predictor value/correlation : NOT COMPUTED
official R4 result          : NOT PRODUCED
```

synthetic preflight 只报告 engineering facts，不将概率数值作为科学结论保存或讨论。

---

## 6. Terminal status

```text
R4 MEASUREMENT IMPLEMENTATION PROVENANCE CLOSURE CANDIDATE = PASS
```

含义限定：

```text
- measurement contract FROZEN
- runner + raw-evidence + tests implemented and green
- determinism verified
- 4/6 models preflighted PASS with 2 forwards each
- 2/6 legacy models BLOCKED on a missing local cache (operational)
```

```text
NOT human final closure
NOT an execution authorization
NOT a readiness PASS
```
