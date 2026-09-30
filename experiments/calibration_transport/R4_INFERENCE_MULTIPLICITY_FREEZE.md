# R4 Inference + Multiplicity Semantic Freeze

```text
artifact_type   : r4-inference-multiplicity-freeze
artifact_version: 1
status          : FROZEN
fingerprint_version: 1
```

```text
candidate_fingerprint = 5e10be53c8151d10992b70f4940d0e6f6a7aa83dfe4d5cd49e62b485b0c5e267
candidate_commit      = 2ef9d31cda96dfc3bb326625dad0df061bb7063e
freeze_fingerprint    = dcbb7ac9e931145fdee86ab984de1249c1b86ca36ee735b70dafc8cabc06c141
```

Machine-readable companion: `R4_INFERENCE_MULTIPLICITY_FREEZE.json`
(sha256 `fdc07904056fd72bdd702e275743839eea741364324bd169ec2bf97504a45ad1`).

## 0. Status language

```text
R4 INFERENCE + MULTIPLICITY SEMANTICS: FROZEN

FROZEN != FORMAL EXECUTION AUTHORIZED
R4 OVERALL: NOT FULLY FROZEN / NOT EXECUTION-AUTHORIZED
```

This artifact freezes **semantics only**. It does not authorize formal R4
measurement, formal calibration fitting on real study scores, formal R4
bootstrap execution, formal Brier / LogLoss / transport analysis, or any
predictor work.

## 1. Source candidate and semantic equivalence

The freeze was derived mechanically from the reviewed candidate:

```text
experiments/calibration_transport/R4_INFERENCE_MULTIPLICITY_SEMANTIC_CANDIDATE.json
  sha256 7307b075370ca478a26aaace932fa7a3a8498342b845a99df7c9ef2b10251a5d  (1135 lines)

experiments/calibration_transport/R4_INFERENCE_MULTIPLICITY_SEMANTIC_CANDIDATE.md
  sha256 724706172c141bc3a533aa32fe2ef3ab62424dde2d2d6cd6e091f6e15e230f53  (771 lines)
```

The freeze replaces exactly five candidate-specific identity keys
(`artifact_type`, `artifact_version`, `status`, `candidate_fingerprint`,
`fingerprint_version`) and copies every other candidate key verbatim into
`frozen_semantic_payload` (33 keys). The mechanical semantic-difference audit
reported:

```text
differing_keys = []
result         = EXACT_SEMANTIC_EQUIVALENCE
```

No scientific payload value was rewritten. If the audit had reported any
difference the freeze would have stopped with `FREEZE_SEMANTIC_DRIFT`.

## 2. Frozen authorities (byte-for-byte)

```text
R4_POPULATION_FREEZE.md                              850b6b24da61f416b76d0bac83a4ba2775d3002e94894f003fd2e0a5488fee2a
R4_CALIBRATION_FAMILY_FREEZE.md                      1fd06ad4804cb64cd9220cc86187e26f6d690fba977bd76918e057bab418cdff
R4_CALIBRATION_FAMILY_SEMANTIC_CANDIDATE.json        41eaf954cfd29eb870d75e59feae34a1af1700b0c0ba3f3984d713bbcc549fe4
R4_CALIBRATION_FAMILY_SEMANTIC_CLOSURE.md            10a3ab9e7d0849c0aeeeac29c3b7cb6f0bc1fcb54cac97b6c4ee585d2efe2085
R4_CALIBRATION_FAMILY_IMPLEMENTATION_ENGINEERING.md  812fd873de3ce882d35c6e46aac0edb4b09278a44fecef5088478b796174e6fe
R4_CALIBRATION_IMPLEMENTATION_ENVIRONMENT.md         69af279986353cdc9bce33dd175a1a1f7f198056e445281bc4d13849cc5e104c
r4_calibration_families.py                           e5b00548429b5b0999d5847db47e1f4c1ae113ee19854c053aeaca1058536ec3
r3_protocol.py                                       46a7c0ec8e5da95a37868d89f5fc110687e66e65599ee4ac3d0602100435197e
r3_protocol_design.json                              cb54090f08c99c1a666ba297a896ec7be7940f6c295abddd5d594c1dabe90a43
r3_analysis.py                                       819f299304703d27ff89af7e8cfc00e6bffcb8d9ae11d8bb1724db0d7cc6a0c5
```

All ten re-hashed to the values recorded in the candidate's
`authority.frozen_inputs`. Frozen artifacts must remain byte-for-byte
unchanged.

