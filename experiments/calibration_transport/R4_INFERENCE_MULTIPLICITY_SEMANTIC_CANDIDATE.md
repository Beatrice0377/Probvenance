# R4 Inference + Multiplicity Semantic Closure CANDIDATE

Status: `R4 INFERENCE + MULTIPLICITY SEMANTIC CANDIDATE = COMPLETE` (candidate only)

```text
CANDIDATE STATUS = NOT FROZEN
INFERENCE FROZEN = NO
R4 FULLY FROZEN = NO
R4 EXECUTION AUTHORIZED = NO
AWAITING HUMAN / CHATGPT SCIENTIFIC REVIEW
```

This document is the human-readable companion of
`experiments/calibration_transport/R4_INFERENCE_MULTIPLICITY_SEMANTIC_CANDIDATE.json`.
It defines the prospective R4 inference and multiplicity semantics **before any R4 model
outcome exists**. It does not freeze them, does not implement them, and does not authorize
execution. The machine record is authoritative for exact values; this document explains the
rationale.

---

## 1. Authority and entry provenance

Entry commit: `5185f5044fdccf0d976f953a0ff2d6c93c91a08a`
(`experiments: implement R4 calibration families`), branch `main`, `HEAD == origin/main`,
ahead/behind `0 / 0`, worktree clean.

Frozen inputs read (read-only, SHA256 recorded in the JSON `authority` block):

| artifact | sha256 | role |
| --- | --- | --- |
| `R4_POPULATION_FREEZE.md` | `850b6b24…8fee2a` | R4 POPULATION LAYER: FROZEN |
| `R4_CALIBRATION_FAMILY_FREEZE.md` | `1fd06ad4…18cdff` | calibration-family semantics frozen |
| `R4_CALIBRATION_FAMILY_SEMANTIC_CANDIDATE.json` | `41eaf954…549fe4` | calibration-family semantic candidate |
| `R4_CALIBRATION_FAMILY_SEMANTIC_CLOSURE.md` | `10a3ab9e…efe2085` | calibration-family closure |
| `R4_CALIBRATION_FAMILY_IMPLEMENTATION_ENGINEERING.md` | `812fd873…174e6fe` | implementation engineering record |
| `R4_CALIBRATION_IMPLEMENTATION_ENVIRONMENT.md` | `69af2799…5e104c` | pinned environment provenance |
| `r4_calibration_families.py` | `e5b00548…536ec3` | production I-isotonic / B-beta |
| `r3_protocol.py` | `46a7c0ec…35197e` | R3 protocol (continuity reference) |
| `r3_protocol_design.json` | `cb54090f…e90a43` | R3 protocol design (continuity reference) |
| `r3_analysis.py` | `819f2993…6a0c5` | R3 analysis + nearest-rank percentile rule |

No frozen artifact was modified. Population-manifest fingerprint conflicts found: `0`.

### R3 continuity anchors

```text
R3 protocol_id              r3-confirmatory-procedure-conditioned-transport (v1)
R3 protocol_fingerprint     3ef63056ae16b18ad65d9c87d1fbec5b43550873a0e3e25ec0a323f954ee974d
R3 population               cais/mmlu @ c30699e8356da336a370243923dbaf21066bb9fe
R3 population fingerprint   40cc9753a711314ff3b25ed6e234d0cbda11f3f60cd87f1d3915195a3d1780b8
R3 models                   openbmb/MiniCPM5-2B @ 12a3808a956f869c767195e9266b59c4d21d92e2
                            Qwen/Qwen3.5-2B   @ 15852e8c16360a2fea060d615a32b45270f8a8fc
R3 nearest-rank rule        rank = ceil(percentile/100 * n), clamp [1,n], ordered[rank-1]
                            (r3_analysis.py:507-512; even-n median is a single order statistic)
```

R4 extension fingerprints carried forward unchanged:

```text
P-low         7a8e13d51e131f2102cca4e00b172c8bbb2eb49e591acd3746aeb64d003c8857
P-historical  a44e9217dd43e5e29d859c8dd2dc510a5876db4d46a8e0cc2fd4f1df3121a423
L-low         91d7d506275aade7d4676c39722ac2c4d975de7967a25a808395c056307ad619
L-historical  23ec12bbf4a809ba2f419491df80d1f228d3fd778d848115839aab3697f9dd58
I-isotonic    cd13bc07bf92f3375bcd16d57fa5f515cd40f68199b57181791f85c58be8c244
B-beta        f4b710fb98f7c3056794aa709d53309f462a8f598cef8089d2f9c0ed6f7e37ff
```

