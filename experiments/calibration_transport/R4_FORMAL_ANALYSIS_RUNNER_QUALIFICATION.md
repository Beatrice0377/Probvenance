# R4 Formal Analysis Runner — Synthetic Qualification

```text
artifact_type:               r4-formal-analysis-runner-qualification
artifact_version:            1
status:                      PASS
nature:                      OPERATIONAL SYNTHETIC FORMAL-DAG QUALIFICATION
runner_id:                   r4-integrated-formal-analysis-runner
runner_source_path:          experiments/calibration_transport/run_r4_analysis.py
runner_source_sha256:        e86ef34a3435c81fd78285fbc709a7966bf704fbe35987db6d3003d2cf31bac3
runner_contract_fingerprint: d16a8edb9f7edcb5a0dee69e37bb32f4f45dd661fcb324e166db31a2c6b06ff5
qualification_fingerprint:   9e7d998060daf761f1f8914714eb57b16128a18f6db4bde49ddf7db9a0267270
scientific_outputs_computed: false
raw_evidence_analyzed:       false
formal_analysis_authorized:  false
superseded_qualification_fingerprint: 405f3ffcbf2cc67ff179c75ed157437045c6a726a63ae6b81dede28bcfede5ac
```

The runner is **implementation-qualified against the frozen synthetic / direct-call contract**. It
is not claimed to be "scientifically validated" or "empirically validated".

The previous qualification fingerprint
`405f3ffcbf2cc67ff179c75ed157437045c6a726a63ae6b81dede28bcfede5ac` is marked **SUPERSEDED FOR
FORMAL-PATH COVERAGE**: it passed its tested path, but that path was a separate orchestration path
and did not exercise the exact formal orchestration path. Formal execution and synthetic
qualification now call the **same** engine (`run_r4_analysis.run_dag_engine`).

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

The N912 nested synthetic fixture is built by doubling `train_per_stratum` (24 instead of 12), so
the N456 TRAIN item set is a strict prefix of the N912 TRAIN item set and the TEST rows are
byte-identical.

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

refit blocks:             288 (primary) / 96 (legacy) / 189 (n912), all six procedures
                          and both refit estimands (Delta_deploy, Delta_transport)
```

This is exactly the dependency-unavailable propagation the freeze allows: the primary family and
the direction-contrast family remain complete, the extension family and the native-reference
family degrade to INCOMPLETE, no family is shrunk, and no complete-case rescue is performed.

Some primary refit blocks are INCOMPLETE because individual refit replicates fail (B-beta /
I-isotonic resample failures); the interval is withheld and the failure is recorded, e.g.
`B-beta|BootstrapContractViolation|refit calibrator is unavailable:
cross='BetaImplementationError: no constraint face produced an accepted optimum' native=None`.

Full-fit coverage on the synthetic panel:

```text
primary: 288 registry entries (4 models x 3 populations x 2 directions x 6 procedures x 2 sides)
legacy:   96 registry entries (2 models x 2 populations x 2 directions x 6 procedures x 2 sides)
failed / ineligible: []
registry key: model|population|procedure|direction|side
```

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

## 15. Shared formal-DAG engine

Formal execution and synthetic qualification call **the same** engine,
`run_r4_analysis.run_dag_engine`, so the qualification exercises the exact formal orchestration
path. The only differences between the modes are the input source, the replicate counts, the
output root and the formal/synthetic authority marker.

```text
engine blocks observed:
  input_load, point_estimates, n912_robustness, test_bootstrap,
  train_refit, predictor, final_assembly
```

The final artifact contains no `NOT_EXECUTED_IN_THIS_INVOCATION` token for any frozen node.

---

## 16. Dependency failure propagation

The frozen dependency truth table is encoded and tested:

```text
Delta_deploy     requires CROSS fit only
Delta_native     requires NATIVE fit only
Delta_transport  requires CROSS + NATIVE fits
```

A `BetaImplementationError("no constraint face produced an accepted optimum")` was injected into
one synthetic unit (`falcon-h1-7b-instruct|r4-hellaswag-activity-primary|CAT->OVR|B-beta`):

```text
cross-only failure:  computable estimands ["Delta_native"],  status FAILED,
                     failure_type BetaImplementationError
                     family sizes {primary 12, direction 6, extension 6, native 12}