## 3. R3 continuity identity (read-only reference)

```text
protocol_id          = r3-confirmatory-procedure-conditioned-transport
protocol_version     = 1
protocol_fingerprint = 3ef63056ae16b18ad65d9c87d1fbec5b43550873a0e3e25ec0a323f954ee974d

P-low         7a8e13d51e131f2102cca4e00b172c8bbb2eb49e591acd3746aeb64d003c8857
P-historical  a44e9217dd43e5e29d859c8dd2dc510a5876db4d46a8e0cc2fd4f1df3121a423
L-low         91d7d506275aade7d4676c39722ac2c4d975de7967a25a808395c056307ad619
L-historical  23ec12bbf4a809ba2f419491df80d1f228d3fd778d848115839aab3697f9dd58
I-isotonic    cd13bc07bf92f3375bcd16d57fa5f515cd40f68199b57181791f85c58be8c244
B-beta        f4b710fb98f7c3056794aa709d53309f462a8f598cef8089d2f9c0ed6f7e37ff

nearest-rank-percentile rule (frozen):
  rank = ceil(percentile/100 * n), clamped to [1, n], value = ordered[rank-1]
  even n median = single nearest-rank order statistic, NOT averaged
```

Frozen R3 MMLU outcomes are historical / frozen continuity evidence only: they
are NOT pooled into the R4 prospective primary bootstrap, NOT pooled into the
R4 primary multiplicity family, and NOT redefined as independent new
confirmation.

## 4. Primary fixed panel (FROZEN)

```text
allenai/Olmo-3-7B-Instruct       6e5971d9eba42665f5bd5a0fcf047f299ce1dccc
tiiuae/Falcon-H1-7B-Instruct     41e72f27effbab80cd45b6e884688452253a3686
ibm-granite/granite-4.0-h-tiny   791e0d3d28c86e106c9b6e0b4cecdee0375b6124
Qwen/Qwen3.5-9B                  c202236235762e1c871ad0ccb60c8ee5ba337b9a

populations: MMLU, HellaSwag, MedMCQA
directions : CAT->OVR, OVR->CAT
units      : 4 x 3 x 2 = 24 model x population x direction units
cells      : 4 x 3     = 12 model x population cells
```

The panel is a declared fixed finite panel, not a random-effects
superpopulation. Panel inference is conditional on exactly these four models
and exactly these three populations.

```text
MMLU      cais/mmlu @ c30699e8356da336a370243923dbaf21066bb9fe
          manifest 40cc9753a711314ff3b25ed6e234d0cbda11f3f60cd87f1d3915195a3d1780b8
          stratum subject | 57 strata | TRAIN 456 | TEST 1140
HellaSwag Rowan/hellaswag @ 218ec52e09a7e7462a5400043bb9a69a41d06b76
          manifest 5c45043ba4f0ec436c16dcf494ff26be435c7857244bcbefa321d1678129c400
          stratum activity_label | 192 strata | group source_id | TRAIN 456 | TEST 10042
          n912 manifest 6817496f227d9cd57759bf55489cbf8a1dc4dfd27db0ae551e9223d21d02a096
MedMCQA   openlifescienceai/medmcqa @ 91c6572c454088bf71b679ad90aa8dffcd0d5868
          manifest 4a4718438d46ab1ba27c59ca46806756ffb62efa05e6103981dffec4dc48c218
          stratum subject_name | 21 strata | TRAIN 456 | TEST 4162
          n912 manifest e48c37293f196e16d8fba42e7fc255e4ac2e77f81c270ed6f71320981968af12
```

## 5. Legacy secondary role (FROZEN)

```text
role: secondary-lineage-continuity-extension
models  : openbmb/MiniCPM5-2B @ 12a3808a956f869c767195e9266b59c4d21d92e2
          Qwen/Qwen3.5-2B     @ 15852e8c16360a2fea060d615a32b45270f8a8fc
populations: r4-hellaswag-activity-primary, r4-medmcqa-subject-primary
directions : CAT->OVR, OVR->CAT
units      : 2 x 2 x 2 = 8
```

The legacy extension may report raw / native / cross, all three deltas and all
six procedures, but it cannot rescue the primary panel, cannot alter primary
multiplicity, and cannot retroactively upgrade the R3 replication. Frozen R3
MMLU cells are excluded from this extension.

## 6. Estimands (FROZEN)

