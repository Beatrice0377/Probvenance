# R4 Inference + Multiplicity Implementation Engineering

Status: **ENGINEERING IMPLEMENTATION / SYNTHETIC VALIDATION ONLY**

```text
R4 INFERENCE + MULTIPLICITY SEMANTIC FREEZE = FROZEN
R4 INFERENCE IMPLEMENTATION ENGINEERING = COMPLETE (synthetic-only)
FORMAL R4 INFERENCE EXECUTION = NOT AUTHORIZED
PREDICTOR PHASE = NOT STARTED
```

This document records the engineering provenance of the research-layer statistical
infrastructure that will later execute the frozen R4 inference + multiplicity
semantics. It records **no study outcome**: every fixture in this document and in
the accompanying test file is fully synthetic.

---

## 1. Frozen identities

| Item | Value |
| --- | --- |
| freeze artifact type | `r4-inference-multiplicity-freeze` |
| freeze status | `FROZEN` |
| freeze fingerprint | `dcbb7ac9e931145fdee86ab984de1249c1b86ca36ee735b70dafc8cabc06c141` |
| freeze JSON | `experiments/calibration_transport/R4_INFERENCE_MULTIPLICITY_FREEZE.json` (1278 lines, sha256 `fdc07904056fd72bdd702e275743839eea741364324bd169ec2bf97504a45ad1`) |
| freeze MD | `experiments/calibration_transport/R4_INFERENCE_MULTIPLICITY_FREEZE.md` (593 lines) |
| freeze commit | `8fc2f3ae465708aa12b108e838377e745e36116b` |
| candidate fingerprint | `5e10be53c8151d10992b70f4940d0e6f6a7aa83dfe4d5cd49e62b485b0c5e267` |
| candidate commit | `2ef9d31cda96dfc3bb326625dad0df061bb7063e` |
| candidate JSON sha256 | `7307b075370ca478a26aaace932fa7a3a8498342b845a99df7c9ef2b10251a5d` |
| candidate MD sha256 | `724706172c141bc3a533aa32fe2ef3ab62424dde2d2d6cd6e091f6e15e230f53` |
| fingerprint version | `1` |

The freeze JSON embeds the complete reviewed semantic payload under
`frozen_semantic_payload` (33 keys). The implementation encodes the identities above
as module constants so every future analysis artifact can record them.

Artifacts produced by this engineering stage:

| Artifact | Lines | sha256 |
| --- | --- | --- |
| `experiments/calibration_transport/r4_inference.py` | 2177 | `662dee0cf66daf7ef1323919cfc65f19c1bb9724d701749e8ba1e195b3bf41c9` |
| `tests/test_r4_inference.py` | 2031 | `6c24a9748d2e0351eaacf90a05dfc7db7c341e6970f272f1c5bd8c94042a6886` |

Frozen authority files (`R4_POPULATION_FREEZE.md`, `R4_CALIBRATION_FAMILY_FREEZE.md`,
`R4_CALIBRATION_FAMILY_SEMANTIC_CANDIDATE.json`, `R4_CALIBRATION_FAMILY_SEMANTIC_CLOSURE.md`,
`R4_CALIBRATION_FAMILY_IMPLEMENTATION_ENGINEERING.md`, `R4_CALIBRATION_IMPLEMENTATION_ENVIRONMENT.md`,
`r4_calibration_families.py`, `r3_protocol.py`, `r3_protocol_design.json`, `r3_analysis.py`)
are **byte-for-byte unchanged** by this stage.

---

## 2. Architecture

`r4_inference.py` is **research-layer statistical infrastructure**. It is not a model
runner, not a measurement runner and not a study executor.

It never:

- downloads datasets;
- loads Hugging Face models;
- opens a GPU;
- searches the filesystem for result files;
- auto-discovers outcomes.

Every analysis function takes **explicit in-memory records or mappings**. Any file
path is supplied by a future caller after formal execution authorization.

Imports are `stdlib` plus `probvenance.fingerprint`
(`canonical_json`, `fingerprint`). It does **not** import `scipy`, `numpy`, `torch`,
`transformers`, or the standalone calibration-family module, and it does not modify
`src/probvenance/*`.

Layout, in module order:

