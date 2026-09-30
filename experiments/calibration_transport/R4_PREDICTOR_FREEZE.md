# R4 Target-Label-Free Predictor — SEMANTIC FREEZE

```text
R4 TARGET-LABEL-FREE PREDICTOR SEMANTICS: FROZEN
R4 OVERALL: DRAFT / NOT FULLY FROZEN / NOT EXECUTION-AUTHORIZED
FORMAL R4 EXECUTION: NOT AUTHORIZED
```

This document freezes the **scientific semantics** of the R4 target-label-free
predictor layer. It is a freeze of the reviewed semantic candidate only.

It is **not**:

- a predictor implementation;
- a predictor execution authorization;
- a final integrated R4 protocol;
- a formal R4 execution authorization.

`FROZEN != FORMAL EXECUTION AUTHORIZED`.

---

## 1. Frozen authority inputs

| Authority | Path | SHA256 | Status |
|---|---|---|---|
| Population layer | `experiments/calibration_transport/R4_POPULATION_FREEZE.md` | `850b6b24da61f416b76d0bac83a4ba2775d3002e94894f003fd2e0a5488fee2a` | `R4 POPULATION LAYER: FROZEN` |
| Calibration-family semantics | `experiments/calibration_transport/R4_CALIBRATION_FAMILY_FREEZE.md` | `1fd06ad4804cb64cd9220cc86187e26f6d690fba977bd76918e057bab418cdff` | `R4 CALIBRATION-FAMILY SEMANTICS: FROZEN` |
| Inference + multiplicity semantics | `experiments/calibration_transport/R4_INFERENCE_MULTIPLICITY_FREEZE.json` | `fdc07904056fd72bdd702e275743839eea741364324bd169ec2bf97504a45ad1` | `R4 INFERENCE + MULTIPLICITY SEMANTICS: FROZEN` |
| Inference freeze narrative | `experiments/calibration_transport/R4_INFERENCE_MULTIPLICITY_FREEZE.md` | `a08b8c14d462a348ce6be4d46513f9703126f313758d334e05c085661075cf88` | frozen |
| Inference implementation closure | `experiments/calibration_transport/R4_INFERENCE_IMPLEMENTATION_PROVENANCE_CLOSURE.md` | `22f7f93c742cb7c1b1865c133e635b5e6903d6e879f4e5693bc1eaf2e28438df` | `IMPLEMENTATION PROVENANCE CLOSURE CANDIDATE = PASS` |

Frozen identity anchors:

```text
inference freeze fingerprint   = dcbb7ac9e931145fdee86ab984de1249c1b86ca36ee735b70dafc8cabc06c141
inference amendment commit     = bdaa088a1f5b508c47875039d2cf2be5df1595a1
inference candidate commit     = 2ef9d31cda96dfc3bb326625dad0df061bb7063e
inference candidate fingerprint= 5e10be53c8151d10992b70f4940d0e6f6a7aa83dfe4d5cd49e62b485b0c5e267
inference freeze commit        = 8fc2f3ae465708aa12b108e838377e745e36116b
```

Population manifest fingerprints:

```text
hellaswag_primary       = 5c45043ba4f0ec436c16dcf494ff26be435c7857244bcbefa321d1678129c400
hellaswag_robustness912 = 6817496f227d9cd57759bf55489cbf8a1dc4dfd27db0ae551e9223d21d02a096
medmcqa_primary         = 4a4718438d46ab1ba27c59ca46806756ffb62efa05e6103981dffec4dc48c218
medmcqa_robustness912   = e48c37293f196e16d8fba42e7fc255e4ac2e77f81c270ed6f71320981968af12
```

Calibration scientific fingerprints:

```text
P-low        = 7a8e13d51e131f2102cca4e00b172c8bbb2eb49e591acd3746aeb64d003c8857
P-historical = a44e9217dd43e5e29d859c8dd2dc510a5876db4d46a8e0cc2fd4f1df3121a423
L-low        = 91d7d506275aade7d4676c39722ac2c4d975de7967a25a808395c056307ad619
L-historical = 23ec12bbf4a809ba2f419491df80d1f228d3fd778d848115839aab3697f9dd58
I-isotonic   = cd13bc07bf92f3375bcd16d57fa5f515cd40f68199b57181791f85c58be8c244
B-beta       = f4b710fb98f7c3056794aa709d53309f462a8f598cef8089d2f9c0ed6f7e37ff
```

R3 continuity identity:

```text
r3_protocol_id          = r3-confirmatory-procedure-conditioned-transport
r3_protocol_version     = 1
r3_protocol_fingerprint = 3ef63056ae16b18ad65d9c87d1fbec5b43550873a0e3e25ec0a323f954ee974d
```

---

## 2. Candidate provenance

```text
candidate commit         = ed2ba62ffdae7b1c9890682e3550b54021df6c99
candidate fingerprint    = d3625912fadb5e6c68e20495256aa1f90b53686f13c9d25d1eb9ceb212dfbb06
candidate JSON SHA256    = 31aa9e0b4bf1a95fddd4cad3250ffe3cbb27fb9ac334129c19e020f791f6bcce
candidate MD SHA256      = b82e87c4b2ce8142bd7d9dd7fa8d8c9cb1a46e901625f6a4289c001c50cd3bef
candidate commit message = experiments: specify R4 target-label-free predictor semantics
```

Human / ChatGPT scientific review of this candidate: **PASS**.

---

## 3. Exact semantic-equivalence audit

The freeze payload is derived mechanically:

```text
frozen_semantic_payload =
    reviewed candidate payload
    minus artifact identity keys
      (artifact_type, artifact_version, status,
       candidate_fingerprint, fingerprint_version)
```

Audit result:

```text
result                = EXACT_SEMANTIC_EQUIVALENCE
differing_keys        = []
replaced_keys         = [artifact_type, artifact_version,
                         candidate_fingerprint, fingerprint_version, status]
semantic key count    = 19
```

The only permitted differences between candidate and freeze are artifact
identity, status, candidate provenance, freeze provenance and the freeze
fingerprint. **No scientific key or value was altered.**

Any semantic drift would have been `STOP / PREDICTOR_FREEZE_SEMANTIC_DRIFT`.

---

## 4. Predictor scientific identities

```text
Primary predictor           = r4-target-range-exceedance-warning v1
Secondary predictor         = r4-source-target-wasserstein1-warning v1
Primary predictor outcome   = r4-core4-mean-transport-penalty v1
Secondary predictor outcome = r4-core4-mean-deployment-delta v1
Validation protocol         = r4-heldout-population-predictor-validation v1
```

---

## 5. Label firewall

The predictor feature computation is **target-label-free**.

Allowed predictor inputs:

```text
SOURCE TRAIN raw fixed-event scores
TARGET TEST raw fixed-event scores
model identity
population identity
direction
```

Forbidden predictor inputs:

```text
TARGET Y
TARGET correctness
TARGET ground truth
TARGET Brier
TARGET LogLoss
R_native
R_cross
Delta values
calibrated TARGET probabilities
```

```text
predictor_X_never_uses_labels                = true
target_label_free_is_not_label_free_entire_study = true
outcome_validation_uses_labels               = true
future_function_signature_requirement        = the primary predictor function must
  accept only source_train_scores and target_test_scores; it must not require
  labels, a calibrator, an outcome or ground truth
```

---

## 6. Score geometry

```text
expected domain              = [0, 1]
exact endpoint scores allowed= 0, 1
invalid conditions           = non-finite, score < 0, score > 1
invalid state                = PREDICTOR_INPUT_INVALID
clipping forbidden           = true
```

---

## 7. Primary predictor — X_range

