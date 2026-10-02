# R4 Formal Analysis Runner — Synthetic Qualification

```text
artifact_type:               r4-formal-analysis-runner-qualification
artifact_version:            1
status:                      PASS
nature:                      OPERATIONAL SYNTHETIC QUALIFICATION
runner_id:                   r4-integrated-formal-analysis-runner
runner_source_path:          experiments/calibration_transport/run_r4_analysis.py
runner_source_sha256:        5b4ab21d262afe1b1755120f83afaa37798df3a41dbef8274cd00ede1350f176
runner_contract_fingerprint: 2fe5d962a706c822a63573bbd8e553a44b6b0fd082dd582af8cdaa25bc6c7c60
qualification_fingerprint:   405f3ffcbf2cc67ff179c75ed157437045c6a726a63ae6b81dede28bcfede5ac
scientific_outputs_computed: false
raw_evidence_analyzed:       false
formal_analysis_authorized:  false
```

The runner is **implementation-qualified against the frozen synthetic / direct-call contract**. It
is not claimed to be "scientifically validated" or "empirically validated".

---

## 1. Entry Git authority

```text
branch:      main
HEAD:        47db3213b350ad9274af3780351c22b211dc21b6
origin/main: 47db3213b350ad9274af3780351c22b211dc21b6
ahead/behind: 0 / 0
worktree:    clean
```

---

## 2. Frozen scientific authority

All frozen artifacts and both frozen statistical implementations were verified by SHA-256 at
startup. Every frozen scientific artifact remains byte-identical after this task.

```text
R4_POPULATION_FREEZE.md                       850b6b24da61f416b76d0bac83a4ba2775d3002e94894f003fd2e0a5488fee2a
R4_CALIBRATION_FAMILY_FREEZE.md               1fd06ad4804cb64cd9220cc86187e26f6d690fba977bd76918e057bab418cdff
R4_INFERENCE_MULTIPLICITY_FREEZE.json         fdc07904056fd72bdd702e275743839eea741364324bd169ec2bf97504a45ad1
R4_PREDICTOR_FREEZE.json                      423c5cdaf68ce7cdbbb80cf704ed18f67692995e418d0dc8f707871322554f8c
R4_MEASUREMENT_EXECUTION_CONTRACT.json        c9d61ed3011a3d42c1455c8e6ff1c724d80a5ceebc2f507992e371d661e15e52
R4_FINAL_PROTOCOL_FREEZE.json                 8d105b2010227b0b6467f3384ca471e536f2ae877ba351546bf4088f501d0fb6
R4_EXECUTION_MANIFEST_FREEZE.json             8b56f62bfe053ddbc92518f92f7aac9da9f6b02af342699eb4db0ee12e61721d
R4_EPOCH1_RAW_MEASUREMENT_EVIDENCE_LEDGER.json 146ad254dda64778cb684283e24ae1dca2987bc6827652c448739b75ae2e1a6a
R4_FORMAL_ANALYSIS_INPUT_REGISTRY.json        cb3e7625ecfcb7ec6dd71431739969eaf7f05eb1ca6a262cd8e5d3276c632921
R4_FORMAL_ANALYSIS_DEPENDENCY_GRAPH.json      fd1248052402de5c6b575957f7465b8f6094455851a16528ea92bc0242d16872
```

```text
raw measurement freeze commit:   3aae4528a131ba32582fb015bd2f6a4d201da457
measurement code commit:         100c918345ff829dd6fdb96bf99cd14285d6472f
ledger fingerprint:              2ed383f67be4476024d12a03c26699a1a50ed8656d75bb089986ce558d1be541
analysis registry fingerprint:   b0051d96eaeea693a37a0116ced4eecc7e7a7fcd34d93049b074a7010c8cb355
dependency graph fingerprint:    449c9b19d61e4edbe95ea856b1d13e3b373765f8a9d05931f20e4d12bf28ed9f
analysis preflight fingerprint:  500ae1cb5ee19d030dad6c27a164b84650adbd79d81451f416126892d2e48873
```

No frozen statistical module was modified. `FROZEN STATISTICAL IMPLEMENTATIONS = UNCHANGED`.

---

## 3. Real-input validate-only result

`run_r4_analysis.py --validate-only` over the real frozen registry and raw evidence:

```text
status:                     PASS
cells:                      16
rows:                       100728
current directional units:  24
legacy directional units:   8
calibrator fits:            0
metrics computed:           0
bootstrap draws:            0
predictor values:           0
scientific_outputs_computed: false
problems:                   []
```

This mode verified only hashes, fingerprints, row identities, counts, schema, unit mapping,
dependency availability, authority identities and output-destination cleanliness. It accessed no
aggregate raw score value beyond the frozen mechanical finite/range checks.

---

## 4. Synthetic fixture identity

```text
marker:              SYNTHETIC_ONLY_NOT_SCIENTIFIC_EVIDENCE
strata per population: 6
train per stratum:     12
test per stratum:      12
clusters per stratum:  3
score source:        sha256 fingerprint of a frozen synthetic identity payload
labels:              invented non-separable labels derived from the invented scores
formal evidence consumed: false
```

The synthetic fixture never reads the formal evidence root, and the formal mode never accepts the
synthetic fixture. The rejection is enforced in both directions.

---

## 5. Synthetic CORE4 / isotonic / beta qualification

The integrated runner result is compared against an **independent recomposition** of the frozen
modules (`r3_analysis.fit_calibrator`, `r4_calibration_families`, `r4_inference.risk_matrix`):

```text
point_estimate_oracle_equal: true
point_estimate_mismatches:   []
available_procedures:        P-low, P-historical, L-low, L-historical, I-isotonic, B-beta
```

