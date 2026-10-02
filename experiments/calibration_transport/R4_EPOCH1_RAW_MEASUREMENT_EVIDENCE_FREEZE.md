# R4 Epoch 1 Raw Measurement Evidence Freeze

```text
STATUS: FROZEN
ARTIFACT: r4-epoch1-raw-measurement-evidence-freeze
EPOCH: 1
FORMAL R4 EPOCH 1 RAW MEASUREMENT EXECUTION = COMPLETE
R4 EPOCH 1 RAW MEASUREMENT COMPLETENESS = PASS
FORMAL R4 CALIBRATION / INFERENCE = NOT AUTHORIZED
PUSH PERFORMED = NO
```

## 1. Execution identity

```text
repository_execution_authority      = 100c918345ff829dd6fdb96bf99cd14285d6472f
repo_head                          = 100c918345ff829dd6fdb96bf99cd14285d6472f
measurement_code_commit            = 100c918345ff829dd6fdb96bf99cd14285d6472f
production_code_equivalence_anchor = 65eb75ceabecbd5f30c07135b62c184d028b4f0f
measurement_contract_fingerprint   = 7b126d300e774cb44d2c47fcb12513865d03c2b08ffd03a5ce409b2ea976e1e5
final_protocol_fingerprint         = d1b56d702e1f260cef47eee05b7d878ace07a15168e89408e15e7eb741c0ad34
execution_manifest_fingerprint     = f32381c51db24f5dbeb240b5e0fdf73c59a56a615c8607ad8979e2a7e2586775
environment_map_fingerprint        = aebeb528b6db1d09d23c83ff8078e5a9cb0b779c8fbada0f19617c878cfb45eb
distinct_execution_environments    = ['R0']
staging_root                       = /root/rivermind-data/r4-formal-measurements
resume_policy                      = r4-measurement-resume-policy v1
ledger_fingerprint                 = 2ed383f67be4476024d12a03c26699a1a50ed8656d75bb089986ce558d1be541
```

Provenance interpretation (human ruling, `measurement_code_commit` is the exact
repository commit under which the formal measurement process executed):

```text
measurement_code_commit = repo_head = HEAD at execution time
production_code_equivalence_anchor = origin of the last production-code change
  (MMLU adapter fix); production measurement paths are byte-identical across
  the anchor and the executed HEAD (verified by git diff --exit-code).
```

## 2. Measurement call contract

```text
contract_id            = r4-fixed-event-two-forward-measurement
CAT forwards per item  = 1
OVR forwards per item  = 1
total forwards per item= 2
OVR scope              = designated_candidate_only
```

## 3. Cell ledger (exactly 16 cells)