```text
X_range(u) = fraction of TARGET TEST raw scores S_B
             such that S_B < q_low or S_B > q_high
```

where `q_low` / `q_high` are the **SOURCE TRAIN primary N=456** nearest-rank
2.5th / 97.5th percentiles of `S_A^TRAIN`.

```text
source                     = measurement A primary TRAIN N=456 raw fixed-event scores
target                     = measurement B full frozen TEST raw fixed-event scores
source quantile rule       = nearest-rank-percentile
lower fraction / decimal   = 1/40  / 0.025   rank at N=456 = 12
upper fraction / decimal   = 39/40 / 0.975   rank at N=456 = 445
rank convention            = 1-indexed nearest rank; rank = ceil(fraction * 456)
boundary rule              = equality counts as INSIDE; outside test is strict
uses calibrated probabilities = false
uses N912                  = false
N912 forbidden for primary definition = true
expected positive association = true
reads labels               = false
```

Direction source/target mapping:

```text
CAT->OVR: source_measurement A = CAT, target_measurement B = OVR
OVR->CAT: source_measurement B = OVR, target_measurement A = CAT
```

---

## 8. Secondary predictor — X_W1

```text
X_W1(u) = W1(mu, nu) = integral |F_mu(t) - F_nu(t)| dt
```

the one-dimensional **exact empirical** Wasserstein-1 distance between the
SOURCE TRAIN raw-score empirical distribution and the TARGET TEST raw-score
empirical distribution.

```text
mu = (1/n) sum delta_{x_i}
nu = (1/m) sum delta_{y_j}
mass rule                  = every row carries equal mass within each side
allowed computation        = exact sorted-support CDF sweep for 1D empirical measures
forbidden computation      = histogram approximation, binning approximation,
                             random subsampling, quantile-grid approximation
hellaswag target distribution = row-weighted empirical distribution over the
                             frozen TEST rows; NOT an equal-source_id distribution
uses calibrated probabilities = false
reads labels               = false
```

---

## 9. Predictor outcomes — CORE4

```text
CORE4 = P-low, P-historical, L-low, L-historical
```

```text
Y_transport_core(u) = (1/4) * sum over F in CORE4 of Delta_transport(u, F)   [PRIMARY]
Y_deploy_core(u)    = (1/4) * sum over F in CORE4 of Delta_deploy(u, F)      [SECONDARY]

Delta_transport = R_cross(m,p,d,F) - R_native(m,p,d,F)
Delta_deploy    = R_cross(m,p,d,F) - R_raw(m,p,d)
```

```text
outcome ids              = r4-core4-mean-transport-penalty v1 / r4-core4-mean-deployment-delta v1
core procedure count     = 4
standalone extensions excluded = I-isotonic, B-beta
I or B can rescue        = false
averaging remaining three forbidden = true
any dependency unavailable -> unit predictor outcome = INCOMPLETE
source of delta values   = consumes frozen formal inference semantic outputs only
```

Rationale for the CORE4 average (frozen):

```text
- the X predictor has no F dimension, so the same X cannot be treated as
  several independent observations
- removes F pseudo-replication
- preserves continuity with R3 predictor development
- does not let the newly added I/B extensions redefine the primary predictor outcome
- retains procedure-conditioned outcomes separately elsewhere in inference
```

---

## 10. Predictor unit

```text
observational unit = model x population x direction
unit_id_fields     = model_id, population_id, direction_id
rule               = each (model, population, direction) unit appears exactly once
                     in any predictor statistic; procedures are aggregated
                     inside the unit outcome
F is not an independent predictor observation = true
six-procedure pseudo-replication forbidden    = true
```

---

## 11. Development / continuity units

### 11.1 R3 MMLU

```text
classification          = DEVELOPMENT / CONTINUITY
is independent validation = false
reason                  = the predictor idea was motivated by R3 MMLU evidence
forbidden wording       = "validated independently on R3 MMLU"
```