```text
R_raw(m,p,d)      = mean loss(S_B, Y)
R_native(m,p,d,F) = mean loss(g_F^B(S_B), Y)
R_cross(m,p,d,F)  = mean loss(g_F^A(S_B), Y)

Delta_deploy    = R_cross    - R_raw
Delta_transport = R_cross    - R_native
Delta_native    = R_native   - R_raw
```

`g_F^A` is fitted on SOURCE measurement A TRAIN probabilities and applied to
TARGET measurement B TEST scores `S_B`. It is never applied to `S_A`.

```text
Delta_deploy < 0  = deployment improvement relative to raw
Delta_deploy > 0  = deployment degradation relative to raw
Delta_transport > 0 = positive transport penalty
Delta_transport < 0 = cross has lower Brier than native in that condition
  (must NOT be described as "transport succeeded", "transport bonus",
   or "universal compatibility")
Delta_native = reference behaviour of target-native calibration relative to
  raw; never a substitute for Delta_deploy or Delta_transport
```

The three deltas are algebraically related but scientifically distinct and are
always reported separately.

## 7. Losses (FROZEN)

```text
primary     : Brier  (p - y)^2
secondary   : exact LogLoss
reliability : descriptive only, equal-width 10 bins
forbidden   : ECE, ACE, other confirmatory metric zoo
```

### Exact LogLoss extended-real policy

```text
no epsilon clipping
no nextafter
no smoothing
no post-calibration clipping
zero mass for the observed outcome -> LogLoss = +infinity, preserved verbatim
rows causing infinity must NOT be removed

finite - finite = defined
+inf   - finite = +inf
finite - +inf   = -inf
+inf   - +inf   = UNDEFINED_EXTENDED_REAL

a bootstrap contrast with an undefined value -> that secondary LogLoss
interval = INCOMPLETE / UNDEFINED
successful-subset intervals after dropping replicates are forbidden
LogLoss is always secondary and cannot rescue Brier primary inference
```

## 8. Weighting (FROZEN)

```text
MMLU      equal-subject mean of subject means (57 subjects)
          numerically equal to the row mean at 20/subject, but the semantic
          contract remains equal-subject and is not silently rewritten
HellaSwag row-weighted mean over all frozen eligible TEST rows
          (not equal-activity-label, not equal-source_id)
MedMCQA   row-weighted mean over all frozen eligible TEST rows
          (not equal-subject_name)

estimand weighting and bootstrap stratification are distinct concepts
```

## 9. Panel aggregation (FROZEN)

```text
protocol_id      = r4-equal-population-equal-current-model-panel-aggregation
protocol_version = 1

PopulationMean_p = 1/4 * sum over the 4 current-generation models
R4PanelMean      = 1/3 * (MMLU + HellaSwag + MedMCQA)

equal model weight within population
equal population weight across populations
direct 12-cell averaging forbidden
averaging interval endpoints forbidden
random-effects meta-analysis forbidden
panel-level intervals come from the replicate-level panel statistic distribution
```

## 10. TEST bootstrap (FROZEN)

```text
protocol_id      = r4-population-aware-paired-test-bootstrap
protocol_version = 1
replicates       = 20000
purpose          = TEST sampling uncertainty
holds full-TRAIN fitted calibrators fixed; never refits calibration maps
```

Within one population a replicate's TEST draw is shared across all 4 models,
both directions, all 6 procedures, raw / native / cross, all estimands and all
factorial contrasts, and the legacy secondary estimates. Independent bootstrap
rows per procedure or direction are forbidden. Across populations the same
replicate number is used with a population-specific deterministic hash domain.

```text
MMLU      protocol r4-mmlu-subject-stratified-paired-test-bootstrap v1
          mode subject-stratified-row; per subject draw exactly 20 positions
          with replacement; all subjects retained; statistic = equal-subject mean
MedMCQA   protocol r4-medmcqa-subject-stratified-paired-test-bootstrap v1
          mode subject_name-stratified-row; per subject_name draw with
          replacement exactly the original frozen TEST row count of that
          subject; statistic = row-weighted TEST mean; topic_name is NOT a stratum
HellaSwag protocol r4-hellaswag-activity-stratified-source-cluster-test-bootstrap v1
          mode activity-stratified-source_id-cluster; cluster = source_id and is
          indivisible; per activity_label draw with replacement exactly the
          original number of unique source_id clusters of that activity_label;
          a drawn cluster contributes ALL of its rows once per draw;
          cluster-internal row-level resampling forbidden;
          statistic = row-weighted mean over the expanded resampled row multiset;
          equal-cluster estimator forbidden
```