1. frozen identity constants;
2. contract errors;
3. extended-real arithmetic;
4. row / metadata / frozen-item structures;
5. direction contract;
6. losses and weighting;
7. risk matrix and the three deltas;
8. panel aggregation;
9. factorial transforms;
10. deterministic draw kernel and ordering;
11. TEST samplers (MMLU / MedMCQA / HellaSwag cluster);
12. formal population validators;
13. TRAIN-refit sampler;
14. nearest-rank percentile and interval structure;
15. multiplicity registries;
16. TEST bootstrap engines (per-population and panel);
17. coverage matrix, failure records, TRAIN-refit dependency engine;
18. measurement-completeness validator;
19. N912 robustness;
20. descriptive diagnostics;
21. deterministic serialization and analysis-artifact skeleton.

---

## 3. Row model and contracts

`R4InferenceRow(item_id, population_id, stratum, label, cat_score, ovr_score,
cluster_id=None, anchor_index=None)` is a frozen dataclass whose `__post_init__`
enforces: non-empty `item_id` / `population_id` / `stratum`; `label ∈ {0, 1}`;
`cat_score` and `ovr_score` real, finite and inside `[0, 1]`; `anchor_index` an
integer or `None`. Violations raise `RowContractViolation`.

`PopulationMetadata` validates that:

- `test_bootstrap_mode` is one of `subject-stratified-row`,
  `subject_name-stratified-row`, `activity-stratified-source_id-cluster`;
- `estimand_weighting` is one of `equal-subject-mean-of-subject-means`,
  `row-weighted-mean`;
- the cluster mode requires `group_field == "source_id"`;
- the MedMCQA mode requires `stratum_field == "subject_name"`;
- the MMLU mode requires `stratum_field == "subject"`.

`FrozenItemReference(item_id, label, anchor_index)` is the expected-side record used by
the measurement-completeness validator.

---

## 4. Direction contract

```text
CAT->OVR : source = CAT, target = OVR
OVR->CAT : source = OVR, target = CAT
```

Cross prediction is always `g_source(S_target)`. The module exposes
`cross_map_inputs(rows, direction_id)`, which returns the **target** measurement scores
and the target measurement name; the source scores are never passed to the cross map.
A regression test asserts this directly (a source-score cross map would change the
result and fails the test).

`DirectionContractViolation` is raised for unknown direction ids.

---

## 5. Losses and extended-real LogLoss

Primary metric: Brier, `brier_loss(p, y) = (p - y) ** 2`.

Secondary metric: exact LogLoss with **no clipping, no smoothing, no `nextafter`
repair**. `logloss_loss(p, y)` branches explicitly on the exact endpoint values so
`log(0)` is never evaluated:

- `p == 0.0` and `y == 1` → `+inf`;
- `p == 0.0` and `y == 0` → `0`;
- `p == 1.0` and `y == 0` → `+inf`;
- `p == 1.0` and `y == 1` → `0`;
- otherwise the ordinary `-log p` / `-log(1 - p)` form.

Extended-real state is explicit rather than bare `float("inf")`:

```text
FINITE
POSITIVE_INFINITY
NEGATIVE_INFINITY
UNDEFINED_EXTENDED_REAL
```

`ExtendedReal` supports `negated()`, `add()`, `subtract()` and the module functions
`extended_real_add`, `extended_real_subtract`, `extended_real_sum`,
`extended_real_mean`. The frozen difference table is reproduced exactly:

| left − right | result |
| --- | --- |
| finite − finite | defined |
| `+inf` − finite | `+inf` |
| finite − `+inf` | `-inf` |
| `+inf` − `+inf` | `UNDEFINED_EXTENDED_REAL` |

The total extension covers every remaining combination (for example
`finite − +inf` is `-inf`, `-inf − -inf` is `UNDEFINED_EXTENDED_REAL`).

---

## 6. Weighting

| Population | Estimator |
| --- | --- |
| MMLU | equal-subject mean of subject means (`equal_stratum_mean_of_stratum_means`) |
| HellaSwag | row-weighted mean |
| MedMCQA | row-weighted mean |

