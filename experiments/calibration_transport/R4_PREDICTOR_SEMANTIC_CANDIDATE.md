# R4 Target-Label-Free Predictor Semantic Candidate

**Status:** `CANDIDATE / NOT FROZEN / NO STUDY FITTING / NO EXECUTION AUTHORIZATION`

This artifact defines the semantics of the R4 target-label-free calibration-transport
**warning-signal predictor**, plus its development / validation unit assignment. It
defines semantics only: it does not implement the predictor, does not fit anything, does
not read any R4 outcome, and does not authorize formal execution.

Machine-readable companion: `experiments/calibration_transport/R4_PREDICTOR_SEMANTIC_CANDIDATE.json`.

```text
candidate_fingerprint = d3625912fadb5e6c68e20495256aa1f90b53686f13c9d25d1eb9ceb212dfbb06
fingerprint_version   = 1
```

---

## 1. Authority

| authority | identity |
| --- | --- |
| R4 inference freeze | `R4_INFERENCE_MULTIPLICITY_FREEZE.json` sha256 `fdc07904056fd72bdd702e275743839eea741364324bd169ec2bf97504a45ad1`, freeze_fingerprint `dcbb7ac9e931145fdee86ab984de1249c1b86ca36ee735b70dafc8cabc06c141` |
| inference candidate fingerprint | `5e10be53c8151d10992b70f4940d0e6f6a7aa83dfe4d5cd49e62b485b0c5e267` |
| freeze commit | `8fc2f3ae465708aa12b108e838377e745e36116b` |
| candidate commit | `2ef9d31cda96dfc3bb326625dad0df061bb7063e` |
| original inference implementation commit | `8c3bb0f0e4367bf7194f22a3f38d66aff3cbbbf7` |
| inference amendment commit | `bdaa088a1f5b508c47875039d2cf2be5df1595a1` (`experiments: harden R4 inference dependency isolation`) |
| R4 calibration-family freeze | `R4_CALIBRATION_FAMILY_FREEZE.md` sha256 `1fd06ad4804cb64cd9220cc86187e26f6d690fba977bd76918e057bab418cdff` |
| R4 population freeze | `R4_POPULATION_FREEZE.md` sha256 `850b6b24da61f416b76d0bac83a4ba2775d3002e94894f003fd2e0a5488fee2a` |
| R3 protocol fingerprint | `3ef63056ae16b18ad65d9c87d1fbec5b43550873a0e3e25ec0a323f954ee974d` |

Calibration scientific fingerprints: I-isotonic `cd13bc07bf92f3375bcd16d57fa5f515cd40f68199b57181791f85c58be8c244`,
B-beta `f4b710fb98f7c3056794aa709d53309f462a8f598cef8089d2f9c0ed6f7e37ff`.
R3 continuity procedure fingerprints: P-low `7a8e13d5…`, P-historical `a44e9217…`,
L-low `91d7d506…`, L-historical `23ec12bb…`.

Population manifest fingerprints: HellaSwag primary
`5c45043ba4f0ec436c16dcf494ff26be435c7857244bcbefa321d1678129c400`, MedMCQA primary
`4a4718438d46ab1ba27c59ca46806756ffb62efa05e6103981dffecdc48c218`, HellaSwag 912
`6817496f227d9cd57759bf55489cbf8a1dc4dfd27db0ae551e9223d21d02a096`, MedMCQA 912
`e48c37293f196e16d8fba42e7fc255e4ac2e77f81c270ed6f71320981968af12`.

---

## 2. Scientific purpose

The predictor is **not** a new calibration method, **not** a causal mechanism estimator
and **not** an accuracy predictor. It is a **target-label-free warning signal** for
calibration-map transport risk. The core question is:

> Without reading TARGET labels, does a support / distribution mismatch between the
> SOURCE TRAIN score distribution and the TARGET score distribution foreshadow the
> calibration transport penalty?

---

## 3. Strict target-label-free definition

Predictor feature computation must never read: TARGET Y, TARGET correctness, TARGET
ground truth, TARGET Brier, TARGET LogLoss, `R_native`, `R_cross`, any Delta value, or
calibrated TARGET probabilities.