### 11.2 R4 current-generation MMLU

```text
classification     = R4 DEVELOPMENT / CONTINUITY UNITS
population_id      = r4-mmlu-57-subject
models             = 4 current-generation models
directions         = CAT->OVR, OVR->CAT
unit_count         = 8
is independent validation = false
reason             = population = MMLU overlaps the predictor development
                     population, even though the models are new
assignment made before any R4 outcome read = true
cannot merge into the 24-unit validation    = true
required label     = DEVELOPMENT / NOT VALIDATION
```

---

## 12. Primary held-out validation units

```text
protocol_id   = r4-heldout-population-predictor-validation
protocol_version = 1
composition   = 4 current-generation models x {HellaSwag, MedMCQA} x 2 directions
unit_count    = 16
fixed panel   = true
unit weighting= each of the 16 fixed units appears exactly once; HellaSwag and
                MedMCQA each contribute exactly 8 units, so the pooled rank
                correlation gives equal unit count per population
```

| Model | Revision |
|---|---|
| `allenai/Olmo-3-7B-Instruct` | `6e5971d9eba42665f5bd5a0fcf047f299ce1dccc` |
| `tiiuae/Falcon-H1-7B-Instruct` | `41e72f27effbab80cd45b6e884688452253a3686` |
| `ibm-granite/granite-4.0-h-tiny` | `791e0d3d28c86e106c9b6e0b4cecdee0375b6124` |
| `Qwen/Qwen3.5-9B` | `c202236235762e1c871ad0ccb60c8ee5ba337b9a` |

Populations:

```text
r4-hellaswag-activity-primary
r4-medmcqa-subject-primary
```

```text
inference scope = association across the declared fixed held-out validation
                  panel; NOT a superpopulation random-effects inference
post-hoc deletion forbidden = drop a population / drop a model / drop a direction
```

---

## 13. Legacy lineage-continuity extension units

```text
role        = SECONDARY LINEAGE-CONTINUITY VALIDATION EXTENSION
composition = 2 legacy models x 2 held-out populations x 2 directions
unit_count  = 8
can rescue the 16-unit primary = false
is fully independent primary validation = false
forbidden label = "fully independent primary validation"
```

| Legacy model | Revision |
|---|---|
| `openbmb/MiniCPM5-2B` | `12a3808a956f869c767195e9266b59c4d21d92e2` |
| `Qwen/Qwen3.5-2B` | `15852e8c16360a2fea060d615a32b45270f8a8fc` |

---

## 14. Primary statistic

```text
rho_primary = Spearman(X_range(u), Y_transport_core(u))
observation_count = 16
observation_set   = the 16 primary held-out validation units
statistic_id      = spearman-rank-correlation v1
expected direction= positive
```

Exact contract:

```text
computation            = Pearson correlation of average ranks
tie handling           = average ranks for ties
constant input condition = variance(rank(X)) == 0 or variance(rank(Y)) == 0
constant input state   = SPEARMAN_UNDEFINED_CONSTANT_INPUT
forbidden returns      = 0, silent NaN
causal claim forbidden = true
```

---

## 15. Predictor TEST-bootstrap validation

```text
test_bootstrap_replicates = 20000
rho_replicate_count       = 20000
paired                    = true
point_statistic           = full-data rho
bootstrap median substitutes point = false
reuse_frozen_test_bootstrap = true
```

Interval:

```text
type        = 95% two-sided nearest-rank percentile interval
rule        = nearest-rank-percentile
n           = 20000
lower tail / rank = 1/40  / 500
median rank       = 10000
upper tail / rank = 39/40 / 19500
```

Per-replicate procedure (frozen):

```text
1. use that population's already frozen shared TEST resample
2. hold SOURCE TRAIN q2.5/q97.5 fixed at the full primary TRAIN
3. recompute X_range on the resampled TARGET raw scores
4. compute that unit's Y_transport_core with the same TEST resample
5. assemble the complete 16-unit replicate table
6. compute the pooled Spearman rho
```

