# R2C — Exploratory Calibration-Method Adequacy Sensitivity

**No new model measurements were collected.**
**Not confirmatory evidence.**
**No R3 calibration method is selected by this report.**

- Round: `calibration-method-adequacy-sensitivity` v1
- Design: `r2c_method_adequacy_design.json` (fingerprint
  `82b7b73769614f1d69bfb5bad0419d5cc855abc2ebfa617c91ad97da6a7bccc0`)
- Round status: **incomplete** (see §12, §14-A). The train-refit bootstrap fails
  closed for the two `lambda = 1e-6` configurations; nothing is imputed for them.
- Source: frozen R2B raw `results/r2b-stability-qwen35-2b-v1.json`
  (sha256 `16a07ecd69a4ec0081f76790b7bde0b4e8bcd87172e06b7af94c06ea699967a4`),
  unmodified.
- Result artifact:
  `results/r2c-method-adequacy-qwen35-2b-v1-analysis.json`
  (sha256 `8b90dbb02c4cdb2d47ceb2e7e0933aa10be05aab3979614634cf43b9e7841018`).

## 0. Why R2C exists

R2B increased the calibration training set from 9 to 90 rows, and still observed

```
raw CAT Brier < CAT→CAT Brier
raw OVR Brier < OVR→OVR Brier
```

with all four fitted-vs-raw Brier changes positive. R2C asks one question only:

> Is the native-calibration degradation specific to the frozen
> `raw-p logistic + lambda = 1e-2` configuration, or does it persist across a
> pre-declared, narrow sensitivity set?

It tests two narrow explanation axes: **regularization strength** and
**raw-p vs logit-p feature geometry**. It is analysis-only and never reruns the
model.

## 1. Frozen R2B evidence lineage

R2C reuses exactly the frozen R2B raw artifact and rebuilds the plan/dataset
from it, re-checking every fingerprint before analysis:

- `source_case_set_version = calibration-transport-r2b-v1`
- `source_case_set_fingerprint = c0bdc31bab6db3b91605321bc70da71c8692aca3ecddc3257840e01171a333d9`
- `plan_fingerprint = 1127ea01f01c2671de6888fcd6759db17addf340aafe64f4e182b5aa2b58ead8`
- `paired_dataset_fingerprint = b17fd3a44747ffa1597e4b74206d79a82135ed97337b69283ef89572181a0062`
- `source_measurement_code_commit = dd68e299c364b038c959c42bc5c264640c52f7ca`
- model `Qwen/Qwen3.5-2B`, revision `15852e8c16360a2fea060d615a32b45270f8a8fc`

The raw artifact sha256 is unchanged before and after R2C, and the R2B raw,
R2B analysis artifact, and R2B report are byte-identical to the pushed baseline.

## 2. Method sensitivity design

Ten fitted configurations = 2 families × the exact pre-declared 5-value lambda
grid, plus the RAW identity baseline. All configurations use the same 90 TRAIN
item IDs and are evaluated on the same 60 held-out TEST item IDs with the same
labels. Nothing is selected away: all ten configurations enter the artifact and
this report.

## 3. Exact method families and lambda grid

| Family | id | feature | map |
| --- | --- | --- | --- |
| RAW | `raw-identity` v1 | none | `q(p) = p` (not fitted) |
| P | `research-l2-logistic-fixed-decision-probability` v1 | `p` (`identity-raw-probability` v1) | `sigmoid(a*p + b)` |
| L | `research-l2-logistic-logit-fixed-decision-probability` v1 | `logit(p)` (`exact-logit-probability` v1) | `sigmoid(a*logit(p) + b)` |

Objective for both fitted families: mean Bernoulli NLL
`+ lambda/2 * (a^2 + b^2)`, solved by the reused production kernel
`_solve_l2_logistic` (unchanged) with `_stable_sigmoid`.

Pre-declared lambda grid (identical for both families, one freeze, never
extended):

```
1e-6, 1e-4, 1e-2, 1e-1, 1.0
```

`lambda = 1e-2` (Family P) is the frozen R2B configuration. `lambda = 0` is
excluded because the reused solver contract is built on positive L2. `1e-6` is a
pre-declared *near-unregularized sensitivity point*, not "unregularized."

