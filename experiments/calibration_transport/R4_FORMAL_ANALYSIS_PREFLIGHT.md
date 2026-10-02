# R4 Formal Analysis Structural Preflight

Status: `NEEDS_EXECUTION_RUNNER`
Preflight fingerprint: `500ae1cb5ee19d030dad6c27a164b84650adbd79d81451f416126892d2e48873`
Raw measurement freeze commit: `3aae4528a131ba32582fb015bd2f6a4d201da457`

本文件是 **结构性 preflight**。没有拟合任何 calibrator，没有计算任何
Brier / LogLoss / risk / Delta / bootstrap / predictor / Spearman。

```text
SCIENTIFIC OUTPUTS COMPUTED = NO
R4 FORMAL ANALYSIS READINESS = NEEDS_EXECUTION_RUNNER
FORMAL R4 CALIBRATION / INFERENCE = NOT YET AUTHORIZED
```

---

## 1. Raw measurement freeze authority

| artifact | path | sha256 |
| --- | --- | --- |
| ledger | `experiments/calibration_transport/R4_EPOCH1_RAW_MEASUREMENT_EVIDENCE_LEDGER.json` | `146ad254dda64778cb684283e24ae1dca2987bc6827652c448739b75ae2e1a6a` |
| freeze doc | `experiments/calibration_transport/R4_EPOCH1_RAW_MEASUREMENT_EVIDENCE_FREEZE.md` | `b027be6183c06878432d22bf41d464c0281d5646269f0994924c2eec06c57727` |
| receipt | `experiments/calibration_transport/R4_EPOCH1_RAW_MEASUREMENT_EXECUTION_RECEIPT.md` | `50bab7148f1aa5689068f012fc16cedbd4df937069c7f69eb815d293c9148dfe` |

```text
ledger_fingerprint = 2ed383f67be4476024d12a03c26699a1a50ed8656d75bb089986ce558d1be541
completeness_status = PASS
```

---

## 2. 16 raw evidence artifacts — validation