`equal_stratum_mean_of_stratum_means(strata, values)` buckets by stratum and averages
the stratum means; it is deliberately **not** reducible to a plain row mean. A test
builds unequal synthetic subject sizes and asserts the two differ, so a future
simplification to a generic row mean fails closed.

Panel aggregation is hierarchical and equally weighted:

```text
PopulationMean_p = mean over the 4 current-generation models
R4PanelMean      = mean over exactly the 3 primary populations
```

`population_mean` and `panel_mean` raise `PanelIncomplete` on any missing **or extra**
cell; a test deletes one cell and asserts the failure. Raw row counts never influence
the panel weight.

---

## 7. Estimands and the risk matrix

```text
R_raw    = mean loss(S_target, Y)
R_native = mean loss(g_target(S_target), Y)
R_cross  = mean loss(g_source(S_target), Y)

Delta_deploy    = R_cross - R_raw
Delta_native    = R_native - R_raw
Delta_transport = R_cross - R_native
```

All three deltas are computed from **paired per-row loss differences**
(`mean_paired_difference`) so covariance is preserved. `risk_matrix` reports the six
values together.

Cross-path numerical audit (synthetic Brier fixture, tolerance `1e-12`): Path A
(risk subtraction) and Path B (per-row paired loss difference aggregation) agree for
`Delta_deploy`, `Delta_native` and `Delta_transport`.

Algebraic identity audit (synthetic finite Brier data, tolerance `1e-12`):

```text
Delta_deploy = Delta_transport + Delta_native
```

This is recorded as an **implementation invariant only**. The three estimands remain
scientifically distinct and no estimand is removed on the basis of this identity.

---

## 8. Factorial contrasts

`factorial_contrasts(values)` accepts exactly the four logistic-core procedures
(`P-low`, `P-historical`, `L-low`, `L-historical`) and returns:

```text
Feature        = 0.5 * (L_low + L_hist - P_low - P_hist)
Regularization = 0.5 * (P_low + L_low - P_hist - L_hist)
Interaction    = (L_low - P_low) - (L_hist - P_hist)
```

Any other key set (including `I-isotonic` or `B-beta`) raises
`FactorialContractViolation`, so the standalone procedures can never leak into the
factorial family.

Linearity audit: `factorial(Delta_deploy) == factorial(Delta_transport) +
factorial(Delta_native)` within floating tolerance. This is an implementation
invariant, not a licence to merge estimands.

---

## 9. Deterministic draw kernel

```text
deterministic_index(identity, pool_size) =
    int(fingerprint(canonical_json(identity))[:16], 16) % pool_size
```

Forbidden sources (never used): `random.Random` mutable state, `numpy` global RNG
state, `secrets`, system entropy, wall-clock seeds, Python `hash()`.

TEST row-draw identity fields:

```text
protocol_id, protocol_version, population_id, population_fingerprint,
replicate_index, stratum, draw_index, pool_size
```

Cluster draws add `cluster_mode_marker`. TRAIN-refit draws add `budget_identity`
(`N456` / `N912`).

Stable ordering is enforced for strata, item pools, source-id pools, cluster rows,
model labels, population labels, direction labels and procedure labels. A test
shuffles the input rows and reverses the mapping insertion order and asserts the
draw identity is identical.

`TestDraw.draw_identity_payload()` deliberately excludes any model label: the same
`(population, replicate)` draw is reusable across all 4 models, 2 directions,
6 procedures and all estimands. A test proves that changing the model label does not
change the row draw.

---

## 10. Population samplers

### 10.1 MMLU TEST

`subject-stratified-row` bootstrap: for each subject, draw the original subject row
count with replacement. The returned occurrence list may repeat `item_id`s; no
uniqueness constraint is applied.

### 10.2 MedMCQA TEST

`subject_name-stratified-row` bootstrap: per `subject_name` stratum, draw the original
row count with replacement. `topic_name` is never used as a stratum.

### 10.3 HellaSwag TEST