## 4. Endpoint / numerical contracts

- `input_transform_id = exact-logit-probability` v1; `endpoint_policy_id =
  reject-exact-probability-endpoints` v1.
- Family L performs **no clipping, no epsilon, no endpoint smoothing**. Any exact
  `p ∈ {0, 1}` in a required TRAIN/TEST score fails closed
  (`ProbabilityEndpointError`). The frozen R2B scores contain no exact endpoints,
  so Family L runs; the fail-closed path is covered by tests.
- The identity map belongs to the Family L function class (`sigmoid(1*logit(p)+0)
  = p`), but positive L2 does not particularly favour it.

## 5. Current R2B-method reproduction

Family P / `lambda = 1e-2`, refit from the frozen R2B raw evidence, reproduces
the committed R2B result exactly: `g_CAT slope 3.846295006005954 / intercept
-2.221059340872021`, `g_OVR slope 2.0115237146443437 / intercept
-1.4188935644173986`, and the full 2×2 Brier matrix
(`fit_a_eval_a 0.048976731499582364`, `fit_a_eval_b 0.17867886241765843`,
`fit_b_eval_a 0.0968565937452747`, `fit_b_eval_b 0.20111698788477606`,
`raw_a 0.037061170992326524`, `raw_b 0.1756641370488051`). This is locked by a
regression test.

Raw baselines (60 TEST rows): CAT Brier `0.037061170992326524`, CAT LogLoss
`0.12378774228600839`; OVR Brier `0.1756641370488051`, OVR LogLoss
`0.5331305979109473`.

## 6. Native CAT adequacy results

Negative = fitted native calibrator has lower held-out Brier than raw CAT.

| family | lambda | native Brier | native − raw | self LogLoss | LogLoss − raw |
| --- | --- | --- | --- | --- | --- |
| P | 1e-6 | 0.037429 | **+0.000367** | 0.15436 | +0.030573 |
| P | 1e-4 | 0.037392 | **+0.000331** | 0.15269 | +0.028900 |
| P | 1e-2 | 0.048977 | **+0.011916** | 0.21741 | +0.093626 |
| P | 1e-1 | 0.143042 | **+0.105981** | 0.47264 | +0.348850 |
| P | 1.0 | 0.232128 | **+0.195067** | 0.65736 | +0.533573 |
| L | 1e-6 | 0.039368 | **+0.002306** | 0.13458 | +0.010795 |
| L | 1e-4 | 0.039328 | **+0.002267** | 0.13439 | +0.010607 |
| L | 1e-2 | 0.037530 | **+0.000469** | 0.12665 | +0.002864 |
| L | 1e-1 | 0.037160 | **+0.000099** | 0.13206 | +0.008271 |
| L | 1.0 | 0.049941 | **+0.012880** | 0.20831 | +0.084527 |

**No pre-declared configuration lowers held-out CAT Brier versus raw CAT.** The
closest is `L:0.1` at `+0.000099`, whose paired-test interval straddles zero. The
degradation is monotone in lambda and is *not* specific to `lambda = 1e-2`.

## 7. Native OVR adequacy results

| family | lambda | native Brier | native − raw | self LogLoss | LogLoss − raw |
| --- | --- | --- | --- | --- | --- |
| P | 1e-6 | 0.154413 | **−0.021251** | 0.47064 | −0.062495 |
| P | 1e-4 | 0.155021 | **−0.020643** | 0.47273 | −0.060396 |
| P | 1e-2 | 0.201117 | **+0.025453** | 0.59034 | +0.057208 |
| P | 1e-1 | 0.233544 | **+0.057879** | 0.65977 | +0.126635 |
| P | 1.0 | 0.244186 | **+0.068521** | 0.68151 | +0.148376 |
| L | 1e-6 | 0.154888 | **−0.020776** | 0.47051 | −0.062624 |
| L | 1e-4 | 0.154918 | **−0.020746** | 0.47060 | −0.062528 |
| L | 1e-2 | 0.158192 | **−0.017472** | 0.48121 | −0.051920 |
| L | 1e-1 | 0.179855 | **+0.004191** | 0.54228 | +0.009146 |
| L | 1.0 | 0.226859 | **+0.051195** | 0.64658 | +0.113445 |

