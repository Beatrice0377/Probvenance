# R4 Measurement Execution Contract

```text
R4 MEASUREMENT EXECUTION CONTRACT: FROZEN

R4 OVERALL:                       NOT FULLY FROZEN
FORMAL R4 EXECUTION:              NOT AUTHORIZED
formal_execution_authorized:      false
```

```text
artifact_type : r4-measurement-execution-contract
version       : 1
status        : FROZEN
fingerprint_version : 1
measurement_contract_fingerprint :
  7b126d300e774cb44d2c47fcb12513865d03c2b08ffd03a5ce409b2ea976e1e5
```

本文件冻结 **R4 正式 measurement execution contract**：每 `model × population × item`
恰好 **2 次 model forward**（1 CAT + 1 designated-only OVR）。

它 **不是** 科学结论，**不是** model / population / procedure / predictor 选择，
**不是** formal R4 execution authorization。

权威 JSON：`experiments/calibration_transport/R4_MEASUREMENT_EXECUTION_CONTRACT.json`
（sha256 `c9d61ed3011a3d42c1455c8e6ff1c724d80a5ceebc2f507992e371d661e15e52`）。

---

## 1. Fixed-event semantics（frozen）

```text
designated candidate : D_i
ground truth         : GT_i
fixed event          : Y_i = 1[D_i = GT_i]
measured quantity    : P(D_i correct)
```

```text
CAT 测量 restricted categorical probability assigned to the frozen D_i
OVR 测量 independent binary proposition probability that D_i is correct
```

```text
winner-event redefinition : FORBIDDEN
```

Anchor（population layer 已冻结）：

```text
anchor_protocol_id      = r4-fixed-event-anchor-deterministic-source-index-hash
anchor_protocol_version = 1
anchor_index = int(fingerprint({ anchor_protocol_id, anchor_protocol_version,
                                 dataset_id, dataset_revision,
                                 source_split, source_row_index })[:16], 16) % 4
```

禁止 anchor 输入：

```text
ground truth / label / cop / question text / candidate text /
model output / measurement score / CAT score / OVR score
```

---

## 2. Measurement call contract（frozen）

```text
measurement_call_contract_id = r4-fixed-event-two-forward-measurement
version                      = 1

cat_forwards_per_item   = 1
ovr_forwards_per_item   = 1
total_forwards_per_item = 2
ovr_scope               = designated-candidate-only
unit                    = model × population × item
```

这是 formal required call count。

---

## 3. CAT call semantics

```text
1 CAT forward
prompt 包含 question/context + all four ordered candidates
verbalizers: A / B / C / D
  exact continuation
  exactly one token each
  four distinct token ids
从同一个 next-token logits vector 取 A/B/C/D 四个 logits
restricted softmax over exactly those four
S_CAT_i = restricted-softmax probability assigned to frozen D_i
```

```text
1 CAT forward != 4 CAT calls
```

anchor 只决定“记录哪一个 restricted probability 为 `anchor_score`”；
prompt 仍然包含全部四个 candidate。

---

## 4. OVR call semantics

```text
1 OVR forward per item
ONE independent binary proposition for the frozen designated candidate D_i
prompt 只包含 question/context + designated candidate D_i
不得包含其它三个 candidate descriptions
verbalizers: yes / no
  exact continuation
  exactly one token each
  two distinct token ids
从同一个 next-token logits vector 取 yes/no 两个 logits
restricted softmax over yes/no
S_OVR_i = p_true(D_i)
```

---

## 5. Why the R3 1 + 4 execution contract is NOT inherited

```text
R3 historical execution : 1 CAT + 4 independent OVR judgments per item
R3 role                 : R3 raw-evidence / winner-diagnostic execution contract
R4 decision             : DO NOT inherit 4 OVR calls per item
non-designated candidates : NO formal OVR forward
```

原因：

```text
R4 calibration-transport estimand 是外部冻结事件 Y_i = 1[D_i = GT_i]；
CAT 与 OVR 都测量 P(D_i correct)；
不需要重新构造 OVR winner。
```

R3 历史 contract 仅作为 provenance 记录：

```text
cat_forwards_per_item = 1 ; ovr_forwards_per_item = 4 ; total = 5
authority: experiments/calibration_transport/run_r3_measurements.py:5, :326, :361-362
```

---

## 6. R4 winner-diagnostic status（frozen）

```text
R4 formal confirmatory protocol 不包含 four-candidate OVR native-winner diagnostic
禁止为 OVR winner / winner agreement 增加三次 OVR calls
R3 historical diagnostics 保持 UNTOUCHED
```

---

## 7. Exact R4 verbalizer table（frozen）

| model key | repo_id | revision | CAT A/B/C/D | yes | no | adapter |
|---|---|---|---|---|---|---|
| olmo-3-7b-instruct | `allenai/Olmo-3-7B-Instruct` | `6e5971d9eba42665f5bd5a0fcf047f299ce1dccc` | 32/33/34/35 | 9891 | 2201 | transformers_backend |
| falcon-h1-7b-instruct | `tiiuae/Falcon-H1-7B-Instruct` | `41e72f27effbab80cd45b6e884688452253a3686` | 1068/1069/1070/1071 | 5763 | 3257 | transformers_backend |
| granite-4-0-h-tiny | `ibm-granite/granite-4.0-h-tiny` | `791e0d3d28c86e106c9b6e0b4cecdee0375b6124` | 32/33/34/35 | 9891 | 2201 | transformers_backend |
| qwen3-5-9b | `Qwen/Qwen3.5-9B` | `c202236235762e1c871ad0ccb60c8ee5ba337b9a` | 32/33/34/35 | 9405 | 2083 | qwen35_text |
| minicpm5-2b | `openbmb/MiniCPM5-2B` | `12a3808a956f869c767195e9266b59c4d21d92e2` | 54/55/56/57 | 15876 | 3707 | transformers_backend |
| qwen3-5-2b | `Qwen/Qwen3.5-2B` | `15852e8c16360a2fea060d615a32b45270f8a8fc` | 32/33/34/35 | 9405 | 2083 | qwen35_text |