| # | cell_id | rows | CAT | OVR | paired | raw_evidence_sha256 | evidence_fingerprint |
|---|---|---|---|---|---|---|---|
| 1 | `olmo-3-7b-instruct__r4-mmlu-57-subject` | 1596 | 1596 | 1596 | True | `e71f464c6e2adef011a588ae1b7056352ecd28a61233cf4520e7ce8f95c26a8a` | `dadb04e97469552a22b600ade8037fac7c0fbd3fc8d1c6232be2c6303b7af728` |
| 2 | `olmo-3-7b-instruct__r4-hellaswag-activity-primary` | 10954 | 10954 | 10954 | True | `e753685f5e4924031a0ef94f1b7b281b2649525a5b53ad754906c0845c0860fc` | `712749c4ae3b7559e77ba1bc8d2db37faa3219f1446d0eaf9c161df1d1510065` |
| 3 | `olmo-3-7b-instruct__r4-medmcqa-subject-primary` | 5074 | 5074 | 5074 | True | `d6240f1979eae4ec2a5d72c422797c590b8d487a20164af02ba11720a21462d2` | `45410b18343ec2066a2d0e648ba086126ae2697d4b0b0c9507a77f2d427a75ff` |
| 4 | `falcon-h1-7b-instruct__r4-mmlu-57-subject` | 1596 | 1596 | 1596 | True | `00c21db5c4f4af839e6be38c4ccc1c914d8d59176415f81b54e188ce68be2681` | `b38c4fe0a83b7fb7fa9e1c8246ff0a0b7ad2a2cdc73bf399068ee3faaa060ebc` |
| 5 | `falcon-h1-7b-instruct__r4-hellaswag-activity-primary` | 10954 | 10954 | 10954 | True | `96bac04bfda5271d1a9e8002530f389fdc30e0579c51af40a4d79a43bd9cbe69` | `85e1ac56ed32b7528c2ccdfc2be2438f6f0b601b596e6a1e2e8dba12326fb5a1` |
| 6 | `falcon-h1-7b-instruct__r4-medmcqa-subject-primary` | 5074 | 5074 | 5074 | True | `3f27c23861be8b78dd194a0b08083f3681e6b28ef454f05337295e927e38ce25` | `4c0b83723b2aeb41d6b008350810dfbec268a2326204501cfeac2a726bca662a` |
| 7 | `granite-4-0-h-tiny__r4-mmlu-57-subject` | 1596 | 1596 | 1596 | True | `5a25898a7255c85fbeea0405061d0cd69e6a55de08a915b1e05a4412bcaa7bff` | `7dbebd1fedf38296a7b08eea6d71cfc6d2fa535a98c9281528b777cad0cf7fdb` |
| 8 | `granite-4-0-h-tiny__r4-hellaswag-activity-primary` | 10954 | 10954 | 10954 | True | `ea74b083117d7f4163ab342981894e80cf684a65fe67dc97ea65c37f81d5e053` | `4cae7b789126e6f0ecff8fbc6e773f20950b533b3f12bdb203e6effccec33a6e` |
| 9 | `granite-4-0-h-tiny__r4-medmcqa-subject-primary` | 5074 | 5074 | 5074 | True | `709597587757a1d5cdecae464bb8d1a9e215011b77a4d1fee7645d2d1c9d6b29` | `c1bb006638bcaf9b32d1df07461b571d3e5130d63209915be360788a9fbe2b6c` |
| 10 | `qwen3-5-9b__r4-mmlu-57-subject` | 1596 | 1596 | 1596 | True | `594d7777c0a99f42d13b85a3e5e79bc3582890145e81e4b8355e96bb6a636a1a` | `faf2b8a5316f41f3e025a0bf9030837a505c1d0f43aab4fa4fe624e9a4ac4cac` |
| 11 | `qwen3-5-9b__r4-hellaswag-activity-primary` | 10954 | 10954 | 10954 | True | `2b4463cf93f1d68ab801aa8268ce5c226ef51343a284ba601560685bf3e00b2a` | `58e7450a0d9f142f0ce08c6c928930c1ed9aeeb8757a692c4481b73647bc5d45` |
| 12 | `qwen3-5-9b__r4-medmcqa-subject-primary` | 5074 | 5074 | 5074 | True | `b03dd0729a84ccbcf779bb42fffecdfba9d9c3d90832336d4ae9757f6f3bbbcd` | `d0ad1dc6570aafad0fb026e9c6f6ccb228b9914a1e34f5140c2220b7d8bab3ba` |
| 13 | `minicpm5-2b__r4-hellaswag-activity-primary` | 10498 | 10498 | 10498 | True | `f65d9be1c123a680295fe75d04d53aefb765175d8cd7e084b9cb8bcb754a260c` | `4d9cd840f9d430f18041d5f0de563976ea6f521c5c9f038929eb56e2fb548826` |
| 14 | `minicpm5-2b__r4-medmcqa-subject-primary` | 4618 | 4618 | 4618 | True | `b75b5252b8541c2c8ab1f201c4dd502e09812497863f957dcb47ff387e8f9a52` | `446f1028391ca930962301f8bde51ef741c760603b7138d7b0bea554aef74e6c` |
| 15 | `qwen3-5-2b__r4-hellaswag-activity-primary` | 10498 | 10498 | 10498 | True | `048b294754edf5b710418202c0e42e50e7522ae0c805f1a8c395e2501a365bd3` | `4764b8aae4bd368aa7730a3dcd59f52c57a23199c1b8e2853f150834a223c612` |
| 16 | `qwen3-5-2b__r4-medmcqa-subject-primary` | 4618 | 4618 | 4618 | True | `48dcdbead32f77d3b5b7a893839c2c76b4776b162226f1fb9a3d7090f8cf67bb` | `75166cee197af719a85a813aab1e9df57ae3ddc4c7360a577031dfe295ad70aa` |

## 4. Totals

```text
cells                     = 16
expected_rows             = 100728
committed_rows            = 100728
CAT scored / missing / ineligible = 100728 / 0 / 0
OVR scored / missing / ineligible = 100728 / 0 / 0
paired_complete_cells     = 16 / 16
planned_logical_forwards  = 201456
operational_attempts      = 201456
recovery_replay_count     = 0
finalizations             = 16
completeness_status       = PASS
```

`planned_logical_forwards == operational_attempts` and `recovery_replay_count == 0`:
every planned logical forward was executed exactly once; no row was replayed,
retried, or terminally failed.

## 5. Outcome firewall

```text
bootstrap = NOT RUN
brier = NOT COMPUTED
calibration = NOT FIT
delta_deploy = NOT COMPUTED
delta_native = NOT COMPUTED
delta_transport = NOT COMPUTED
log_loss = NOT COMPUTED
predictor = NOT COMPUTED
scientific_interpretation = NOT PERFORMED
spearman = NOT COMPUTED
```

The freeze ledger records structural and transactional state only. It contains no
probability, score, accuracy, mean, Brier, LogLoss, Delta, calibration parameter,
correlation, or scientific conclusion.

## 6. What this freeze does and does not authorize

```text
RAW MEASUREMENT COMPLETENESS = PASS
FORMAL R4 CALIBRATION / INFERENCE = NOT AUTHORIZED
```

Raw evidence freeze is the terminal state of this task. Downstream calibration,
inference, predictor validation, and interpretation remain unauthorized pending
human / ChatGPT review.

