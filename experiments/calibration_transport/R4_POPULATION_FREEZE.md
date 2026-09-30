# R4 Population Freeze

**R4 POPULATION LAYER: `FROZEN`**

```text
R4 OVERALL:
NOT FULLY FROZEN
NOT EXECUTION-AUTHORIZED
```

```text
freeze date  : 2026-09-30
freeze scope : dataset source identity
               population construction protocol
               primary TRAIN 456 identities
               secondary nested TRAIN 912 identities
               fixed-event population-layer anchor protocol
```

本文件只冻结 **population layer**。它 **不是** calibration-family 语义冻结，
**不是** predictor inference 规范冻结，**不是** R4 execution authorization。

---

## 1. Dataset source identities（frozen）

| dataset | repo_id | revision | config | license |
|---|---|---|---|---|
| HellaSwag | `Rowan/hellaswag` | `218ec52e09a7e7462a5400043bb9a69a41d06b76` | default | MIT |
| MedMCQA | `openlifescienceai/medmcqa` | `91c6572c454088bf71b679ad90aa8dffcd0d5868` | default | apache-2.0 |

```text
HellaSwag  calibration TRAIN source : train
           evaluation TEST source   : validation（FULL LABELED VALIDATION）
MedMCQA    calibration TRAIN source : train
           evaluation TEST source   : validation
```

两个 revision 均为 `EXACT REVISION VERIFIED`（`resolved sha == requested sha`），
且已由 local pinned snapshot 复验。禁止替换 revision。

---

## 2. Population budgets（frozen）

| population | role | TRAIN | TEST |
|---|---|---|---|
| HellaSwag primary | primary calibration | 456 | 10042 |
| MedMCQA primary | primary calibration | 456 | 4162 |
| HellaSwag robustness-912 | secondary sample-size robustness | 912 | 10042 |
| MedMCQA robustness-912 | secondary sample-size robustness | 912 | 4162 |

```text
primary TRAIN budget      = 456（R3 fitting-budget continuity）
secondary robustness TRAIN= 912 = primary 456 + nested extension 456
robustness TEST           = 与对应 primary TEST 完全相同
```

---

## 3. Manifest identities（frozen）

```text
hellaswag_population_candidate.json
  path                : /root/rivermind-data/r4-population-candidates/hellaswag_population_candidate.json
  train / test        : 456 / 10042
  manifest_fingerprint: 5c45043ba4f0ec436c16dcf494ff26be435c7857244bcbefa321d1678129c400
  file_sha256         : 0724128b9168b15a8796f260441c89025c3a224faf079cf7177b1c2faaec53cc

medmcqa_population_candidate.json
  path                : /root/rivermind-data/r4-population-candidates/medmcqa_population_candidate.json
  train / test        : 456 / 4162
  manifest_fingerprint: 4a4718438d46ab1ba27c59ca46806756ffb62efa05e6103981dffec4dc48c218
  file_sha256         : a3db913227c8b6b32e45d6d6555423fdf6fa34d2b1700bd38fb06515226418f7

hellaswag_population_robustness912_candidate.json
  path                : /root/rivermind-data/r4-population-candidates/hellaswag_population_robustness912_candidate.json
  train / test        : 912 / 10042
  role                : secondary-sample-size-robustness
  parent_primary_budget : 456
  nested_primary      : true
  manifest_fingerprint: 6817496f227d9cd57759bf55489cbf8a1dc4dfd27db0ae551e9223d21d02a096
  file_sha256         : 9920c74071953df24fef760a2878942a17344974bdd341a77e2007f96feb8c4b

medmcqa_population_robustness912_candidate.json
  path                : /root/rivermind-data/r4-population-candidates/medmcqa_population_robustness912_candidate.json
  train / test        : 912 / 4162
  role                : secondary-sample-size-robustness
  parent_primary_budget : 456
  nested_primary      : true
  manifest_fingerprint: e48c37293f196e16d8fba42e7fc255e4ac2e77f81c270ed6f71320981968af12
  file_sha256         : f56b09836da06d88f0be0915a9ebbd2bb01de54b2e48cafbeeb5554deab415fc
```

`manifest_fingerprint = fingerprint(payload without its own manifest_fingerprint)`，
使用 `probvenance.fingerprint` 的 canonical JSON 语义。

---

## 4. Protocol identities（frozen）

```text
population_protocol_id      = r4-stratified-population-construction   (v1)
selection_protocol_id       = r4-stratified-source-index-hash-selection (v1)
extension_protocol_id       = r4-nested-residual-extension            (v1)
anchor_protocol_id          = r4-fixed-event-anchor-deterministic-source-index-hash (v1)
```

```text
item_id = fingerprint({ population_protocol_id, population_protocol_version,
                        dataset_id, dataset_revision, source_split, source_row_index })

selection_rank = fingerprint({ selection_protocol_id, selection_protocol_version,
                               dataset_id, dataset_revision, source_split,
                               stratum, source_row_index })

anchor_index = int(fingerprint({ anchor_protocol_id, anchor_protocol_version,
                                 dataset_id, dataset_revision, source_split,
                                 source_row_index })[:16], 16) % 4
```

