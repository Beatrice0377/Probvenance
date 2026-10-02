# R4 Formal Analysis Runner — Execution Contract

```text
artifact_type:            r4-formal-analysis-runner-contract
artifact_version:         1
status:                   FROZEN CANDIDATE
nature:                   OPERATIONAL ANALYSIS ORCHESTRATION CONTRACT
runner_id:                r4-integrated-formal-analysis-runner
runner_version:           1
runner_source_path:       experiments/calibration_transport/run_r4_analysis.py
runner_source_sha256:     a2c231012893dd7d840aaadb1efd6f2f3b7fe74536ba7e3cf90fc6765fe8f55c
runner_contract_fingerprint: 630cafa6ec7943274c943b1354c6f8acbb7c722764f7770ef3de4c8c9c09fd2e
formal_analysis_authorized:  false
scientific_semantics_changed: false
scientific_outputs_computed:  false
raw_evidence_analyzed:        false
superseded_contract_fingerprints:
  2fe5d962a706c822a63573bbd8e553a44b6b0fd082dd582af8cdaa25bc6c7c60  SUPERSEDED FOR FORMAL-PATH COVERAGE
  d16a8edb9f7edcb5a0dee69e37bb32f4f45dd661fcb324e166db31a2c6b06ff5  SUPERSEDED BY THE MEASUREMENT-MAP
                                                                  IDENTITY + EXCEPTION-BOUNDARY CORRECTION
firewall_deviation:       R4_FORMAL_ANALYSIS_FIREWALL_DEVIATION_ATTEMPT0.json
```

This document defines **fields only**. It carries no real scientific value.

Both earlier contract fingerprints are retained as provenance and are marked **SUPERSEDED**.
`2fe5d962…` described an orchestration path that did not cover the full frozen dependency graph.
`d16a8edb…` described a direction/side fit identity (a measurement fitted once per directional
role) and a catch-all mapping of any unknown fit exception to a scientific `FAILED` status.
Neither is claimed to be still valid.

---

## 1. Purpose

The runner executes an **already frozen** analysis DAG over the frozen R4 raw evidence:

```text
validate frozen authorities
load frozen analysis registry
load formal raw evidence
construct frozen directional units
dispatch frozen calibration implementations
dispatch frozen inference implementations
coordinate frozen shared bootstrap draws
dispatch frozen predictor implementation
assemble deterministic formal result artifacts
```

The runner is **orchestration only**. It never re-implements calibration mathematics, risk
definitions, Delta formulas, bootstrap statistics, multiplicity formulas, Spearman or
Wasserstein-1.

---

## 2. Authority block

```text
measurement_contract_fingerprint
final_protocol_fingerprint
execution_manifest_fingerprint
ledger_fingerprint
environment_map_fingerprint
registry_fingerprint
dependency_graph_fingerprint
preflight_fingerprint
raw_measurement_freeze_commit
measurement_code_commit
frozen_file_sha256
frozen_implementation_sha256
```

All eleven frozen files and both frozen statistical implementations are verified by SHA-256 at
startup. A mismatch fails closed.

---

## 3. Input identity block

One record per frozen measurement cell (16 cells):

```text
cell_id
model_key
model_id
model_revision
model_role              # current-generation | legacy-lineage
population_key
population_id
population_manifest_fingerprint
dataset_id
dataset_revision
train_budget            # N456 | N912
stratum_field
group_id_field
path
sha256
evidence_fingerprint
split_counts
```

No legacy x MMLU cell exists. The directional-unit registry is mechanically derived:

```text
current directional units = 4 current models x 3 populations x 2 directions = 24
legacy  directional units = 2 legacy  models x 2 populations x 2 directions = 8
```

---

## 4. Execution identity block

```text
runner_id
runner_version
runner_source_sha256
runner_contract_fingerprint
measurement_code_commit
test_bootstrap_protocol_id
test_bootstrap_protocol_version
train_refit_protocol_id
train_refit_protocol_version
multiplicity_correction_id
percentile_rule_id
analysis_result_fingerprint_version
```

---

## 5. Direction semantics

Only two directions exist:

```text
CAT -> OVR
OVR -> CAT
```

For any procedure `F` and direction `d`:

```text
cross:  fit the SOURCE measurement of the population TRAIN, apply to the TARGET measurement TEST
native: fit the TARGET measurement of the population TRAIN, apply to the TARGET measurement TEST
raw:    uncalibrated TARGET measurement TEST
```

