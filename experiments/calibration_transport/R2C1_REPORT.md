# Research R2C.1 — Low-Regularization Numerical Adequacy Closure

No new model measurements were collected.
No calibration method, lambda, split, or data was changed.
This round only audits the numerical completeness of the predeclared
`lambda = 1e-6` train-refit configurations from R2C.

- Round: `low-regularization-numerical-adequacy-closure` v1
- Design: `r2c1_numerical_closure_design.json`
  (fingerprint `b40e070859df360d78d85250ea1f3e3a2b3a4836c32132561da58606e77ef49d`)
- Source R2B raw: `results/r2b-stability-qwen35-2b-v1.json`
  (sha256 `16a07ecd69a4ec0081f76790b7bde0b4e8bcd87172e06b7af94c06ea699967a4`, unmodified)
- Source R2C analysis: `results/r2c-method-adequacy-qwen35-2b-v1-analysis.json`
  (sha256 `8b90dbb02c4cdb2d47ceb2e7e0933aa10be05aab3979614634cf43b9e7841018`, unmodified)
- Result artifact: `results/r2c1-low-reg-numerical-closure-v1-analysis.json`
  (sha256 `4a565f1cc97bbd3b9ebee9da0c6eabad185e82fc23c4607b2126c689f9a2220a`;
  classification metadata corrected in the final closure without any numerical
  recomputation)
- Predeclared classification result: **no exact match**; the closest preregistered
  family is **A** (a binary64 numerical-path limitation), but the preregistered A
  submechanism was falsified (see §8).
- Observed mechanism: `binary64-solver-path-stalls-before-certifiable-point` v1.

## 0. Why R2C.1 exists

R2C's train-refit bootstrap fails closed at `lambda = 1e-6`: 15 of 20 000 refits
cannot be certified by the reused binary64 solver, so those two configurations'
train-refit blocks were marked `failed` with no interval, and the R2C round status
became `incomplete`. R2C.1 asks exactly one question:

> Are those 15 uncertifiable fits a pathology of the objective / statistical fit,
> or is the *same* objective already near its optimum in binary64 while the frozen
> sufficient gradient certificate reaches a numerical precision / conditioning
> floor?

It adds no data, model, GPU, network, lambda, or calibration family, and it never
touches `src/`.

## 1. Frozen source lineage

Both source artifacts are byte-identical before and after R2C.1:

- R2B raw sha256 unchanged at
  `16a07ecd69a4ec0081f76790b7bde0b4e8bcd87172e06b7af94c06ea699967a4`.
- R2C analysis sha256 unchanged at
  `8b90dbb02c4cdb2d47ceb2e7e0933aa10be05aab3979614634cf43b9e7841018`.
- `git diff` of `R2B_REPORT.md`, `R2C_REPORT.md`, the R2B raw artifact, and the
  R2C analysis artifact is empty.

## 2. Exact unresolved set (verified, not assumed)

The committed R2C analysis artifact reports exactly 15 failures, all at
`lambda = 1e-6`. R2C.1 re-derived the failure set live by re-running the
production float64 solver on all 4000 resamples and it matches the frozen design
exactly (`recomputed_float64_failure_count = 15`, `matches_frozen_r2c = true`):

| family | measurement | replicates |
| --- | --- | --- |
| P | CAT | 452 |
| P | OVR | 169 |
| L | CAT | 125, 308, 444, 497, 549, 571, 936, 960, 995 |
| L | OVR | 81, 87, 253, 427 |

## 3. Reference solver contract

An independent, dependency-free reference optimizer (`decimal.newton`,
`decimal-newton-backtracking-reference` v1) on the Python standard-library
`decimal` module. It is a **numerical reference backend**, not a new calibration
family, not a new R2C configuration, and not an R3 candidate.

- arithmetic: stdlib `decimal` only (no mpmath/sympy/scipy/numpy)
- decimal precision: 80 digits; rounding `ROUND_HALF_EVEN`
- objective: `mean_i(softplus(a*x_i + b) - y_i*(a*x_i + b)) + (lambda/2)*(a^2+b^2)`,
  `lambda = Decimal("1e-6")`