Population bootstrap modes:

```text
r4-hellaswag-activity-primary:
  protocol_id   = r4-hellaswag-activity-stratified-source-cluster-test-bootstrap v1
  cluster       = source_id
  cluster never split = true
  predictor computation = X_range and X_W1 computed row-weighted on the expanded
                          cluster-resampled row multiset
  separate row bootstrap forbidden = true

r4-medmcqa-subject-primary:
  protocol_id   = r4-medmcqa-subject-stratified-paired-test-bootstrap v1
  mode          = subject_name-stratified-row
  predictor computation = row-weighted target distribution
```

---

## 16. Explicit inferential-scope clarification

```text
The predictor validation bootstrap quantifies
TEST-sampling uncertainty conditional on the
predeclared fixed 16-unit validation panel.

It does NOT resample models, populations, or directions.

It does NOT quantify uncertainty over:
- model selection
- population selection
- direction selection
- future model families
- future benchmark populations.
```

This is a clarification of the already frozen fixed-panel + TEST-bootstrap
semantics. It does **not** change the predictor statistic.

---

## 17. Primary support rule

```text
name      = PRIMARY WARNING-SIGNAL SUPPORT
criterion = rho_primary point statistic > 0 AND 95% TEST-bootstrap lower bound > 0
failure language = PRIMARY WARNING-SIGNAL SUPPORT NOT ESTABLISHED
supports  = association / warning-signal evidence
does not support = causal mechanism, universal predictor, production guarantee
threshold change forbidden = true
```

---

## 18. Undefined replicate rule (fail-closed)

```text
state = SPEARMAN_UNDEFINED_CONSTANT_INPUT
action = record the count and the replicate indices of every undefined planned replicate
consequence = PRIMARY RHO INTERVAL INCOMPLETE
successful subset interval forbidden = true
point rho reported with its own status = true
```

---

## 19. Secondary statistics

Predeclared statistics only:

```text
X_range vs Y_transport_core Spearman   (PRIMARY)
X_W1    vs Y_transport_core Spearman   (SECONDARY)
X_range vs Y_deploy_core    Spearman   (SECONDARY PRACTICAL DIAGNOSTIC)
```

```text
rho_W1_transport  : observation_count 16, reports point statistic + 95% interval,
                    can_rescue_primary = false
rho_range_deploy  : observation_count 16, can_rescue_primary = false
forbidden additional metrics = Pearson, Kendall, mutual information, AUC, R2,
                               threshold optimization, classification accuracy
```

Multiplicity:

```text
merged with inference primary 12-family = false
primary predictor validation claims     = 1
primary criterion scope = frozen 16-unit pooled statistic only
primary gate            = alpha-equivalent 95% interval
secondary cannot rescue primary = true
per-direction descriptive = CAT->OVR 8 units / OVR->CAT 8 units, DESCRIPTIVE ONLY
per-population descriptive = hellaswag 8 / medmcqa 8, DESCRIPTIVE ONLY;
                             one population success cannot claim primary validation
post hoc multiplicity fishing forbidden = true
```

---

## 20. TRAIN-stability infrastructure

```text
protocol_id = r4-stratum-preserving-paired-train-refit-bootstrap v1
train_refit_replicates = 2000
role = SECONDARY STABILITY ONLY
reuse_frozen_train_refit_bootstrap = true
```

Per replicate:

```text
1. resample SOURCE/TRAIN according to the frozen population stratum rule
2. recompute the source q2.5/q97.5 quantiles
3. recompute X_range on the unchanged full TARGET TEST
4. if Y stability is also computed, use the same replicate refitted calibrators
```

Failure rule:

```text
trigger = a TRAIN-resample causes a dependent calibration fit failure
y_stability_block = INCOMPLETE
successful Y-subset correlation CI forbidden = true
X stability may still be reported separately = true
```

