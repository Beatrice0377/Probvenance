# R4 Epoch 1 — Pre-Row1 Code Defect Receipt

**Status:** `R4 EPOCH 1 PRE-ROW1 CODE DEFECT = CONFIRMED / CONTAINED`
**Nature:** operational-attempt provenance. Not a scientific artifact.
**Scientific evidence produced by the blocked attempt:** `NONE`

---

## 1. What happened

The formal Epoch 1 all-reference raw measurement launch (task `R4 FORMAL EPOCH 1
ALL-REFERENCE RAW MEASUREMENT EXECUTION`) was started from the frozen
authority commit `8121fcd4a802651a51bde76d1697ac2e50bdf5a5`.

The first cell in the frozen dispatcher order was:

```text
olmo-3-7b-instruct__r4-mmlu-57-subject
```

It failed closed after **63 seconds** with **exit code 1** and **zero committed
rows**:

```text
KeyError: 'question'
  at experiments/calibration_transport/run_r4_measurements.py:810
     question = str(row["question"])
  raised from run_cell_resumable at run_r4_measurements.py:1154
```

No model forward for any study item was ever attempted: the failure happened
while building the CAT decision for the first item, before the first
`runtime.evaluate_with_trace` call.

```text
STUDY FORWARDS BEFORE DISCOVERY = 0
COMMITTED STUDY ROWS BEFORE DISCOVERY = 0
```

## 2. Root cause (mechanically confirmed)

`run_r4_measurements.py::_mmlu_rows()` built the normalized measurement row
without the frozen `question` field, while `measure_item()` correctly requires
`row["question"]`.

Observed key set of the pre-fix MMLU normalized row:

```text
['anchor_index', 'candidate_descriptions', 'candidate_names',
 'ground_truth_index', 'group_id', 'item_id', 'source_row_index',
 'source_split', 'split', 'stratum']
has 'question' = False
```

HellaSwag and MedMCQA normalize through `_normalize_manifest_row()`, which
already carried `"question": str(row["question"])`. Only the MMLU adapter path
(4 of the 16 frozen cells) was affected.

The defect was latent because:

- the six-model synthetic preflight uses invented items and never exercises a
  population adapter; and
- the aborted Epoch 0 attempt only ever reached
  `falcon-h1-7b-instruct__r4-hellaswag-activity-primary`.

Classification:

```text
PRE-ROW1 IMPLEMENTATION DEFECT (POPULATION ADAPTER OMISSION)
not a protocol amendment, not an estimand amendment, not a measurement redesign
```

## 3. Containment / quarantine

The blocked staging cell was **not deleted**. It was preserved as a pure
operational failed attempt:

```text
source: /root/rivermind-data/r4-formal-measurements/olmo-3-7b-instruct__r4-mmlu-57-subject
target: /root/rivermind-data/r4-formal-measurements-aborted/epoch1-pre-row1-code-defect-attempt0/
```

Deterministic manifest `QUARANTINE_MANIFEST.json`:

```text
label:                r4-epoch1-pre-row1-code-defect-attempt0
manifest_version:     1
file_count:           4
total_bytes:          122201
manifest_fingerprint: 8636a765f1d2808acec0b6b73bdec73f11dd252671eab1bbb126412d79cfddfb
manifest_sha256:      459b7762ee4e6f01f132ef113ecb7f1749a7af25e21867f2a5bd684f522d914c
```

Preserved files:

```text
olmo-3-7b-instruct__r4-mmlu-57-subject/LOCK                     0 bytes      e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
olmo-3-7b-instruct__r4-mmlu-57-subject/cell_identity.json       120837 bytes 8215ab39caa0d15f6d7f92914090bc4f15d94f1b23948828a3d8999a28331aab
olmo-3-7b-instruct__r4-mmlu-57-subject/operations.json          218 bytes    60a8210680c50db4ca9adfa7dbe15fc431f7a6c9a1ac0c1f8d92edf30e7c32e3
olmo-3-7b-instruct__r4-mmlu-57-subject/runtime_provenance.json  1146 bytes   5b5c246692c71f234ea2361c5d561b5d649fabf56491a77526f1194d3222cfbd
```

There is no `raw-evidence.json` and no `rows/` content: the cell never
finalized and never committed a row.

Quarantine policy:

```text
DO_NOT_RESUME
DO_NOT_MERGE
DO_NOT_ANALYZE
```

This attempt is **not** part of the R4 scientific raw-evidence set. Its
contents are ineligible for calibration, risk estimation, bootstrap, predictor
validation, or paper results.

## 4. Outcome firewall

```text
study_forwards:        0
committed_study_rows:  0
scientific_evidence:   NONE
```

No CAT score, OVR score, accuracy, probability, Brier, LogLoss, delta,
bootstrap, calibration parameter, predictor value, or interpretation was
computed, read, or recorded at any point during the blocked attempt or during
this correction task.

## 5. Consequence for the future formal launch

- Epoch 1 root `/root/rivermind-data/r4-formal-measurements` was recreated
  empty (`entries = 0`).
- The scientific epoch remains **Epoch 1** (no Epoch 2): zero real study
  forwards and zero committed study rows were produced, so there is no
  scientific evidence split to separate.
- Epoch 1 launch **attempt 0** = `BLOCKED` (this receipt).
- Epoch 1 launch **attempt 1** = the post-fix measurement code commit.
- All 16 formal cells will use **one single post-fix measurement code commit**.
  Although 12 HellaSwag/MedMCQA cells were unaffected by the adapter defect,
  none of them was executed before the correction. This is a deliberate
  provenance simplification: one measurement code identity for all 16 cells.
