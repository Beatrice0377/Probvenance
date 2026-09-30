# R4 Target-Label-Free Predictor — Implementation Engineering

Status: `PREDICTOR IMPLEMENTATION ENGINEERING`
R4 predictor semantics: `FROZEN`
R4 overall: `DRAFT / NOT FULLY FROZEN / NOT EXECUTION-AUTHORIZED`
Formal R4 execution: `NOT AUTHORIZED`

This document records the **engineering** implementation of the frozen R4
target-label-free predictor semantics. It is a synthetic-only engineering
record. It contains no study outcome, no model inference, no calibration fit,
and no formal R4 bootstrap.

---

## 1. Frozen authority inputs

| Item | Identity |
| --- | --- |
| Predictor freeze artifact | `experiments/calibration_transport/R4_PREDICTOR_FREEZE.json` |
| Predictor freeze fingerprint | `c856fcc161910497a3431593639606682905adcb50fc443455468dfc295d73a9` |
| Predictor freeze commit | `bc2562104a7e84b52aaf76fec613b874c431760d` |
| Predictor candidate fingerprint | `d3625912fadb5e6c68e20495256aa1f90b53686f13c9d25d1eb9ceb212dfbb06` |
| Predictor candidate commit | `ed2ba62ffdae7b1c9890682e3550b54021df6c99` |
| Inference freeze fingerprint | `dcbb7ac9e931145fdee86ab984de1249c1b86ca36ee735b70dafc8cabc06c141` |
| Inference amendment commit | `bdaa088a1f5b508c47875039d2cf2be5df1595a1` |
| Original inference implementation commit | `8c3bb0f0e4367bf7194f22a3f38d66aff3cbbbf7` |
| R3 protocol fingerprint | `3ef63056ae16b18ad65d9c87d1fbec5b43550873a0e3e25ec0a323f954ee974d` |
| Predictor implementation id | `r4-predictor-range-exceedance-w1-spearman-v1` |
| Validation protocol id | `r4-heldout-population-predictor-validation` (v1) |
| Spearman statistic id | `spearman-rank-correlation` (v1) |

The implementation module hard-codes the freeze fingerprint, the candidate
fingerprint and the inference freeze fingerprint as importable constants so
that a future formal run can assert identity before consuming anything.

---

## 2. Artifacts

| Path | Lines | SHA256 |
| --- | --- | --- |
| `experiments/calibration_transport/r4_predictor.py` | 1162 | `ccbfbbd681cf55d0cb1f7d3f12ba19e5cd68aa4c65d0ebf52045dc8f0fb2787e` |
| `tests/test_r4_predictor.py` | 1062 | `f6282b624988a55777be5410b5e6c3d2b50d1f0706c5db0b492a316f7bcfd040` |

The module is stdlib-only plus two research-layer imports:

```text
math, collections.abc, dataclasses, fractions, itertools, typing   (stdlib)
r4_inference                                                       (research layer)
probvenance.fingerprint                                            (core)
```

It imports **no** `numpy`, `scipy`, `random`, `torch` or `transformers`.

---

## 3. What this module is not

`r4_predictor.py` is research-layer infrastructure. It is **not** a result
loader, a model runner, or a formal R4 executor. It does not:

* auto-search score files,
* load an official result artifact,
* run a GPU,
* download datasets,
* run a formal 20000-replicate predictor bootstrap,
* fit a calibration family.

---

## 4. Label firewall

The frozen predictor is **target-label-free**: the predictor feature is a
function of raw scores only.

### 4.1 Signature-level firewall

```text
range_exceedance_warning(source_train_scores, target_test_scores)
wasserstein1_warning(source_train_scores, target_test_scores)
```

Both feature functions accept exactly two parameters. Neither accepts a label,
`Y`, ground truth, a calibrator, a native risk, a cross risk, or a transport
delta. This is asserted mechanically with `inspect.signature`.

### 4.2 Code-level firewall

The executable body (docstrings excluded, extracted with `ast`) of the feature
path —

```text
validate_predictor_score, validate_predictor_scores, source_quantile_levels,
source_thresholds, range_exceedance_warning, exact_empirical_wasserstein1,
wasserstein1_warning, _count_at_most
```

— contains none of the tokens

```text
ground_truth, correctness, brier, logloss, delta_transport, delta_deploy,
calibrator
```