`activity-stratified-source_id-cluster` bootstrap. First a structural validator
(`validate_hellaswag_cluster_stratum`) requires every `source_id` to map to exactly one
`activity_label`; a conflict raises `HellaswagClusterStratumAmbiguity` with no
fallback. Then, per activity: pool = unique `source_id` clusters; draw the original
unique cluster count with replacement; each drawn cluster contributes **all** of its
original rows; a cluster drawn twice contributes its complete row set twice. There is
no row bootstrap inside a cluster. The statistic is row-weighted over the expanded
multiset, so the resampling unit (cluster) and the statistic unit (row) are both
honoured simultaneously. Tests cover singleton clusters, a 1-row/5-row cluster pair,
the same cluster drawn twice, cluster size variation, an activity with one cluster, a
`source_id`/activity conflict, input-order permutation, and the fact that the expanded
row count may differ from the original row count.

### 10.4 Formal population validators

`validate_formal_population(rows, metadata)` reproduces the frozen structural audit:

- MMLU: 57 subjects, exactly 20 TEST rows per subject, 1140 rows;
- HellaSwag: cluster audit + 10042 TEST rows + 192 activity labels + 8407 source ids;
- MedMCQA: 21 `subject_name` strata + 4162 TEST rows.

Any mismatch raises `PopulationContractViolation`.

### 10.5 TRAIN-refit sampler

`build_train_refit_draw(rows, metadata, replicate_index, budget_identity=N456)` draws,
per stratum, exactly the original selected TRAIN count with replacement, so the total
N is preserved (`validate_train_total_n`). The budget identity is `N456` (456) or
`N912` (912).

- MMLU: 8 draws per subject (`mmlu_refit_draw_counts`), never the R3-historical 10.
- HellaSwag: `activity_label` strata, **selected-row** bootstrap; the selected TRAIN is
  already at most one row per `source_id`, so this is not the TEST cluster bootstrap.
- MedMCQA: `subject_name` strata; `topic_name` forbidden.

The refit draw is shared across all models, both CAT/OVR fits, all 6 procedures and
both directions; it depends only on `(population, budget, replicate)`. A test asserts
the occurrence list is unchanged when the model or procedure label changes, and
unchanged under input-order permutation.

---

## 11. Nearest-rank percentile

```text
rank = ceil(percentile * n)  clamped to [1, n]    (1-indexed)
value = ordered_values[rank - 1]
```

No interpolation. `percentile` is a **fraction** of the sample
(`Fraction(1, 480)`, not `1/480 %`), validated to lie in `(0, 1]`.

Mandatory rank audits:

| n | tail | rank |
| --- | --- | --- |
| 20000 | `1/480` | 42 |
| 20000 | `479/480` | 19959 |
| 20000 | `1/320` | 63 |
| 20000 | `319/320` | 19938 |
| 20000 | `1/240` | 84 |
| 20000 | `239/240` | 19917 |
| 2000 | 2.5 % (`1/40`) | 50 |
| 2000 | 50 % (`1/2`) | 1000 |
| 2000 | 97.5 % (`39/40`) | 1950 |

**Implementation note (deviation resolved during this stage).** The freeze expresses
the confirmatory family tails as fractions (`"lower_tail": "1/480"`,
`lower_tail_decimal 0.0020833…`, `audit_lower_rank 42`) but the TRAIN-refit interval
levels as percentages (`levels [2.5, 50, 97.5]`, ranks `50/1000/1950`). Both are the
same nearest-rank rule with `p` as a fraction of the sample. The first draft of the
implementation divided by 100 unconditionally, which reproduced the refit ranks but
collapsed the family tails to rank 1. The rank functions now take a fraction, and the
refit level constants were re-expressed as fractions
(`REFIT_LOWER_LEVEL = Fraction(1, 40)`, `REFIT_MEDIAN_LEVEL = Fraction(1, 2)`,
`REFIT_UPPER_LEVEL = Fraction(39, 40)`) so the frozen audit ranks are reproduced
exactly. The reported `tail_rule` string for a refit interval is therefore
`"1/40/39/40"`; the ranks are identical to the frozen percentage levels. No frozen
semantic value was changed.

Interval structure keeps the point estimate and the bootstrap median **separate**:

```text
n, point_estimate, bootstrap_median, lower, upper,
tail_rule, excludes_zero, status
```

`status` is `COMPLETE` or `INCOMPLETE`; an empty sample yields an `INCOMPLETE` interval
with `n = 0` and null bounds. `excludes_zero(lower, upper)` is
`lower > 0.0 or upper < 0.0`; an exact zero boundary is therefore *not* exclusion.