It may read: SOURCE TRAIN raw fixed-event scores, TARGET TEST raw fixed-event scores,
model identity, population identity, direction.

```text
target-label-free  !=  label-free entire study
```

Outcome validation necessarily uses labels to compute the transport outcome, but the
predictor `X` itself never does. The future primary predictor function must accept only
`source_train_scores` and `target_test_scores` — never labels, a calibrator, an outcome
or ground truth — and future tests must prove that by API signature or monkey-free
inspection. The candidate stage records this requirement and implements nothing.

---

## 4. Predictor unit

The only predictor observational unit is `model × population × direction`. `F` is never
an independent predictor observation, and the six procedures must never become six
pseudo-replicates. Each unit appears exactly once in any predictor statistic; procedures
are aggregated inside the unit outcome.

---

## 5. Primary predictor — `X_range`

```text
predictor_id      = r4-target-range-exceedance-warning
predictor_version = 1
role              = PRIMARY
```

For unit `u = (model m, population p, direction A->B)`:

- SOURCE = measurement A, primary TRAIN, N = 456, raw fixed-event scores `S_A^TRAIN`;
- TARGET = measurement B, full frozen TEST, raw fixed-event scores `S_B`;
- `q_low` / `q_high` = SOURCE TRAIN primary N=456 nearest-rank 2.5th / 97.5th
  percentiles of `S_A^TRAIN`.

```text
X_range(u) = fraction of TARGET TEST raw scores S_B with S_B < q_low or S_B > q_high
```

Boundary: `S_B == q_low` and `S_B == q_high` count as **inside**; the outside test is
strict (`<`, `>`).

Frozen nearest-rank rule: `rank = ceil(fraction * n)` clamped to `[1, n]`,
`value = ordered[rank-1]`, even `n` is NOT averaged. At N = 456 this gives
`ceil(0.025 * 456) = 12` and `ceil(0.975 * 456) = 445` (1-indexed).

The primary predictor uses only the primary N=456 SOURCE TRAIN. N=912 must never define
the primary predictor; an N=912 version is at most future secondary robustness.

---

## 6. Secondary predictor — `X_W1`

```text
predictor_id      = r4-source-target-wasserstein1-warning
predictor_version = 1
role              = SECONDARY
```

`X_W1(u)` is the one-dimensional empirical Wasserstein-1 distance between the SOURCE
TRAIN raw-score empirical distribution and the TARGET TEST raw-score empirical
distribution. For empirical measures `mu = (1/n) Σ δ_{x_i}` and `nu = (1/m) Σ δ_{y_j}`:

```text
W1(mu, nu) = ∫ |F_mu(t) - F_nu(t)| dt
```

Every row carries equal mass within each side. The HellaSwag TARGET distribution remains
a **row-weighted empirical distribution**, not an equal-`source_id` distribution. An exact
sorted-support CDF sweep is allowed; histogram approximation, binning approximation,
quantile-grid approximation and random subsampling are forbidden. W1 reads no labels and
uses no calibrated probabilities. The candidate stage does not implement it.

---

## 7. Outcomes

### 7.1 Primary — `Y_transport_core`

```text
outcome_id      = r4-core4-mean-transport-penalty
outcome_version = 1
```

```text
Y_transport_core(u) = (1/4) * Σ_{F in CORE4} Delta_transport(u, F)
CORE4 = {P-low, P-historical, L-low, L-historical}
Delta_transport(m,p,d,F) = R_cross(m,p,d,F) - R_native(m,p,d,F)
```

Positive larger = larger average transport penalty relative to target-native calibration,
across the R3-continuity core. This is the predictor's primary target.

**Why core-four averaging.** The `X` predictor has no `F` dimension, so the same `X`
cannot be treated as several independent observations. The equal core-four mean:
(1) removes `F` pseudo-replication; (2) preserves continuity with R3 predictor
development; (3) does not let the newly added I/B extensions redefine the primary
predictor outcome; (4) retains procedure-conditioned outcomes separately elsewhere in
inference. This is not a statement that `F` is unimportant.