The direction is resolved from frozen directional-unit metadata, never guessed from a string or a
position.

---

## 6. Calibration procedures

Exactly six procedures, four logistic-core plus two extension:

```text
CORE4:      P-low, P-historical, L-low, L-historical
EXTENSION2: I-isotonic, B-beta
```

No seventh procedure, no temperature scaling, no fallback calibrator. Isotonic and beta propagate
their frozen ineligibility; neither clips an endpoint nor falls back to another family.

---

## 7. Risk and estimand records

```text
risk_record_fields:     risk_id, procedure, direction_id, measurement, metric_id, state, value
risk_ids:               R_raw, R_native, R_cross
estimand_record_fields: estimand_id, procedure, direction_id, measurement, metric_id, state, value
estimand_ids:           Delta_native, Delta_deploy, Delta_transport
```

The formulas live in the frozen implementation only:

```text
Delta_native(F)    = R_native(F) - R_raw
Delta_deploy(F)    = R_cross(F)  - R_raw
Delta_transport(F) = R_cross(F)  - R_native(F)
```

Each estimand carries its **own** dependency requirement. The runner never shares one requirement
across all three merely because `risk_matrix()` returns them together; it calls the frozen
`r4_inference.delta_deploy` / `delta_native` / `delta_transport` individually.

```text
dependency truth table:
  Delta_deploy     requires CROSS fit only
  Delta_native     requires NATIVE fit only
  Delta_transport  requires CROSS + NATIVE fits
  R_raw            requires no calibrator
```

Fit source:

```text
cross fit   fit the SOURCE measurement A on the population TRAIN (N456 primary / N912 robustness)
native fit  fit the TARGET measurement B on the population TRAIN (N456 primary / N912 robustness)
```

### 7.1 Canonical fitted-map identity

There is exactly **one** scientific fitted-map identity per

```text
fit_identity = model x population x budget x procedure x measurement
measurement  = CAT | OVR
```

`direction`, `cross/native side`, `estimand` and `metric` are **references** into that registry,
never distinct fit identities. The same fitted map therefore serves two directional roles:

```text
fit(CAT)  =  CAT->OVR cross   =  OVR->CAT native
fit(OVR)  =  OVR->CAT cross   =  CAT->OVR native
```

A measurement is never fitted twice. A measurement-level failure propagates automatically to
both of its directional roles:

```text
B-beta CAT fit FAILED -> CAT->OVR cross unavailable  AND  OVR->CAT native unavailable
B-beta OVR fit FAILED -> OVR->CAT cross unavailable  AND  CAT->OVR native unavailable
```

Resulting truth table (only the affected estimands disappear):

```text
CAT failed:
  CAT->OVR   Delta_deploy INCOMPLETE   Delta_native AVAILABLE   Delta_transport INCOMPLETE
  OVR->CAT   Delta_deploy AVAILABLE    Delta_native INCOMPLETE  Delta_transport INCOMPLETE
OVR failed:
  CAT->OVR   Delta_deploy AVAILABLE    Delta_native INCOMPLETE  Delta_transport INCOMPLETE
  OVR->CAT   Delta_deploy INCOMPLETE   Delta_native AVAILABLE   Delta_transport INCOMPLETE
both failed:
  both directions  Delta_deploy INCOMPLETE  Delta_native INCOMPLETE  Delta_transport INCOMPLETE
```

Unique fit counts:

```text
primary N456 current generation   4 models x 3 populations x 6 procedures x 2 measurements = 144
legacy N456                       2 models x 2 populations x 6 procedures x 2 measurements =  48
current N912 robustness           4 models x 2 populations x 6 procedures x 2 measurements =  96
```

The runner helper is `run_r4_analysis.canonical_fit_key` plus
`run_r4_analysis.directional_measurement`; the reference map is
`run_r4_analysis.directional_reference_map`.

---

## 8. Metrics

```text
metric_record_fields: metric_id, state, value, undefined_reason
metric_ids:           Brier, LogLoss
extended_real_states: FINITE, POSITIVE_INFINITY, UNDEFINED_EXTENDED_REAL
```

Primary metric is Brier; secondary metric is exact LogLoss. There is **no clipping, no epsilon,
no finite cap**. `+inf` is representable, and `+inf - +inf` is `UNDEFINED_EXTENDED_REAL`, which
marks the dependent result incomplete.

The exact LogLoss secondary is formally wired through the frozen extended-real carrier:

```text
carrier:      r4_inference.ExtendedReal
functions:    r4_inference.logloss_loss, r4_inference.mean_logloss,
              r4_inference.extended_real_subtract, r4_inference.extended_real_mean
estimands:    raw, native, cross, Delta_native, Delta_deploy, Delta_transport
rule:         if any replicate contrast is UNDEFINED_EXTENDED_REAL the whole dependent
              interval is INCOMPLETE / UNDEFINED; undefined replicates are never dropped
              and no successful-subset interval is produced
```

LogLoss uses the same dependency truth table as Brier and can never rescue the Brier primary.
Population weighting is preserved.

---

## 9. Bootstrap families

Family sizes are fixed and are never shrunk by a missing result, a failed procedure or an
ineligible beta:

```text
primary12              12   Bonferroni 1/480 .. 479/480,   ranks 42 / 19959
extension8              8   Bonferroni 1/320 .. 319/320,   ranks 63 / 19938
direction_difference6   6   Bonferroni 1/240 .. 239/240,   ranks 84 / 19917
native_reference12     12   Bonferroni 1/480 .. 479/480,   ranks 42 / 19959
```

```text
bootstrap_family_record_fields:
  family_id, family_size, members, member_status,
  bonferroni_lower, bonferroni_upper, interval_rank_low, interval_rank_high,
  replicates, status, incomplete_reason
```

A successful-subset confidence interval, a complete-case rescue and a family shrink are all
forbidden.

---

## 10. Shared TEST draw

Formal mode uses `20000` TEST bootstrap draws. One population-level draw is shared across

```text
all models
both directions
all procedures
all estimands
```

MMLU uses subject-stratified paired draws with equal-subject means; HellaSwag uses
activity strata with `source_id` cluster draws expanded as a row-weighted multiset; MedMCQA uses
`subject_name`-stratified paired draws. HellaSwag clusters are never split.

TRAIN-refit uses `2000` separate draws, under a separate protocol identity. The two draw systems
are never mixed.

---

## 11. Randomness authority

```text
prng:  none
seed:  none
mechanism: sha256 fingerprint of a frozen identity payload, reduced modulo the pool size
kernel:    r4_inference.deterministic_index
```

TEST draw identity fields:

```text
protocol_id, protocol_version, population_id, population_fingerprint,
replicate_index, stratum, draw_index, pool_size, cluster_mode_marker
```

TRAIN-refit identity fields:

```text
protocol_id, protocol_version, population_id, population_fingerprint,
budget_identity, replicate_index, stratum, draw_index, pool_size
```

No system entropy, no wall clock, no builtin `hash`. Qualification replicate counts are not
formal counts and cannot be selected in formal mode.

---

## 12. N912 robustness

```text
n912_robustness_record_fields:
  cell_id, population_id, train_budget, role, status, reason,
  separate_from_primary, cannot_rescue_primary,
  shared_test_draw_paired_by_replicate, comparisons, refit_blocks, refit_statuses
```

N912 is a nested `N456 + extension456` direct-robustness budget. It never replaces, overrides or
rescues the `N456` primary result, and legacy cells never use N912.

```text
role:        SECONDARY ROBUSTNESS ONLY
computed:    Delta_deploy_456, Delta_deploy_912,
             Delta_transport_456, Delta_transport_912,
             Delta_N912_minus_N456
pairing:     the N912 - N456 difference is subtracted directly within the SAME shared
             TEST replicate index; no independent resampling stream is introduced
scope:       frozen new-population 912 manifests only (HellaSwag, MedMCQA)
new_confirmatory_multiplicity_family: null
rule:        if N456 failed and N912 succeeds, the primary stays FAILED / INCOMPLETE
```

The N912 secondary-robustness TRAIN-refit blocks are executed as well, over the same frozen
procedure set and estimands as the primary refit.

---

## 13. Predictor

```text
predictor_record_fields:
  unit_id, model_key, population_id, direction_id, role,
  x_range, x_wasserstein1, y_transport_core4, y_deploy_core4,
  spearman_rho, interval_low, interval_high, status, incomplete_reason

predictor_role_counts:
  development 8, primary_validation 16, legacy_extension 8
```

The observational unit is `model x population x direction`. `F` is not a pseudo-replicate. The
primary statistic is `Spearman(X_range, Y_transport_core)` over exactly the 16 heldout validation
units; the CORE4-only outcome mean never includes isotonic or beta. The same TEST resample
recomputes both target `X` and outcome `Y`, while the source TRAIN thresholds stay fixed. An
undefined replicate makes the interval incomplete; a successful-subset CI is forbidden.