Direct contrast rule: all interval families are built from **replicate-level**
contrasts (`contrast_per_replicate`). Subtracting or averaging interval endpoints is
forbidden and a regression test asserts the direct contrast is not the naive endpoint
difference.

---

## 12. Multiplicity registries

| Family | Size | Composition | Tails | Audit ranks |
| --- | --- | --- | --- | --- |
| primary | 12 | 2 estimands × 2 directions × 3 factorial effects | `1/480`, `479/480` | 42 / 19959 |
| I/B extension | 8 | 2 procedures × 2 directions × 2 estimands | `1/320`, `319/320` | 63 / 19938 |
| direction-difference | 6 | 3 effects × 2 estimands | `1/240`, `239/240` | 84 / 19917 |
| native-reference | 12 | 2 directions × 6 procedures | `1/480`, `479/480` | 42 / 19959 |

Correction id: `bonferroni-percentile-interval`; percentile rule:
`nearest-rank-percentile`. Deterministic hypothesis ids:

```text
primary::{estimand}::{direction}::{effect}
extension::{procedure}::{direction}::{estimand}
direction-difference::{estimand}::{effect}
native-reference::{direction}::{procedure}
```

`I-isotonic` and `B-beta` never appear in the factorial registry. Tests assert the
exact Cartesian products, no duplicates and the exact family sizes. The direction
family is a direct paired replicate difference; a test proves it cannot be derived
from the two directions' significance flags.

Native-reference states:

```text
upper < 0  -> NATIVE_IMPROVEMENT_SUPPORTED
lower > 0  -> NATIVE_DEGRADATION_SUPPORTED
otherwise  -> NATIVE_ADEQUACY_UNRESOLVED      (exact 0 boundary is unresolved)
```

---

## 13. Bootstrap engines

`run_test_bootstrap(rows_by_population, metadata_by_population, statistic, replicates,
model_label=None)` is a generic engine: one draw per population per replicate, the
statistic callback receives `(population_id, draw)`, and the result exposes
`.interval(population_id, lower_tail=…, upper_tail=…, point_estimate=…)`.

`run_panel_test_bootstrap(...)` implements the frozen panel path:

```text
replicate
  -> one draw per population (shared across models/procedures/directions)
  -> unit values per (model, population, direction, procedure, estimand)
  -> PopulationMean_p (equal mean over models)
  -> R4PanelMean     (equal mean over populations)
  -> factorial contrasts, direction differences, extension panel, native reference
```

Formal replicate constants are `TEST_BOOTSTRAP_REPLICATES = 20000` and
`TRAIN_REFIT_REPLICATES = 2000`. Unit tests use small replicate counts; a 20000-
replicate synthetic smoke test is also run (see §17).

The engine precomputes stratum pools and per-population draw lists, and reuses the
shared draw across models/procedures/directions, which is the intended cost model. It
does not introduce parallel nondeterministic reduction, and it does not use a GPU.

---

## 14. Coverage, failure and completeness engine

`CoverageMatrix` records `(model, population, procedure, measurement) -> status` with
statuses `AVAILABLE`, `INELIGIBLE`, `FAILED` (default `INELIGIBLE`).

- `primary_hypothesis_status(direction, estimand)` requires the 4 logistic-core
  procedures to be `AVAILABLE` in all 4 models × 3 populations at the target
  measurement.
- `extension_hypothesis_status(procedure, direction, estimand)` requires that
  procedure to be `AVAILABLE` in all 12 primary model × population cells.
- `incomplete_cells()` lists every recorded cell that is not `AVAILABLE`.

A missing required cell makes the dependent hypothesis `INCOMPLETE`; unrelated blocks
remain reportable. Cells are never silently dropped.

`FailureRecord(replicate, procedure, model, population, measurement_dependency,
direction_dependency, error_code, exception_type, message)` records every failure
explicitly; failures are never swallowed and `continue`-ed past.

`run_train_refit_block(...)` is the TRAIN-refit dependency engine. On any failing
replicate it records `error_code = "TRAIN_REFIT_REPLICATE_FAILED"` and returns
`status = INCOMPLETE` with `interval = None`. There is no successful-subset interval.
Tests assert `planned = N`, `successful = N - 1`, `failed = 1`, `status = INCOMPLETE`,
`interval is None`, while an unrelated procedure still reports `COMPLETE` with an
interval.

