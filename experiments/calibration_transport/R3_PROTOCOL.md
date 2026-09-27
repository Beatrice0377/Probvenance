# R3 Confirmatory Protocol

```text
R3 STATUS:
PROTOCOL FROZEN AFTER THIS COMMIT

OFFICIAL MEASUREMENT:
NOT YET AUTHORIZED

CONFIRMATORY TEST OUTCOMES OBSERVED:
NO
```

This document is a preregistration-like freeze of the R3 confirmatory study
"Procedure-Conditioned Calibration Transport". It is governed prospectively by
`docs/research/calibration-transport-research-spec-v2.md`. It freezes what R3
will measure, fit, test, report, and interpret **before any R3 model outcome
exists**. R3.0 produced zero model evaluations.

Frozen identifiers:

```text
population manifest:   experiments/calibration_transport/data/r3-mmlu-57-subject-manifest-v1.json
manifest fingerprint:  40cc9753a711314ff3b25ed6e234d0cbda11f3f60cd87f1d3915195a3d1780b8

protocol design:       experiments/calibration_transport/r3_protocol_design.json
protocol fingerprint:  3ef63056ae16b18ad65d9c87d1fbec5b43550873a0e3e25ec0a323f954ee974d

primary child plan:    787c668201fa1a2046bb3eb7c00ec1fd929d76bc164dadcef6f7dd6a2edb0ee6
replication child plan: dc2f58732921466891de16a031f20141e82a28107de7fef114456f65159c6ebe
```

## 0. Scope / research gate

R2 (exploratory) is CLOSED. The research gate PASSED for R3 **design**. R3
**measurement** is not authorized by this document. This document selects no
method winner, declares no compatibility epsilon, creates no transport-graph
edge, and authorizes no production change.

## 1. Relation to Research Spec v2

R3 follows Research Specification v2. The calibration procedure `F` is an
explicit conditioning axis. Spec v1 remains the immutable historical authority
for R0/R1/R2 and is unchanged by this round. The R1 artifacts
`PairedFixedDecisionPlan` / `PairedFixedDecisionDataset` remain Research Spec v1
child structures; this protocol commits their fingerprints but does not treat
them as the R3 protocol identity.

## 2. Confirmatory question

> On an untouched confirmatory population and a new transport-model condition,
> does the risk of cross-measurement calibration depend detectably on the
> predeclared calibration procedure `F`?

The primary risk reference is **cross-vs-raw**, not cross-vs-native alone,
because R2 showed a poor finite-data native calibrator can make
`cross-vs-native < 0` while `cross-vs-raw > 0`.

## 3. Claim level

R3 PRIMARY inference is an **exact fitted-map confirmatory claim** conditioned on
the exact TRAIN/TEST manifest, the exact model revision, and the exact `F`. It is
not automatically a universal procedure-level compatibility claim.

## 4. Models

```text
PRIMARY:      openbmb/MiniCPM5-2B
              revision 12a3808a956f869c767195e9266b59c4d21d92e2

REPLICATION:  Qwen/Qwen3.5-2B
              revision 15852e8c16360a2fea060d615a32b45270f8a8fc

dtype:        bfloat16
rendering:    {"enable_thinking": false}
future run:   local_files_only = true
```

Qwen/MMLU is a population-shift replication (same model as R2, new untouched
R3 population), labeled PREREGISTERED REPLICATION, never a second primary. The
two models are never pooled. No model inference was performed in R3.0.

## 5. Population / data source

```text
repository: cais/mmlu
revision:   c30699e8356da336a370243923dbaf21066bb9fe   (full immutable SHA)
license:    MIT
TRAIN source: validation
TEST source:  test
unused:       dev, auxiliary_train
```

All 57 canonical MMLU subjects are included; none is chosen by model behaviour,
difficulty, or R2 similarity.

## 6. Population selection