### Outcome firewall

This candidate was produced without any R4 model outcome. No model was loaded, no GPU
inference ran, no calibration was fitted on real study scores, no Brier/LogLoss/transport
result and no predictor correlation exists. The R3 official result JSON was not opened to
design R4 inference; only R3 structural/protocol identity was used.

---

## 2. Scientific status

Closed already:

```text
MODEL PANEL                    CLOSED
MODEL ENGINEERING              COMPLETE
POPULATION LAYER               FROZEN
CALIBRATION FAMILY SEMANTICS   FROZEN
CALIBRATION IMPLEMENTATION
  PROVENANCE CLOSURE           PASS
```

Still open:

```text
INFERENCE / MULTIPLICITY       OPEN   <- this candidate
TARGET-LABEL-FREE PREDICTOR    NOT FROZEN
FINAL R4 PROTOCOL              NOT FROZEN
FORMAL R4 EXECUTION            NOT AUTHORIZED
```

---

## 3. Prospective primary panel

```text
models (4, current generation)
  allenai/Olmo-3-7B-Instruct        6e5971d9eba42665f5bd5a0fcf047f299ce1dccc
  tiiuae/Falcon-H1-7B-Instruct      41e72f27effbab80cd45b6e884688452253a3686
  ibm-granite/granite-4.0-h-tiny    791e0d3d28c86e106c9b6e0b4cecdee0375b6124
  Qwen/Qwen3.5-9B                   c202236235762e1c871ad0ccb60c8ee5ba337b9a

populations (3)
  MMLU        cais/mmlu @ c30699e8356da336a370243923dbaf21066bb9fe
              manifest 40cc9753a711314ff3b25ed6e234d0cbda11f3f60cd87f1d3915195a3d1780b8
  HellaSwag   Rowan/hellaswag @ 218ec52e09a7e7462a5400043bb9a69a41d06b76
              manifest 5c45043ba4f0ec436c16dcf494ff26be435c7857244bcbefa321d1678129c400
  MedMCQA     openlifescienceai/medmcqa @ 91c6572c454088bf71b679ad90aa8dffcd0d5868
              manifest 4a4718438d46ab1ba27c59ca46806756ffb62efa05e6103981dffec4dc48c218

directions (2)   CAT->OVR      OVR->CAT

primary units            4 x 3 x 2 = 24
model x population cells 4 x 3     = 12
```

The panel is a **declared fixed finite panel**, not a random sample from a model or
population superpopulation. Panel-average inference is evidence *across the declared R4
panel*, and nothing stronger.

---

## 4. R3 / legacy evidence roles

**Frozen R3 MMLU cells are excluded from the R4 prospective primary family.** The frozen R3
models (`MiniCPM5-2B`, `Qwen3.5-2B`) already have observed MMLU outcomes that participated in
scientific development. Pooling those outcomes into the R4 prospective bootstrap or into the
R4 prospective multiplicity family would silently convert historical evidence into new
confirmation. They are continuity evidence only, are not re-run, and are not redefined.

**Legacy-lineage new-population cells.** HellaSwag / MedMCQA will later also be measured for
the two legacy models, giving

```text
2 legacy models x 2 new populations x 2 directions = 8 secondary units
```

These are a `secondary lineage-continuity extension`. They may report `R_raw` / `R_native` /
`R_cross`, `Delta_deploy`, `Delta_transport`, `Delta_native` for all six procedures, but they
cannot rescue the primary panel, cannot alter primary multiplicity, and cannot retroactively
upgrade R3 replication.

---

## 5. Estimands

For model `m`, population `p`, direction `d = A -> B`, calibration procedure `F`, target
measurement `B`:

```text
R_raw(m,p,d)      = mean loss(S_B, Y)
R_native(m,p,d,F) = mean loss(g_F^B(S_B), Y)
R_cross(m,p,d,F)  = mean loss(g_F^A(S_B), Y)
```

`g_F^A` is fitted on **source measurement A TRAIN** probabilities and applied to **target
measurement B TEST** scores `S_B`. It is never applied to `S_A`.

```text
Delta_deploy(m,p,d,F)    = R_cross - R_raw
Delta_transport(m,p,d,F) = R_cross - R_native
Delta_native(m,p,d,F)    = R_native - R_raw
```

Interpretation:

- `Delta_deploy < 0` → deployment improvement relative to raw; `> 0` → degradation.
- `Delta_transport > 0` → positive transport penalty; `< 0` → cross has lower Brier than
  native in that condition.
- A negative `Delta_transport` must **never** be written as "transport succeeded",
  "transport bonus", or "universal compatibility".
- The three deltas are stored and reported independently. `Delta_native` is a native
  reference, never a substitute for the other two.

### Losses

```text
primary      Brier
secondary    exact LogLoss
reliability  descriptive only, equal-width 10-bin
forbidden    ECE, ACE, other confirmatory metric zoo
```

---

## 6. Weighting and panel aggregation

Estimand weighting and bootstrap stratification are different things and are stated
separately.

| population | TEST estimand weighting |
| --- | --- |
| MMLU | equal-subject mean of subject means (57 subjects) |
| HellaSwag | row-weighted mean over all frozen eligible TEST rows |
| MedMCQA | row-weighted mean over all frozen eligible TEST rows |

For MMLU the frozen TEST is 20 per subject, so equal-subject equals the row mean
numerically; the semantic contract still says **equal-subject** and is not silently rewritten
into a general row-weighting identity. HellaSwag is **not** an equal-activity-label or
equal-`source_id` mean. MedMCQA is **not** an equal-`subject_name` mean.

Panel aggregation (`r4-equal-population-equal-current-model-panel-aggregation`, v1):

```text
PopulationMean_p(...) = 1/4 * sum over the 4 current-generation models
R4PanelMean(...)      = 1/3 * ( PopulationMean_MMLU
                              + PopulationMean_HellaSwag
                              + PopulationMean_MedMCQA )
```

Equal model weight within population, equal population weight across populations. A direct
average of the 12 cells is forbidden because a change in model count would silently change
population weight. All panel-level intervals come from the replicate-level panel statistic
distribution — interval endpoints are never averaged.

---

## 7. Calibration-family inferential roles

```text
R3 continuity core   P-low, P-historical, L-low, L-historical   (2 x 2 feature x regularization)
standalone extensions I-isotonic, B-beta
```

There is **no six-cell factorial**. Isotonic and beta are not feature or regularization
levels and must not be inserted into the 2 x 2 structure.

Logistic-core factorial transforms for any estimand `X in {Delta_deploy, Delta_transport}`:

```text
Feature(X)        = 0.5 * (L_low + L_hist - P_low - P_hist)
Regularization(X) = 0.5 * (P_low + L_low - P_hist - L_hist)
Interaction(X)    = (L_low - P_low) - (L_hist - P_hist)
```

identical to the frozen R3 factorial algebra.

---

## 8. TEST bootstrap

```text
protocol_id   r4-population-aware-paired-test-bootstrap (v1)
replicates    20000
purpose       TEST sampling uncertainty
holds the full-TRAIN fitted calibrators fixed; never refits calibration maps
```

Shared draws within a population: the same replicate's TEST resample is shared across all 4
models, both directions, all 6 procedures, raw/native/cross, all estimands and all factorial
contrasts — and by the legacy-lineage secondary estimates. Independent bootstrap rows per
procedure or direction are forbidden. Across populations the same replicate number is used
with a population-specific deterministic hash domain.

### Population modes

```text
MMLU      r4-mmlu-subject-stratified-paired-test-bootstrap (v1)      subject-stratified-row
HellaSwag r4-hellaswag-activity-stratified-source-cluster-test-bootstrap (v1)
                                                                      activity-stratified-source_id-cluster
MedMCQA   r4-medmcqa-subject-stratified-paired-test-bootstrap (v1)   subject_name-stratified-row
```

- **MMLU**: per replicate, for each frozen subject draw exactly 20 positions with replacement
  from that subject's 20 TEST rows; all subjects retained; statistic = equal-subject mean.
- **MedMCQA**: stratum `subject_name` (21 subjects); per replicate, for each subject draw with
  replacement exactly that subject's original frozen TEST row count; concatenate; statistic =
  row-weighted TEST mean. `topic_name` is not a bootstrap stratum.
- **HellaSwag**: cluster `source_id`, which is indivisible. A structural audit runs first:
  *within frozen TEST, does every `source_id` map to exactly one `activity_label`?* If not →
  `HELLASWAG_CLUSTER_STRATUM_AMBIGUITY` and STOP, with no invented fallback. The audit passes
  (§13). Per replicate, within each `activity_label`, draw with replacement exactly that
  activity label's original number of unique `source_id` clusters; a cluster drawn twice
  contributes its full row set twice; row-level resampling inside a cluster is forbidden;
  statistic = row-weighted mean over the expanded resampled row multiset (not an equal-cluster
  estimator). The 14 validation-only activity labels remain eligible bootstrap strata even
  though TRAIN has no rows for them.