`validate_measurement_completeness(expected, provided, population_id, model_id)`
fails closed with ordered codes: `DUPLICATE_EXPECTED_ITEM`, `POPULATION_MISMATCH`,
`DUPLICATE_PROVIDED_ITEM`, `EXTRA_ROW`, `MISMATCHED_LABEL`, `MISSING_ANCHOR`,
`MISMATCHED_ANCHOR`, `MISSING_CAT`, `MISSING_OVR`, `MISSING_ROW`. Synthetic tests
cover missing CAT, missing OVR, duplicate item, mismatched Y, mismatched anchor, extra
row and missing row. `MISSING_CAT` / `MISSING_OVR` are retained for completeness but
are unreachable through the row contract, which forbids `None` scores (documented
limitation).

---

## 15. N912 robustness

`validate_n912_pairing(train_456, train_912, test_456, test_912)` confirms the primary
TRAIN 456 is a subset of the robustness TRAIN 912, reports the extension count, and
confirms the TEST identity is identical. `n912_minus_n456` is the paired
replicate-level contrast. The registry marks this family
`SECONDARY_ROBUSTNESS` with `CANNOT_RESCUE_PRIMARY = True`.

---

## 16. Descriptive diagnostics

`equal_width_reliability_10_bins(predictions, labels)` implements only the
equal-width 10-bin descriptive diagnostic. Empty bins report `count = 0` and null
means. No ECE confirmatory test and no ACE are implemented.

`split_type_diagnostic(rows, split_type_by_item)` returns
`role = "DESCRIPTIVE_SECONDARY"`, `is_independent_population = False`,
`primary_population_count = 3` and the `indomain` / `zeroshot` subgroups. HellaSwag
`split_type` is never registered as a population, a primary family or a predictor
independent unit.

No IID-cell inference interfaces exist: there is no `t_test_over_units`, no
`random_effects_meta_analysis` and no `naive_cell_standard_error`. A test asserts these
names are absent.

---

## 17. Determinism, state fingerprint and performance

Deterministic serialization uses `probvenance.fingerprint.canonical_json` /
`fingerprint`. `build_analysis_artifact_skeleton(...)` builds the future formal
analysis artifact schema and adds `artifact_fingerprint`. Composite mapping keys (for
example `(model, population, direction, procedure)`) are canonicalized to
`"|"`-joined strings so the artifact stays JSON- and fingerprint-compatible without
losing the composite identity.

Synthetic state probe (`/tmp/opencode/r4_inference_state_probe.py`, temporary and not
committed; synthetic rows only, no study data, no model, no GPU):

```text
STATE_SHA256          = 07b37954eeb4e4b1a920de10b06cc18727d70c1c6b0afe2d370184a13b66c83a
ARTIFACT_FINGERPRINT  = 691e91222c36ec68ff4ed3f45eebff9536ef89e4ca28b296a0612d82c3c96dcf
CANONICAL_BYTES       = 25381
```

The probe covers a 50-replicate synthetic panel (4 models × 3 populations × 2
directions × 6 procedures), all four interval families, all four registries and the
artifact skeleton. Two separate processes produced **identical** `STATE_SHA256`,
`ARTIFACT_FINGERPRINT` and byte length.

Performance note (synthetic only, tiny 4-row population, single population, 20000
replicates): `2.185 s` and `2.216 s` across two runs; interval
`n=20000, median 0.065, lower 0.0575, upper 0.0725, tail_rule "1/480/479/480",
excludes_zero True, status COMPLETE`. The replicate machinery does not show an obvious
`O(R × models × procedures × repeated regrouping)` pathology.

---

## 18. Tests

| Suite | Result |
| --- | --- |
| `python -m py_compile r4_inference.py tests/test_r4_inference.py` | exit 0 |
| `ruff check r4_inference.py tests/test_r4_inference.py` | `All checks passed!` exit 0 |
| `pytest tests/test_r4_inference.py` (run 1) | 115 passed |
| `pytest tests/test_r4_inference.py` (run 2) | 115 passed |
| `pytest tests/test_r4_calibration_families.py` | 53 passed |
| `pytest` (full repository) | 2089 passed, 4 skipped, exit 0 |
| `python -m json.tool R4_INFERENCE_MULTIPLICITY_FREEZE.json` | exit 0 |
| `git diff --check` | exit 0 |