The formal predictor path runs over the **merged** panel, which must provide all three roles:

```text
development 8   MMLU continuity units — can never rescue the primary
primary_validation 16   the ONLY units entering the primary Spearman statistic
legacy_extension 8      legacy lineage units — can never rescue the primary
```

A merged panel is required so the legacy units are reachable; the primary statistic is still
computed over exactly the 16 validation units. The predictor result is recorded in the final
artifact under `secondary_diagnostics.predictor`.

---

## 14. Completeness

```text
completeness_record_fields:
  status, complete_blocks, incomplete_blocks, missing_dependency,
  undefined_reason, incomplete_reason, analysis_result_fingerprint
status_vocabulary: COMPLETE, INCOMPLETE, UNDEFINED, DEPENDENCY_UNAVAILABLE, FAILED
```

A frozen required node is never reported as `NOT_EXECUTED_IN_THIS_INVOCATION`; only the frozen
terminal states above are permitted.

```text
fixed family incompleteness propagation:
  primary12              12   never shrinks
  extension8              8   never shrinks
  direction6              6   never shrinks
  native12               12   never shrinks
  member_rule            each family member independently checks its own required
                         model x population dependency; a member whose dependency is
                         missing is INCOMPLETE and does not remove a member without
                         that dependency
  core4_isolation        a standalone I-isotonic / B-beta failure never blocks CORE4
                         primary12 or direction6
  native_isolation       Delta_native depends only on the TARGET / native fit
  complete_case_rescue   forbidden
```

---

## 15. Shared formal-DAG engine

Formal execution and synthetic qualification call **the same** engine:

```text
engine:  run_r4_analysis.run_dag_engine
blocks:  input_load, point_estimates, n912_robustness, test_bootstrap,
         train_refit, predictor, final_assembly
```

The only differences between the two modes are:

```text
input source (frozen raw evidence vs invented synthetic fixture)
replicate counts
output root
formal / synthetic authority marker
```

The synthetic qualification must never use a different orchestration path from the formal
execution; a qualification that exercises only a parallel path does not qualify the formal path.

---

## 16. Full-fit coverage and failure semantics

```text
coverage_record_fields:
  fit_identity{model, population, budget, procedure, measurement}, status, failure_type,
  reason, directional_references[{direction, side}]
coverage_key:   model|population|budget|procedure|measurement
fit_status_vocabulary: AVAILABLE, INELIGIBLE, FAILED
```

The registry is keyed by the **canonical fitted-map identity** and carries every directional
role that references it under `directional_references`. Direction and side are references, so a
single measurement-level failure is reported once — never as two independent fit states.
Failed and ineligible cells are retained: never dropped, replaced or averaged over.

A full-TRAIN fit that cannot produce a frozen accepted optimum is an explicit **FAILED** fit,
never a fatal process exception and never a silent `INELIGIBLE`:

```text
logistic core:
  ProbabilityEndpointError -> INELIGIBLE
  AnalysisError            -> FAILED
I-isotonic:
  IsotonicContractViolation-> FAILED
B-beta:
  BetaFitIneligible        -> INELIGIBLE
  BetaContractViolation    -> FAILED
  BetaImplementationError  -> FAILED
any other exception        -> PROPAGATE (FORMAL_ANALYSIS_CODE_DEFECT)
```

The whitelist is **explicit and closed**: there is no `except Exception -> FAILED` policy. An
unknown fit exception is treated as an operational defect, not a scientific failure, and it must
cross the fit layer to be classified as `FORMAL_ANALYSIS_CODE_DEFECT`.

The exception type and message are retained, and the failure is never renamed to
`DEPENDENCY_UNAVAILABLE` at the fit layer. The beta solver, tolerance, starts and constraint
handling are unchanged: no other solver, no other start, no loosened `1e-10` KKT tolerance, no
probability clipping, no regularization, no retry-until-success, and no N912 rescue of N456.

---

## 17. Checkpoint policy

```text
granularity:                 block-level
blocks:                      authority_validation, input_load, point_estimates,
                             n912_robustness, test_bootstrap, train_refit,
                             predictor, final_assembly
atomic_writes:               true
draws_never_checkpointed:    true
replay_rule:                 discard the uncommitted block output and recompute the whole
                             block from identical frozen inputs and identical frozen
                             randomness authority
partial_draw_merge_forbidden: true
bootstrap_chunking:          not introduced
```

