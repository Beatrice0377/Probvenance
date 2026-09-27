# R2B — Calibration-Transport Stability / Deconfounding Round

**Exploratory Stability / Deconfounding Round.
Not a benchmark.
Not confirmatory evidence.
No compatibility claim is authorized by this round alone.**

- Research specification: `docs/research/calibration-transport-research-spec-v1.md` (R0, frozen).
- This round: R2B, a stability/deconfounding follow-up to the exploratory R2A pilot
  (`REPORT.md`).
- Harness: `experiments/calibration_transport/` (R1 integrity + R2A pilot + R2B).
- Raw artifact: `results/r2b-stability-qwen35-2b-v1.json`
  (sha256 `16a07ecd69a4ec0081f76790b7bde0b4e8bcd87172e06b7af94c06ea699967a4`).
- Analysis artifact: `results/r2b-stability-qwen35-2b-v1-analysis.json`
  (sha256 `9c9f168599c9518cf169e65834583cef6d51eeb727afe2d6b1d5588dc8ff6c4d`).
- Pre-measurement design freeze commit: `dd68e299c364b038c959c42bc5c264640c52f7ca`
  (`experiment: freeze R2B stability study design`).

> R2B was designed after R2A was seen, so it is **hypothesis-generating**, not
> confirmatory. Reproducing R2A here would not confirm a theory; failing to
> reproduce it would not refute one. It removes the cheapest alternative
> explanation for R2A: that the structure was mostly estimator noise from two
> calibrators fitted on nine rows and evaluated on six.

---

## 0. Scope / why R2B exists

R2A fitted `g_CAT` and `g_OVR` on 9 paired TRAIN rows and evaluated on 6 paired
TEST rows. That is small enough that any directional structure could be noise.
R2B repeats the same frozen measurement/estimation design on a much larger,
deliberately harder paired population (90 TRAIN / 60 TEST) and adds two
pre-declared stability diagnostics (a paired test bootstrap and a paired
train-refit bootstrap) plus an observed-range loss decomposition.

R2B does **not**: sweep `l2`, change the CAT or OVR formulation, renormalize OVR,
change the OVR prompt, rebalance the split or the anchor, add a second model, add
a second measurement axis, or make a Research Gate decision.

---

## 1. Frozen dimensions inherited from R2A (unchanged)

| Dimension | Value |
| --- | --- |
| Model | `Qwen/Qwen3.5-2B` |
| Revision | `15852e8c16360a2fea060d615a32b45270f8a8fc` |
| dtype | `bfloat16` |
| Rendering | `{"enable_thinking": false}` |
| Measurement A | `direct-categorical-anchor-probability` v1 |
| Measurement B | `independent-binary-anchor-probability` v1 |
| OVR proposition | `choice-candidate-correctness-binary-judgment` v1 |
| Anchor protocol | `sha256-case-id-candidate-set-anchor` v1 |
| Research calibrator | `research-l2-logistic-fixed-decision-probability` v1 |
| Regularization | `l2_strength = 0.01` |
| Paired-fit eligibility | `CAT.status == SCORED AND OVR.status == SCORED` |

CAT reads the categorical probability assigned to the frozen anchor; OVR reads the
raw independent binary `p_true` for the frozen anchor and is **not** renormalized.

---

## 2. New 150-item population construction

`r2b_cases.json` (`source_case_set_version = calibration-transport-r2b-v1`) holds
**150 hand-written three-way cases**: 3 categories × 5 declared synthesis strata ×
10 items per cell. Item ids are opaque (`r2b-0001` … `r2b-0150`) and do not encode
the category, so no category label leaks into the anchor mechanism through the id.

- categories: `billing`, `shipping`, `technical` (unchanged R2A three-way taxonomy).
- candidate set and candidate descriptions: unchanged from R2A `three_way`.
- question: `Which team should handle this request?`
- strata: `direct`, `indirect`, `distractor`, `mixed-primary`, `contrast-negation`.

The strata are **declared synthesis styles** (how the context was written), not a
difficulty score, and not an effect variable. No item is intentionally ambiguous:
ground truth stays decidable from the explicit requested action.

Structural validation (enforced by `r2b_plan.validate_case_set`, and checked in
tests) confirms:

- exactly 150 items, all ids unique, all contexts unique;
- 50 per category, 30 per stratum, 10 per category × stratum cell;
- every `expected_category ∈ {billing, shipping, technical}`;
- **zero exact context overlap with R2A**;
- candidate set exact (no drift).

### Representative cases (one per category × stratum, lowest item id)

