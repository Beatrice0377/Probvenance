# R3 Analysis-Entry Audit Erratum

**Artifact type:** `r3-analysis-entry-audit-erratum`
**Artifact version:** 1
**Machine-readable companion:** `experiments/calibration_transport/results/r3-analysis-entry-audit-erratum-v1.json`
**Erratum fingerprint:** `fb16bf3dfa32d02bd8d6878d9f43bd99f0292bbb5f393d1697068087a0392fb7`

## Status summary

| Dimension | State |
| --- | --- |
| Production analysis semantics | UNCHANGED / ALREADY CORRECT |
| Test evidence | STRENGTHENED |
| Frozen scientific design | UNCHANGED |
| Raw evidence | UNCHANGED (byte-preserved) |
| Official R3 confirmatory outcome | NOT RUN |
| Analysis-entry authorization | STILL REQUIRES HUMAN FINAL REVIEW |

## Why this erratum exists

This is an **audit-evidence precision** record, not a scientific correction.

The previous final audit
(`experiments/calibration_transport/R3_ANALYSIS_ENTRY_FINAL_AUDIT.md`, commit
`b317eb11d6c7c5e73f4cd2ef660f6257c1dee4bf`) correctly identified and corrected the
native-winner semantic defect in `end_to_end_diagnostics`. That production correction was
made in commit `b4afae24b1a8b84f65fa7c842850a225c35ef376` and is **unchanged** by this
erratum.

During human review of the audit evidence, two synthetic oracle descriptions were found to
be stronger than the literal fixture contents:

1. one OVR oracle was described as having all four candidate scores below 0.5, while the
   fixture only encoded the anchor score;

2. one agreement oracle was described as having CAT/OVR threshold classes differ, while the
   fixture encoded only native winner identities.

This follow-up changes **no production analysis semantics**. It strengthens the synthetic
evidence so the tests literally instantiate the counterexamples already described by the
audit. No new scientific defect was found.

## Scope of this erratum

```text
Production code:            NOT TOUCHED  (r3_analysis.py byte-unchanged this round)
Frozen protocol/design:     NOT TOUCHED
Raw evidence:               NOT TOUCHED  (byte-preserved)
Official R3 outcome:        NOT COMPUTED
```

The only implementation file changed by this round is:

```text
experiments/calibration_transport/tests/test_r3_analysis.py
```

changed by the test-only commit:

```text
d9ec4db6a5fed3fed65081187100a4d6dcd9efbe
test: strengthen R3 winner diagnostic oracles
```

## Issue A — OVR native winner with all four candidate scores below 0.5

### Previous fixture limitation

The oracle `test_ovr_winner_correct_when_all_candidate_scores_below_half` constructed only a
`R3WinnerRecord(item_id, ground_truth_value, cat_winner, ovr_winner)`, which carries **no
candidate scores at all**. A sibling synthetic helper
(`test_ovr_all_scores_below_half_with_recorded_winner`) carried only
`ovr_anchor_score = 0.47`. Both proved the anchor score is below 0.5, but neither literally
proved that **all four** OVR candidate scores are below 0.5.

### Strengthened fixture

Both oracles now build a synthetic evidence item whose OVR block explicitly encodes four
candidate scores:

```text
option-1 = 0.42
option-2 = 0.47
option-3 = 0.44
option-4 = 0.31
```

and assert, literally:

```python
assert [entry["candidate"] for entry in recorded["candidates"]] == [
    "option-1", "option-2", "option-3", "option-4",
]
assert all(entry["probability_true"] < 0.5 for entry in recorded["candidates"])
assert all(score < 0.5 for score in candidate_scores.values())
```

Facts proven:

```text
ground_truth_value          = "option-2"
recorded OVR winner         = "option-2"
all four candidate scores   < 0.5
```

The recorded native winner is then mapped through `winner_record_from_evidence(...)` and the
diagnostic yields:

```text
ovr_own_winner_accuracy == 1.0
```

Therefore a `>= 0.5` rule cannot define the OVR winner: the recorded winner (`option-2`) is
correct even though every candidate score is below 0.5.

## Issue B — recorded winner agreement despite differing threshold classes

### Previous fixture limitation