### 7.2 Secondary — `Y_deploy_core`

```text
outcome_id      = r4-core4-mean-deployment-delta
outcome_version = 1
Y_deploy_core(u) = (1/4) * Σ_{F in CORE4} Delta_deploy(u, F)
Delta_deploy(m,p,d,F) = R_cross(m,p,d,F) - R_raw(m,p,d)
```

Role: secondary deployment-warning interpretation. It must not be merged with
`Y_transport_core`; the primary predictor claim rests on `Y_transport_core` only.

### 7.3 I-isotonic / B-beta

`I-isotonic` and `B-beta` are **not** part of the primary predictor outcome. A future
formal analysis may report descriptive extension sensitivity
(`X_range` vs `Delta_transport(I)`, `X_range` vs `Delta_transport(B)`) separately, with
no pseudo-replication and no primary rescue. The candidate establishes no new
confirmatory predictor family.

---

## 8. Development / validation isolation

This is the most important part of the candidate. The assignment below is made **before
any R4 outcome is read**.

| block | composition | count | classification |
| --- | --- | --- | --- |
| R3 MMLU | all R3 MMLU evidence | — | DEVELOPMENT / CONTINUITY (the predictor idea was motivated by R3 MMLU) |
| R4 MMLU current-generation | 4 current-generation models × MMLU × 2 directions | 8 | DEVELOPMENT / CONTINUITY UNITS |
| primary held-out validation | 4 current-generation models × {HellaSwag, MedMCQA} × 2 directions | 16 | PRIMARY HELD-OUT VALIDATION UNITS |
| legacy extension | 2 legacy models × {HellaSwag, MedMCQA} × 2 directions | 8 | SECONDARY LINEAGE-CONTINUITY VALIDATION EXTENSION |

`R3 MMLU ≠ independent validation`. R4 MMLU current-generation units are development /
continuity units even though the models are new, because the population overlaps the
predictor development population; they must never be merged with the 16 held-out units
into a "24-unit independent validation".

Legacy-model Hella/Med units have held-out populations but lineages that participated in
prior R3 development, so they are secondary lineage-continuity evidence and cannot
rescue the 16-unit primary validation.

Current-generation models (exact revisions): `allenai/Olmo-3-7B-Instruct` @
`6e5971d9eba42665f5bd5a0fcf047f299ce1dccc`, `tiiuae/Falcon-H1-7B-Instruct` @
`41e72f27effbab80cd45b6e884688452253a3686`, `ibm-granite/granite-4.0-h-tiny` @
`791e0d3d28c86e106c9b6e0b4cecdee0375b6124`, `Qwen/Qwen3.5-9B` @
`c202236235762e1c871ad0ccb60c8ee5ba337b9a`. Legacy models: `openbmb/MiniCPM5-2B` @
`12a3808a956f869c767195e9266b59c4d21d92e2`, `Qwen/Qwen3.5-2B` @
`15852e8c16360a2fea060d615a32b45270f8a8fc`.

### No validation-set tuning

After seeing the Hella/Med predictor outcome it is forbidden to: change `q2.5/q97.5`,
switch to `q5/q95`, choose min/max, change the W1 definition, drop a model, drop a
direction, change the core-F aggregation, switch the primary outcome to
`Delta_deploy`, or choose the predictor by the larger observed correlation. Primary
predictor `X_range` and secondary `X_W1` are locked.

---

## 9. Primary validation statistic

```text
statistic_id      = spearman-rank-correlation
statistic_version = 1
rho_primary = Spearman( X_range(u), Y_transport_core(u) )  over exactly 16 units
```

Expected direction: **positive** (larger support mismatch hypothesized as a larger
transport-penalty warning). No causal claim.

Exact contract: average ranks for ties; Pearson correlation of average ranks; if
`variance(rank(X)) == 0` or `variance(rank(Y)) == 0` the result is
`SPEARMAN_UNDEFINED_CONSTANT_INPUT` — never a silent `0` or `NaN`.

---

## 10. Primary validation uncertainty