| item | stratum | expected | context |
| --- | --- | --- | --- |
| `r2b-0001` | direct | billing | I can see two charges for the same order on my card and I need one of them reversed. |
| `r2b-0011` | indirect | billing | The money that left my account this week is more than I agreed to pay. |
| `r2b-0021` | distractor | billing | I changed my surname last spring and I shop mostly on my phone, and my latest statement repeats a charge I already paid; I need it reversed. |
| `r2b-0031` | mixed-primary | billing | The delivery of my parcel was late last week, but what I actually need is an explanation of the duplicate charge on my card. |
| `r2b-0041` | contrast-negation | billing | The delivery came earlier than promised, so shipping is not a problem, but I was charged the wrong amount and need it adjusted. |
| `r2b-0051` | direct | shipping | My parcel has not arrived even though the estimated date was three days ago. |
| `r2b-0061` | indirect | shipping | Whatever I ordered last week still has not reached me and I would like to know when it will. |
| `r2b-0071` | distractor | shipping | I signed up during a spring sale and my account number ends in 42, and my parcel still has not arrived; I want to know where it is. |
| `r2b-0081` | mixed-primary | shipping | I was charged an extra shipping fee by mistake, but what I actually need is for you to find my missing parcel. |
| `r2b-0091` | contrast-negation | shipping | The payment for my order went through without any problem; the issue is that the parcel has not arrived. |
| `r2b-0101` | direct | technical | The mobile app closes immediately whenever I tap the profile tab. |
| `r2b-0111` | indirect | technical | The programme shuts itself down the moment I try to look at my profile. |
| `r2b-0121` | distractor | technical | I have a fast new phone and a reliable connection, and the app still crashes whenever I open my profile; please fix it. |
| `r2b-0131` | mixed-primary | technical | I was charged twice for my subscription, but what I actually need is for the crashing app to be fixed. |
| `r2b-0141` | contrast-negation | technical | My payment went through without any issue; the real problem is that the app crashes when I open my profile. |

---

## 3. Source-population and code provenance

- source case-set fingerprint: `c0bdc31bab6db3b91605321bc70da71c8692aca3ecddc3257840e01171a333d9`
  (content fingerprint of the whole fixture, including question/contexts/descriptions).
- plan fingerprint: `1127ea01f01c2671de6888fcd6759db17addf340aafe64f4e182b5aa2b58ead8`.
- paired dataset fingerprint: `b17fd3a44747ffa1597e4b74206d79a82135ed97337b69283ef89572181a0062`.
- run provenance fingerprint: `3eeab561b27453a6af80e0f1bd1fd3b8da36412ee12961d5203a2e1ead0c0683`.
- pre-measurement git commit: `dd68e299c364b038c959c42bc5c264640c52f7ca`;
  `git_worktree_clean = true`. The runner **fails closed** if the tree is dirty
  before the first score.

The R2B run provenance commits the source-population content fingerprint, the exact
R1 plan payload, the model + revision, both measurement identities, the anchor and
split protocols, the research target/input-score ids, and the code commit. So a
change to any question/context/description would change the run identity even if
the item ids stayed the same. R1's `PairedFixedDecisionPlan` fingerprint schema and
`integrity.py` are unchanged.

Library/runtime metadata (recorded, not part of the identity):

| key | value |
| --- | --- |
| python | 3.11.14 |
| torch | 2.14.0 |
| torch CUDA | 13.0 |
| transformers | 5.17.0 |
| huggingface_hub | 1.32.0 |
| safetensors | 0.8.0 |
| requested device | auto |
| resolved device | cuda |
| GPU | NVIDIA GeForce RTX 5060 Laptop GPU |

---

## 4. Split / anchor / Y distribution

Pre-declared, deterministic split (`r2b-five-strata-6-train-4-test-per-cell` v1):
within each category × stratum cell, the first 6 items by fixture order are TRAIN
and the last 4 are TEST. There is no randomness, no shuffle, and no rebalancing.

- TRAIN = 90, TEST = 60, AUDIT = 0.
- TRAIN Y = 1: **32**, Y = 0: **58**.
- TEST Y = 1: **23**, Y = 0: **37**.

Per-stratum Y = 1 (train / test): direct 3/12, indirect 6/12, distractor 5/12,
mixed-primary 5/12, contrast-negation 4/12 — i.e. (7/18, 3/12), (5/18, 6/12),
(7/18, 5/12), (8/18, 5/12), (5/18, 4/12) counting train/test separately.

The anchor is produced by the **same** R2A function `pilot_plan.select_anchor`,
whose only inputs are the opaque item id and the candidate names. No id or anchor
was edited to rebalance Y.