- convergence certificate: `||grad||^2 / (2*lambda) <= 1e-24`
- own 2x2 Newton solve; Armijo `c = 1e-4`, backtracking `0.5`, max 200 steps
- fixed start `(a, b) = (0, 0)`; max 500 Newton iterations
- no adaptive precision

Feature semantics match R2C exactly: Family P uses `Decimal.from_float(p)`; Family
L uses `Decimal.from_float(logit(p))` where `logit(p)` is the R2C binary64 logit
transform. The reference never re-defines a "more precise" feature. Labels are
`Decimal(0)`/`Decimal(1)`.

## 4. Full-N reference sanity

The four full-90-TRAIN `lambda = 1e-6` reference fits agree with the R2C point
estimates (and with the R2C artifact's stored calibrators, exact match
`true` for all four):

| group | float64 vs reference objective-gap upper | parameter distance | matches R2C artifact |
| --- | --- | --- | --- |
| P CAT | 2.82e-28 | 5.37e-16 | true |
| P OVR | 5.75e-22 | 8.59e-10 | true |
| L CAT | 8.45e-20 | 2.70e-09 | true |
| L OVR | 5.77e-20 | 1.86e-09 | true |

## 5. 4000-fit completion

The high-precision reference was run for **all** 4000 `lambda = 1e-6` train-refit
fits (P/CAT 1000, P/OVR 1000, L/CAT 1000, L/OVR 1000), reusing the exact R2C
`sha256-r2c-paired-train-refit-bootstrap` v1 draws and the same shared multiset
per replicate.

- attempted: **4000**
- certified: **4000**
- failed: **0**

So the entire `lambda = 1e-6` train-refit summary now comes from one numerically
consistent backend, not a hybrid of 3985 float64 and 15 Decimal fits.

## 6. Successful-float64 validation

The 3985 fits the production binary64 solver *did* certify are used as a
cross-implementation validation set. For each, the binary64 objective at the
float64 parameters and at the reference optimum was recomputed in high precision:

- successful float64 fits: **3985**
- agreement gate (`float64_actual_gap_upper <= 2e-14`): **3985 / 3985 passed**
- overall maximum `float64_actual_gap_upper`: `7.93e-16`
- agreement violations: **0**

| group | n | max gap upper | median gap upper | max param dist | median param dist |
| --- | --- | --- | --- | --- | --- |
| P CAT | 999 | 8.50e-17 | 1.34e-25 | 3.60e-06 | 1.38e-11 |
| P OVR | 999 | 4.95e-18 | 8.42e-25 | 1.17e-07 | 3.11e-11 |
| L CAT | 991 | 7.93e-16 | 7.76e-24 | 1.41e-05 | 2.27e-10 |
| L OVR | 996 | 6.26e-19 | 2.68e-25 | 1.06e-08 | 2.49e-12 |

Parameter-distance columns are descriptive only; no pass/fail threshold is
imposed on them.

## 7. Fifteen failure diagnostics

Per failed fit: the reference optimum, its own gap bound, the actual objective
gap at the nearest binary64 point (`float(a_ref)`, `float(b_ref)`), the
production-style binary64 gradient norm at that rounded point (production
certificate threshold `sqrt(2)*sqrt(1e-6)*sqrt(1e-14) = 1.4142e-10`), and the
minimum production-style gradient norm over the `5x5` `math.nextafter`
neighbourhood (radius 2 ULP).