The outcome-aggregation half of the module *may* name outcomes; that is why the
audit is scoped to the feature functions rather than applied to the whole file.

---

## 5. Score validation

Predictor raw scores must be real, finite and inside `[0, 1]`.

```text
exact 0    legal
exact 1    legal
NaN        PREDICTOR_INPUT_INVALID
+inf/-inf  PREDICTOR_INPUT_INVALID
< 0        PREDICTOR_INPUT_INVALID
> 1        PREDICTOR_INPUT_INVALID
```

Invalid values raise `PredictorInputInvalid` (state `PREDICTOR_INPUT_INVALID`).
Nothing is clipped, repaired or dropped. An empty score vector is rejected.

---

## 6. X_range — primary predictor

### 6.1 Source thresholds

```text
SOURCE = full primary N=456 SOURCE TRAIN raw scores
q_low  = nearest-rank 2.5%   (rank 12 at N=456)
q_high = nearest-rank 97.5%  (rank 445 at N=456)
```

The nearest-rank rule is the frozen `r4_inference` helper
(`percentile_rank` / `nearest_rank_percentile`): `rank = ceil(fraction * n)`
clamped to `[1, n]`, with **no interpolation**. The module does not implement a
second, semantically different quantile algorithm.

### 6.2 Exceedance fraction

```text
X_range = fraction(target_score < q_low OR target_score > q_high)
```

Boundary equality is **INSIDE** the source range. `range_exceedance_warning`
returns `source_count`, `target_count`, `q_low`, `q_high`, `outside_count` and
`fraction_outside`.

### 6.3 Boundary and invariance evidence

Covered by tests: below lower, equal lower, inside, equal upper, above upper,
plus deterministic permutation invariance of the input score order.

---

## 7. X_W1 — secondary predictor

### 7.1 Exact algorithm

Exact 1D empirical Wasserstein-1 with equal row mass, computed as a
**merged sorted-support CDF sweep**:

```text
W1(mu, nu) = integral |F_mu(t) - F_nu(t)| dt
```

The implementation merges the two sorted supports and accumulates
`|F_mu - F_nu| * (t_{i+1} - t_i)` over the merged breakpoints. When the union
support has fewer than two points the value is `0.0`.

Explicitly **not** used: histogram, binning, quantile-grid approximation,
random subsampling, SciPy.

### 7.2 Independent reference audit

Every W1 test fixture is cross-checked against a second, independent exact path
(quantile coupling on `[0, 1]` with the frozen nearest-rank quantile function):

```text
abs(primary - reference) <= 1e-12
```

Fixtures: identical distributions → 0; singletons `[0]` vs `[1]` → 1;
translation `[0.1, 0.2]` vs `[0.2, 0.3]` → 0.1; unequal sample counts; ties;
endpoints `0`/`1`; permuted inputs; plus three mixed multi-point fixtures. All
pass. Unequal `n`/`m` uses a genuine equal-mass empirical W1 — sorted arrays are
never naively zipped.

---

## 8. Spearman rank correlation

```text
rho = Spearman(X_range, Y_transport_core)  over exactly the 16 held-out units
```

* `average_ranks(values)`: ascending, 1-indexed, ties share the mean rank.
* `spearman_fixed_units(left, right)`: Pearson correlation of the two rank
  vectors.
* Constant input (either side has zero rank variance) raises `SpearmanUndefined`
  with state `SPEARMAN_UNDEFINED_CONSTANT_INPUT`.
* Length mismatch or fewer than two units raises `PredictorContractViolation`.

Evidence: perfect increasing → `+1`; perfect decreasing → `-1`; a tie fixture
compared against a hand-computed value (`4.5 / sqrt(4.5 * 5.0)`); constant X and
constant Y both raise; permutation invariance.

---

## 9. CORE4 outcome aggregation

```text
CORE4 = P-low, P-historical, L-low, L-historical
Y_transport_core = mean CORE4 Delta_transport
Y_deploy_core    = mean CORE4 Delta_deploy
```

Any missing CORE4 member raises `Core4Incomplete` with `.missing`. A 3-of-4
mean is impossible. Extra standalone procedures (`I-isotonic`, `B-beta`) are
reported as `ignored_extra_procedures` and can never change the CORE4 value.

---

## 10. Unit registries

```text
predictor unit = model x population x direction
```

The factorial procedure label `F` is **not** a unit key.