| cell_id | raw evidence sha256 | evidence_fingerprint |
| --- | --- | --- |
| `falcon-h1-7b-instruct__r4-hellaswag-activity-primary` | `96bac04bfda5271d1a9e8002530f389fdc30e0579c51af40a4d79a43bd9cbe69` | `85e1ac56ed32b7528c2ccdfc2be2438f6f0b601b596e6a1e2e8dba12326fb5a1` |
| `falcon-h1-7b-instruct__r4-medmcqa-subject-primary` | `3f27c23861be8b78dd194a0b08083f3681e6b28ef454f05337295e927e38ce25` | `4c0b83723b2aeb41d6b008350810dfbec268a2326204501cfeac2a726bca662a` |
| `falcon-h1-7b-instruct__r4-mmlu-57-subject` | `00c21db5c4f4af839e6be38c4ccc1c914d8d59176415f81b54e188ce68be2681` | `b38c4fe0a83b7fb7fa9e1c8246ff0a0b7ad2a2cdc73bf399068ee3faaa060ebc` |
| `granite-4-0-h-tiny__r4-hellaswag-activity-primary` | `ea74b083117d7f4163ab342981894e80cf684a65fe67dc97ea65c37f81d5e053` | `4cae7b789126e6f0ecff8fbc6e773f20950b533b3f12bdb203e6effccec33a6e` |
| `granite-4-0-h-tiny__r4-medmcqa-subject-primary` | `709597587757a1d5cdecae464bb8d1a9e215011b77a4d1fee7645d2d1c9d6b29` | `c1bb006638bcaf9b32d1df07461b571d3e5130d63209915be360788a9fbe2b6c` |
| `granite-4-0-h-tiny__r4-mmlu-57-subject` | `5a25898a7255c85fbeea0405061d0cd69e6a55de08a915b1e05a4412bcaa7bff` | `7dbebd1fedf38296a7b08eea6d71cfc6d2fa535a98c9281528b777cad0cf7fdb` |
| `minicpm5-2b__r4-hellaswag-activity-primary` | `f65d9be1c123a680295fe75d04d53aefb765175d8cd7e084b9cb8bcb754a260c` | `4d9cd840f9d430f18041d5f0de563976ea6f521c5c9f038929eb56e2fb548826` |
| `minicpm5-2b__r4-medmcqa-subject-primary` | `b75b5252b8541c2c8ab1f201c4dd502e09812497863f957dcb47ff387e8f9a52` | `446f1028391ca930962301f8bde51ef741c760603b7138d7b0bea554aef74e6c` |
| `olmo-3-7b-instruct__r4-hellaswag-activity-primary` | `e753685f5e4924031a0ef94f1b7b281b2649525a5b53ad754906c0845c0860fc` | `712749c4ae3b7559e77ba1bc8d2db37faa3219f1446d0eaf9c161df1d1510065` |
| `olmo-3-7b-instruct__r4-medmcqa-subject-primary` | `d6240f1979eae4ec2a5d72c422797c590b8d487a20164af02ba11720a21462d2` | `45410b18343ec2066a2d0e648ba086126ae2697d4b0b0c9507a77f2d427a75ff` |
| `olmo-3-7b-instruct__r4-mmlu-57-subject` | `e71f464c6e2adef011a588ae1b7056352ecd28a61233cf4520e7ce8f95c26a8a` | `dadb04e97469552a22b600ade8037fac7c0fbd3fc8d1c6232be2c6303b7af728` |
| `qwen3-5-2b__r4-hellaswag-activity-primary` | `048b294754edf5b710418202c0e42e50e7522ae0c805f1a8c395e2501a365bd3` | `4764b8aae4bd368aa7730a3dcd59f52c57a23199c1b8e2853f150834a223c612` |
| `qwen3-5-2b__r4-medmcqa-subject-primary` | `48dcdbead32f77d3b5b7a893839c2c76b4776b162226f1fb9a3d7090f8cf67bb` | `75166cee197af719a85a813aab1e9df57ae3ddc4c7360a577031dfe295ad70aa` |
| `qwen3-5-9b__r4-hellaswag-activity-primary` | `2b4463cf93f1d68ab801aa8268ce5c226ef51343a284ba601560685bf3e00b2a` | `58e7450a0d9f142f0ce08c6c928930c1ed9aeeb8757a692c4481b73647bc5d45` |
| `qwen3-5-9b__r4-medmcqa-subject-primary` | `b03dd0729a84ccbcf779bb42fffecdfba9d9c3d90832336d4ae9757f6f3bbbcd` | `d0ad1dc6570aafad0fb026e9c6f6ccb228b9914a1e34f5140c2220b7d8bab3ba` |
| `qwen3-5-9b__r4-mmlu-57-subject` | `594d7777c0a99f42d13b85a3e5e79bc3582890145e81e4b8355e96bb6a636a1a` | `faf2b8a5316f41f3e025a0bf9030837a505c1d0f43aab4fa4fe624e9a4ac4cac` |

总计 `expected_rows = 100728`，
`committed_rows = 100728`。

---

## 3. Cell structure