The oracle `test_recorded_agreement_when_threshold_classes_differ` constructed only a
`R3WinnerRecord`, so it contained no CAT / OVR anchor scores. It proved
`same native winner => winner_agreement == 1`, but it did **not** literally prove that the
CAT and OVR threshold classes differ.

### Strengthened fixture

The oracle now builds a synthetic evidence item with:

```text
CAT anchor_score = 0.60
OVR anchor_score = 0.40
CAT recorded winner = "option-3"
OVR recorded winner = "option-3"
```

and asserts, literally:

```python
assert (cat_anchor >= 0.5) != (ovr_anchor >= 0.5)
```

Facts proven:

```text
CAT threshold class:  0.60 >= 0.5 => True
OVR threshold class:  0.40 >= 0.5 => False
threshold classifications disagree
native winner identities agree ("option-3" == "option-3")
winner_agreement == 1.0
```

Therefore winner agreement cannot be threshold agreement.

## Retained counterexamples (unchanged in intent)

### Opposite direction — same threshold class, different native winners

`test_threshold_class_agreement_masks_recorded_disagreement` and
`test_disagreeing_winners_below_half_threshold` remain present. Both now literally encode:

```text
CAT anchor_score = 0.40   -> threshold class False
OVR anchor_score = 0.42   -> threshold class False
old threshold agreement  == True
CAT winner = "option-1", OVR winner = "option-3"
native winner agreement  == 0.0
```

### CAT below-0.5 correctness counterexample

`test_cat_anchor_below_half_with_anchor_as_winner` remains present, with
`cat_anchor_score = 0.40`, `CAT recorded winner == ground truth`, proving the retired
`>= 0.5` classification path is wrong while the native winner is correct.

Together the retained and strengthened oracles prove both directions:

```text
threshold classes same      does NOT imply native winners same
threshold classes different does NOT imply native winners different
```

## Test-name / fixture consistency

Every winner-diagnostic test whose name makes a score or threshold claim now literally
encodes the corresponding score condition in its fixture. Names are no stronger than the
fixtures they exercise:

```text
..._all_candidate_scores_below_half      -> carries + asserts all four candidate scores
..._threshold_classes_differ             -> carries + asserts opposite threshold classes
..._threshold_class_agreement_masks...   -> carries + asserts equal threshold classes
..._below_half_threshold                 -> carries + asserts CAT anchor below 0.5
```

## Production semantics statement

`winner_record_from_evidence()` continues to read **only** the frozen native winners and the
ground truth. It does **not** consume `candidate_scores`, `anchor_score`,
`probability_true`, or any calibrated probability. The extra candidate scores exist only in
the synthetic test evidence, so the tests can prove the stated counterexamples honestly.

Production winner semantics remain:

```text
winner = record["winner"]
```

and never:

```text
winner = argmax(candidate_scores)
winner = score >= 0.5
```

The candidate winner is never recomputed.

## Append-only provenance

This erratum does **not** amend or modify:

```text
experiments/calibration_transport/R3_ANALYSIS_ENTRY_FINAL_AUDIT.md
experiments/calibration_transport/results/r3-analysis-entry-final-audit-v1.json
```

Their wording is historically preserved. This erratum is an append-only addendum that
cross-references them.

## Cross-references

```text
previous final audit commit       : b317eb11d6c7c5e73f4cd2ef660f6257c1dee4bf
winner-fix commit                 : b4afae24b1a8b84f65fa7c842850a225c35ef376
oracle-strengthening commit       : d9ec4db6a5fed3fed65081187100a4d6dcd9efbe
human-readable final audit        : experiments/calibration_transport/R3_ANALYSIS_ENTRY_FINAL_AUDIT.md
machine-readable final audit      : experiments/calibration_transport/results/r3-analysis-entry-final-audit-v1.json
human-readable erratum (this file): experiments/calibration_transport/R3_ANALYSIS_ENTRY_AUDIT_ERRATUM.md
machine-readable erratum          : experiments/calibration_transport/results/r3-analysis-entry-audit-erratum-v1.json
```

## Non-claims

```text
No official R3 statistical outcome was computed, inspected, aggregated, or written.
No raw evidence was opened for statistical aggregation (hashing only).
No production analysis semantics were changed.
No frozen scientific design was changed.
No raw→analysis ingestion/execution runner was added.
Analysis-entry authorization is NOT granted by this erratum.
```