Five configurations lower held-out OVR Brier versus raw OVR: `P:1e-6`, `P:1e-4`,
`L:1e-6`, `L:1e-4`, `L:0.01`. So the R2B OVR degradation (`P:0.01`, `+0.0255`)
**is** sensitive to regularization strength and to feature geometry: low lambda
shrinks toward the raw score and improves OVR. Yet even the best OVR config
remains a fitted estimator, not oracle truth.

## 8. Full transport sensitivity

Transport excess risks per configuration (point estimates, full 90-train fits,
60 TEST rows):

| family | lambda | CAT→OVR delta | OVR→CAT delta |
| --- | --- | --- | --- |
| P | 1e-6 | +0.039273 | +0.001462 |
| P | 1e-4 | +0.034188 | +0.001144 |
| P | 1e-2 | −0.022438 | +0.047880 |
| P | 1e-1 | −0.016568 | +0.079019 |
| P | 1.0 | −0.000771 | +0.013116 |
| L | 1e-6 | +0.055596 | +0.000023 |
| L | 1e-4 | +0.055101 | +0.000051 |
| L | 1e-2 | +0.030414 | +0.000988 |
| L | 1e-1 | +0.003170 | −0.000396 |
| L | 1.0 | −0.019453 | +0.061445 |

The R2B `CAT→OVR < 0` and `OVR→CAT > 0` structure does **not** survive across the
method set: the CAT→OVR sign flips. See §15.

## 9. Raw-relative cross risks

Cross-vs-raw (not cross-vs-self) values, so a cross prediction is never confused
with an improvement over raw:

| family | lambda | CAT→OVR − raw OVR | OVR→CAT − raw CAT |
| --- | --- | --- | --- |
| P | 1e-6 | +0.018023 | +0.001829 |
| P | 1e-4 | +0.013545 | +0.001475 |
| P | 1e-2 | +0.003015 | +0.059795 |
| P | 1e-1 | +0.041311 | +0.185000 |
| P | 1.0 | +0.067751 | +0.208183 |
| L | 1e-6 | +0.034820 | +0.002329 |
| L | 1e-4 | +0.034355 | +0.002318 |
| L | 1e-2 | +0.012942 | +0.001457 |
| L | 1e-1 | +0.007361 | −0.000297 |
| L | 1.0 | +0.031742 | +0.074326 |

Every CAT→OVR value is positive (transported CAT calibrators are worse than raw
OVR on OVR scores, under every configuration). OVR→CAT is positive except a
negligible `L:0.1` value.

## 10. Exact LogLoss secondary results

Exact Bernoulli LogLoss, no clipping, no smoothing; all cells finite for all ten
configurations. LogLoss direction agrees with Brier direction in every
configuration (see §6–7). Because raw OVR LogLoss (`0.5331`) is high, several
low-lambda OVR configs beat it on LogLoss even when their Brier gain is modest.
Exact LogLoss is a secondary metric only: without bounded-loss assumptions no
finite-sample concentration argument is claimed for it.

## 11. Paired TEST bootstrap

Protocol `sha256-r2c-paired-test-bootstrap` v1, 2000 deterministic paired draws,
one shared set of resampled TEST positions across all ten configurations and both
measurements. Calibrators stay at the full 90-train fit. Intervals are
exploratory paired bootstrap percentile intervals (nearest-rank rule) — **not**
confidence intervals, no p-values.

Selected intervals (point estimate in §6–8):