```text
任一 tokenizer 现在产生不同 identity -> STOP / VERBALIZER_IDENTITY_DRIFT
任一 exact verbalizer 不是单 token   -> STOP / MEASUREMENT_INTERFACE_DRIFT
```

---

## 8. No verbalizer fallback（frozen）

绝对禁止：

```text
leading-space fallback
uppercase / lowercase fallback
multi-token fallback
generation
string-search over generated text
tokenizer monkey patch
```

---

## 9. Failure handling（frozen）

```text
每个 item 的两次 formal calls 是 independent attempt
CAT failure 不 suppress OVR attempt
OVR failure 不 retroactively invalidate CAT evidence
planned deterministic forward count 仍为 2 per attempted item
```

禁止：

```text
retry / fallback verbalizer / row substitution / fresh anchor / fresh candidate
```

downstream paired completeness 仍要求两者均 `SCORED`。

---

## 10. Model runtime（frozen）

```text
batch size       = 1
dtype            = bfloat16
eval()           = true
inference_mode() = true
device           = cuda:0
enable_thinking  = False
trust_remote_code = False
```

禁止：

```text
quantization / vLLM / tensor parallel / multi-GPU / CPU offload / compile / generation
```

Qwen3.5：existing `Qwen35TextBackend` path **AS-IS**。

---

## 11. Offline / local model policy（frozen）

```text
local_files_only = True
formal run 时禁止自动下载模型
cache 缺失 -> STOP / MODEL_CACHE_MISSING
```

---

## 12. Raw-evidence contract（frozen）

每个 artifact 覆盖一个 `model × population`，包含该组合的 required frozen TRAIN union + TEST。

每 row 至少：

```text
item_id
source split
source row identity / index
population identity
population manifest identity
anchor D_i
ground-truth candidate identity GT_i
Y_i = 1[D_i = GT_i]
CAT block
OVR block
```

CAT block 至少：

```text
status
anchor_score
restricted candidate probabilities 或 exact score provenance
verbalizer token ids
top-token diagnostic
source-record fingerprint
```

若存四个 candidate restricted scores，其和必须 ~1。
fixed-event analysis 只消费 `anchor_score`。

OVR block 只记录 designated candidate：

```text
designated_candidate = D_i
status
probability_true
probability_false
yes_token_id
no_token_id
source-record fingerprint
```

不得要求：

```text
four candidate OVR table / OVR winner
```

---

## 13. Paired completeness gate（frozen）

Calibration fitting / TEST inference 只能消费：

```text
CAT = SCORED AND OVR = SCORED
```

for every required frozen row。

任何 missing：

```text
affected model × population block = INCOMPLETE
```

禁止：

```text
drop row / replace row / use only successful pairs
```

---

## 14. Required execution grid（frozen）

| grid | models | TRAIN/model | TEST/model | rows/model | model×item rows |
|---|---|---|---|---|---|
| MMLU current-generation | 4 | 456 | 1140 | 1596 | 6384 |
| HellaSwag current-generation | 4 | 912 (N912 union) | 10042 | 10954 | 43816 |
| HellaSwag legacy | 2 | 456 | 10042 | 10498 | 20996 |
| MedMCQA current-generation | 4 | 912 (N912 union) | 4162 | 5074 | 20296 |
| MedMCQA legacy | 2 | 456 | 4162 | 4618 | 9236 |
| R3 legacy MMLU | — | — | — | — | 0 (FROZEN_EXISTING, DO_NOT_RERUN) |

---

## 15. Exact workload arithmetic（frozen）

```text
required_unique_model_item_rows = 100728
required_cat_forwards           = 100728
required_ovr_forwards           = 100728
required_total_forwards         = 201456
```

primary-only audit：

```text
N456-only unique model×item rows = 97080
corresponding forwards           = 194160
```

N912 extension（current-generation only）：

```text
456 extension rows × 4 current models × 2 populations = 3648 unique model×item rows
additional forwards = 7296

97080 + 3648 = 100728
194160 + 7296 = 201456
```

---

## 16. N912 nested reuse（frozen）

```text
current-generation HellaSwag raw measurement TRAIN union = 912
current-generation MedMCQA   raw measurement TRAIN union = 912
PRIMARY FIT        consumes selected N456 subset
N912 robustness    consumes full N912
raw scores         measured once, reused
```

---

## 17. Legacy N912 exclusion（frozen）

```text
legacy HellaSwag / MedMCQA required TRAIN = N456
legacy N912 = NOT REQUIRED / NOT MEASURED IN THE FORMAL R4 PLAN
```

这样 formal workload 不包含 optional undeclared experiment。

---

## 18. Rejected previous workload numbers

早先 candidate report 曾给出：

```text
104376 model×item measurements
521880 inherited R3-style calls
```

它们 **NOT AUTHORITATIVE**。原因：

```text
1. inherited 5-call/item R3 contract 不是 R4 contract
2. nested N912 必须 reuse N456 raw measurement rows
3. required N912 robustness 只适用于 current-generation panel，不是 legacy secondary cells
```

```text
scientific estimand changes = NONE
```

---

## 19. Non-claims

```text
本 contract 是 measurement-execution contract，不是科学结论
不是 formal R4 execution authorization
不选择 model / population / procedure / predictor
不读取任何真实 study row / model logit / calibration fit / metric
只冻结 R4 measurement call contract
```