| Registry | Count | Composition |
| --- | --- | --- |
| `development_units()` | 8 | 4 current-generation models x 1 population (MMLU) x 2 directions |
| `primary_validation_units()` | 16 | 4 current-generation models x 2 populations (HellaSwag, MedMCQA) x 2 directions |
| `legacy_extension_units()` | 8 | 2 legacy models x 2 populations x 2 directions |

`unit_id` is answer-independent and deterministic:

```text
unit_id = fingerprint({
  protocol_id, protocol_version, model_id, population_id, direction_id
})
```

Role firewall: `require_primary_validation_unit`, `require_development_unit` and
`require_legacy_extension_unit` raise `PredictorRoleViolation`. A development
(MMLU) unit or a legacy model can never enter the primary 16-unit validation
panel.

---

## 11. Primary validation table

`validate_primary_validation_table(rows)` requires exactly the 16 frozen units:

* no duplicate unit,
* no missing unit,
* no extra unit,
* every `x_range`, `x_wasserstein1`, `y_transport_core`, `y_deploy_core`
  complete.

Any violation raises `PrimaryValidationIncomplete` (state
`PRIMARY_VALIDATION_INCOMPLETE`). Complete-case correlation is impossible: an
incomplete row cannot be silently dropped.

---

## 12. TEST bootstrap integration

### 12.1 Reuse of frozen samplers

The predictor module does **not** re-invent an MMLU sampler, a HellaSwag cluster
sampler or a MedMCQA sampler. It consumes the frozen `r4_inference`
`TestDraw` representation produced by `build_test_draw`.

| Population | Draw mode | Property |
| --- | --- | --- |
| HellaSwag | `activity-stratified-source_id-cluster` | `source_id` cluster never split |
| MedMCQA | `subject_name-stratified-row` | subject_name-stratified row bootstrap |
| MMLU | `subject-stratified-row` | development only |

### 12.2 Shared draw

For a given population and replicate index there is exactly **one** draw. The
same draw supplies the predictor X (`_draw_target_scores`) and the transport
outcome Y (`measurement.y_provider(draw)`). X and Y are never resampled
independently. This is asserted by tests that record the identity of the draw
handed to each provider and compare it against the shared draw map, and by a
test that recomputes the expected target score vector from the same draw.

A missing shared draw raises `BootstrapContractViolation`.

### 12.3 Fixed SOURCE thresholds

During the TEST bootstrap the SOURCE TRAIN `q_low` / `q_high` stay fixed at the
full primary TRAIN. TEST-sampling uncertainty and TRAIN uncertainty are
separate; the source is never re-bootstrapped per TEST replicate.

---

## 13. Fixed-panel inference scope

The predictor bootstrap resamples **only** TEST rows / clusters. It never
resamples models, populations or directions.

```text
The predictor validation bootstrap quantifies TEST-sampling uncertainty
conditional on the predeclared fixed 16-unit validation panel.

It does NOT resample models, populations, or directions.

It does NOT quantify uncertainty over: model selection, population selection,
direction selection, future model families, future benchmark populations.
```

Evidence: the draw stratum orders stay inside the frozen per-population strata,
every drawn row carries the frozen population id, and the unit set is the fixed
16 units for every replicate.

---

## 14. Bootstrap result state

```text
planned_replicates
successful_replicates
undefined_replicates   + undefined_indices
incomplete_replicates  + incomplete_indices
status
```

* A `None` transport outcome marks the replicate **incomplete**.
* A `SpearmanUndefined` replicate marks the replicate **undefined**.
* `status = INCOMPLETE` if there is any undefined or incomplete replicate,
  otherwise `COMPLETE`.
* `interval()` returns an all-`None` `INCOMPLETE` interval unless the status is
  `COMPLETE`. No successful-subset interval is ever produced.

Interval levels (exact fractions, no interpolation):

```text
lower  = 1/40   (rank 500 at n = 20000)
median = 1/2    (rank 10000)
upper  = 39/40  (rank 19500)
```

Support state (`primary_support_state`) is mechanical:

```text
rho_point > 0 AND lower_95 > 0   -> PRIMARY_WARNING_SIGNAL_SUPPORTED
otherwise                        -> PRIMARY_WARNING_SIGNAL_NOT_ESTABLISHED
interval incomplete              -> PRIMARY_WARNING_SIGNAL_INCOMPLETE
```

---