HellaSwag cluster-stratum audit: within frozen TEST every `source_id` maps to
exactly one `activity_label` (conflicts = 0, status PASS, 192 activity labels,
8407 unique source_ids). Any conflict must raise the explicit structural
failure state `HELLASWAG_CLUSTER_STRATUM_AMBIGUITY` with no fallback. The 14
validation-only activity labels stay eligible strata.

### Deterministic draw identity

```text
forbidden: random.Random mutable state, numpy global RNG state, system entropy,
           wall-clock seed, Python hash()
convention: repository deterministic fingerprint / SHA256 convention
index mapping: int(fingerprint(identity)[:16], 16) % pool_size

row draw identity fields:
  protocol_id, protocol_version, population_id, population_fingerprint,
  replicate_index, stratum, draw_index, pool_size
  (+ cluster_mode_marker for the HellaSwag cluster draw)

ordering: strata sorted by label; source_ids sorted; rows sorted by item_id;
          rows inside a source_id sorted by item_id
canonical serialization: probvenance.fingerprint.canonical_json
```

### Uncertainty scope

The TEST bootstrap quantifies the sampling uncertainty of the frozen TEST
population construction, conditional on the fixed model panel, the fixed
populations and the fixed full-TRAIN fitted calibrators. It does not quantify
model-selection uncertainty, population-selection uncertainty, TRAIN fitting
uncertainty, or future-domain uncertainty.

## 11. TRAIN-refit bootstrap (FROZEN)

```text
protocol_id      = r4-stratum-preserving-paired-train-refit-bootstrap
protocol_version = 1
replicates       = 2000
purpose          = calibration fitting-sample instability
test_held_fixed  = true
enters_primary_multiplicity = false
separate_from_test_bootstrap = true
```

Numeric combination with the TEST bootstrap is forbidden (no variance
addition, CI convolution, double bootstrap, quadrature combination).

```text
sample size = frozen TRAIN sample size: primary N = 456, secondary robustness N = 912
per stratum: draw with replacement exactly the original selected TRAIN count
             of that stratum; total N preserved
shared across: all models, all procedures, both CAT/OVR fits, both directions
each replicate refits source and target calibrators on the same paired
resampled TRAIN multiset, then evaluates on the full unchanged TEST
Delta_transport must take both maps from that replicate's refit
mixed dependency forbidden

MMLU      stratum subject, 8 per subject, total 456
HellaSwag stratum activity_label, at most one selected row per source_id;
          validation-only labels do not get invented TRAIN rows;
          n912 uses the frozen nested 912 per-activity selected counts (sum 912)
MedMCQA   stratum subject_name, topic_name forbidden;
          n912 uses the frozen 912 subject counts (sum 912)

intervals: nearest-rank-percentile, levels 2.5 / 50 / 97.5, replicates 2000,
           audit ranks 50 / 1000 / 1950, even n median NOT averaged
reported : full-TRAIN reference point, TRAIN-refit median, 95% interval,
           planned replicates, successful replicates, failed replicates
```

## 12. Primary family (FROZEN)

```text
name          = primary-prospective-confirmatory
composition   = 2 estimands x 2 directions x 3 logistic-core factorial effects
family_size   = 12
estimands     = Delta_deploy, Delta_transport
directions    = CAT->OVR, OVR->CAT
effects       = Feature, Regularization, Interaction
null          = effect = 0
alternative   = effect != 0 (two-sided)
alpha         = 0.05
correction    = bonferroni-percentile-interval
percentile    = nearest-rank-percentile
replicates    = 20000
lower_tail    = 1/480      upper_tail = 479/480
audit ranks   = 42 / 19959
forbidden interval methods: BCa, normal approximation, studentized bootstrap,
                            interpolated percentile
```

Factorial algebra (X in {Delta_deploy, Delta_transport}):

```text
Feature(X)        = 0.5 * (L_low + L_hist - P_low - P_hist)
Regularization(X) = 0.5 * (P_low + L_low - P_hist - L_hist)
Interaction(X)    = (L_low - P_low) - (L_hist - P_hist)
```

R3-continuity subset: the 6 `Delta_deploy` hypotheses, algebra identical to the
R3 primary family. R4 multiplicity stays the full 12; a second narrower primary
correction for those 6 is forbidden, and R3 outcomes must not enter the R4
bootstrap.