| family | lambda | native CAT [2.5, 50, 97.5] | native OVR | CAT→OVR | OVR→CAT |
| --- | --- | --- | --- | --- | --- |
| P | 1e-6 | [−0.0099, +0.0003, +0.0102] | [−0.0458, −0.0222, +0.0045] | [+0.0035, +0.0394, +0.0743] | [−0.0087, +0.0011, +0.0135] |
| P | 1e-4 | [−0.0095, +0.0002, +0.0097] | [−0.0438, −0.0216, +0.0037] | [+0.0020, +0.0344, +0.0657] | [−0.0080, +0.0008, +0.0119] |
| P | 1e-2 | [+0.0028, +0.0124, +0.0191] | [+0.0038, +0.0259, +0.0462] | [−0.0330, −0.0226, −0.0115] | [+0.0332, +0.0486, +0.0618] |
| P | 1e-1 | [+0.0788, +0.1081, +0.1279] | [+0.0299, +0.0583, +0.0848] | [−0.0299, −0.0167, −0.0036] | [+0.0621, +0.0793, +0.0971] |
| P | 1.0 | [+0.1576, +0.1983, +0.2248] | [+0.0414, +0.0691, +0.0933] | [−0.0046, −0.0008, +0.0030] | [+0.0088, +0.0131, +0.0177] |
| L | 1e-6 | [−0.0123, +0.0024, +0.0170] | [−0.0440, −0.0217, +0.0038] | [+0.0143, +0.0562, +0.0971] | [−0.0197, −0.0005, +0.0193] |
| L | 1e-4 | [−0.0123, +0.0023, +0.0169] | [−0.0439, −0.0216, +0.0037] | [+0.0141, +0.0557, +0.0963] | [−0.0196, −0.0005, +0.0192] |
| L | 1e-2 | [−0.0102, +0.0006, +0.0106] | [−0.0365, −0.0182, +0.0030] | [+0.0062, +0.0310, +0.0543] | [−0.0127, +0.0004, +0.0150] |
| L | 1e-1 | [−0.0067, +0.0005, +0.0060] | [−0.0086, +0.0043, +0.0161] | [−0.0002, +0.0032, +0.0062] | [−0.0019, −0.0005, +0.0015] |
| L | 1.0 | [−0.0034, +0.0142, +0.0262] | [+0.0301, +0.0515, +0.0703] | [−0.0269, −0.0196, −0.0119] | [+0.0493, +0.0622, +0.0719] |

Native CAT intervals are strictly positive only for `P:0.01`, `P:0.1`, `P:1.0`,
`L:1.0`; the rest straddle or include zero. The five OVR-improving configs have
median native OVR below zero but 97.5 percentiles near or above zero.

## 12. Train-refit bootstrap

Protocol `sha256-r2c-paired-train-refit-bootstrap` v1, 1000 replicates, one
shared resampled training multiset per replicate across all ten configurations
and both measurements; each replicate refits both calibrators on the unchanged
90 positions and evaluates on the fixed 60 TEST rows.

