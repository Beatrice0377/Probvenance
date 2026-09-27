# R3 Official Raw Measurement Report

```text
R3 OFFICIAL RAW MEASUREMENT:
COMPLETE

CONFIRMATORY STATISTICAL ANALYSIS:
NOT RUN

PRIMARY HYPOTHESES INSPECTED:
NO
```

This document is the **measurement-only** report for Research R3.1. It records
provenance, evaluation counts, and structural completeness of the frozen raw
confirmatory evidence. It contains **no statistical result**: no calibration map
was fitted, no risk or transport-delta quantity was computed, no factorial
contrast was evaluated, and no resampling was performed. It is not
`R3_REPORT.md`.

---

## 1. Frozen protocol

```text
R3 protocol Git commit (semantic):   12f602a9527f0db4b1575abe6999235a40d55ef6
R3 protocol fingerprint:             3ef63056ae16b18ad65d9c87d1fbec5b43550873a0e3e25ec0a323f954ee974d
population manifest fingerprint:     40cc9753a711314ff3b25ed6e234d0cbda11f3f60cd87f1d3915195a3d1780b8
measurement-code commit:             8b1ea40aee0e7518c2ab3b25a8cc6d4ec2d0f800
```

Both fingerprints were recomputed at run time and matched the frozen protocol
exactly. The child-plan fingerprints were recomputed and matched:

```text
primary      child plan: 787c668201fa1a2046bb3eb7c00ec1fd929d76bc164dadcef6f7dd6a2edb0ee6
replication  child plan: dc2f58732921466891de16a031f20141e82a28107de7fef114456f65159c6ebe
```

Population:

```text
dataset:        cais/mmlu @ c30699e8356da336a370243923dbaf21066bb9fe (MIT)
subjects:       57
TRAIN:          456   (8 / subject)
TEST:           1140  (20 / subject)
AUDIT:          0
TOTAL items:    1596
```

## 2. Declared model conditions

```text
PRIMARY       openbmb/MiniCPM5-2B @ 12a3808a956f869c767195e9266b59c4d21d92e2
              role primary-confirmatory

REPLICATION   Qwen/Qwen3.5-2B   @ 15852e8c16360a2fea060d615a32b45270f8a8fc
              role preregistered-replication
```

Both were executed with `dtype=bfloat16`, `device=cuda`,
`rendering={"enable_thinking": false}`, `trust_remote_code=false`,
`local_files_only=true`.

## 3. Runtime provenance

Recorded identically in both artifacts:

```text
Python:              3.11.14
torch:               2.14.0+cu130
torch CUDA runtime:  13.0
GPU:                 NVIDIA GeForce RTX 5060 Laptop GPU
transformers:        5.17.0
huggingface_hub:     1.32.0
dtype:               bfloat16
device:              cuda
local_files_only:    true
HF_HUB_OFFLINE:      1
TRANSFORMERS_OFFLINE: 1
HF_DATASETS_OFFLINE:  1
```

This matches the successful operational preflight environment exactly; no
environment drift was observed.

`model_config_commit_hash` was exposed and matched the requested revision for
both models (`12a3808a…` and `15852e8c…`). `tokenizer_commit_hash` was
**not exposed** by the loader and is recorded as `null` (not invented).

## 4. Measurement identities (frozen; unchanged)

```text
CAT:              direct-categorical-anchor-probability v1
OVR:              independent-binary-anchor-probability v1
OVR proposition:  choice-candidate-correctness-binary-judgment v1
anchor:           sha256-case-id-candidate-set-anchor v1
target:           fixed-decision-correctness v1
input score:      fixed-decision-semantic-probability v1
```

## 5. Evaluation counts

```text
MiniCPM (primary):
  items:              1596
  CAT evaluations:    1596
  OVR evaluations:    6384   (4 independent binary judgments per item)
  total:              7980

Qwen (replication):
  items:              1596
  CAT evaluations:    1596
  OVR evaluations:    6384
  total:              7980

GRAND TOTAL:          15960 official evaluations
```