### Deterministic draw identity

No `random.Random` mutable state, no numpy global RNG, no system entropy, no wall-clock seed,
no Python `hash()`. Draws use the repository fingerprint convention
(`probvenance.fingerprint`), with identity at least:

```text
protocol_id, protocol_version, population_id, population_fingerprint,
replicate_index, stratum, draw_index, pool_size
```

plus a `cluster_mode_marker` for the Hella cluster bootstrap. Index mapping:
`int(fingerprint(identity)[:16], 16) % pool_size`. Ordering is deterministic: strata sorted by
stratum label, rows sorted by `item_id`, `source_id` sorted, rows inside a `source_id` sorted
by `item_id`. The canonical serialization is `probvenance.fingerprint.canonical_json`.

### Uncertainty scope

The TEST bootstrap quantifies only the sampling uncertainty of the frozen TEST population
construction, conditional on the fixed model panel, the fixed populations, and the fixed
full-TRAIN fitted calibrators. It does not quantify model-selection uncertainty,
population-selection uncertainty, TRAIN fitting uncertainty, or future-domain uncertainty.

---

## 9. TRAIN-refit bootstrap

```text
protocol_id   r4-stratum-preserving-paired-train-refit-bootstrap (v1)
replicates    2000
purpose       calibration fitting-sample instability
TEST          held fixed at the full frozen TEST set
```

TRAIN-refit and TEST bootstrap are conceptually separate, reported separately, and **never
numerically combined** (no variance addition, CI convolution, double bootstrap, or quadrature).

Sample size = frozen TRAIN sample size: primary `N = 456`, secondary robustness `N = 912`.
Per stratum, draw with replacement exactly the original selected TRAIN count, so the total N
is preserved.

- **MMLU**: 57 subjects, 8 selected TRAIN rows per subject → 456. The same resampled TRAIN
  multiset is shared across all 4 models, both measurements and all 6 procedures; each
  `model x measurement x procedure` still fits its own map.
- **HellaSwag**: stratum `activity_label`, primary 456 with at most one selected row per
  `source_id`. Validation-only activity labels do not get invented TRAIN rows. The 912 case
  uses the frozen nested 912 per-activity selected counts (sum 912).
- **MedMCQA**: stratum `subject_name`, primary 456; the 912 case uses the frozen 912 subject
  counts (sum 912). `topic_name` is never a resampling stratum.

Shared TRAIN-refit draws: within a population, budget and replicate, the resampled TRAIN row
identities are shared across all models, all procedures, both CAT/OVR fits and both
directions. Identity includes `train_refit_protocol_id/version`, population identity and
fingerprint, `budget_identity` (`N456` / `N912`), replicate index, stratum, draw index and
pool size.

Each refit replicate refits source and target calibrators on the same paired resampled TRAIN
multiset, then evaluates on the full unchanged TEST. For `Delta_transport`, both the
source-fitted cross map and the target-native map come from that replicate's refit — never a
refit cross map against a full-TRAIN native map.

Intervals: `nearest-rank-percentile`, levels `2.5 / 50 / 97.5`, 2000 replicates, audit ranks
`50 / 1000 / 1950`; the even-n median is a single nearest-rank order statistic, not an
average. Reported: full-TRAIN reference point, TRAIN-refit median, 95% interval, planned
replicates, successful replicates, failed replicates. TRAIN-refit does not enter primary
significance multiplicity.

---

## 10. Primary prospective hypothesis family

The only primary confirmatory family, size **12**:

```text
Delta_deploy    CAT->OVR : Feature, Regularization, Interaction
Delta_deploy    OVR->CAT : Feature, Regularization, Interaction
Delta_transport CAT->OVR : Feature, Regularization, Interaction
Delta_transport OVR->CAT : Feature, Regularization, Interaction
```

Each is a hierarchically equal-weighted `R4PanelMean` factorial contrast. Null `effect = 0`,
alternative two-sided.

```text
alpha                    0.05
correction               bonferroni-percentile-interval
percentile rule          nearest-rank-percentile
lower tail               1/480   (= 0.0020833333333333333)
upper tail               479/480 (= 0.9979166666666667)
replicates               20000
audit lower rank         42
audit upper rank         19959
forbidden                BCa, normal approximation, studentized bootstrap, interpolated percentile
```