---

## 5. Measurement completeness

| quantity | value |
| --- | --- |
| CAT scored / missing / ineligible | 150 / 0 / 0 |
| OVR scored / missing / ineligible | 150 / 0 / 0 |
| paired-scored TRAIN | 90 |
| paired-scored TEST | 60 |
| total model evaluations | 600 (150 CAT + 450 OVR binary) |

There was no missingness and no ineligibility in this run.

---

## 6. Raw CAT / OVR score geometry (all 150 items)

| statistic | CAT anchor score | OVR anchor score |
| --- | --- | --- |
| min | 0.000096 | 0.119203 |
| q25 | 0.003531 | 0.320821 |
| median | 0.058759 | 0.437823 |
| q75 | 0.969084 | 0.500000 |
| max | 0.999485 | 0.867036 |
| mean | 0.388923 | 0.433649 |

CAT is sharply bimodal (near 0 or near 1 with a thin middle); OVR is compressed
into roughly [0.12, 0.87] with a median near 0.44. Supporting diagnostics:

- CAT `scoring_label_mass`: min 0.9574, mean 0.9904, max 0.9974.
- OVR `verbalizer_mass` (over 450 candidate judgments): min 0.9762, mean 0.9868,
  max 0.9927.
- OVR `candidate_score_sum` per item: min 0.4993, mean 1.2930, max 1.9626; 20/150
  items have more than one candidate above 0.5. OVR scores are **not** renormalized;
  the non-simplex sums are a property of the independent-binary measurement.

---

## 7. Full-N fitted calibrators (90 paired TRAIN rows, identical ids)

Both calibrators are fitted on the **same** 90 paired TRAIN item ids with the same
`Y`, differing only in `S_CAT` vs `S_OVR`. Method
`research-l2-logistic-fixed-decision-probability` v1, `l2_strength = 0.01`.

| calibrator | slope | intercept | fingerprint |
| --- | --- | --- | --- |
| `g_CAT` | 3.846295 | −2.221059 | `138bc913ac4061988a56d9246d9699c1fda9bc5972ec4efdec84bc5b821a9fd0` |
| `g_OVR` | 2.011524 | −1.418894 | `2a149a4f2550fabfcc221a5b3925220663f2791f07cccc8d4513876d21904655` |

Numerical kernel identity (recorded, reused; not a `CalibrationProfile`): objective
`mean-bernoulli-nll-plus-l2` v1, solver `newton-backtracking` v2, input transform
`identity-selected-probability` v1, endpoint policy `exact-raw-selected-probability`
v1, convergence `strong-convexity-objective-gap` v1.

---

## 8. Raw / self / cross Brier (60 paired TEST rows)

| cell | Brier |
| --- | --- |
| raw CAT | 0.037061 |
| raw OVR | 0.175664 |
| CAT → CAT (`g_CAT` on `S_CAT`) | 0.048977 |
| CAT → OVR (`g_CAT` on `S_OVR`) | 0.178679 |
| OVR → CAT (`g_OVR` on `S_CAT`) | 0.096857 |
| OVR → OVR (`g_OVR` on `S_OVR`) | 0.201117 |