Deterministic selection, frozen id/version
`mmlu-subject-balanced-source-index-hash-selection` v1. The selection key depends
only on protocol id/version, dataset revision, subject, source split, and source
row index — never on the answer, question text, choice text, ground truth, or any
model output. No RNG, no seed.

```text
TRAIN = 8 validation rows per subject   (456 total)
TEST  = 20 test rows per subject        (1140 total)
AUDIT = 0
TOTAL = 1596
```

**Deviation from the drafted 10/subject (human-approved, disclosed):** two of
the 57 subjects cannot supply 10 validation rows (`college_chemistry` has 8,
`high_school_computer_science` has 9), so uniform TRAIN=8 was frozen instead. The
drafted 10/subject was infeasible; the change is not silent.

**MMLU validation/test overlap (human-approved fix):** two `college_physics`
items and one `college_medicine` item share identical question+choices content
across the two source splits. TEST is selected first and kept pristine; TRAIN
then excludes any validation row whose content equals a selected TEST item and
backfills by rank. `counts.overlap_excluded_train_rows = 3` records this. No
silent row substitution.

## 7. Anchor / ground truth

Anchor: `sha256-case-id-candidate-set-anchor` v1, reused from R2, consuming only
`item_id` + candidate semantic names. Candidate names `option-0..option-3` with
the exact source choice strings in source order (not A/B/C/D). No anchor
rebalancing, no reroll, no Y balancing.

Ground-truth semantics (research layer, v1):

```text
label source:      pinned cais/mmlu answer field
labeling rule:     mmlu-answer-index-to-source-option
ambiguity policy:  pinned-dataset-answer-key-as-authoritative
taxonomy:          mmlu-four-option-answer-key v1
```

Target semantics remain `fixed-decision-correctness` v1; input semantics remain
`fixed-decision-semantic-probability` v1 (distinct axes from the taxonomy).

Observed class balance (audit only, not rebalanced):

```text
TRAIN  Y=1: 108   Y=0: 348
TEST   Y=1: 276   Y=0: 864
```

## 8. CAT/OVR measurement semantics

```text
CAT: direct-categorical-anchor-probability v1
OVR: independent-binary-anchor-probability v1
OVR proposition: choice-candidate-correctness-binary-judgment v1
```

Question = exact MMLU source question; context = None; candidate description =
exact source choice string. No paraphrasing, no few-shot, no chain-of-thought. No
new measurement axis, no OVR normalization, no CAT permutations.

## 9. Fixed F panel

Option A: a fixed calibration-procedure panel. No method selection, no winner, no
TEST-driven choice. Panel = 2 feature geometries × 2 regularization strengths:

| label | family | feature | λ | endpoint policy |
|---|---|---|---|---|
| `P-low` | `research-l2-logistic-fixed-decision-probability` v1 | `identity-raw-probability` v1 | 1e-4 | `exact-raw-probability-accepted` v1 |
| `P-historical` | same | same | 1e-2 | same |
| `L-low` | `research-l2-logistic-logit-fixed-decision-probability` v1 | `exact-logit-probability` v1 | 1e-4 | `reject-exact-probability-endpoints` v1 |
| `L-historical` | same | same | 1e-2 | same |

Common: objective `mean-bernoulli-nll-plus-l2` v1; regularization rule
`fixed-l2-strength` v1; fitting-data protocol `paired-frozen-decision-train` v1;
selection rule `fixed-panel-no-selection` v1.

```text
procedure fingerprints:
  P-low          7a8e13d51e13...
  P-historical   a44e9217dd43...
  L-low          91d7d506275a...
  L-historical   23ec12bbf4a8...
```

λ=1e-6 is excluded (R2C.1 documented binary64 solver-path operational limitation
at that strength). λ=0.1 and 1.0 are excluded (not a grid reproduction). No new
calibration family is introduced. RAW (`q_raw(p)=p`) is a required baseline, not
a fifth procedure.