Reuse the already frozen R4 TEST bootstrap (20000 replicates), but keep the predictor
validation **paired**. For each TEST bootstrap replicate, for each held-out unit:

1. use that population's already frozen shared TEST resample;
2. hold the SOURCE TRAIN `q2.5/q97.5` fixed at the full primary TRAIN;
3. recompute `X_range` on the resampled TARGET raw scores;
4. compute that unit's `Y_transport_core` with the same TEST resample;
5. assemble the complete 16-unit replicate table;
6. compute the pooled Spearman rho.

This yields 20000 rho replicates. The reported interval is the 95% two-sided
nearest-rank percentile interval with tails `1/40` and `39/40`, n = 20000, giving
lower rank **500**, median rank **10000**, upper rank **19500**. The formal point
statistic is the full-data rho; the bootstrap median must not substitute for it.

Bootstrap modes are reused unchanged: HellaSwag
`r4-hellaswag-activity-stratified-source-cluster-test-bootstrap` v1 (`source_id` clusters
are never split; `X_range` / `X_W1` are computed row-weighted on the expanded
cluster-resampled row multiset; no separate row bootstrap) and MedMCQA
`r4-medmcqa-subject-stratified-paired-test-bootstrap` v1 (`subject_name`-stratified row
bootstrap, row-weighted target distribution).

**Undefined bootstrap rho.** If any planned replicate yields
`SPEARMAN_UNDEFINED_CONSTANT_INPUT`, record the count and the replicate indices and
declare `PRIMARY RHO INTERVAL INCOMPLETE`. A successful-subset interval is forbidden. The
point rho is still reported with its own status.

---

## 11. Primary support criterion

```text
PRIMARY WARNING-SIGNAL SUPPORT
  iff  rho_primary point > 0
  and  95% TEST-bootstrap lower bound > 0
otherwise
  PRIMARY WARNING-SIGNAL SUPPORT NOT ESTABLISHED
```

The threshold is not changeable. This criterion supports **association / warning-signal
evidence only** — not a causal mechanism, not a universal predictor, not a production
guarantee.

---

## 12. Secondary statistics

```text
rho_W1_transport  = Spearman( X_W1, Y_transport_core )   (SECONDARY)
rho_range_deploy  = Spearman( X_range, Y_deploy_core )   (SECONDARY PRACTICAL DIAGNOSTIC)
```

Both use the same 16 units and report a point statistic plus a 95% TEST-bootstrap
interval. Neither can rescue the primary predictor validation.

**No metric zoo.** Only the three statistics above are predeclared. Pearson, Kendall,
mutual information, AUC, R², threshold optimization and classification accuracy are not
added.

**Multiplicity.** There is exactly one primary predictor validation claim, gated by an
alpha-equivalent 95% interval; it is not merged with the inference primary 12 family. The
two secondary statistics cannot rescue the primary. Per-population (8 units each) and
per-direction (8 units each) rho values are **DESCRIPTIVE ONLY**: no separate
significance gate, and one population succeeding cannot claim primary validation. The
primary criterion looks only at the frozen 16-unit pooled statistic.

---

## 13. TRAIN uncertainty (secondary stability)

Primary predictor inference uses TEST uncertainty only, conditional on the full primary
TRAIN. A secondary stability analysis reuses the frozen
`r4-stratum-preserving-paired-train-refit-bootstrap` v1 (2000 TRAIN-refit draws). Each
replicate resamples SOURCE/TRAIN by the frozen population stratum rule, recomputes the
source `q2.5/q97.5`, and recomputes `X_range` on the unchanged full TARGET TEST; if Y
stability is also computed it uses the same replicate refitted calibrators. TEST and
TRAIN uncertainty are never combined numerically (no variance addition, CI convolution,
double bootstrap or quadrature).

If a TRAIN resample causes a dependent calibration fit failure, the corresponding Y
stability block is `INCOMPLETE`; `X_range` stability may still be reported separately, and
a successful-Y-subset correlation CI is forbidden.

---

## 14. Completeness and failure rules

- `Y_transport_core(u)` requires all four CORE4 procedures. If any is unavailable the
  unit predictor outcome is `INCOMPLETE`; averaging the remaining three is forbidden.