native-only failure: computable estimands ["Delta_deploy"]
both failed:         computable estimands []
                     family sizes {primary 12, direction 6, extension 6, native 11}
both failed fits:    the two injected B-beta cross/native keys
core4 primary12 and direction6 remain COMPLETE under injection: true
family sizes fixed:  {primary 12, extension 8, direction_difference 6, native_reference 12}
```

The runner does not crash, the exact failure class and message are retained, dependent members are
INCOMPLETE, unaffected members continue, and no family is shrunk.

---

## 17. Exact LogLoss formal path

```text
status:              INCOMPLETE
contrasts:           36
undefined contrasts: CAT->OVR|I-isotonic|Delta_transport,
                     OVR->CAT|I-isotonic|Delta_transport
```

An isotonic calibrator producing exact 0/1 probabilities makes the replicate contrast
`+inf - +inf = UNDEFINED_EXTENDED_REAL`; the whole dependent interval is withheld. No undefined
replicate is dropped and no successful-subset interval is produced. The carrier is
`r4_inference.ExtendedReal`, with no clipping, epsilon or `nextafter`.

---

## 18. N912 robustness formal path

```text
role:                         SECONDARY ROBUSTNESS ONLY
comparisons:                  32
paired within the same TEST replicate: true
cannot_rescue_primary:        true
refit blocks:                 189 (192 minus 3 dependency-skipped), statuses ["COMPLETE"]
scope:                        frozen new-population 912 manifests only (HellaSwag, MedMCQA)
```

The `N912 - N456` difference is subtracted directly within the same shared TEST replicate index;
no independent resampling stream is introduced. If N456 failed and N912 succeeded, the primary
would stay FAILED / INCOMPLETE.

---

## 19. Legacy secondary formal path

```text
models:        minicpm5-2b, qwen3-5-2b
populations:   HellaSwag, MedMCQA
budget:        N456 only
refit blocks:  96, covering all six procedures and both refit estimands
```

The legacy panel produces its own secondary point estimates, bootstrap quantities and predictor
legacy-8 quantities. A legacy model never enters `primary12` and never enters the predictor
`validation16`; the legacy units can never rescue the 16-unit primary statistic.

---

## 20. Frozen-DAG coverage matrix

```text
artifact:   experiments/calibration_transport/R4_FORMAL_ANALYSIS_RUNNER_DAG_COVERAGE.json
coverage_fingerprint: 39ac890e7b7e564cfb14d42353b5db44997c9392513f433c7473cb0a53007d1d
frozen dependency graph: 449c9b19d61e4edbe95ea856b1d13e3b373765f8a9d05931f20e4d12bf28ed9f
frozen nodes:                 20
required nodes with no formal path:            0
required nodes with no synthetic test:         0
```

Every frozen node records its formal engine path, its engine output key, its result-schema path,
its synthetic test and its status propagation rule.

---

## 21. Tests

```text
tests/test_r4_analysis_runner.py:  collected 106, passed 106, failed 0
```

---

## 22. Status

```text
R4 FORMAL ANALYSIS RUNNER BUILD = PASS

R4 FORMAL ANALYSIS RUNNER SYNTHETIC QUALIFICATION = PASS

R4 FORMAL ANALYSIS RUNNER FULL-DAG CLOSURE = PASS

EXACT LOGLOSS FORMAL PATH = QUALIFIED
N912 FORMAL PATH = QUALIFIED
LEGACY SECONDARY FORMAL PATH = QUALIFIED
PREDICTOR 8/16/8 FORMAL PATH = QUALIFIED
DEPENDENCY FAILURE PROPAGATION = QUALIFIED

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