## 13. I-isotonic / B-beta extension family (FROZEN)

```text
name        = standalone-i-isotonic-b-beta-extension
composition = 2 procedures x 2 directions x 2 estimands
family_size = 8
procedures  = I-isotonic, B-beta
estimands   = Delta_deploy, Delta_transport
unit        = R4PanelMean delta (not a factorial effect)
null        = panel mean delta = 0 (two-sided)
alpha       = 0.05 ; correction bonferroni-percentile-interval
lower_tail  = 1/320    upper_tail = 319/320    audit ranks 63 / 19938
status      = SECONDARY ; cannot rescue primary
forbidden   : "isotonic universally best", "beta universally best"
```

I-isotonic and B-beta are standalone extensions and are NOT members of the 2x2
logistic factorial; a six-cell factorial is forbidden.

## 14. Formal between-direction contrast family (FROZEN)

```text
name        = formal-between-direction-contrast
composition = 3 logistic-core factorial effects x 2 estimands
family_size = 6
definition  = DirectionDifference(E,X)
              = R4PanelMean_CAT->OVR(E,X) - R4PanelMean_OVR->CAT(E,X)
alpha       = 0.05 ; correction bonferroni-percentile-interval
lower_tail  = 1/240    upper_tail = 239/240    audit ranks 84 / 19917
must_be_direct_replicate_difference = true
```

Inference from CI overlap or from separate per-direction significance is
forbidden. I-isotonic / B-beta direction differences are descriptive only.

## 15. Native-reference family (FROZEN)

```text
name        = native-reference
composition = 2 target directions/measurements x 6 procedures
family_size = 12
unit        = R4PanelMean Delta_native(d,F)
alpha       = 0.05 ; correction bonferroni-percentile-interval
lower_tail  = 1/480    upper_tail = 479/480    audit ranks 42 / 19959

upper < 0 -> NATIVE_IMPROVEMENT_SUPPORTED
lower > 0 -> NATIVE_DEGRADATION_SUPPORTED
otherwise -> NATIVE_ADEQUACY_UNRESOLVED   (including upper == 0 or lower == 0)
```

## 16. Multiplicity and FWER scope (FROZEN)

```text
family sizes: primary 12, extension 8, direction-difference 6, native-reference 12
Bonferroni guarantees within-family FWER only
a cross-family "0.05 FWER across every printed number" claim is forbidden
the primary scientific conclusion is owned by the PRIMARY 12 alone
secondary families cannot rescue the primary
```

Unit-level reporting: all six procedures' raw / native / cross, the three
deltas and the six logistic-core contrasts are reported for all 24 primary
units with 95% pointwise percentile intervals that are descriptive estimation
intervals and NOT members of the primary multiplicity family. Counting
"significant" cells as confirmatory and cherry-picking are forbidden. Point
estimates and bootstrap medians are stored separately; the official effect
estimate is the full-data point estimate.

Heterogeneity: full 24-unit reporting, descriptive per-population and per-model
means, unit min / max / median / IQR, sign pattern, complete heatmap. Forbidden:
t-test over 24 units, random-effects meta-analysis, naive standard error over
units, treating the six procedures as independent replication.

## 17. HellaSwag split_type subgroup (FROZEN)

`split_type` (indomain / zeroshot) is a secondary subgroup diagnostic only:
counts and grouped point estimates are allowed. It is not an independent
population, does not change the primary population count from 3, adds no
predictor independent units, cannot rescue the aggregate, and has no
confirmatory subgroup multiplicity family. A formal subgroup claim requires a
separate pre-outcome freeze.

## 18. N912 robustness (FROZEN)

```text
status = SECONDARY ROBUSTNESS ONLY
scope  = frozen new-population 912 manifests only (HellaSwag, MedMCQA)
guarantees: TRAIN_456 subset TRAIN_912, same TEST, same model measurement
            semantics, same procedures, same loss, same direction
computed  : Delta_deploy_456, Delta_deploy_912, Delta_transport_456,
            Delta_transport_912, Delta_N912_minus_N456
paired difference: subtract directly within the same shared TEST replicate
reporting: pointwise 95% interval
new_confirmatory_multiplicity_family = null
primary_remains_N456 = true
cannot rescue N456; cannot redefine primary
if 456 fails and 912 succeeds -> primary remains failed/incomplete
legacy-model 912 diagnostics cannot enter the current-generation primary panel
```

## 19. Failure rules (FROZEN)

### Full-TRAIN point fit

