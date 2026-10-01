# R4 Formal Measurement Runbook

```text
status = OPERATIONAL RUNBOOK
FORMAL R4 EXECUTION = NOT YET AUTHORIZED
```

本文件是 formal R4 measurement 的机械运行手册：cell registry、staging root、命名、
workload、CLI、以及执行边界。

本文件 **不是** scientific artifact，不参与任何 evidence fingerprint。

---

## 1. 授权状态

```text
R4 MEASUREMENT EXECUTION CONTRACT   = FROZEN
R4 FINAL INTEGRATED PROTOCOL        = FROZEN
R4 EXECUTION MANIFEST               = FROZEN

FORMAL R4 EXECUTION                 = NOT YET AUTHORIZED
```

在 human / ChatGPT 完成 review → normal push → verify remote SHA → **explicit
execution authorization** 之前，**不得** 对任何真实 population 调用 runner。

---

## 2. Formal cell registry（16 cells）

### MMLU current — 4 cells

```text
olmo-3-7b-instruct      × mmlu
falcon-h1-7b-instruct   × mmlu
granite-4-0-h-tiny      × mmlu
qwen3-5-9b              × mmlu
```

### HellaSwag — 6 cells

```text
olmo-3-7b-instruct      × hellaswag
falcon-h1-7b-instruct   × hellaswag
granite-4-0-h-tiny      × hellaswag
qwen3-5-9b              × hellaswag

minicpm5-2b             × hellaswag      （legacy secondary）
qwen3-5-2b              × hellaswag      （legacy secondary）
```

### MedMCQA — 6 cells

```text
olmo-3-7b-instruct      × medmcqa
falcon-h1-7b-instruct   × medmcqa
granite-4-0-h-tiny      × medmcqa
qwen3-5-9b              × medmcqa

minicpm5-2b             × medmcqa        （legacy secondary）
qwen3-5-2b              × medmcqa        （legacy secondary）
```

**禁止**：

```text
minicpm5-2b × mmlu      → R3 frozen legacy MMLU = FROZEN_EXISTING / DO_NOT_RERUN
qwen3-5-2b  × mmlu      → R3 frozen legacy MMLU = FROZEN_EXISTING / DO_NOT_RERUN
```

---

## 3. Population identity

| population key | population_id | dataset_id | revision | train / test |
|---|---|---|---|---|
| `mmlu` | `r4-mmlu-57-subject` | `cais/mmlu` | `c30699e8356da336a370243923dbaf21066bb9fe` | 456 / 1140 |
| `hellaswag` | `r4-hellaswag-activity-primary` | `Rowan/hellaswag` | `218ec52e09a7e7462a5400043bb9a69a41d06b76` | 456 / 10042 |
| `medmcqa` | `r4-medmcqa-subject-primary` | `openlifescienceai/medmcqa` | `91c6572c454088bf71b679ad90aa8dffcd0d5868` | 456 / 4162 |

manifest fingerprints：

```text
mmlu       40cc9753a711314ff3b25ed6e234d0cbda11f3f60cd87f1d3915195a3d1780b8
hellaswag  5c45043ba4f0ec436c16dcf494ff26be435c7857244bcbefa321d1678129c400
medmcqa    4a4718438d46ab1ba27c59ca46806756ffb62efa05e6103981dffec4dc48c218
```

nested N912 robustness（**不 rescue** primary N456）：

```text
hellaswag robustness912  6817496f227d9cd57759bf55489cbf8a1dc4dfd27db0ae551e9223d21d02a096   912 / 10042
medmcqa   robustness912  e48c37293f196e16d8fba42e7fc255e4ac2e77f81c270ed6f71320981968af12   912 / 4162
```

---

## 4. Exact workload

```text
required_unique_model_item_rows = 100,728

CAT logical forwards = 100,728
OVR logical forwards = 100,728

planned logical forwards = 201,456
```

分解：

```text
MMLU current    4 × (456 + 1140)                     =  6,384
Hella current   4 × (456 + 10042) + 4 × 456 (N912)   = 43,816
Hella legacy    2 × (456 + 10042)                    = 20,996
Med current     4 × (456 + 4162)  + 4 × 456 (N912)   = 20,296
Med legacy      2 × (456 + 4162)                     =  9,236
                                                total = 100,728
```