## 15. Secondary statistic isolation

```text
rho_W1_transport   = Spearman(X_W1, Y_transport_core)
rho_range_deploy   = Spearman(X_range, Y_deploy_core)
```

`secondary_statistics` returns `role = "SECONDARY"` and
`can_rescue_primary = False`. A regression test overwrites the secondary inputs
and asserts the primary statistic is unchanged: secondary significance can never
flip the primary state.

---

## 16. TRAIN stability

`run_predictor_train_stability` reuses the frozen 2000-replicate
`r4-stratum-preserving-paired-train-refit-bootstrap` draw identity. Per
replicate it rebuilds the refit draw, recomputes the SOURCE TRAIN
`q2.5`/`q97.5`, and recomputes `X_range` on the unchanged full TARGET TEST.

* X-only stability (no `fixed_outcomes`) is complete when every replicate can
  rebuild its refit draw.
* When `fixed_outcomes` is supplied, a missing population / row set / outcome
  makes the whole block `INCOMPLETE`; no successful-subset correlation interval
  is produced.
* TEST and TRAIN intervals are never combined.

---

## 17. N912 robustness

`n912_predictor_difference(predictor_456, predictor_912)` reports
`x_456`, `x_912`, `difference`, `role = "SECONDARY_ROBUSTNESS"` and
`cannot_rescue_primary = True`. The module never auto-selects whichever budget
yields the better correlation.

---

## 18. Tests

```text
python -m py_compile experiments/calibration_transport/r4_predictor.py \
                       tests/test_r4_predictor.py       exit 0
ruff check               experiments/calibration_transport/r4_predictor.py \
                         tests/test_r4_predictor.py     All checks passed!
pytest -q tests/test_r4_predictor.py                   69 passed  (x2)
pytest -q tests/test_r4_inference.py                   115 passed
pytest -q tests/test_r4_calibration_families.py        53 passed
pytest -q                                              2158 passed, 4 skipped
git diff --check                                       exit 0
```

Groups: frozen identity continuity; label firewall (signature + AST-scoped code
scan + source scan for sampling/clipping tokens); score validation; source
quantiles; X_range boundary + order invariance; W1 fixtures + independent
reference audit; Spearman; CORE4; registries + role firewall; primary table
validator; secondary isolation; support rule; shared-draw bootstrap; Hella
cluster indivisibility; undefined/incomplete fail-closed; missing-draw contract
violation; TRAIN stability; N912; synthetic end-to-end; artifact
stringification; 20000-replicate smoke; determinism.

---

## 19. Determinism

A temporary probe (not a deliverable) built a full synthetic predictor state —
16-unit panel, X values, outcome summaries, a 50-replicate bootstrap interval,
the validation audit, the secondary statistics and the artifact skeleton — and
printed its canonical SHA256. Two independent processes produced byte-identical
output:

```text
PREDICTOR_SYNTHETIC_STATE_SHA256 = b053f1dc49c1d7cea1c52fccc3a4534ed7b011db9d67bc66f142576adc1f674c
ARTIFACT_FINGERPRINT             = 87e41e4a8a6b2db5109d33653d6352e934f866e28c9262443b8c9e6d491a6903
CANONICAL_BYTES                  = 3751
```

---

## 20. Performance

```text
20000-replicate synthetic smoke: 14.47 s (single CPU process)
```

The synthetic smoke uses a tiny synthetic panel and is an engineering timing
observation only. It is not a scientific result and it is not the formal R4
bootstrap.

---

## 21. Static scan

The module contains no `clip(`, `nextafter(`, `np.clip`, `random.Random`,
`numpy.random`, `secrets.`, `time.time` or builtin `hash(` token. Sampling is
deterministic and fingerprint-derived; there is no hidden random state and no
score clipping.

---

## 22. Formal execution firewall

This implementation performs no formal measurement, no calibration fitting, no
GPU work, no model or tokenizer load, and no real R4 bootstrap. The freeze
fingerprints are hard-coded so that a future formal execution can assert
identity before consuming anything, but nothing in this module authorizes that
execution.

```text
R4 PREDICTOR SEMANTICS = FROZEN
R4 PREDICTOR IMPLEMENTATION = IMPLEMENTED (this document)
R4 FINAL INTEGRATED PROTOCOL = NOT YET INTEGRATED
FORMAL R4 EXECUTION = NOT AUTHORIZED
```