Forbidden combination of TEST and TRAIN uncertainty:

```text
variance addition, CI convolution, double bootstrap, quadrature combination
```

---

## 21. Completeness rules

```text
predictor completeness:
  trigger = any primary validation unit has incomplete source TRAIN scores or
            incomplete target TEST raw scores
  unit_state = INCOMPLETE
  primary_validation_state = INCOMPLETE
  unit dropping forbidden = true

outcome completeness:
  Y_transport_core dependencies = P-low, P-historical, L-low, L-historical
  any dependency unavailable -> unit predictor outcome = INCOMPLETE
  any incomplete validation unit -> PRIMARY PREDICTOR VALIDATION = INCOMPLETE
  averaging remaining three forbidden = true
  complete-case Spearman forbidden    = true

outcome construction firewall:
  consume frozen inference semantic outputs only = true
  forbidden = refit calibration, redefine Delta_transport,
              change procedure eligibility, recompute a different transport outcome
```

---

## 22. N912 robustness

```text
role = SECONDARY ROBUSTNESS ONLY
primary predictor remains N456 = true
n912 cannot replace, rescue or retune primary = true
allowed comparisons = X_range_456 vs X_range_912,
                      X_W1_456 vs X_W1_912 (optional)
```

---

## 23. Generalization scope and non-claims

```text
claim type = association across the declared fixed panel
panel      = declared fixed held-out validation panel
is random sample = false
is superpopulation random-effects inference = false
universal behavior across models or populations = false
```

Non-claims:

```text
The predictor does not use TARGET labels as input.
The predictor is an association-based warning signal, not a causal mechanism.
The predictor does not certify calibration transportability.
R3 MMLU is development evidence, not independent validation.
R4 MMLU current-generation units are development/continuity units, not held-out validation.
Primary held-out validation is restricted to the 16 current-generation HellaSwag/MedMCQA direction units.
Legacy-model Hella/Med units are secondary lineage-continuity evidence.
F is not treated as independent predictor replication.
The primary predictor outcome averages only the four R3-continuity logistic procedures.
I-isotonic and B-beta cannot rescue primary predictor validation.
N912 cannot rescue N456 predictor validation.
The predictor does not establish universal behavior across models or populations.
```

---

## 24. Freeze fingerprint and reproduction

```text
artifact_type      = r4-target-label-free-predictor-freeze
artifact_version   = 1
status             = FROZEN
fingerprint_version= 1
freeze_fingerprint = c856fcc161910497a3431593639606682905adcb50fc443455468dfc295d73a9
```

The freeze fingerprint is computed with
`probvenance.fingerprint.fingerprint` over the freeze payload **excluding**
`freeze_fingerprint` itself.

Reproduction: generate the freeze twice from the pinned candidate; both
generations must be byte-identical and fingerprint-identical.

```text
python -m json.tool experiments/calibration_transport/R4_PREDICTOR_FREEZE.json
```

---

## 25. Frozen vs not frozen

Frozen by this document:

```text
- primary and secondary target-label-free predictor identities and definitions
- primary and secondary predictor outcomes (CORE4 means)
- development / validation / legacy unit registries
- predictor TEST-bootstrap validation protocol
- predictor TRAIN-stability protocol
- predictor primary support rule and completeness rules
- N912 robustness role for the predictor layer
- label firewall contract
- score geometry contract
```

Not frozen by this document:

```text
- predictor implementation engineering
- formal R4 predictor validation execution
- formal R4 bootstrap execution
- final integrated R4 protocol
- formal R4 execution authorization
```

---

## 26. Status

```text
R4 TARGET-LABEL-FREE PREDICTOR SEMANTICS: FROZEN
R4 OVERALL: DRAFT / NOT FULLY FROZEN / NOT EXECUTION-AUTHORIZED
FORMAL R4 EXECUTION: NOT AUTHORIZED
```