Isotonic qualification covered an ordinary eligible fit, exact-score aggregation (ties) and
out-of-boundary application. Beta qualification covered an ordinary eligible fit, TRAIN endpoint
ineligibility, monotone-separation ineligibility and the application endpoint mathematical limit.
No clipping is used to make any qualification pass.

---

## 6. Synthetic metric / extended-real qualification

```text
mean_brier:                             0.28125
mean_logloss_state:                     FINITE
logloss_zero_mass_correct_state:        FINITE
logloss_zero_mass_incorrect_state:      POSITIVE_INFINITY
inf_minus_inf_state:                    UNDEFINED_EXTENDED_REAL
inf_plus_finite_state:                  POSITIVE_INFINITY
undefined_constant:                     UNDEFINED_EXTENDED_REAL
```

All values above are synthetic. The zero-mass LogLoss is never clipped, smoothed or repaired.

---

## 7. Synthetic Delta / family qualification

```text
full panel family status:
  primary12              12/12 COMPLETE
  direction_difference6   6/6 COMPLETE
  extension8              8/8 COMPLETE
  native_reference12     12/12 COMPLETE

CORE4-only family status:
  primary12              12/12 COMPLETE
  direction_difference6   6/6 COMPLETE
  extension8              0/8 INCOMPLETE
  native_reference12      8/12 INCOMPLETE

refit blocks:             192 (primary) / 64 (legacy), statuses ["COMPLETE"]
```

This is exactly the dependency-unavailable propagation the freeze allows: the primary family and
the direction-contrast family remain complete, the extension family and the native-reference
family degrade to INCOMPLETE, no family is shrunk, and no complete-case rescue is performed.

---

## 8. Synthetic bootstrap-sharing qualification

```text
shared_draw_identity_equal_across_models: true
cluster_never_split:                      true
shared across models / directions / procedures / estimands: true
```

One population-level TEST draw is used by every model, direction, procedure and estimand; a
HellaSwag `source_id` cluster is never split.

---

## 9. Synthetic predictor qualification

```text
units_total:          32
development_units:     8
validation_units:     16
legacy_units:          8
status:               COMPLETE
successful_replicates: 16/16
tail_rule:            1/40, 39/40
```

Covered: range thresholds, strict exceedance (equality inside), exact empirical Wasserstein-1,
development-8 / validation-16 / legacy-8 classification, CORE4-only outcome mean, Spearman ties,
a constant predictor yielding `undefined`, and an undefined replicate yielding an incomplete
interval. The same TEST resample is used for target `X` and outcome `Y`; the source TRAIN
thresholds stay fixed.

---

## 10. Golden direct-call equivalence

Because the runner calls the same frozen functions, the comparison requires exact canonical
equality rather than a looser numerical tolerance:

```text
primary panel: point_estimate_oracle_equal = true, mismatches = []
legacy  panel: point_estimate_oracle_equal = true, mismatches = []
```

No runner-specific tolerance was introduced.

---

## 11. Formal safety tests

```text
no flag                    -> no analysis
--validate-only            -> no analysis
--synthetic-qualification  -> synthetic only
formal flag + missing authority      -> rejected
formal flag + dirty / wrong identity -> rejected
synthetic fixture in formal mode     -> rejected
formal evidence in synthetic mode    -> rejected
```

---

## 12. Checkpoint / replay policy

```text
granularity:                  block-level
blocks:                       authority_validation, input_load, point_estimates,
                              n912_robustness, test_bootstrap, train_refit,
                              predictor, final_assembly
atomic writes:                true
draws never checkpointed:     true
replay rule:                  whole-block recomputation from identical frozen inputs
                              and identical frozen randomness authority
partial draw merge forbidden: true
bootstrap chunking:           not introduced
```

---

## 13. Randomness authority

```text
prng:  none
seed:  none
mechanism: sha256 fingerprint of a frozen identity payload, reduced modulo the pool size
kernel:    r4_inference.deterministic_index
```

TEST identity fields: `protocol_id, protocol_version, population_id, population_fingerprint,
replicate_index, stratum, draw_index, pool_size, cluster_mode_marker`.
TRAIN-refit identity fields: `protocol_id, protocol_version, population_id,
population_fingerprint, budget_identity, replicate_index, stratum, draw_index, pool_size`.

Formal counts are TEST `20000` and TRAIN-refit `2000`. No system entropy, wall clock or builtin
`hash` participates.

---

## 14. Determinism

Two independent `--synthetic-qualification --synthetic-replicates 16` runs produced
**byte-identical** canonical output. The qualification artifact is regenerable and deterministic.

---

## 15. Tests

```text
tests/test_r4_analysis_runner.py:  collected 89, passed 89, failed 0
```

---

## 16. Status

```text
R4 FORMAL ANALYSIS RUNNER BUILD = PASS

R4 FORMAL ANALYSIS RUNNER SYNTHETIC QUALIFICATION = PASS

FROZEN STATISTICAL IMPLEMENTATIONS = UNCHANGED

RAW EVIDENCE = NOT ANALYZED

SCIENTIFIC OUTPUTS COMPUTED = NO

CURRENT DIRECTIONAL UNITS = 24
LEGACY SECONDARY UNITS = 8

PRIMARY FAMILY = 12
EXTENSION FAMILY = 8
DIRECTION-CONTRAST FAMILY = 6
NATIVE-REFERENCE FAMILY = 12

PREDICTOR DEVELOPMENT = 8
PREDICTOR HELDOUT VALIDATION = 16
PREDICTOR LEGACY SECONDARY = 8

R4 FORMAL ANALYSIS RUNNER = QUALIFIED CANDIDATE

FORMAL R4 CALIBRATION / INFERENCE / PREDICTOR = NOT YET AUTHORIZED

PUSH PERFORMED = NO
```