Transport excess risks (baseline = the target's own self-fitted calibrator):

- `Delta CAT→OVR = CAT→OVR − OVR→OVR = 0.178679 − 0.201117 = -0.022438`
- `Delta OVR→CAT = OVR→CAT − CAT→CAT = 0.096857 − 0.048977 = +0.047880`

Raw-target-relative changes (baseline = the raw target score; positive = fitted
worse than raw):

| quantity | value | sign |
| --- | --- | --- |
| CAT self − raw CAT | +0.011916 | fitted worse |
| OVR self − raw OVR | +0.025453 | fitted worse |
| CAT → OVR − raw OVR | +0.003015 | fitted worse |
| OVR → CAT − raw CAT | +0.059795 | fitted worse |

Two readings must not be conflated: cross-vs-self (`Delta`) and fitted-vs-raw
(raw-relative). Even the cross applications are still *worse than the raw target
score* on this held-out sample.

---

## 9. Exact LogLoss (secondary)

No clipping, no smoothing.

| cell | LogLoss | state |
| --- | --- | --- |
| raw CAT | 0.123788 | finite |
| raw OVR | 0.533131 | finite |
| CAT → CAT | 0.217414 | finite |
| CAT → OVR | 0.539822 | finite |
| OVR → CAT | 0.358371 | finite |
| OVR → OVR | 0.590338 | finite |

All LogLoss values are finite here, but exact LogLoss is unbounded in general, so
it is not used for the bootstrap and no bounded-loss concentration argument is
claimed for it.

---

## 10. Paired test bootstrap (2000 deterministic replicates)

Protocol `sha256-paired-test-bootstrap` v1 over the 60 paired TEST items; whole
paired items `(Y, S_CAT, S_OVR)` are resampled together. Interval via
`nearest-rank-percentile` v1. This is an **exploratory paired bootstrap percentile
interval — not a confidence interval, with no coverage guarantee and no p-values.**

| quantity | point estimate | 2.5% | median | 97.5% |
| --- | --- | --- | --- | --- |
| `Delta CAT→OVR` | −0.022438 | −0.033835 | −0.022118 | −0.011068 |
| `Delta OVR→CAT` | +0.047880 | +0.030569 | +0.048381 | +0.061645 |

Both exploratory intervals sit entirely on one side of zero in this resample
distribution. That is a stability diagnostic; it is **not** a significance claim.

---

## 11. Paired train-refit calibrator stability (1000 deterministic replicates)

Protocol `sha256-paired-train-refit-bootstrap` v1. Each replicate resamples 90
TRAIN positions with replacement and uses the **same** multiset for both
calibrators, then refits and evaluates on the original fixed 60 TEST items.

| quantity | 2.5% | median | 97.5% |
| --- | --- | --- | --- |
| `g_CAT` slope | 3.435141 | 3.864939 | 4.213195 |
| `g_CAT` intercept | −2.478659 | −2.224927 | −1.869819 |
| `g_OVR` slope | 1.178032 | 2.015832 | 2.740595 |
| `g_OVR` intercept | −1.838619 | −1.418598 | −0.997771 |
| `Delta CAT→OVR` | −0.038228 | −0.023137 | −0.012918 |
| `Delta OVR→CAT` | +0.023007 | +0.048971 | +0.097958 |

Four Brier cells (summary): CAT→CAT [0.045173, 0.058552], CAT→OVR [0.175127,
0.190575], OVR→CAT [0.070682, 0.151571], OVR→OVR [0.191572, 0.223105].

Failed refits: **0**. The two deltas keep their signs across the resample
distribution, but `g_OVR`'s slope/intercept and the `OVR→CAT` delta are noticeably
wider than `g_CAT`'s — the OVR-fitted map is the more training-composition
sensitive of the two. This is a within-sample sensitivity diagnostic, not a
population-level transportability proof.

---

## 12. Empirical observed-range diagnostics

Definition: SOURCE→TARGET range diagnostic = TARGET TEST scores outside the SOURCE
TRAIN observed [min, max] range. This is an empirical observed-range diagnostic,
not a claim about true distribution support.

| direction | target TEST outside source TRAIN range | count |
| --- | --- | --- |
| CAT → OVR (OVR test vs CAT train range [0.00010, 0.99948]) | 0.00 | 0 / 60 |
| OVR → CAT (CAT test vs OVR train range [0.11920, 0.86704]) | 0.85 | 51 / 60 |

The asymmetry is stark and mirrors R2A: CAT's training range essentially covers
OVR test scores, while 85% of CAT test scores fall outside OVR's compressed
training range.

---

## 13. In-range / outside-range transport-loss decomposition

Per target TEST row, `d_i = Brier(g_SOURCE(S_TARGET_i), Y_i) −
Brier(g_TARGET(S_TARGET_i), Y_i)`; the mean of `d_i` is the transport excess risk.
Regions are defined by whether `S_TARGET_i` lies in the source TRAIN observed range.
Contributions are `sum(d_i over region)/N_total`.

| direction | N in | N out | mean d in | mean d out | in contrib | out contrib | sum | overall delta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CAT → OVR | 60 | 0 | −0.022438 | null | −0.022438 | 0.000000 | −0.022438 | −0.022438 |
| OVR → CAT | 9 | 51 | +0.030263 | +0.050989 | +0.004539 | +0.043340 | +0.047880 | +0.047880 |

For `OVR → CAT`, about 91% of the transport excess risk (`0.043340` of `0.047880`)
comes from the 51 outside-range rows, where the mean per-row difference
(`+0.050989`) is larger than in-range (`+0.030263`). This is a **descriptive**
statement about where the loss sits; it does **not** establish that the range
mismatch causes the transport effect.

---

## 14. Stratum descriptive summaries (TEST, n = 12 each)

Descriptive only. No calibrator is fitted per stratum and no stratum was selected
after seeing effects.

| stratum | raw CAT Brier | raw OVR Brier | mean CAT score | mean OVR score | CAT win acc | OVR win acc |
| --- | --- | --- | --- | --- | --- | --- |
| direct | 0.000078 | 0.136220 | 0.251747 | 0.439276 | 1.000 | 0.833 |
| indirect | 0.072317 | 0.212956 | 0.442756 | 0.410737 | 0.917 | 0.833 |
| distractor | 0.000074 | 0.195804 | 0.416951 | 0.544141 | 1.000 | 0.917 |
| mixed-primary | 0.098554 | 0.152306 | 0.524637 | 0.325387 | 0.833 | 0.917 |
| contrast-negation | 0.014283 | 0.181035 | 0.326712 | 0.438569 | 0.917 | 0.833 |

The strata mostly move the raw geometry, not obviously the transport direction;
this table is context, not a result, and its per-cell n = 12 is small.

---

## 15. End-to-end secondary diagnostics (TEST, n = 60)

| quantity | value |
| --- | --- |
| CAT winner accuracy | 0.9333 |
| OVR winner accuracy | 0.8667 |
| winner agreement | 0.8000 |

End-to-end is the *other* condition, not the Frozen-decision estimand: here each
protocol chooses and scores its own winner with its own correctness label. It does
not affect the anchor, split, eligibility, fitting, or transport analysis.

---

## 16. R2A vs R2B descriptive comparison

Different synthetic populations and sample sizes, so this is a descriptive
stability comparison, **not** an isolated causal estimate of a sample-size effect.

| quantity | R2A (9/6) | R2B (90/60) | same? |
| --- | --- | --- | --- |
| `Delta CAT→OVR` sign | negative (−0.054364) | negative (−0.022438) | yes |
| `Delta OVR→CAT` sign | positive (+0.043762) | positive (+0.047880) | yes |
| test-support asymmetry (OVR→CAT outside fraction) | 0.833 | 0.850 | yes (direction/magnitude) |
| CAT→OVR outside fraction | 0.000 | 0.000 | yes |
| all four raw-relative changes positive | yes | yes | yes |
| `g_CAT` slope / intercept | 4.187 / −2.250 | 3.846 / −2.221 | similar |
| `g_OVR` slope / intercept | 2.748 / −1.816 | 2.012 / −1.419 | same sign/scale |

The directional structure and orderings R2A showed are still visible at 90/60, with
`Delta CAT→OVR` shrinking in magnitude and `Delta OVR→CAT` roughly stable. R2A's own
record says the tiny-sample fit made the magnitudes untrustworthy; R2B does not
contradict that and does not prove it either.

---

## 17. Limitations

- R2B is exploratory. It was designed after R2A and is not confirmatory; it
  authorizes no compatibility claim and no Research Gate decision.
- The population is synthetic and hand-written; the strata are synthesis styles,
  not a validated difficulty scale.
- `g_CAT`/`g_OVR` are finite-data estimators, not the oracle `q_B`. The bootstrap
  measures sensitivity to training composition, not distance to an oracle.
- The observed-range decomposition is descriptive; `in-range`/`outside-range` are
  empirical regions, not distribution support, and no causality is claimed.
- One model, one dtype, one rendering configuration, one calibrator family, one
  `l2` value. No method sweep, no second model, no second measurement axis.
- The exploratory bootstrap intervals are not confidence intervals and carry no
  coverage guarantee.

---

## 18. Research Gate evidence

Facts only:

- Did R2A transport directions persist? **Yes** — `Delta CAT→OVR` negative,
  `Delta OVR→CAT` positive, both signs stable across the train-refit distribution.
- Did the self-calibrators become more stable? `g_CAT` is fairly stable (slope
  3.44–4.21); `g_OVR` is materially less stable (slope 1.18–2.74).
- Did self-fitted maps still worsen the raw target? **Yes** — all four
  raw-relative changes are positive at 90/60.
- How wide were the paired-test bootstrap intervals? `Delta CAT→OVR`
  [−0.0338, −0.0111]; `Delta OVR→CAT` [+0.0306, +0.0616] (exploratory percentile
  intervals).
- How sensitive were fitted parameters/deltas to train refitting? Refit 2.5–97.5%
  ranges are narrow for `CAT→CAT`/`CAT→OVR` and wider for `OVR→CAT`/`OVR→OVR`;
  0 failed refits.
- How much transport delta came from empirical outside-range rows? For
  `OVR→CAT`, ~91% of the delta came from outside-range rows; for `CAT→OVR` there
  were no outside-range test rows.
- Did End-to-end differences persist? CAT winner accuracy 0.933 vs OVR 0.867,
  agreement 0.800 (secondary).

**Human Research Gate decision: PENDING**