| cell_id | role | model_revision | population | TRAIN/TEST | strata | group field | rows | paired |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `falcon-h1-7b-instruct__r4-hellaswag-activity-primary` | current-generation | `41e72f27effbab80cd45b6e884688452253a3686` | hellaswag | 912/10042 | 192 | group_id | 10954 | True |
| `falcon-h1-7b-instruct__r4-medmcqa-subject-primary` | current-generation | `41e72f27effbab80cd45b6e884688452253a3686` | medmcqa | 912/4162 | 21 | — | 5074 | True |
| `falcon-h1-7b-instruct__r4-mmlu-57-subject` | current-generation | `41e72f27effbab80cd45b6e884688452253a3686` | mmlu | 456/1140 | 57 | — | 1596 | True |
| `granite-4-0-h-tiny__r4-hellaswag-activity-primary` | current-generation | `791e0d3d28c86e106c9b6e0b4cecdee0375b6124` | hellaswag | 912/10042 | 192 | group_id | 10954 | True |
| `granite-4-0-h-tiny__r4-medmcqa-subject-primary` | current-generation | `791e0d3d28c86e106c9b6e0b4cecdee0375b6124` | medmcqa | 912/4162 | 21 | — | 5074 | True |
| `granite-4-0-h-tiny__r4-mmlu-57-subject` | current-generation | `791e0d3d28c86e106c9b6e0b4cecdee0375b6124` | mmlu | 456/1140 | 57 | — | 1596 | True |
| `minicpm5-2b__r4-hellaswag-activity-primary` | legacy-lineage | `12a3808a956f869c767195e9266b59c4d21d92e2` | hellaswag | 456/10042 | 192 | group_id | 10498 | True |
| `minicpm5-2b__r4-medmcqa-subject-primary` | legacy-lineage | `12a3808a956f869c767195e9266b59c4d21d92e2` | medmcqa | 456/4162 | 21 | — | 4618 | True |
| `olmo-3-7b-instruct__r4-hellaswag-activity-primary` | current-generation | `6e5971d9eba42665f5bd5a0fcf047f299ce1dccc` | hellaswag | 912/10042 | 192 | group_id | 10954 | True |
| `olmo-3-7b-instruct__r4-medmcqa-subject-primary` | current-generation | `6e5971d9eba42665f5bd5a0fcf047f299ce1dccc` | medmcqa | 912/4162 | 21 | — | 5074 | True |
| `olmo-3-7b-instruct__r4-mmlu-57-subject` | current-generation | `6e5971d9eba42665f5bd5a0fcf047f299ce1dccc` | mmlu | 456/1140 | 57 | — | 1596 | True |
| `qwen3-5-2b__r4-hellaswag-activity-primary` | legacy-lineage | `15852e8c16360a2fea060d615a32b45270f8a8fc` | hellaswag | 456/10042 | 192 | group_id | 10498 | True |
| `qwen3-5-2b__r4-medmcqa-subject-primary` | legacy-lineage | `15852e8c16360a2fea060d615a32b45270f8a8fc` | medmcqa | 456/4162 | 21 | — | 4618 | True |
| `qwen3-5-9b__r4-hellaswag-activity-primary` | current-generation | `c202236235762e1c871ad0ccb60c8ee5ba337b9a` | hellaswag | 912/10042 | 192 | group_id | 10954 | True |
| `qwen3-5-9b__r4-medmcqa-subject-primary` | current-generation | `c202236235762e1c871ad0ccb60c8ee5ba337b9a` | medmcqa | 912/4162 | 21 | — | 5074 | True |
| `qwen3-5-9b__r4-mmlu-57-subject` | current-generation | `c202236235762e1c871ad0ccb60c8ee5ba337b9a` | mmlu | 456/1140 | 57 | — | 1596 | True |

---

## 4. Directional units

```text
current_generation_primary = 0 cells
                           = 0 directional units
                             (4 models x 3 populations x 2 directions)

legacy_lineage_secondary   = 16 cells
                           = 32 directional units
                             (2 models x 2 populations x 2 directions)
```

Directions: `CAT->OVR`（source CAT，target OVR）、`OVR->CAT`（source OVR，target CAT）。
两方向对同一 fixed event `D_i`、同一 `Y_i = 1[D_i = GT_i]`。

---

## 5. N456 / N912 map

```text
primary               = N456 (456 rows)
secondary_robustness  = N912 (912 rows), nested superset of N456, extension = 456 rows
                        cannot_rescue_primary = true
legacy                = N456 only (no legacy N912)
```

