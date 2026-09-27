# R3 Analysis-Entry Re-Audit (TRAIN-refit Failure-Contract Closure)

```text
raw evidence:                              PRESERVED / BYTE-FROZEN
model rerun:                               NOT REQUIRED
population rebuild:                        NOT REQUIRED
frozen protocol redesign:                  NOT PERFORMED
scientific redesign:                       NOT PERFORMED
official R3 confirmatory statistical analysis:  NOT RUN
analysis implementation:                   CORRECTED TO FROZEN SECTION 17 FAILURE CONTRACT
analysis provenance closure:               APPEND-ONLY (previous records preserved)
analysis-entry authorization:              STILL REQUIRES HUMAN RE-AUDIT
```

## 1. Purpose and scope

This record supersedes the analysis-entry **status** of the earlier closure record
`R3_ANALYSIS_ENTRY_GATE.md` after an independent human re-audit found one remaining
frozen-contract mismatch. The earlier record is **not** deleted, rewritten, or amended;
it remains in the repository as an accurate account of the state reached by its commits.
This new record appends the later finding and its fix.

No R3 confirmatory statistical analysis was run, before or during this round. No raw
measurement artifact was modified. No frozen scientific design element was changed.

## 2. Previous closure commits (preserved, unchanged)

```text
5829a8650c826c2521ce3287764d3f83b582f015   fix: conform R3 analysis to frozen protocol
fa97d6f548c2d1b820f076225e28527fde3c669a   docs: record R3 pre-analysis closure
```

Those commits corrected cross application `g_A(S_B)`, empirical support geometry
(SOURCE TRAIN / TARGET TEST), the required 2.5–97.5% geometry diagnostic, the
TRAIN-refit draw unit (10 draws / subject with replacement), and closed the missing
historical analysis-code provenance append-only. This re-audit does **not** reopen any
of those corrections.

## 3. Independent re-audit finding

```text
finding:      TRAIN-refit successful-subset interval behavior violated frozen section 17
class:        protocol-conformance-must-fix
```

The pre-reaudit `_train_refit_stability` implementation refit the **full procedure
panel atomically** once per replicate and, on any refit failure, recorded the failure
and `continue`d. It then computed each procedure's TRAIN-refit interval from whichever
replicates happened to succeed. Two distinct violations followed:

1. **Successful-subset inference.** With, say, 1,999 of 2,000 replicates succeeding,
   an interval could still be produced from the 1,999 successful replicates. Frozen
   `R3_PROTOCOL.md §17` forbids this: the affected procedure/model block must be
   `INCOMPLETE`, and no interval may be computed from a successful subset.
2. **Panel-atomic failure suppression.** Because `fit_panel(resampled, procedures)` was
   atomic, a failure in any one procedure suppressed the entire replicate for *all*
   procedures, contradicting §17's rule that only the affected procedure/model block
   becomes `INCOMPLETE` while other blocks remain reportable.

## 4. Frozen failure contract (as now implemented)

For each `model × procedure` block:

```text
planned_replicates      = 2000
successful_replicates   = count of replicates whose procedure refit succeeded
failed_replicates       = count of replicates whose procedure refit failed
failures                = exact records: {replicate, procedure_label, error_type, message}

if failed_replicates == 0:  status = COMPLETE
if failed_replicates >  0:  status = INCOMPLETE
```

For an `INCOMPLETE` procedure:

```text
interval = null            (no successful-subset interval is ever emitted)
point    = full-TRAIN reference point estimate (retained; not a bootstrap estimate)
```

Unchanged and preserved: one deterministic resampled TRAIN multiset per replicate,
reused across every procedure; exactly 10 TRAIN item-position draws per subject with
replacement; no retry; no replacement replicate; no substitute sample; the full-TRAIN
reference fit and its fail-closed behavior are untouched.

## 5. The fix

Commit:

```text
8996e6760a7c5d424edbd5747ee5c6caffca4283   fix: fail closed on R3 train-refit instability
```

Files:

```text
experiments/calibration_transport/r3_analysis.py
experiments/calibration_transport/tests/test_r3_analysis.py
```

Change: the bootstrap refit loop now refits **each procedure independently** from the
same per-replicate resampled multiset (`fit_panel(resampled, (procedure,))`), records
failures at procedure granularity, and gates the interval on `failed == 0`. A failure
in one procedure no longer destroys any other procedure's stability block. New tests
prove the contract directly, including a spy test that asserts `_interval()` is never
invoked for an incomplete procedure.

## 6. Raw / frozen evidence impact

```text
raw_artifacts_rewritten:                          false
frozen_scientific_design_changed:                 false
official_confirmatory_statistical_outcome_computed: false
```

The two official raw measurement JSONs and the raw evidence index are byte-identical to
their frozen state (SHA256 values re-verified after all edits). No model rerun and no
population rebuild were required or performed.

## 7. Tests and verification

```text
uv run pytest experiments/calibration_transport/tests/test_r3_analysis.py \
              experiments/calibration_transport/tests/test_r3_protocol.py
uv run pytest experiments/calibration_transport/tests/
uv run ruff check .
uv run ruff format --check .
```

All pass. All prior conformance tests (`g_CAT(S_OVR)`, `g_OVR(S_CAT)`, cross Brier /
LogLoss / reliability oracles, SOURCE TRAIN geometry, TARGET TEST outside fractions,
nearest-rank 2.5/97.5 diagnostic, range-loss decomposition, 10 draws / subject,
deterministic TRAIN-refit sampling) remain green.

## 8. Non-claims

```text
No R3 Brier result, exact LogLoss value, cross/native/raw contrast,
committed calibrator parameter, 20,000-replicate TEST bootstrap interval,
2,000-replicate TRAIN-refit stability result, native-reference state,
accuracy aggregate, winner-agreement aggregate, or empirical score-geometry
summary was computed as part of this task.
```

Nothing in this correction was selected or tuned based on observed R3 results; the
correction implements the frozen section 17 text as written, before any confirmatory
statistical outcome was produced.

## 9. Supersession

```text
The previous closure record `R3_ANALYSIS_ENTRY_GATE.md` was not silently deleted
or amended. This new record supersedes its analysis-entry status after a later
re-audit finding, and is chain-linked by commit hash and by the machine-readable
artifact `results/r3-analysis-entry-reaudit-v1.json`.
```

## 10. Gate outcome

```text
TRAIN-REFIT FAILURE-CONTRACT CLOSURE COMPLETE

RAW EVIDENCE PRESERVED

FROZEN SCIENTIFIC DESIGN UNCHANGED

OFFICIAL R3 CONFIRMATORY ANALYSIS:  NOT RUN

NEXT GATE:  HUMAN RE-AUDIT

PUSH: NO
```