**R3-continuity subset**: the six `Delta_deploy` hypotheses have algebra identical to the R3
primary family. The R4 multiplicity nevertheless remains the full 12-hypothesis family; the
six are not given a separate narrower primary correction, and R3 outcomes never enter the R4
bootstrap. The frozen R3 six contrasts may be reported side by side with the new R4
corresponding six contrasts.

---

## 11. Secondary families

### 11.1 Standalone I-isotonic / B-beta extension (size 8)

```text
2 procedures (I-isotonic, B-beta) x 2 directions x 2 estimands (Delta_deploy, Delta_transport)
unit   R4PanelMean delta (not a factorial effect)
null   panel mean delta = 0, two-sided
alpha  0.05, bonferroni-percentile-interval
tails  1/320 (= 0.003125), 319/320 (= 0.996875)
replicates 20000, audit ranks 63 / 19938
status SECONDARY — cannot rescue the primary family
forbidden claims: "isotonic universally best", "beta universally best"
```

### 11.2 Formal between-direction contrast (size 6)

The pattern "CAT->OVR CI excludes zero, OVR->CAT CI does not" is **not** a direction
difference. The formal family is:

```text
DirectionDifference(E, X) = R4PanelMean_CAT->OVR(E, X) - R4PanelMean_OVR->CAT(E, X)
E in {Feature, Regularization, Interaction},  X in {Delta_deploy, Delta_transport}
size 6, alpha 0.05, bonferroni-percentile-interval
tails 1/240 (= 0.004166666666666667), 239/240 (= 0.9958333333333333)
replicates 20000, audit ranks 84 / 19917
```

The bootstrap must compute the difference directly on each shared replicate. Inferring a
direction difference from CI overlap or separate significance is forbidden. I/Beta direction
differences are descriptive only in R4 unless a future pre-outcome freeze says otherwise.

### 11.3 Native-reference family (size 12)

```text
R4PanelMean Delta_native(d,F) over 2 target directions/measurements x 6 procedures
alpha 0.05, bonferroni-percentile-interval
tails 1/480, 479/480; replicates 20000, audit ranks 42 / 19959
upper < 0  -> NATIVE_IMPROVEMENT_SUPPORTED
lower > 0  -> NATIVE_DEGRADATION_SUPPORTED
otherwise  -> NATIVE_ADEQUACY_UNRESOLVED
role: secondary reference family, cannot rescue the primary family
```

### 11.4 Family FWER scope

```text
PRIMARY                          12 hypotheses
SECONDARY EXTENSION               8 hypotheses
SECONDARY DIRECTION-DIFFERENCE    6 hypotheses
SECONDARY NATIVE REFERENCE       12 hypotheses
```

Bonferroni guarantees within-family FWER only. No claim of "0.05 FWER across every number
printed in the R4 paper". The primary scientific conclusion is carried by the PRIMARY 12
alone; secondary families cannot rescue the primary.

---

## 12. Unit-level and heterogeneity reporting

All 24 primary units report, for all six procedures, `R_raw`, `R_native`, `R_cross`,
`Delta_native`, `Delta_deploy`, `Delta_transport`, and the six logistic-core factorial
contrasts. Unit-level intervals are 95% pointwise percentile intervals: descriptive
estimation intervals, **not** members of the primary multiplicity family. Counting
"significant" unit cells as a confirmatory result, or cherry-picking, is forbidden.

Descriptive heterogeneity reporting is allowed: per-population 4-model mean, per-model
3-population mean, unit min/max/median/IQR, sign pattern, and a complete table/heatmap.
Forbidden: a t-test over 24 units, random-effects meta-analysis, naive standard errors over
units, or treating the six procedures as extra independent replication.

**HellaSwag `split_type`** (`indomain` / `zeroshot`) remains a secondary subgroup diagnostic
only. It is not two independent populations, does not expand the primary population count
from 3 to 4, adds no predictor independent units, and cannot rescue the aggregate. No
subgroup confirmatory multiplicity family is defined; formal subgroup claims require a
separate pre-outcome freeze.

### Point estimates and direct contrast bootstrap