Per-item contract was exactly one CAT plus four independent OVR evaluations; no
retries, permutations, alternate prompts, or confidence thresholds were used.

## 6. Structural completeness

```text
MiniCPM (primary):
  items:            1596
  CAT  scored:      1596   missing: 0   ineligible: 0
  OVR  scored:      1596   missing: 0   ineligible: 0

Qwen (replication):
  items:            1596
  CAT  scored:      1596   missing: 0   ineligible: 0
  OVR  scored:      1596   missing: 0   ineligible: 0
```

Every one of the 1596 frozen manifest items is represented exactly once; no
extra item ID and no duplicate item ID exists. Both model artifacts carry the
same item IDs, the same subject/split labels, the same anchors, and the same
ground-truth values.

## 7. Wall time

```text
MiniCPM (primary):      started 2026-09-27T11:38:49Z
                        artifact written 2026-09-27T11:45:09Z
                        runner-reported duration: 373.9 s

Qwen (replication):     started 2026-09-27T11:45:40Z
                        artifact written 2026-09-27T11:53:51Z
                        runner-reported duration: 469.9 s
```

Wall time is reported here only; it is not part of any evidence fingerprint.

## 8. Frozen artifacts

```text
experiments/calibration_transport/results/
  r3-raw-minicpm5-2b-mmlu-v1.json
      file SHA256:           e7b45e921d35523f9fb6aabaefe10e585f43f35f25e5e4159bb2211cec8b999b
      internal evidence fp:  726bb8340aecfa0c98e4d4b7fe1548278f3cc8ff391b9f6d14aa5215e84d7c71
      paired dataset fp:     e143ad0afb2b3f00e25345d2334f1acf2f70b441e2cece660064a1eaebe66bf9

  r3-raw-qwen35-2b-mmlu-v1.json
      file SHA256:           00a1d04e6cb308cf609ccf3cde69b761497c4a3a110704ea069f3e933cf9248a
      internal evidence fp:  378b2676dad4b12be4d57c9030c9d44823df921dc62f4d9b7f73acf79f0d4887
      paired dataset fp:     9c24a733c11fe58c1ee5052c61bc2574af7e2409468b7fe3674e6ca892523880

  r3-raw-evidence-index-v1.json
      index fingerprint:     25fa4086e67a1cbd48cb8d857337092b132790ceb04925407649629c35d1bc51
      artifact version:      1
      all_declared_conditions_complete: true
```

Credentials: both artifacts were staged outside the repository
(`/tmp/probvenance-r3-official/`) during both model runs, and copied
byte-for-byte only after both conditions completed; staged and committed-path
SHA256 match exactly for both.

## 9. Operational retries and post-outcome code changes

```text
Any operational retries occurred?
  YES — one. The primary (MiniCPM) condition was first launched under the
  committed runner but the launch process was terminated by the operating
  shell's process-group cleanup before any artifact was written. The condition
  was restarted from the beginning under the IDENTICAL committed runner and the
  IDENTICAL frozen protocol. The first attempt produced no artifact and no
  partial records were merged; the second attempt completed coherently.

Any code/config change after the first official forward?
  NO. No source, test, protocol, population, procedure, hypothesis, or
  multiplicity change occurred after official measurement began. The
  measurement-code commit used for both conditions is the unmodified
  8b1ea40aee0e7518c2ab3b25a8cc6d4ec2d0f800.
```

## 10. Explicit non-analysis statement

```text
Calibrator fitting performed:             NO
Risk / excess-risk quantity computed:     NO
Transport delta computed:                 NO
Primary factorial contrasts computed:     NO
Resampling / intervals computed:          NO
Native reference states computed:         NO
Score distributions summarized:           NO
Model accuracies computed:                NO
Primary hypothesis results interpreted:   NO
```

Only structural integrity validation (record counts, item-ID coverage,
candidate coverage, status completeness, probability domain/sum checks,
source/result linkage) was performed. No probability value was aggregated.

```text
R3 RAW EVIDENCE GATE:
PENDING EXTERNAL + HUMAN REVIEW
```
