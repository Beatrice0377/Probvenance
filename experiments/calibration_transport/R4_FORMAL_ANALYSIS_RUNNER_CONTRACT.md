# R4 Formal Analysis Runner — Execution Contract

```text
artifact_type:            r4-formal-analysis-runner-contract
artifact_version:         1
status:                   FROZEN CANDIDATE
nature:                   OPERATIONAL ANALYSIS ORCHESTRATION CONTRACT
runner_id:                r4-integrated-formal-analysis-runner
runner_version:           1
runner_source_path:       experiments/calibration_transport/run_r4_analysis.py
runner_source_sha256:     5b4ab21d262afe1b1755120f83afaa37798df3a41dbef8274cd00ede1350f176
runner_contract_fingerprint: 2fe5d962a706c822a63573bbd8e553a44b6b0fd082dd582af8cdaa25bc6c7c60
formal_analysis_authorized:  false
scientific_semantics_changed: false
scientific_outputs_computed:  false
raw_evidence_analyzed:        false
```

This document defines **fields only**. It carries no real scientific value.

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
  separate_from_primary, cannot_rescue_primary
```

N912 is a nested `N456 + extension456` direct-robustness budget. It never replaces, overrides or
rescues the `N456` primary result, and legacy cells never use N912.

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

---

## 14. Completeness

```text
completeness_record_fields:
  status, complete_blocks, incomplete_blocks, missing_dependency,
  undefined_reason, incomplete_reason, analysis_result_fingerprint
status_vocabulary: COMPLETE, INCOMPLETE, UNDEFINED, DEPENDENCY_UNAVAILABLE
```

---

## 15. Checkpoint policy

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

---

## 16. CLI modes

```text
(default)                  no mode: no analysis, exit non-zero
--validate-only            structural validation of frozen authorities and raw-evidence identity only
--synthetic-qualification  invented fixtures only; never reads the formal evidence root
--execute-formal-analysis  explicit formal mode; never implied by any other flag
```

The default invocation performs no calibration fit, no bootstrap and no metric computation.

---

## 17. Formal output roots

```text
formal analysis root:       /root/rivermind-data/r4-formal-analysis
qualification output root:  /root/rivermind-data/r4-analysis-runner-qualification
formal evidence root:       /root/rivermind-data/r4-formal-measurements
```

Formal mode refuses a non-empty unknown output root, and never overwrites existing formal results.

---

## 18. Status

```text
R4 FORMAL ANALYSIS RUNNER = FROZEN CANDIDATE

FORMAL R4 CALIBRATION / INFERENCE / PREDICTOR = NOT YET AUTHORIZED

SCIENTIFIC OUTPUTS COMPUTED = NO

RAW EVIDENCE = NOT ANALYZED
```