Solver boundary: `newton-backtracking` v2 and other execution details are NOT
part of the statistical `F`; they belong to future run provenance.

## 10. Three baselines

For target measurement `B` and direction `A -> B`:

```text
R_raw(B)          = loss(S_B_i, Y_i)
R_native(B;F)     = loss(g_F^B(S_B_i), Y_i)
R_cross(A->B;F)   = loss(g_F^A(S_B_i), Y_i)
```

All three contrasts are always reported together:

```text
Delta_native/raw  = R_native(B;F) - R_raw(B)
Delta_cross/raw   = R_cross(A->B;F) - R_raw(B)
Delta_cross/native = R_cross(A->B;F) - R_native(B;F)
```

A negative cross-vs-native delta alone is never transport success.

## 11. Primary cross/raw estimands

```text
C_d(F) = R_cross(A->B;F) - R_raw(B)     (primary metric: Brier)
C_CAT->OVR(F) = R_cross(CAT->OVR;F) - R_raw(OVR)
C_OVR->CAT(F) = R_cross(OVR->CAT;F) - R_raw(CAT)
```

Point estimates use the equal-weight mean of the 57 per-subject means.

## 12. Six primary factorial contrasts

For each direction `d`:

```text
FeatureEffect_d        = 0.5*(C_L_low + C_L_hist - C_P_low - C_P_hist)
RegularizationEffect_d = 0.5*(C_P_low + C_L_low - C_P_hist - C_L_hist)
Interaction_d          = (C_L_low - C_P_low) - (C_L_hist - C_P_hist)
```

Exactly six primary contrasts on the PRIMARY model: {CAT->OVR, OVR->CAT} ×
{feature, regularization, interaction}. Null `effect = 0`; two-sided. No
additional primary hypothesis may be added after outcomes exist.

## 13. TEST bootstrap inference

```text
protocol:    sha256-r3-subject-stratified-paired-test-bootstrap v1
replicates:  20,000
unit:        within each of 57 subjects, sample 20 TEST item positions with replacement
             (the whole paired record travels together: item, Y, CAT, OVR, all four F predictions)
draws:       deterministic fingerprint draws, no RNG; the same (replicate, subject, draw)
             selection is reused for all four F, both directions, all baselines,
             both models, and all primary contrasts
percentile:  nearest-rank-percentile v1 (documented 1-based rank)
```

CAT and OVR are never bootstrapped separately.

## 14. Multiplicity

```text
primary family:            m = 6, alpha = 0.05, Bonferroni percentile intervals
primary tails:             lower = 1/240, upper = 239/240
native-reference family:   m = 8, alpha = 0.05
native-reference tails:    lower = 1/320, upper = 319/320
```

No primary p-values. Decision: interval excludes 0 → detected nonzero contrast;
interval includes 0 → not detected. These are bootstrap-based confirmatory
intervals, not finite-sample exact guarantees; Bonferroni protects the
predeclared family conditional on the interval procedure's coverage behaviour.

## 15. Native-reference assessment

For each model independently, `Delta_native/raw` over 2 measurements × 4
procedures = 8 cells, using the same 20,000 paired TEST bootstrap. States:

```text
interval entirely below 0 -> NATIVE_IMPROVEMENT_SUPPORTED
interval entirely above 0 -> NATIVE_DEGRADATION_SUPPORTED
otherwise                 -> NATIVE_ADEQUACY_UNRESOLVED
```

`NATIVE_DEGRADATION_SUPPORTED` triggers a native-reference adequacy concern;
`NATIVE_ADEQUACY_UNRESOLVED` stays explicitly unresolved.

## 16. Required secondary metrics

exact LogLoss (no clipping/smoothing; structured infinity; no bootstrap
inference), equal-width 10-bin reliability (empty bins retained; no ECE-driven
selection), observed score geometry (source TRAIN min/max, source 2.5–97.5%
quantile range, target TEST fractions outside them), range-loss decomposition
(inside vs outside source min/max), end-to-end winner diagnostics. All secondary;
none alters the primary estimand, eligibility, anchor, fitting, or inference.
Score geometry is diagnostic, never causal.