**Fail-closed result:** 15 of 20 000 refits cannot be certified by the reused
solver (`InvalidDecisionError`, "could not certify an objective gap within
1e-14 ... within 100 iterations"), **all at `lambda = 1e-6`**:

- `L:1e-6`: 13 (CAT replicates 125, 308, 444, 497, 549, 571, 936, 960, 995; OVR
  replicates 81, 87, 253, 427)
- `P:1e-6`: 2 (OVR replicate 169; CAT replicate 452)

These are recorded per measurement/replicate with the exact error. Per the
PART 36 failure policy, the affected configurations' train-refit blocks are
marked `failed` and **no interval is computed over the surviving replicates**;
the round status is `incomplete`. The other eight configurations completed all
1000 replicates (`failed_fits = 0`).

| family | lambda | native CAT | native OVR | CAT→OVR | OVR→CAT | cat neg-frac | ovr neg-frac |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P | 1e-6 | — failed — | — failed — | — failed — | — failed — | — | — |
| P | 1e-4 | [−0.0001, +0.0013, +0.0167] | [−0.0227, −0.0189, −0.0018] | [−0.0034, +0.0349, +0.1748] | [−0.0148, −0.0000, +0.0048] | 0.097 | 0.982 |
| P | 1e-2 | [+0.0081, +0.0120, +0.0227] | [+0.0161, +0.0271, +0.0495] | [−0.0401, −0.0234, −0.0129] | [+0.0237, +0.0496, +0.1022] | 0.000 | 0.000 |
| P | 1e-1 | [+0.1004, +0.1065, +0.1205] | [+0.0561, +0.0588, +0.0661] | [−0.0227, −0.0166, −0.0131] | [+0.0672, +0.0791, +0.0911] | 0.000 | 0.000 |
| P | 1.0 | [+0.1940, +0.1951, +0.1970] | [+0.0658, +0.0685, +0.0723] | [−0.0014, −0.0008, −0.0003] | [+0.0116, +0.0131, +0.0145] | 0.000 | 0.000 |
| L | 1e-6 | — failed — | — failed — | — failed — | — failed — | — | — |
| L | 1e-4 | [−0.0004, +0.0031, +0.0328] | [−0.0225, −0.0187, −0.0023] | [+0.0094, +0.0586, +0.2238] | [−0.0306, −0.0012, +0.0045] | 0.127 | 0.983 |
| L | 1e-2 | [−0.0004, +0.0008, +0.0066] | [−0.0221, −0.0160, +0.0014] | [+0.0052, +0.0289, +0.0887] | [−0.0053, +0.0005, +0.0034] | 0.252 | 0.964 |
| L | 1e-1 | [−0.0004, +0.0001, +0.0019] | [−0.0042, +0.0051, +0.0191] | [−0.0105, +0.0024, +0.0121] | [−0.0018, −0.0002, +0.0037] | 0.396 | 0.159 |
| L | 1.0 | [+0.0107, +0.0127, +0.0161] | [+0.0460, +0.0512, +0.0579] | [−0.0257, −0.0194, −0.0145] | [+0.0414, +0.0613, +0.0935] | 0.000 | 0.000 |

Negative fractions are exploratory stability *frequencies*, not probabilities or
posterior probabilities.

## 13. Parameter stability

Train-refit slope/intercept intervals per configuration; Family L intervals are
on the **logit(p) feature scale** and are not the same physical quantity as
Family P intervals.

| family | lambda | CAT slope [2.5, 50, 97.5] | OVR slope [2.5, 50, 97.5] |
| --- | --- | --- | --- |
| P | 1e-4 | [+5.98, +8.42, +17.14] | [+5.53, +9.53, +15.83] |
| P | 1e-2 | [+3.40, +3.88, +4.21] | [+1.20, +2.00, +2.71] |
| P | 1e-1 | [+0.95, +1.15, +1.28] | [−0.04, +0.15, +0.32] |
| P | 1.0 | [+0.10, +0.14, +0.18] | [−0.05, −0.01, +0.02] |
| L | 1e-4 | [+0.79, +1.23, +5.60] | [+1.29, +2.32, +4.35] |
| L | 1e-2 | [+0.76, +1.09, +1.55] | [+1.11, +1.85, +2.73] |
| L | 1e-1 | [+0.65, +0.78, +0.90] | [+0.58, +0.85, +1.08] |
| L | 1.0 | [+0.39, +0.42, +0.45] | [+0.12, +0.17, +0.22] |

`P:1e-4` slopes are the most unstable (wide intervals); `1e-6` is indeterminate.

## 14. Joint-native-improvement configurations

`joint_native_improvement(m)` = `NativeDelta_CAT(m) < 0 AND NativeDelta_OVR(m) < 0`.

**NONE.** No pre-declared configuration lowers held-out Brier for both
measurements. Per measurement:

- `NativeDelta_CAT < 0`: **NONE**
- `NativeDelta_OVR < 0`: `P:1e-6`, `P:1e-4`, `L:1e-6`, `L:1e-4`, `L:0.01`

The grid is not changed.

## 15. Transport-sign robustness

Across the ten pre-declared configurations (exact sign, no practical-equivalence
epsilon):

```
CAT→OVR:  negative 4/10,  positive 6/10,  zero 0/10
OVR→CAT:  negative 1/10,  positive 9/10,  zero 0/10
```

The R2A/R2B `CAT→OVR < 0` direction is **not robust to the calibration-method
configuration** — it flips to positive for the low-lambda / logit-family
configurations. The `OVR→CAT > 0` direction is broadly stable (9/10), with only
a negligible `L:0.1` flip. Therefore any future transport claim must be
conditioned on the calibration method.

## 16. Limitations / excluded methods

> R2C reuses R2B held-out data after R2B results were already observed. It is
> therefore an exploratory method-sensitivity study, not an independent
> confirmation of any selected calibration method.

The train-refit bootstrap is incomplete at `lambda = 1e-6` (§12); the affected
cells are marked `failed` and are not imputed. `g_B` is a finite-data estimator,
never oracle `q_B`. The observed R2B geometry is extreme (CAT near-saturated,
OVR compressed), so "difficulty to improve" and "range mismatch" remain
co-entangled.

Deliberately deferred (not贬低 — simply out of R2C's narrow scope):

- isotonic regression
- full 3-parameter beta calibration
- temperature-only scaling
- other nonlinear / nonparametric calibration families

## 17. R3-method-adequacy gate evidence

Facts only:

- Did any pre-declared config lower native held-out Brier vs raw CAT? **No.**
- Did any lower native held-out Brier vs raw OVR? **Yes** — `P:1e-6`, `P:1e-4`,
  `L:1e-6`, `L:1e-4`, `L:0.01`.
- Did any single config lower native Brier for BOTH measurements? **No.**
- Were those signs stable in paired-test bootstrap? OVR gains are median-negative
  with 97.5 percentiles near/above zero; CAT has no gain to confirm.
- Were they stable to train-refit resampling? For `P:1e-4` OVR neg-frac 0.982;
  for `L:1e-4` 0.983; `L:0.01` 0.964. The `1e-6` cells are indeterminate.
- Was current `lambda = 1e-2` specifically responsible for degradation? For OVR,
  **partly yes** (low lambda removes OVR degradation); for CAT, **no** (all
  configs degrade).
- Did logit-feature geometry materially change native adequacy? For CAT, barely
  (best `L:0.1` +0.000099 vs raw); for OVR, yes (Family L at `1e-2` already
  improves OVR while Family P at `1e-2` does not).
- Did CAT→OVR transport sign persist across configurations? **No** — it flips.
- Did OVR→CAT transport sign persist? Broadly **yes** (9/10).
- Did cross-vs-self and cross-vs-raw tell different stories? **Yes** — the
  degraded "cross" deltas partially reflect a poor OVR self-calibrator, while
  cross-vs-raw is less dramatic.

## Appendix A — First-round findings (disclosed)

1. **Train-refit solver non-certification at `lambda = 1e-6`.** First official
   attempt aborted (fail-closed). Root cause: the reused strong-convexity
   certificate requires `||grad|| <= sqrt(2*lambda*1e-14) ≈ 1.4e-10`, a
   double-precision conditioning floor for some resamples; raising the iteration
   cap to 5000 does not help. Not an implementation defect (kernel untouched,
   production src untouched). Fix: implemented the PART 36 failure-recording
   policy (record per measurement/replicate; mark affected configs `failed`; no
   subset interval; round status `incomplete`). Commit
   `0002ef8`. Version impact: none.

2. **Transport bootstrap evaluated on the wrong measurement score.** The
   per-item transport diffs for the bootstraps used `g_cat` on CAT (score_a)
   instead of the target OVR score, so bootstrap transport intervals measured
   `fit_a_eval_a − fit_b_eval_b` rather than `fit_a_eval_b − fit_b_eval_b`. The
   point-estimate transport table (from `brier_matrix`) was always correct.
   Root cause: a private per-item helper re-implemented without the R2B
   target-score convention. Fix: evaluate both legs on the target measurement
   score. Regression:
   `test_transport_point_matches_brier_matrix_delta` (would have failed before).
   Commit `77c051a`. The prior buggy artifact was regenerated; version impact:
   none (research-only). R2B itself was unaffected (its own helper uses the
   correct convention).

## Appendix B — Provenance

```
source_measurement_code_commit = dd68e299c364b038c959c42bc5c264640c52f7ca
r2c_analysis_design_commit    = 8e2289cb898d19ca61f7cfa6caf544635e95bef5
r2c_analysis_execution_commit = 77c051a2f47d98e253d546b8dfcf532face1ca6e
git_worktree_clean            = true
source R2B raw sha256         = 16a07ecd69a4ec0081f76790b7bde0b4e8bcd87172e06b7af94c06ea699967a4
design fingerprint            = 82b7b73769614f1d69bfb5bad0419d5cc855abc2ebfa617c91ad97da6a7bccc0
analysis artifact sha256      = 8b90dbb02c4cdb2d47ceb2e7e0933aa10be05aab3979614634cf43b9e7841018
```

Round status: **incomplete** (train-refit indeterminate at `lambda = 1e-6`).
Human Research Gate decision: **PENDING**. R2C selects no method and authorizes
no R3 work.