```text
fail closed: record exact state, NO fallback, NO clipping, NO row filtering
unaffected procedures are still reported
```

### Panel hypothesis dependency

```text
primary factorial hypothesis depends on the four logistic-core procedures
  -> if any required primary cell lacks a core procedure full fit, the
     corresponding direction x estimand primary hypothesis = INCOMPLETE
I/B extension hypothesis depends on the corresponding procedure being eligible
  in all required current-generation primary-panel cells
     -> otherwise that panel extension hypothesis = INCOMPLETE
silent cell drop from a panel aggregate forbidden
complete-case averaging forbidden
eligibility coverage matrix required
```

### Measurement completeness

```text
requirement: 100% paired fixed-event measurement completeness for every frozen
             selected row required by that model/population analysis:
             CAT score available, OVR score available, same frozen Y,
             same frozen anchor index
forbidden  : row substitution, complete-case deletion, winner-agreement
             filtering, fresh anchor, fresh winner
on incompleteness: affected model x population block = INCOMPLETE and its
             inferential calculation stops
```

### TRAIN-refit

```text
fail closed per block procedure x model x population
on any failed replicate -> INCOMPLETE, interval = None
successful-subset interval forbidden
must record: replicate index, measurement dependency, failure code,
             exception/error type, exact message
forbidden recovery: retry with changed solver, drop failed replicate,
             replace failed rows, change procedure, change tolerance,
             change bootstrap seed
unaffected blocks are still reported
```

## 20. Generalization limits (FROZEN)

Supported wording is limited to the predeclared current-generation R4 panel and
the three declared populations. Forbidden: "all models", "all benchmarks", "all
calibration settings", "universal directional asymmetry". No post-hoc
generalization threshold.

## 21. Scientific non-claims (FROZEN)

```text
1.  R4 does not establish universal CAT/OVR compatibility.
2.  R4 does not establish universal superiority of any calibration procedure.
3.  R4 panel-average inference is conditional on the declared fixed
    current-generation model panel and declared populations.
4.  R4 TEST bootstrap does not quantify model-selection or population-selection
    uncertainty.
5.  R4 TRAIN-refit uncertainty is separate from TEST sampling uncertainty.
6.  R4 does not combine R3 observed MMLU cells into the new prospective R4
    primary multiplicity family.
7.  Direction-specific significance patterns do not establish between-direction
    differences without the formal direction contrast.
8.  I-isotonic and B-beta are standalone extensions, not members of the 2x2
    logistic factorial.
9.  N=912 robustness cannot rescue N=456 primary results.
10. Exact LogLoss infinities are not clipped away.
11. Hella split_type subgroups are not independent populations.
12. No result authorizes production cross-identity calibration reuse.
```

## 22. Frozen vs open

```text
FROZEN
  primary fixed panel; legacy secondary role
  R_raw / R_native / R_cross; Delta_native / Delta_deploy / Delta_transport
  MMLU / HellaSwag / MedMCQA weighting; panel aggregation
  TEST bootstrap (architecture, modes, replicates, draw identity)
  TRAIN-refit bootstrap (architecture, replicates, intervals)
  primary family 12; I/B extension family 8; direction-difference family 6;
  native-reference family 12 (with tails and audit ranks)
  N912 robustness role; full-fit failure; refit failure; measurement completeness
  exact LogLoss extended-real policy; generalization limits; scientific non-claims

NOT FROZEN / NOT AUTHORIZED
  formal R4 measurement execution
  formal R4 bootstrap execution
  formal R4 analysis results (Brier / LogLoss / transport / panel)
  target-label-free predictor design and validation
  final R4 protocol integration
  R4 overall freeze; R4 execution authorization
```

## 23. Reproduction

```text
candidate fingerprint recomputation:
  python -c "import json,sys; sys.path.insert(0,'src');
             from probvenance.fingerprint import fingerprint;
             p=json.load(open('experiments/calibration_transport/R4_INFERENCE_MULTIPLICITY_SEMANTIC_CANDIDATE.json'));
             print(fingerprint({k:v for k,v in p.items() if k!='candidate_fingerprint'}))"
  -> 5e10be53c8151d10992b70f4940d0e6f6a7aa83dfe4d5cd49e62b485b0c5e267

freeze fingerprint recomputation:
  same construction over the freeze JSON payload excluding freeze_fingerprint
  -> dcbb7ac9e931145fdee86ab984de1249c1b86ca36ee735b70dafc8cabc06c141
```