禁止作为上述任一函数的输入：

```text
ground truth, label, cop, question text, candidate text,
model output, measurement score, CAT score, OVR score
```

因此 `item_id` answer-independent，`anchor_index` 与内容、与正确性无关。

---

## 5. Construction semantics（frozen）

### 5.1 HellaSwag

```text
primary stratum        : activity_label
selection              : Hamilton / largest-remainder proportional allocation
                         weight = eligible source-train rows per stratum
within-stratum ranking : deterministic source-index fingerprint（见 §4）
group identity         : source_id
TRAIN constraint       : at most one selected row per source_id（跨整个 912）
TEST                   : all eligible labeled validation rows（不 subsample）
split_type             : secondary subgroup diagnostic only（indomain / zeroshot）
```

rare / target-only strata（frozen decision）：

```text
174 / 178 source-train activity strata receive positive quota
4 source-train activity strata receive quota 0:
  Home,Categories / Knitting / Spread mulch / Windsurfing
=> 不强制 minimum-one allocation

14 validation-only activity labels 为 target-only semantic support，保留在 TEST。
它们不是 "train strata with zero eligible rows"。
train unique 178 / validation unique 192 / shared 178 / validation-only 14 / train-only 0
```

### 5.2 MedMCQA

```text
primary stratum        : subject_name
selection              : Hamilton / largest-remainder proportional allocation
within-stratum ranking : deterministic source-index fingerprint（见 §4）
keep                   : choice_type = single 与 multi
reject as stratum      : topic_name
TEST                   : all structurally eligible labeled validation rows
```

---

## 6. Structural eligibility 与 overlap guard（frozen）

MedMCQA duplicate-option structural rule：

```text
candidate option strings 经 Unicode NFC + CRLF/CR -> LF + outer strip 之后
必须 pairwise distinct，否则该行 STRUCTURALLY INELIGIBLE
```

该规则不得读取 `cop` / correctness / model output / score。

```text
expected exclusions : TRAIN source 693 ; validation 21
primary TEST        : 4183 - 21 = 4162
```

R3-style overlap guard（两个 dataset 相同）：

```text
TEST 先冻结且 pristine；
TRAIN 中 exact question + exact ordered candidates 与 TEST 重复者排除，
并取下一个 deterministic ranked row；
若重复且 ground truth 冲突 => STOP FOR HUMAN REVIEW。
current frozen revisions: actual overlap exclusions = 0
```

---

## 7. Sample-size roles（frozen）

```text
PRIMARY CALIBRATION TRAIN BUDGET : 456（R3 fitting-budget continuity）
SECONDARY SAMPLE-SIZE ROBUSTNESS : 912（nested 456 + 456 extension，same TEST）
```

```text
N=456 remains the sole primary R3-continuity fitting budget.
N=912 is secondary only:
  cannot rescue / cannot override / cannot redefine the primary-456 conclusion.
```

禁止在观察 calibration outcome 之后再决定是否报告 912。

明确记录：

```text
NO ANCHOR-BALANCE OPTIMIZATION
```

（MedMCQA TRAIN anchor==cop ≈ 0.188596 仅为 selection 之后的 structural diagnostic，
不得据此 resample / rebalance / 更换 hash / 更换 anchor protocol / 更换 row selection。）

---

## 8. Provenance commits（frozen chain）

```text
330928ee43b3e89cedb4965d789a665393b9310b  experiments: add Qwen3.5-9B engineering probe
3d105a069169391b7333b8ee4b41ae9af99d0afb  experiments: audit R4 dataset semantics
b90d822191a17d7d35fbcd7d4578b2edf47a8ca3  docs: record R4 population construction plan
7948b3da1508818fb1907c0809d49461828a2593  docs: add R4 calibration-sample-size robustness plan
0e8156ccfe2f12dc4f1e0eb1d039d4a9f4faf88d  experiments: record R4 population construction
```

（本 freeze 自身的 commit 见 §9。）

---

## 9. Frozen / not frozen

frozen：

```text
dataset source identity
population construction protocol
primary TRAIN 456 identities
secondary nested TRAIN 912 identities
fixed-event population-layer anchor protocol
```

NOT frozen（仍属 later closure）：

```text
calibration-family full semantics
isotonic implementation
beta implementation
predictor inference / inferential specification
bootstrap replicate count / bootstrap CI / cluster-bootstrap implementation
multiplicity
formal statistical analysis
formal R4 execution protocol
```

因此：

```text
R4 POPULATION LAYER : FROZEN
R4 OVERALL          : NOT FULLY FROZEN
R4 EXECUTION        : NOT AUTHORIZED
```

---

## 10. Reproduction

```bash
cd /root/rivermind-data/Probvenance
PYTHONPATH=/root/rivermind-data/r4-dataset-audit/pylibs \
  /root/rivermind-data/envs/probvenance-r4/bin/python \
  experiments/calibration_transport/r4_population_candidate.py
```

只读取 local pinned snapshots，无网络，无 model load，无 calibration fitting。
完整 construction 两次必须 byte-identical（4 个 manifest 全部）。