Both targeted runs produce the same count, the same pass/fail set and the same
deterministic hashes.

**R3 regression discovery.** A mechanical search of `tests/` found no test module
referencing `r3_protocol` or `r3_analysis`; the R3 continuity is asserted inside
`tests/test_r4_inference.py` against the frozen `r3_protocol_design.json`
(`protocol_fingerprint 3ef63056ae16b18ad65d9c87d1fbec5b43550873a0e3e25ec0a323f954ee974d`,
the four logistic-core procedure fingerprints, and the absence of `I-isotonic` /
`B-beta` from the R3 design). R3 source and tests were not modified.

Forbidden-token scan of `r4_inference.py`: no code-level `clip(`, `nextafter(`,
`random.Random`, `numpy.random`, `secrets.`, `time.time` or `hash(`. The only textual
hits are docstring sentences that state clipping is forbidden or absent
(lines 17, 20, 395, 555).

---

## 19. Known warnings and limitations

1. ~~`run_panel_test_bootstrap` assembles the extension and native-reference panels
   after the replicate loop and therefore requires the standalone procedures to have
   been executed; callers must pass `procedures = ALL_PROCEDURES`. A subset that omits
   `I-isotonic` / `B-beta` raises `KeyError`. This is an engineering constraint of the
   current implementation, not a semantic choice.~~ **RESOLVED** by the dependency
   isolation amendment (§21): the primary logistic-core family is now independent of
   `I-isotonic` / `B-beta` availability, no formal API leaks `KeyError`, and every
   frozen family keeps its declared size with unavailable members marked `INCOMPLETE`.
2. `MISSING_CAT` / `MISSING_OVR` completeness codes are unreachable through the row
   contract (which forbids `None` scores); they are retained for schema completeness.
3. `torch_dtype` and reference-PyTorch fallbacks are unrelated to this module; this
   module touches neither PyTorch nor a GPU.
4. The TRAIN-refit `tail_rule` string is expressed as `"1/40/39/40"` rather than
   `"2.5/97.5"`; the ranks are identical to the frozen percentage levels (§11).

---

## 20. Formal execution firewall

This stage read no study outcome. It produced no CAT/OVR probability, no fitted
calibration state, no Brier result, no LogLoss result, no transport delta and no
predictor value. No model was loaded, no dataset was downloaded and no GPU was opened.

Formal R4 execution (real measurement, real calibration fitting, the real 20000-
replicate TEST bootstrap, the real 2000-replicate TRAIN refit, Brier/LogLoss
evaluation, transport analysis, predictor development and validation) remains
**NOT AUTHORIZED** and requires final R4 protocol integration plus explicit human
authorization.

```text
R4 INFERENCE + MULTIPLICITY SEMANTIC FREEZE = FROZEN
R4 INFERENCE IMPLEMENTATION ENGINEERING = COMPLETE (synthetic-only)
FORMAL R4 INFERENCE EXECUTION = NOT AUTHORIZED
PREDICTOR PHASE = NOT STARTED
```

---

## 21. Dependency Isolation Amendment

**Original implementation provenance.** The implementation described in §1–§20 is
commit `8c3bb0f0e4367bf7194f22a3f38d66aff3cbbbf7`
(short `8c3bb0f`), parent `8fc2f3ae465708aa12b108e838377e745e36116b`, exactly three
paths (`r4_inference.py`, `tests/test_r4_inference.py`,
`R4_INFERENCE_IMPLEMENTATION_ENGINEERING.md`). Its file identities were
`r4_inference.py` 2177 lines /
`662dee0cf66daf7ef1323919cfc65f19c1bb9724d701749e8ba1e195b3bf41c9`,
`tests/test_r4_inference.py` 2031 lines /
`6c24a9748d2e0351eaacf90a05dfc7db7c341e6970f272f1c5bd8c94042a6886`.

### 21.1 Old issue