Every terminal block carries an identity, an input fingerprint, an output fingerprint and a
status.

Formal mode refuses to start unless the live formal analysis root is absent or empty; an aborted
attempt's checkpoint root is quarantined, never resumed and never merged into a later attempt.

---

## 18. CLI modes

```text
(default)                  no mode: no analysis, exit non-zero
--validate-only            structural validation of frozen authorities and raw-evidence identity only
--synthetic-qualification  invented fixtures only; never reads the formal evidence root
--execute-formal-analysis  explicit formal mode; never implied by any other flag
```

The default invocation performs no calibration fit, no bootstrap and no metric computation.

---

## 19. Formal output roots

```text
formal analysis root:       /root/rivermind-data/r4-formal-analysis
qualification output root:  /root/rivermind-data/r4-analysis-runner-qualification
formal evidence root:       /root/rivermind-data/r4-formal-measurements
```

Formal mode refuses a non-empty unknown output root, and never overwrites existing formal results.

---

## 20. Status

```text
R4 FORMAL ANALYSIS RUNNER = FROZEN CANDIDATE

CANONICAL FIT IDENTITY = MODEL x POPULATION x BUDGET x PROCEDURE x MEASUREMENT
DIRECTION / SIDE = REFERENCES, NOT DISTINCT FIT IDENTITIES
UNKNOWN EXCEPTIONS = OPERATIONAL DEFECTS, NOT SCIENTIFIC FAILURES

FORMAL R4 CALIBRATION / INFERENCE / PREDICTOR = NOT YET AUTHORIZED

FORMAL SCIENTIFIC OUTCOME ESTIMATES COMPUTED = NO
REAL CALIBRATOR FIT ATTEMPTS IN THIS CLOSURE TASK = NO
PRIOR UNAUTHORIZED REAL FIT STATUS EXPOSURE = YES (provenance-only deviation recorded)
FORMAL RESULTS PRODUCED = NO

RAW EVIDENCE = NOT ANALYZED
```

The blocked formal analysis attempt 0 is quarantined at
`/root/rivermind-data/r4-formal-analysis-aborted/attempt0-beta-gate9-runner-defect/` and is
`READ_ONLY / DO_NOT_RESUME / DO_NOT_MERGE / DO_NOT_USE_AS_RESULT`. Its last committed block was
`authority_validation` and it computed zero scientific outputs. The live formal analysis root
`/root/rivermind-data/r4-formal-analysis` does not exist.

Superseded fingerprints, retained as provenance:

```text
contract      2fe5d962a706c822a63573bbd8e553a44b6b0fd082dd582af8cdaa25bc6c7c60  SUPERSEDED FOR FORMAL-PATH COVERAGE
contract      d16a8edb9f7edcb5a0dee69e37bb32f4f45dd661fcb324e166db31a2c6b06ff5  SUPERSEDED BY THE IDENTITY/EXCEPTION CORRECTION
qualification 405f3ffcbf2cc67ff179c75ed157437045c6a726a63ae6b81dede28bcfede5ac  SUPERSEDED FOR FORMAL-PATH COVERAGE
qualification 9e7d998060daf761f1f8914714eb57b16128a18f6db4bde49ddf7db9a0267270  SUPERSEDED BY THE IDENTITY/EXCEPTION CORRECTION
coverage      39ac890e7b7e564cfb14d42353b5db44997c9392513f433c7473cb0a53007d1d  SUPERSEDED BY THE IDENTITY CORRECTION
```

The frozen dependency-graph coverage matrix is
`experiments/calibration_transport/R4_FORMAL_ANALYSIS_RUNNER_DAG_COVERAGE.json`, with
`coverage_fingerprint 5bbd1b0d11c337b410b02fa996ef44389d6c135177ccc3f76145a940819098d1` and
`required_nodes_uncovered = 0`, `required_nodes_without_synthetic_test = 0`.

### 20.1 Firewall deviation provenance

`R4_FORMAL_ANALYSIS_FIREWALL_DEVIATION_ATTEMPT0.json` records a prior
`UNAUTHORIZED_REAL_FIT_STATUS_EXPOSURE`: one ad-hoc debug invocation fitted real current-generation
TRAIN calibrators. No Brier, LogLoss, risk, Delta, bootstrap interval, factorial effect, direction
contrast, predictor value, Spearman correlation or model ranking was computed or inspected, and no
fit parameter or scientific result was persisted. Disposition:
`DO_NOT_USE_FOR_SELECTION_OR_INTERPRETATION`.