Every inferential result stores the full-data point estimate, bootstrap median, bootstrap
lower and bootstrap upper separately. The official effect estimate is the full-data point
estimate; the bootstrap median never substitutes for it. Every contrast interval is computed
by calculating the contrast directly on each replicate — subtracting or averaging CI
endpoints is forbidden (factorial contrasts, all three deltas, direction differences,
N912−N456 differences, panel averages).

### Deterministic ordering

Replicate numbering `0 … N-1`; deterministic ordering of strata, pools, draws, cluster
expansion, models, populations, directions and procedures using frozen canonical labels.
Results must not depend on dict insertion order, filesystem order, OS locale, or Python hash
randomization.

---

## 13. Failure rules

### Full-data calibration-fit failure

Formal full-TRAIN point fits fail closed. Any frozen eligibility/fitting failure records the
exact state with no fallback, no clipping and no row filtering. Unaffected procedures are
still reported. If a panel-level inferential hypothesis depends on any missing cell, that
hypothesis is `INCOMPLETE`; a cell is never silently dropped from a panel aggregate.
Primary factorial hypotheses depend on the four logistic-core procedures; the I/Beta
extension hypotheses depend on the corresponding procedure being eligible in every required
current-generation panel cell. Complete-case averaging is forbidden and an eligibility
coverage matrix must be reported.

### Measurement completeness

Formal analysis requires 100% paired fixed-event measurement completeness for every frozen
selected row required by that model/population analysis: CAT score available, OVR score
available, same frozen `Y`, same frozen anchor index. Row substitution, complete-case
deletion, winner-agreement filtering, a fresh anchor or a fresh winner are forbidden.
Incompleteness makes the affected `model x population` block `INCOMPLETE` and stops its
inferential calculation.

### TRAIN-refit failure

Fail closed per `procedure x model x population`: if any planned refit replicate fails, is
ineligible, has a non-finite accepted state, or violates the frozen fit contract, that block
is `INCOMPLETE` and **no successful-subset interval** is computed. The replicate index,
measurement dependency, failure code, exception type and exact message are recorded.
Unaffected blocks are still reported. Retrying with a changed solver, dropping a failed
replicate, replacing failed rows, or changing the procedure, tolerance or bootstrap seed is
forbidden.

---

## 14. N = 912 sample-size robustness

Only the frozen new-population 912 manifests (HellaSwag, MedMCQA). Primary remains `N = 456`.
The 912 analysis is `SECONDARY ROBUSTNESS ONLY` and guarantees `TRAIN_456 ⊂ TRAIN_912`, the
same TEST, the same model measurement semantics, the same procedures, the same loss and the
same direction. For the current-generation 4-model panel it computes `Delta_deploy_456`,
`Delta_deploy_912`, `Delta_transport_456`, `Delta_transport_912` and the paired
`Delta_N912_minus_N456`, subtracting directly within the same shared TEST replicate and
reporting a pointwise 95% interval. No new confirmatory multiplicity family is created. 912
cannot rescue 456, cannot redefine the primary, and if 456 fails while 912 succeeds the
primary remains failed/incomplete. Legacy-model 912 results, if formally measured, may be
reported as the same secondary diagnostics but cannot enter the current-generation primary
panel.

---

## 15. Exact LogLoss extended-real policy

```text
NO epsilon clipping, NO nextafter, NO smoothing, NO post-calibration clipping
zero mass for the observed outcome  ->  LogLoss = +infinity, preserved verbatim
rows causing infinity must not be removed
finite - finite  -> defined
+inf   - finite  -> +inf
finite - +inf    -> -inf
+inf   - +inf    -> UNDEFINED_EXTENDED_REAL
```

If a bootstrap contrast is undefined (`+inf - +inf`), that secondary LogLoss interval is
`INCOMPLETE / UNDEFINED`; replicates are not dropped and an interval is not computed over a
successful subset. LogLoss is always secondary and can never rescue Brier primary inference.

---

## 16. Structural audits (pre-outcome, exact counts)

All counts were read from the frozen population manifests and the frozen R3 MMLU manifest.
No model outcome, no calibration fit and no bootstrap draw was involved.

### MMLU (`cais/mmlu`, manifest `40cc9753…`)

```text
subjects                57
TRAIN                   456 (8 per subject), all item_ids unique
TEST                    1140 (20 per subject), all item_ids unique
items per subject       28
```

### HellaSwag (`Rowan/hellaswag`, manifest `5c45043b…` primary / `6817496f…` 912)