| fam | meas | rep | ref slope | ref intercept | ref gap | rounded gap | rounded meets 1e-14 | prod grad @rounded | prod cert met | ULP min grad | ULP ratio |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P | CAT | 452 | 7.0229462245 | -3.9253552094 | 1.46e-28 | 1.46e-28 | true | 9.28e-18 | true | 6.92e-18 | 0.0000 |
| P | OVR | 169 | 5.8416326995 | -3.3093916001 | 1.02e-31 | 1.03e-31 | true | 3.78e-17 | true | 9.95e-18 | 0.0000 |
| L | CAT | 125 | 1.1990101516 | -1.1480988102 | 3.77e-30 | 3.77e-30 | true | 3.16e-18 | true | 3.16e-18 | 0.0000 |
| L | CAT | 308 | 0.8204669104 | -0.7220467016 | 7.93e-31 | 7.94e-31 | true | 6.11e-18 | true | 4.59e-18 | 0.0000 |
| L | CAT | 444 | 1.3340910323 | -0.6665787411 | 3.78e-29 | 3.78e-29 | true | 4.29e-18 | true | 3.59e-18 | 0.0000 |
| L | CAT | 497 | 1.2590577220 | -0.8231741374 | 6.11e-29 | 6.11e-29 | true | 1.68e-17 | true | 3.47e-18 | 0.0000 |
| L | CAT | 549 | 1.2432895044 | -0.7946196923 | 1.30e-28 | 1.30e-28 | true | 9.41e-18 | true | 8.34e-18 | 0.0000 |
| L | CAT | 571 | 1.3156762630 | -0.9960116065 | 1.99e-31 | 2.00e-31 | true | 9.49e-18 | true | 5.99e-18 | 0.0000 |
| L | CAT | 936 | 0.6718752620 | -0.5479469727 | 6.17e-32 | 6.19e-32 | true | 2.32e-18 | true | 2.32e-18 | 0.0000 |
| L | CAT | 960 | 1.1381505859 | -0.6445310449 | 3.17e-31 | 3.18e-31 | true | 4.90e-18 | true | 3.59e-18 | 0.0000 |
| L | CAT | 995 | 1.2013273828 | -1.9924911847 | 1.07e-30 | 1.07e-30 | true | 3.37e-17 | true | 3.90e-18 | 0.0000 |
| L | OVR | 81 | 1.5071745904 | -0.0961863201 | 8.71e-29 | 8.71e-29 | true | 1.93e-17 | true | 2.16e-18 | 0.0000 |
| L | OVR | 87 | 2.5121479721 | -0.1930191434 | 4.14e-28 | 4.14e-28 | true | 3.55e-17 | true | 1.10e-17 | 0.0000 |
| L | OVR | 253 | 2.5327021388 | -0.1594481896 | 5.16e-30 | 5.16e-30 | true | 1.12e-17 | true | 2.71e-18 | 0.0000 |
| L | OVR | 427 | 1.9021204207 | -0.8092003673 | 2.06e-30 | 2.06e-30 | true | 7.86e-18 | true | 3.55e-18 | 0.0000 |

The reference certifies every fit with a gap bound of order `1e-28` to `1e-32`
(far below the `1e-24` reference tolerance). Every rounded reference point is
already within the declared `1e-14` objective-gap tolerance.

## 8. Numerical classification and the audited mechanism

The predeclared A/B/C/D mechanism taxonomy had **no exact match** for the observed
result. The closest predeclared family is **A** (a binary64 numerical-path
limitation), but the preregistered A submechanism was **not supported**.

The preregistered A submechanism was: "a binary64 point near the optimum meets the
objective-gap tolerance, while the frozen sufficient gradient certificate cannot
certify it." **Contrary to that submechanism, all 15 rounded high-precision
reference points satisfy both the declared `1e-14` objective-gap tolerance and the
frozen sufficient gradient certificate.** In all 15 cases the production-style
gradient norm at the rounded reference is `~1e-18` to `~4e-17`, *below* the
production threshold `1.4142e-10`.

The observed limitation is instead that the frozen binary64 Newton/backtracking
solver path fails to reach such a certifiable point for these resamples. A trace of
the frozen solver on two failing fits (P OVR rep 169 and L CAT rep 125) is
consistent with a binary64 solver-advancement / line-search precision floor:

- The frozen binary64 Newton solver converges to a point `~6e-9` to `~3e-8` in
  parameter distance from the high-precision optimum, then its iterates stop
  changing (no representable objective decrease remains along the low-curvature
  direction, whose objective differences fall below the binary64 resolution of the
  objective).