- If any primary validation unit outcome is incomplete, `PRIMARY PREDICTOR VALIDATION =
  INCOMPLETE`; complete-case Spearman is forbidden.
- If any unit has incomplete source TRAIN scores or incomplete target TEST raw scores,
  that unit predictor is `INCOMPLETE` and the primary validation is `INCOMPLETE`; units
  are never dropped.
- Outcome construction consumes frozen inference semantic outputs only: no refitting, no
  redefining `Delta_transport`, no changing procedure eligibility, no recomputing a
  different transport outcome.

---

## 15. N912 robustness

HellaSwag / MedMCQA N912 is allowed for secondary robustness only:
`X_range_456` vs `X_range_912`, and optionally `X_W1_456` vs `X_W1_912`. The primary
predictor remains N456; 912 cannot replace, rescue or retune the primary validation.

---

## 16. Score geometry and no-threshold rule

Raw fixed-event scores are expected in `[0, 1]`. Non-finite, `< 0` or `> 1` yields
`PREDICTOR_INPUT_INVALID`; clipping is forbidden. Exact `0` and `1` are legal for the
predictor score distribution itself.

The predictor is not a binary deployment rule. Selecting `X_range > threshold` to
classify "safe/unsafe" after seeing the validation outcome is forbidden, as are ROC
tuning, a Youden threshold and an optimal cutoff. Paper wording is *warning signal*,
*association*, *support mismatch* — never *certifier*, *guarantee* or *decision rule*.

---

## 17. Predictor IDs and input identity

| item | id | version |
| --- | --- | --- |
| primary predictor | `r4-target-range-exceedance-warning` | 1 |
| secondary predictor | `r4-source-target-wasserstein1-warning` | 1 |
| primary outcome summary | `r4-core4-mean-transport-penalty` | 1 |
| secondary outcome summary | `r4-core4-mean-deployment-delta` | 1 |
| validation protocol | `r4-heldout-population-predictor-validation` | 1 |

Every predictor row records: `model_id`, `model_revision`, `population_id`,
`population_fingerprint`, `direction`, `source_measurement`, `target_measurement`,
`source_train_budget`, `source_train_manifest_fingerprint`, `target_test_identity`,
`predictor_id`, `predictor_version`.

---

## 18. Validation commands

```text
python -m json.tool experiments/calibration_transport/R4_PREDICTOR_SEMANTIC_CANDIDATE.json   exit 0
git diff --check                                                                              exit 0
```

Mechanically verified: development R4 MMLU units = 8; primary held-out validation
units = 16; legacy secondary units = 8; primary predictor count = 1; secondary predictor
count = 1; primary outcome core procedures = exactly 4; N456 quantile ranks 12 / 445;
N20000 interval ranks 500 / 10000 / 19500; candidate fingerprint recomputes from the
payload minus `candidate_fingerprint`; the two candidate generations are byte-identical.

---

## 19. Scientific non-claims

- The predictor does not use TARGET labels as input.
- The predictor is an association-based warning signal, not a causal mechanism.
- The predictor does not certify calibration transportability.
- R3 MMLU is development evidence, not independent validation.
- R4 MMLU current-generation units are development/continuity units, not held-out validation.
- Primary held-out validation is restricted to the 16 current-generation HellaSwag/MedMCQA direction units.
- Legacy-model Hella/Med units are secondary lineage-continuity evidence.
- F is not treated as independent predictor replication.
- The primary predictor outcome averages only the four R3-continuity logistic procedures.
- I-isotonic and B-beta cannot rescue primary predictor validation.
- N912 cannot rescue N456 predictor validation.
- The predictor does not establish universal behavior across models or populations.

---

## 20. Status

```text
R4 TARGET-LABEL-FREE PREDICTOR SEMANTIC CANDIDATE = COMPLETE
PREDICTOR STATUS = NOT FROZEN
FORMAL R4 EXECUTION = NOT AUTHORIZED
```

Predictor freeze, predictor implementation and final R4 protocol integration remain
outside this candidate and require human / ChatGPT review.