## 17. TRAIN-refit stability

```text
protocol:    sha256-r3-subject-stratified-paired-train-refit-bootstrap v1
replicates:  2,000
unit:        within each subject, resample 10 TRAIN item positions with replacement;
             the same resampled TRAIN multiset refits CAT, OVR, all four F, for both models
evaluation:  the original fixed 1,140 TEST items (no TEST resampling)
failure:     recorded exactly; affected procedure/model block = INCOMPLETE; no subset
             interval; other blocks remain reportable
```

## 18. Missingness / completeness

R3 primary Frozen-decision analysis requires 100% paired measurement completeness
(CAT = SCORED and OVR = SCORED) for every selected item. No post-hoc row dropping,
no winner-agreement filtering, no anchor/winner filtering. A MISSING/INELIGIBLE
record is preserved; the row is never replaced and no substitute MMLU item is
drawn: that model condition is PRIMARY CONFIRMATORY ANALYSIS INCOMPLETE unless a
protocol revision is made before examining results. Operational failures (OOM,
process/file failure, implementation defect) may be restarted after fixing the
problem, provided protocol/data/methods are unchanged and partial attempts are
not merged. Any required Family L TRAIN score exactly 0 or 1 makes Family L fail
closed; the panel is never silently reduced from 4 to 3.

## 19. Implementation invariants

Locked by `experiments/calibration_transport/tests/test_r3_analysis.py` against
synthetic fixtures: raw Brier = mean((p−y)²); the cross/native and cross/raw
identities; the factorial-contrast oracle; subject-weighted mean = mean of
per-subject means; paired bootstrap (with a counterexample); the shared
deterministic draw rule; multiplicity tails 1/240, 239/240, 1/320, 319/320; and an
algebraically independent calculation path. A structural test asserts no method
selection surface exists.

## 20. Provenance

Future official raw evidence must record: R3 protocol fingerprint, R3 protocol
Git commit, population manifest fingerprint, both model full revisions,
measurement code commit, analysis code commit, and runtime/library/device
provenance. The canonical protocol exists before its Git commit; the commit
externally pins it. No self-referential Git SHA is embedded in the payload.

## 21. Execution ordering

```text
1. protocol/design commit exists
2. human audit authorizes R3 measurement
3. working tree clean
4. model/data snapshots local
5. network disabled / local_files_only
6. collect ALL TRAIN + TEST raw measurements for BOTH model conditions
7. do not run R3 statistical analysis until all declared raw conditions are complete
8. freeze raw evidence
9. run predeclared analysis
10. write R3 report
```

No peeking after the first model: both declared conditions are measured under the
frozen protocol before confirmatory interpretation. Expected budget:
1596 items × 5 evaluations/item = 7,980 per model; 15,960 total. R3.0 performed
0 / 15,960.

## 22. Non-claims

R3 does not automatically establish: global CAT/OVR compatibility; universal
calibration-procedure superiority; a causal effect of score-range mismatch;
contamination-free MMLU generalization (MMLU is public and the model may have
seen its content); production cross-identity reuse; transitivity or symmetry;
all-model procedure-level generalization.

## 23. Stop conditions

Stop and report (do not silently proceed) if: the population or a model revision
cannot be pinned to a full immutable SHA; a subject lacks enough rows; the
manifest fails a structural gate; a primary panel procedure cannot fit on full
TRAIN; any selected item is MISSING/INELIGIBLE; a primary contrast or
multiplicity rule would need changing after outcomes exist.

## Human measurement gate

```text
R3 PROTOCOL DESIGN:
FROZEN

R3 MEASUREMENT AUTHORIZATION:
PENDING HUMAN REVIEW
```