N456 ⊂ N912 已通过 frozen manifest identity 验证（两数据集均为 456 / 912 / extension 456）。

---

## 6. Calibration procedure map

```text
CORE4        = P-low, P-historical, L-low, L-historical
EXTENSION2   = I-isotonic, B-beta
seventh_procedure = FORBIDDEN
```

科学 fingerprint 见 `R4_CALIBRATION_FAMILY_FREEZE.md`。

---

## 7. Risk / Delta dependency map

```text
Delta_native(F)    = R_native(F) - R_raw
Delta_deploy(F)    = R_cross(F)  - R_raw
Delta_transport(F) = R_cross(F)  - R_native(F)
```

---

## 8. Bootstrap population map

| population | mode | stratum | group |
| --- | --- | --- | --- |
| MMLU | subject-stratified paired | `stratum` (subject) | — |
| HellaSwag | source_id cluster | `stratum` (activity_label) | `group_id` (source_id) |
| MedMCQA | subject_name-stratified row | `stratum` (subject_name) | — |

TEST bootstrap = 20000 draws，population-shared across models / directions / procedures。
TRAIN refit bootstrap = 2000 draws，与 TEST bootstrap 分开。

---

## 9. Multiplicity family map

```text
primary12   = 12
extension8  = 8
direction6  = 6
native12    = 12
r3_continuity_subset = 6
```

---

## 10. Predictor 8 / 16 / 8 split

```text
development      = 8  (MMLU current-generation; NOT independent validation)
primary_validation = 16 (held-out)
legacy_extension = 8  (secondary; cannot rescue primary)
```

---

## 11. Analysis-code authority

| implementation | path | last commit | status |
| --- | --- | --- | --- |
| calibration | `experiments/calibration_transport/r4_calibration_families.py` | `5185f5044fdccf0d976f953a0ff2d6c93c91a08a` | MATCHES_FROZEN_AUTHORITY |
| inference | `experiments/calibration_transport/r4_inference.py` | `bdaa088a1f5b508c47875039d2cf2be5df1595a1` | MATCHES_FROZEN_AUTHORITY |
| predictor | `experiments/calibration_transport/r4_predictor.py` | `b6b1bc08763ab8c369611b2303cd272f99bdf1b1` | MATCHES_FROZEN_AUTHORITY |

---

## 12. Formal analysis runner availability

```text
formal_analysis_runner = MISSING
detail                 = no run_r4_analysis.py; the three implementation modules expose no CLI or __main__ entry point
dry_run_status         = NOT_APPLICABLE
```

没有 integrated runner，因此本任务没有调用任何真实 analysis 入口。

---

## 13. Test status

```text
test_r4_calibration_families.py = PASS
test_r4_inference.py            = PASS
test_r4_predictor.py            = PASS
test_r4_measurements.py         = PASS
test_r4_epoch1_dispatch.py      = PASS
full repo                       = PASS
py_compile / ruff / diff --check = PASS / PASS / PASS
```

---

## 14. Outcome firewall

本任务产出的 artifact 只包含身份、计数、hash、fingerprint 与结构依赖。

```text
Brier               = PLANNED
LogLoss             = PLANNED
Delta_transport     = DEPENDENCY_READY
Spearman            = NOT EXECUTED
scientific_outputs_computed = false
```

禁止字段列表（不得出现）：brier value、log_loss value、risk value、delta value、
correlation value、spearman value、accuracy、mean probability、calibration coefficients。

---

## 15. Fingerprints

```text
registry_fingerprint  = b0051d96eaeea693a37a0116ced4eecc7e7a7fcd34d93049b074a7010c8cb355
graph_fingerprint     = 449c9b19d61e4edbe95ea856b1d13e3b373765f8a9d05931f20e4d12bf28ed9f
preflight_fingerprint = 500ae1cb5ee19d030dad6c27a164b84650adbd79d81451f416126892d2e48873
fingerprint_version   = 1
```