```text
primary TRAIN            456 rows, 456 unique item_ids, 456 unique source_id (max 1 row per source_id)
primary TRAIN strata     174 activity labels, min 1 / median 1 / max 45, 162 below 5
912 TRAIN                912 rows, 912 unique item_ids, 912 unique source_id (max 1)
912 TRAIN strata         175 activity labels (adds "Knitting")
TEST                     10042 rows, 192 activity labels
TEST strata              min 1 / median 11 / max 2627, 17 below 5
TEST source_id           8407 unique clusters, max 10 rows per cluster, 902 repeated clusters,
                         2537 rows inside repeated clusters
TEST cluster sizes       min 1 / median 1 / max 10; 7505 singleton clusters; pool total 8407
TEST cluster pool sizes  per activity label: min 1 / median 6 / max 2627, total 8407
source_id -> activity    conflicts 0  =>  every TEST source_id maps to exactly one activity_label
                         (cluster-stratum audit PASS, no HELLASWAG_CLUSTER_STRATUM_AMBIGUITY)
train ∩ test source_id   0
eligible TRAIN labels    178
selected TRAIN labels    174
quota-zero labels        4 (Home,Categories, Knitting, Spread mulch, Windsurfing);
                         912 selects Knitting too, so 912 quota-zero = 3
test-only labels         18 = 4 quota-zero + 14 validation-only
validation-only labels   14 (stay eligible TEST bootstrap strata)
split_type (TEST)        indomain 5001 / zeroshot 5041
TEST anchor counts       {0: 2420, 1: 2548, 2: 2542, 3: 2532}
structural exclusions    test 0 / train 0
overlap exclusions       train excluded by test overlap 0 / skipped for source_id reuse 0
```

### MedMCQA (`openlifescienceai/medmcqa`, manifest `4a471843…` primary / `e48c3729…` 912)

```text
primary TRAIN            456 rows, 456 unique item_ids, 21 subject_name strata
                         min 4 / median 21 / max 45, 1 stratum below 5
912 TRAIN                912 rows, 912 unique item_ids, 21 subject_name strata (min 8 / max 90)
TEST                     4162 rows, 21 subject_name strata, min 2 / median 127 / max 1312
choice_type (TEST)       single 2802 / multi 1360
TEST anchor counts       {0: 1002, 1: 1056, 2: 1065, 3: 1039}
structural exclusions    TEST 21 duplicate-option-string rows (multi 7 / single 14)
                         TRAIN 693 duplicate-option-string rows (multi 188 / single 505)
overlap exclusions       train excluded by test overlap 0
topic_name               not a stratum (rejected as a cross-split stratum)
```

### Nestedness and identity of the four frozen manifests

```text
HellaSwag  primary TRAIN ⊂ 912 TRAIN: missing 0; extension item_ids match true
MedMCQA    primary TRAIN ⊂ 912 TRAIN: missing 0; extension item_ids match true
HellaSwag  TEST item_id sequence identical between primary and 912 manifests
MedMCQA    TEST item_id sequence identical between primary and 912 manifests
```

All four manifest fingerprints in the frozen population layer match the values declared in
this candidate: conflicts `0`.

---

## 17. Semantic consistency checks

```text
primary family size                       12
secondary extension family size            8
direction-difference family size           6
native-reference family size              12
primary unit count                        24
primary model x population cell count     12
legacy secondary unit count                8
I/Beta inside the factorial                NO
R3 MMLU outcomes in the R4 prospective
  primary family                           NO
N912 inside the primary                    NO
split_type inside the population count     NO
procedure treated as independent
  replication                              NO
```

---

## 18. Scientific non-claims

```text
R4 does not establish universal CAT/OVR compatibility.
R4 does not establish universal superiority of any calibration procedure.
R4 panel-average inference is conditional on the declared fixed current-generation model
  panel and declared populations.
R4 TEST bootstrap does not quantify model-selection or population-selection uncertainty.
R4 TRAIN-refit uncertainty is separate from TEST sampling uncertainty.
R4 does not combine R3 observed MMLU cells into the new prospective R4 primary
  multiplicity family.
Direction-specific significance patterns do not establish between-direction differences
  without the formal direction contrast.
I-isotonic and B-beta are standalone extensions, not members of the 2x2 logistic factorial.
N=912 robustness cannot rescue N=456 primary results.
Exact LogLoss infinities are not clipped away.
Hella split_type subgroups are not independent populations.
No result authorizes production cross-identity calibration reuse.
```

---

## 19. Rationale

