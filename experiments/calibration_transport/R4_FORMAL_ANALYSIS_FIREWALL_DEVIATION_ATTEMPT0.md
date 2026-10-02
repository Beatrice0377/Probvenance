# R4 Formal Analysis — Firewall Deviation (Attempt 0)

```text
artifact_type:                        r4-formal-analysis-firewall-deviation
artifact_version:                     1
deviation_id:                         r4-formal-analysis-firewall-deviation-attempt0
deviation_type:                       UNAUTHORIZED_REAL_FIT_STATUS_EXPOSURE
formal_outcome_estimates_computed:    false
real_calibrator_fit_attempt_occurred: true
scientific_interpretation_performed:  false
persisted_fit_parameters:             false
persisted_scientific_results:         false
scientific_design_changed_after_exposure: false
disposition:                          DO_NOT_USE_FOR_SELECTION_OR_INTERPRETATION
deviation_fingerprint:                ba8dd5a155e1c42fe2693d59e2067b6b6dfe97dceea58686303651b7098c0dc4
fingerprint_version:                  1
```

This document records a **limited analysis firewall deviation** that occurred before the runner
closure was complete. It is a provenance record, **not** a formal result, and it carries no
scientific value.

---

## 1. What happened

```text
invocation_count:   1
nature:             one ad-hoc debug invocation
input:              frozen real TRAIN evidence (current-generation panel, budget N456)
mechanism:          run_r4_analysis.build_panel_inputs on the real frozen cells
```

A throwaway debug one-liner called `build_panel_inputs` on the **real** frozen cells rather than
on the synthetic fixture. That call fitted real calibrators, including `B-beta`, for the
current-generation panel. It was unintentional and was disclosed in the previous task report.

## 2. What was exposed

```text
- full-TRAIN fit availability status per fitted map (AVAILABLE / INELIGIBLE / FAILED)
- the exact exception class and message of a failed fit
- incidental: olmo-3-7b-instruct + r4-mmlu-57-subject + B-beta full-TRAIN fits,
  both directional roles, returned BetaImplementationError
  ("no constraint face produced an accepted optimum")
```

Only **fit status and exception identity** were visible. No fit parameters were inspected or
saved.

## 3. What was NOT computed and NOT inspected

```text
Brier
LogLoss
risk
Delta
bootstrap confidence intervals
factorial effects
direction contrasts
predictor X / Y
Spearman
model ranking
```

```text
output_written_to_disk:  false
artifact_changed:        false
```

## 4. Human adjudication

```text
classification:        LIMITED ANALYSIS FIREWALL DEVIATION
is_a_formal_result:    false
```

`DO_NOT_USE_FOR`:

```text
scientific inference
estimator selection
procedure selection
threshold selection
family selection
solver modification
```

The study is **not** discarded because:

```text
- beta gate-9 failure handling had already been human-adjudicated before this accidental exposure
- scientific procedure identities remain frozen
- no scientific threshold, family or estimator changed
```

## 5. Closure

```text
recorded_before_any_new_real_fit: true
```

The runner now carries a defensive guard (`run_r4_analysis.assert_synthetic_inputs`) that
rejects any non-synthetic row inside the synthetic qualification path, so this class of exposure
cannot recur through the qualification entry point. The canonical measurement-level fitted-map
identity further removes the incentive to probe directional fits: one measurement is fitted once.

```text
PRIOR UNAUTHORIZED REAL FIT STATUS EXPOSURE = YES, provenance-only deviation recorded
FORMAL SCIENTIFIC OUTCOME ESTIMATES COMPUTED IN THIS CLOSURE TASK = NO
REAL CALIBRATOR FIT ATTEMPTS IN THIS CLOSURE TASK = NO
FORMAL RESULTS PRODUCED = NO
```