crash recovery 时 physical attempts 可能超过 planned logical forwards，但只能通过
**已记录** 的 UNCOMMITTED RECOVERY REPLAY 超出（见 `R4_MEASUREMENT_RESUME_POLICY.md`）。

---

## 5. Output root 与命名

staging root：

```text
/root/rivermind-data/r4-formal-measurements
```

每 cell 目录：

```text
<staging_root>/<model_key>__<population_id>/
  cell_identity.json
  runtime_provenance.json
  LOCK
  operations.json
  rows/<item_id>.json
  raw-evidence.json          ← final artifact
```

final artifact 的 deterministic 定位：

```text
<staging_root>/<model_key>__<population_id>/raw-evidence.json
```

**不得** 以 outcome 命名任何文件。formal output **不得** 写入 Git repo。

---

## 6. CLI

```bash
python experiments/calibration_transport/run_r4_measurements.py \
  --model-role <model_key> \
  --population <population_key> \
  --staging-root /root/rivermind-data/r4-formal-measurements \
  --resume \
  --device cuda:0
```

offline 环境（formal measurement 强制）：

```text
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
HF_DATASETS_OFFLINE=1
```

synthetic-only preflight（唯一允许在授权前运行的路径）：

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 \
python experiments/calibration_transport/run_r4_measurements.py \
  --synthetic-preflight --device cuda:0
```

---

## 7. 每个 cell 的 preconditions

```text
cell identity header exact match（或首次写入）
runtime provenance exact match（或首次写入）
model cache 在 exact revision 可 local-only resolve
offline flags == 1
environment contract PASS
verbalizer ids 与 frozen registry 一致
single-writer lock 可获取
```

任一不符 → STOP（见 resume policy 的 fail-closed 列表）。

---

## 8. 每 cell 完成判据

```text
every expected frozen item has exactly one valid committed row
→ validate_raw_evidence PASS
→ evidence_fingerprint 计算
→ atomic publish final artifact
→ cell COMPLETE
```

已有 valid final artifact 且 identity / fingerprint 匹配：

```text
ALREADY_COMPLETE（0 new forwards）
```

---

## 9. 执行边界

```text
single worker per cell              （MULTI-WORKER = NOT AUTHORIZED）
single GPU cuda:0
dtype bfloat16
no CPU offload / no tensor parallel
```

禁止：multi-worker、multi-GPU、parallel cell mutation。

---

## 10. 已接受的 known fail-closed risks

### B-beta endpoint

```text
KNOWN ACCEPTED FAIL-CLOSED RISK:

B-beta primary N456 TRAIN 若出现 exact raw score 0 or 1
  => BETA_FIT_INELIGIBLE_ENDPOINT
  => dependent B-beta secondary extension result may be INCOMPLETE
  => no clipping / no fallback / no N912 rescue of primary N456 status
```

frozen beta semantics 不变。

### Exact LogLoss

```text
exact LogLoss 是 SECONDARY
calibrated q == 0/1 被保留
opposite realized label 可能产生 +infinity
+infinity 是合法的 frozen secondary outcome state
no epsilon clipping / no cap / no row deletion
```

只记录 possibility，不预先声称 large-scale infinity 一定发生。

### Isotonic N456

```text
isotonic sample-size sensitivity 是 predeclared nested N912 robustness 的已知理由
N456 仍是 primary；N912 不能 rescue N456
```

---

## 11. Predictor held-out accounting

```text
R4 primary units:                     4 models × 3 populations × 2 directions = 24
predictor development / continuity:   4 models × MMLU × 2                     =  8
primary held-out predictor validation:4 models × {Hella, Med} × 2             = 16
legacy Hella/Med:                     8 secondary lineage units
```

理由：MMLU 参与了 predictor idea development，因此 **不是** independent validation。

---

## 12. Status

```text
R4 FORMAL MEASUREMENT RUNBOOK = DEFINED
FORMAL R4 EXECUTION = NOT YET AUTHORIZED
```