**Why only four current-generation models in the primary panel.** The R4 prospective claim is
a prospective, pre-outcome statement about a declared panel. The two frozen R3 models already
have observed MMLU outcomes, so including them would mix historical development evidence into
a prospective family. Four current-generation models give a balanced 4 x 3 x 2 grid that is
declared, not selected.

**Why frozen R3 MMLU cells are excluded.** Their outcomes are known and were used during
development. Re-using them would make the R4 primary family partly retrospective, and would
make multiplicity arithmetic meaningless because some cells would already be observed.

**Why equal population weighting.** Populations differ in size (1140 / 10042 / 4162 TEST
rows) and in stratum structure. Equal population weight prevents the largest benchmark from
dominating the panel mean, and separates the population-level statement from any single
benchmark's row count.

**Why equal model weight within population.** The panel is fixed, not random. Equal model
weight gives each declared model the same influence and prevents accidental reweighting if
the model count changes.

**Why TEST and TRAIN uncertainty are separate.** TEST sampling uncertainty asks how much the
panel statistic would move under a different draw of the frozen TEST population, holding the
fitted calibrators fixed. TRAIN-refit uncertainty asks how much it would move if the
calibration fitting sample were redrawn. They answer different questions and have different
scopes; combining them numerically would produce an interval with no single interpretation.

**Why the HellaSwag bootstrap is cluster-aware.** HellaSwag validation rows share `source_id`
contexts (up to 10 rows per cluster, 2537 rows in repeated clusters). Resampling rows
independently would treat correlated rows as independent and understate uncertainty. The
cluster is the unit of resampling, while the estimator stays a row-weighted mean.

**Why I/Beta are a separate family.** They are different procedures, not factor levels. They
cannot be placed on the feature or regularization axes without changing the meaning of the
contrasts. They are therefore tested as standalone panel-mean deltas in their own family.

**Why a formal direction contrast is needed.** Each direction has its own interval. Two
intervals can look different for reasons unrelated to a genuine direction difference.
Only a contrast computed directly on each replicate answers the between-direction question.

**Why 912 cannot rescue 456.** 912 is a nested superset of the same 456 rows plus 456
extension rows. If the primary 456 block is incomplete, a larger, partly different sample
cannot repair it; it can only be reported as a secondary robustness diagnostic.

**Why unit-level intervals are not multiplicity-adjusted confirmatory tests.** There are 24
units x 6 procedures x several quantities. Treating each pointwise interval as a test would
create a large, undeclared multiplicity problem. They are descriptive.

---

## 20. Implementation impact for later freeze stage

Not implemented here. A later freeze/implementation stage will need:

```text
population-aware bootstrap sampler
Hella cluster sampler (indivisible source_id clusters, stratum-preserving)
TRAIN-refit sampler (N456 / N912, stratum-preserving, shared draws)
risk matrix (raw / native / cross per unit and procedure)
unit estimands (Delta_native / Delta_deploy / Delta_transport)
factorial transforms (Feature / Regularization / Interaction)
panel aggregation (equal model within population, equal population across)
nearest-rank intervals
family-specific adjusted intervals (1/480, 1/320, 1/240 tails)
direction contrasts (direct replicate difference)
fit-failure dependency graph
exact LogLoss extended-real cells (no clipping)
N912 paired robustness differences
determinism fingerprints (draw identity, manifest identity)
```

---

## 21. Validation performed

```text
python -m json.tool R4_INFERENCE_MULTIPLICITY_SEMANTIC_CANDIDATE.json   -> valid JSON
deterministic fingerprint generation run twice                          -> byte-identical
git diff --check                                                        -> clean
```

Candidate fingerprint (over the canonical payload excluding `candidate_fingerprint`):

```text
fingerprint_version  1
candidate_fingerprint 5e10be53c8151d10992b70f4940d0e6f6a7aa83dfe4d5cd49e62b485b0c5e267
```

The temporary audit and generator scripts live outside the repository
(`/tmp/opencode/r4_inference_audit.py`, `/tmp/opencode/gen_r4_inference_candidate.py`) and are
not committed.

---

## 22. Status

```text
R4 INFERENCE + MULTIPLICITY SEMANTIC CANDIDATE = COMPLETE
CANDIDATE STATUS                               = NOT FROZEN
INFERENCE FROZEN                               = NO
R4 FULLY FROZEN                                = NO
R4 EXECUTION AUTHORIZED                        = NO
AWAITING HUMAN / CHATGPT SCIENTIFIC REVIEW
```