`run_panel_test_bootstrap` assembled `extension_panel` and `native_reference` after
the replicate loop by indexing `panel_values[(direction, procedure)]` for every
`procedure in ALL_PROCEDURES` (and `primary_contrasts` for every core procedure),
regardless of which procedures the caller had actually requested. A caller that
omitted `I-isotonic` / `B-beta` therefore hit a raw `KeyError`.

### 21.2 Scientific reason

The frozen dependency doctrine is that the primary logistic-core inference depends
only on `P-low`, `P-historical`, `L-low`, `L-historical`, while `I-isotonic` and
`B-beta` are a standalone secondary extension. An unavailable / ineligible / omitted
extension must not make an otherwise-complete logistic-core primary block fail, and a
failure of one secondary extension must not silently shrink any multiplicity family.
Equally, an unavailable core procedure must block only the hypotheses that depend on
it, leaving complete extensions and unrelated descriptive cells reportable.

### 21.3 Code change

- New domain error `DependencyUnavailable(R4InferenceError)` with a fixed
  `code = "DEPENDENCY_UNAVAILABLE"` and `family` / `dependency` attributes. It is
  deliberately **not** a `KeyError` subclass, so `isinstance(exc, DependencyUnavailable)`
  (expected incompleteness) and `isinstance(exc, KeyError)` (programming bug) are
  machine-distinguishable.
- `PanelBootstrapResult` gained presence predicates (`has_primary_contrast`,
  `has_direction_difference`, `has_extension_panel`, `has_native_reference`) and a
  `family_status()` method that reports every frozen family member as `COMPLETE` /
  `INCOMPLETE` against the frozen sizes 12 / 8 / 6 / 12.
- The four interval accessors (`primary_interval`, `extension_interval`,
  `direction_interval`, `native_interval`) and `TestBootstrapResult.interval` now raise
  `DependencyUnavailable` (with family and dependency) instead of `KeyError`.
- Assembly in `run_panel_test_bootstrap` is now dependency-aware: it derives
  availability from what was actually computed, so the primary contrasts are built iff
  all four core procedures are present, the extension panel contains only the
  standalone procedures that were computed, and `native_reference` contains only the
  procedures that were computed.
- `PRIMARY_FAMILY_PROCEDURES` / `EXTENSION_FAMILY_PROCEDURES` name the two frozen
  selections; family selection is expressed through the `procedures` argument.

### 21.4 Dependency behaviour matrix

| Scenario | Primary 12 | Direction-difference 6 | Extension 8 | Native-reference 12 |
| --- | --- | --- | --- | --- |
| All six procedures | COMPLETE | COMPLETE | COMPLETE | COMPLETE |
| Core four only (I/B unavailable) | COMPLETE | COMPLETE | INCOMPLETE (8/8) | 8 COMPLETE, 4 INCOMPLETE |
| One core missing (e.g. `L-historical`), I/B complete | INCOMPLETE (0/12) | INCOMPLETE (0/6) | COMPLETE | 10 COMPLETE, 2 INCOMPLETE |

No family size changes; no interval tail changes; no KeyError is reachable.

### 21.5 Tests

Six new tests were added to `tests/test_r4_inference.py` (109 → 115):

- `test_primary_bootstrap_does_not_require_extension_procedures`
- `test_extension_incompleteness_does_not_block_primary`
- `test_missing_core_blocks_primary_but_not_complete_extension`
- `test_native_reference_preserves_fixed_family_when_member_incomplete`
- `test_missing_dependency_uses_domain_state_not_keyerror`
- `test_refit_level_representation_is_normalization_only`

### 21.6 No frozen semantic change

`R4_INFERENCE_MULTIPLICITY_FREEZE.json` / `.md` and the candidate were not modified.
Family sizes 12 / 8 / 6 / 12, tails, bootstrap counts, weighting, estimands and failure
rules are unchanged. The synthetic determinism probe is byte-identical
(`STATE_SHA256 07b37954eeb4e4b1a920de10b06cc18727d70c1c6b0afe2d370184a13b66c83a`,
`ARTIFACT_FINGERPRINT 691e91222c36ec68ff4ed3f45eebff9536ef89e4ca28b296a0612d82c3c96dcf`),
because the amendment only changes behaviour when a dependency is absent.