- At that stalled iterate the float64 gradient norm is `~2.0e-10` (P OVR 169) and
  `~2.3e-10` (L CAT 125), just *above* the `1.4142e-10` threshold, so the frozen
  certificate is not established within the iteration budget.
- Only two fits were traced in detail; this is **not** an individually proven
  Armijo-failure diagnosis for all 15. It is the minimal common conclusion the
  frozen evidence supports.

So the objective is mathematically well-defined and high-precision solvable at
`lambda = 1e-6`, and a certifiable binary64 representation exists; the limitation
is a **solver-path numerical limitation** (the frozen binary64 Newton/backtracking
path does not uniformly advance to a certifiable point). The sufficient gradient
certificate itself is not defective, and there is no claim that binary64 cannot
represent a certifiable solution. The ULP-neighbourhood diagnostic is consistent
with this: the minimum gradient norm within 2 ULP of the reference (ratio `0.0000`
of the threshold) is many orders of magnitude below the threshold. That
neighbourhood result is local only; it does not prove that no binary64 point
anywhere fails the certificate.

The result artifact records this as `predeclared_classification_result`
(`exact_match = null`, `closest_family = "A"`,
`preregistered_a_submechanism_supported = false`) together with
`observed_mechanism = {id: "binary64-solver-path-stalls-before-certifiable-point",
version: 1}`. It does not store a bare `classification = A`, so the falsified
submechanism is not misrepresented as an exact match.

## 9. Completed `P:1e-6` train-refit summaries (reference-only)

Intervals use the frozen nearest-rank percentile rule `[p2.5, median, p97.5]`,
1000 replicates.

| quantity | interval | sign fractions |
| --- | --- | --- |
| native CAT | [-0.000107, +0.001709, +0.037445] | neg 0.114 |
| native OVR | [-0.022649, -0.019032, -0.002857] | neg 0.984 |
| transport CAT->OVR | [-0.002878, +0.042536, +0.229048] | neg 0.047, pos 0.953 |
| transport OVR->CAT | [-0.035615, -0.000450, +0.005614] | neg 0.544, pos 0.456 |

Parameter intervals: CAT slope `[6.047, 8.821, 95.131]`; OVR slope
`[5.731, 10.158, 18.442]`.

## 10. Completed `L:1e-6` train-refit summaries (reference-only)

| quantity | interval | sign fractions |
| --- | --- | --- |
| native CAT | [-0.000414, +0.003399, +0.042456] | neg 0.127 |
| native OVR | [-0.022506, -0.018670, -0.002366] | neg 0.983 |
| transport CAT->OVR | [+0.009547, +0.058914, +0.229607] | neg 0.001, pos 0.999 |
| transport OVR->CAT | [-0.040027, -0.001396, +0.004538] | neg 0.599, pos 0.401 |

Parameter intervals: CAT slope `[0.788, 1.234, 34.476]`; OVR slope
`[1.290, 2.332, 4.390]`.

The negative/positive fractions are exploratory resampling frequencies, not
probabilities or posterior statements.

## 11. Impact on the R2C conclusions

Filling the `lambda = 1e-6` gap does **not** materially change R2C's qualitative
method-sensitivity conclusions:

- **CAT**: no improvement. `native CAT` is centered slightly above zero with only
  `0.11`–`0.13` of resamples negative; this matches R2C's "no pre-declared
  configuration lowers CAT Brier".
- **OVR**: low-`lambda` improvement holds. `native OVR` is median-negative with
  `0.98` negative fraction for both families, matching R2C's finding that low
  `lambda` removes the OVR degradation.
- **CAT->OVR**: sign is **positive** at `lambda = 1e-6` (median `+0.043` for P and
  `+0.059` for L; `0.95`–`0.999` positive), consistent with R2C's "the R2B
  `CAT->OVR < 0` direction flips at low lambda".
- **OVR->CAT**: near zero and mixed-sign at `lambda = 1e-6`, consistent with the
  low-lambda region of R2C.

## 12. Production-contract implication

