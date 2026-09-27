# R3 Final Pre-Analysis Audit (Secondary-Path Census + Native-Winner Closure)

```text
audit kind:                                FINAL PRE-ANALYSIS STATIC SEMANTIC AUDIT
outcome review:                            NO (no R3 result was read or computed)
raw evidence:                              PRESERVED / BYTE-FROZEN
protocol:                                  UNCHANGED
population:                                UNCHANGED
model rerun:                               NOT REQUIRED
population rebuild:                        NOT REQUIRED
frozen scientific design:                  UNCHANGED
official R3 confirmatory statistical analysis:  NOT RUN
analysis implementation:                   CORRECTED TO FROZEN END-TO-END WINNER SEMANTICS
analysis provenance closure:               APPEND-ONLY (previous records preserved)
analysis-entry authorization:              STILL REQUIRES HUMAN FINAL AUTHORIZATION
```

## 1. Purpose and scope

This record closes the last known pre-analysis semantic defect before any R3
confirmatory analysis may be authorized. It is a **static semantic audit of the
analysis code and its inputs**: no R3 statistical outcome was computed, printed,
logged, or inspected. The two earlier audit records are preserved unchanged:

```text
R3_ANALYSIS_ENTRY_GATE.md
R3_ANALYSIS_ENTRY_REAUDIT.md
```

Neither is deleted, rewritten, or amended.

## 2. Commit chain (all local; origin/main is unchanged)

```text
3a929a6931762a518498ad9df2e5f82cf6e6deed   experiment: freeze R3 confirmatory protocol
12f602a9527f0db4b1575abe6999235a40d55ef6   fix: clarify R3 cross-split contamination guard
8b1ea40aee0e7518c2ab3b25a8cc6d4ec2d0f800   experiment: freeze R3 official measurement runner
ba90a6c325b764347feaa5ba9cc5b8956d36cb21   experiment: record R3 raw confirmatory measurements
5829a8650c826c2521ce3287764d3f83b582f015   fix: conform R3 analysis to frozen protocol
fa97d6f548c2d1b820f076225e28527fde3c669a   docs: record R3 pre-analysis closure
8996e6760a7c5d424edbd5747ee5c6caffca4283   fix: fail closed on R3 train-refit instability
1fdd373a6bbc0359d79aa17f2b1ca097c9bd132d   docs: record R3 train-refit closure re-audit
b4afae24b1a8b84f65fa7c842850a225c35ef376   fix: use native winners in R3 diagnostics
```

`b4afae24b1a8b84f65fa7c842850a225c35ef376` is the new implementation commit from this
round. The four earlier local closure commits (`5829a865`, `fa97d6f`, `8996e676`,
`1fdd373`) are preserved unchanged. The historical raw evidence commit is
`ba90a6c325b764347feaa5ba9cc5b8956d36cb21`, and the historical pre-outcome analysis
code commit is `3a929a6931762a518498ad9df2e5f82cf6e6deed`.

## 3. Complete secondary-path static census

Every frozen required secondary-analysis path was read end-to-end and checked against
the frozen protocol's required input semantics. Verdicts after the fix:

| secondary path | frozen semantic input | actual code input | verdict |
| --- | --- | --- | --- |
| exact LogLoss | raw `S_B`; native `g_B(S_B)`; cross `g_A(S_B)` | raw `_target_score`; native `target` calibrator on `_target_score`; cross `_cross_predictions` → `_cross_prediction` | PASS |
| 10-bin reliability | same three legs; empty bins retained | raw `_target_score`; native `target` calibrator on `_target_score`; cross `_cross_prediction` | PASS |
| empirical score geometry | SOURCE TRAIN min/max + 2.5–97.5%; TARGET TEST outside fractions | `_source_score` over TRAIN; `_target_score` over TEST; `nearest_rank_percentile` | PASS |
| range-loss decomposition | boundary = SOURCE TRAIN `[min,max]`; cross `g_SOURCE(S_TARGET)` | `_source_score` over TRAIN; `_cross_prediction`; diff vs raw Brier | PASS |
| end-to-end winner diagnostics | recorded native CAT/OVR winners vs truth; agreement = winner identity | recorded native winners via `winner_record_from_evidence` → `end_to_end_diagnostics` | PASS_AFTER_FIX |
| TRAIN-refit stability | 10 draws/subject with replacement; one resample/replicate; procedure-level `INCOMPLETE`, no subset interval | `resample_train_multiset`; per-procedure refit; interval gated on `failed == 0` | PASS |
| native-reference assessment | native `g_B(S_B) − raw`; m=8 tails | `_native_loss`/`_raw_loss`; `NATIVE_PERCENTILES` | PASS |
| primary TEST bootstrap | subject-stratified paired, deterministic, 20,000 | `_cross_loss`; `_draw_index`; `TEST_BOOTSTRAP_ID` | PASS |

**New mismatches discovered beyond the known winner defect: NONE.**

### 3.1 Score-leg audit (`.apply()` / `_target_score` / `_source_score` / `_cross_prediction`)

Every calibrated-application site in `r3_analysis.py` was classified; no ambiguous
score leg remains:

```text
_cross_prediction          : g_SOURCE(S_TARGET)                     cross
_native_loss               : g_TARGET(S_TARGET)                     native
reliability native branch  : g_TARGET(S_TARGET)                     native
exact_logloss native branch: g_TARGET(S_TARGET)                     native
raw branches               : S_TARGET                               raw
score geometry / range-loss: S_SOURCE over TRAIN, S_TARGET over TEST diagnostics
```

## 4. The winner-diagnostic mismatch and its root cause

The pre-fix `end_to_end_diagnostics` reported:

```text
cat_own_winner_accuracy = mean( (cat_score >= 0.5) == (label == 1.0) )
ovr_own_winner_accuracy = mean( (ovr_score >= 0.5) == (label == 1.0) )
winner_agreement        = mean( (cat_score >= 0.5) == (ovr_score >= 0.5) )
```

This is invalid. The frozen fixed-decision anchor score answers *"what probability did
this measurement assign to the frozen anchor `D_i`?"* — it does **not** answer *"which
candidate did this measurement choose as its own winner?"*. For OVR, the four
independent binary scores are not a simplex, so `anchor_score >= 0.5` is not winner
identity. The diagnostic silently reported a threshold classification instead of the
recorded native decision.

## 5. Raw winner evidence (the true source)

The frozen raw evidence already records the native winners per item (validated to be
members of the frozen candidate set):

```text
item["ground_truth_value"]
item["cat"]["record"]["winner"]
item["ovr"]["record"]["winner"]
```

No model rerun was required or performed: the winners were already measured and frozen.

## 6. The fix

```text
commit:  b4afae24b1a8b84f65fa7c842850a225c35ef376   fix: use native winners in R3 diagnostics
files:   experiments/calibration_transport/r3_analysis.py
         experiments/calibration_transport/tests/test_r3_analysis.py
```

Semantics now implemented:

```text
cat_own_winner_accuracy = mean( cat_winner == ground_truth_value )
ovr_own_winner_accuracy = mean( ovr_winner == ground_truth_value )
winner_agreement        = mean( cat_winner == ovr_winner )
```

- A new frozen `R3WinnerRecord` carries the winner-diagnostic data **separately** from
  the fixed-decision probability row `R3Item`, so probability data and winner data are
  never conflated.
- `winner_record_from_evidence` reads the recorded winners and ground truth verbatim and
  fails closed when a structurally SCORED block lacks a recorded winner. It never
  consults an anchor score, a candidate-score threshold, or a calibrated probability.
- `_require_winner_population` enforces that winner diagnostics cover exactly the
  eligible fixed TEST rows (no winner-only subset, no dropped/replaced rows).
- No anchor `0.5` threshold and no calibrated probability participates; winner agreement
  never affects row eligibility.

## 7. Raw → analysis ingestion audit

There is currently **no** official raw-evidence → `R3Item` runner: `r3_analysis._main`
refuses to run, and `R3Item` is constructed only in tests. That absence is by design
(analysis is not yet authorized). This round added only the single-item winner mapping
`winner_record_from_evidence` (not a runner and not a parallel ingestion path); the full
official ingestion runner remains a separately authorized future step.

## 8. Fisher-combination provenance wording clarification

The prior machine-readable record `results/r3-analysis-entry-reaudit-v1.json` lists an
`analyses_not_run` entry reading `"Fisher combination / six primary factorial contrasts"`.
Frozen R3 does **not** define a Fisher combination as part of its six primary factorial
contrasts; the wording is misleading. This is clarified append-only (the prior record is
not amended):

```text
previous wording:   "Fisher combination / six primary factorial contrasts"
corrected meaning:  "six primary factorial contrasts"
scientific impact:  NONE
outcome impact:     NONE
reason:             provenance wording correction only
```

Fisher combination was never part of frozen R3.

## 9. Raw / frozen immutability

```text
MiniCPM raw SHA256:   e7b45e921d35523f9fb6aabaefe10e585f43f35f25e5e4159bb2211cec8b999b
Qwen raw SHA256:      00a1d04e6cb308cf609ccf3cde69b761497c4a3a110704ea069f3e933cf9248a
raw index SHA256:     b04351acd878161d21022f3e5f5f08da1443977a484f62c8ba465adba051c461
```

Re-verified after all edits: unchanged. No change to the research specs, `R3_PROTOCOL.md`,
`r3_protocol_design.json`, the population manifest, the measurement runner, the two raw
JSONs, or the raw evidence index.

## 10. Tests and verification

```text
uv run pytest experiments/calibration_transport/tests/test_r3_analysis.py \
              experiments/calibration_transport/tests/test_r3_protocol.py \
              experiments/calibration_transport/tests/test_r3_raw_evidence.py   -> pass
uv run pytest experiments/calibration_transport/tests/                            -> 375 passed
uv run ruff check .                                                               -> All checks passed
uv run ruff format --check .                                                      -> already formatted
```

New native-winner oracles include: CAT winner correct with anchor `< 0.5`; OVR winner
correct with every candidate score `< 0.5`; threshold classes agreeing while recorded
winners disagree; threshold classes differing while recorded winners agree; winner-input
sourcing from the raw record; empty/subset/extra winner populations failing closed; and a
SCORED row without a recorded winner failing closed. All prior conformance tests remain
green.

## 11. Non-claims

```text
No R3 Brier result, exact LogLoss value, cross/native/raw contrast, factorial contrast,
20,000-replicate TEST bootstrap interval, 2,000-replicate TRAIN-refit result,
native-reference state, accuracy aggregate, winner-agreement aggregate, support
diagnostic, or empirical score-geometry summary was computed as part of this task.
```

Nothing in this correction was selected or tuned based on observed R3 results; it
implements the frozen protocol's recorded-native-winner semantics before any confirmatory
statistical outcome was produced.

## 12. Gate outcome

```text
SECONDARY-PATH STATIC CENSUS COMPLETE

NATIVE-WINNER DIAGNOSTIC CLOSURE COMPLETE

TRAIN-REFIT FAILURE CONTRACT REMAINS CLOSED

RAW EVIDENCE PRESERVED

FROZEN SCIENTIFIC DESIGN UNCHANGED

OFFICIAL R3 CONFIRMATORY ANALYSIS:  NOT RUN

ANALYSIS-ENTRY CANDIDATE:  READY FOR HUMAN FINAL AUTHORIZATION

PUSH: NO
```