None. The audit changes no production source. It does not require changing the
production solver, its tolerance, its iterations, or its certificate, and it does
not change the method, objective, or version. No production defect was found; the
limitation is confined to the exploratory `lambda = 1e-6` research setting under
the frozen binary64 kernel. `lambda = 1e-6` is retained (not removed) as a
pre-declared configuration with a documented numerical-operational limitation.

## 13. Determinism

The numerical closure was run three times (two to a scratch path with a clean tree,
then the identical output placed at the result path). All numerical runs were
byte-identical at:

- run sha256: `ed69ccd11a54125d4d7f835ee88e3780af4f9387ac1ce9f1cfc1094ee6911f9e`

The final closure then re-rendered only the classification/interpretation metadata
of that artifact via `reclassify_artifact` (no refit, no numerical recomputation),
producing the committed artifact:

- committed sha256: `4a565f1cc97bbd3b9ebee9da0c6eabad185e82fc23c4607b2126c689f9a2220a`

The re-render is deterministic, and the numerical projection (all quantitative
evidence, source lineage, failure identities, reference diagnostics, and bootstrap
summaries) is exactly equal to the pre-correction artifact. The artifact contains
no timestamp, UUID, or wall-clock field.

## 14. Scope

R2C.1 selects no calibration method, chooses no lambda, and authorizes no R3 work.
It is not confirmatory evidence. Human Research Gate decision: **PENDING**.

## Appendix A — First-round findings (disclosed)

1. **Completed-summary raw Brier baseline bug.** The first implementation of the
   completed `lambda = 1e-6` summaries computed the raw-target baseline as
   `sigmoid(raw score)` instead of the plain squared error `(p - y)^2`, which
   produced absurd native deltas (median `~-0.16` for CAT, inconsistent with R2C's
   `+0.0004` point estimate). Root cause: an identity-calibrator helper was used
   where the raw baseline must bypass any calibrator. Fix: a dedicated `_raw_brier`
   of `mean((p_i - y_i)^2)`. Regression:
   `test_raw_brier_is_plain_squared_error` and
   `test_reference_native_delta_matches_r2c_point_estimate` (the latter would have
   failed before). The first (buggy) artifact was deleted and regenerated. No
   version or identity impact; `src/` untouched.

2. **Hypothesis/mechanism correction (final closure).** The preregistered
   classification-A sub-claim (frozen gradient certificate unmet at a
   tolerance-meeting point) was not observed: the rounded reference meets the
   frozen gradient certificate
   (`production_certificate_met_at_rounded_count = 15`). The preregistered taxonomy
   therefore has **no exact match**; the closest family is A, and the A submechanism
   is recorded as unsupported. The observed mechanism is
   `binary64-solver-path-stalls-before-certifiable-point` v1 (§8). The
   classification metadata was corrected from a bare "A" to this honest
   predeclared-vs-observed structure by a classification-only re-render
   (`reclassify_artifact`), with **no numerical recomputation**: the fitted values,
   intervals, sign fractions, and failure identities are unchanged.

## Appendix B — Provenance

```
round_id                       = low-regularization-numerical-adequacy-closure v1
reference solver               = decimal-newton-backtracking-reference v1
design fingerprint             = b40e070859df360d78d85250ea1f3e3a2b3a4836c32132561da58606e77ef49d
r2c1_design_commit             = 431b45c1a43306785d9ee6582597af84ae2b2382
r2c1_execution_commit          = 0b28ed2d600361c4a13650e7a76e3a94869c5bd9
git_worktree_clean             = true
source R2B raw sha256          = 16a07ecd69a4ec0081f76790b7bde0b4e8bcd87172e06b7af94c06ea699967a4
source R2C analysis sha256     = 8b90dbb02c4cdb2d47ceb2e7e0933aa10be05aab3979614634cf43b9e7841018
R2C.1 analysis artifact sha256 = 4a565f1cc97bbd3b9ebee9da0c6eabad185e82fc23c4607b2126c689f9a2220a
```

Human Research Gate decision: **PENDING**. No push performed.
