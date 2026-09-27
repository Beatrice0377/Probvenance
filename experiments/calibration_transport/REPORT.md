# Calibration Transportability — CAT ↔ OVR Frozen-Decision Pilot

**Exploratory Pilot**

Not a benchmark. Not confirmatory evidence. No compatibility claim is authorized
by this pilot alone.

This report records the first successful empirical run of the Research R2 pilot
defined by `docs/research/calibration-transport-research-spec-v1.md`. It is a
single 15-item, 60-evaluation pilot on one model. It is exploratory: it exists to
decide whether a transport phenomenon is worth investing in, not to certify any
compatibility.

## 1. Environment / model snapshot recovery

The first empirical attempt (previous round) failed **before any measurement**:

```
huggingface_hub.errors.IncompleteSnapshotError
```

The frozen pilot had an unpinned revision (`revision=None`), and the locally
resolved `main` commit was `15852e8c16360a2fea060d615a32b45270f8a8fc`. The cached
snapshot for that commit was incomplete — three files were missing:

```
model.safetensors-00001-of-00001.safetensors
preprocessor_config.json
video_preprocessor_config.json
```

and `local_files_only=True` prevented completion. No CAT score, OVR score, paired
dataset, calibrator, matrix, artifact, or report was produced by that attempt.

Recovery this round:

- The weight was **not** present locally under any other revision (only tokenizer/
  config blobs existed; the interrupted weight download left two 0-byte
  `.incomplete` files). It was therefore downloaded, not copied.
- `main` was confirmed by `huggingface_hub` to still resolve to
  `15852e8c16360a2fea060d615a32b45270f8a8fc`; no newer `main` was adopted.
- The exact pinned snapshot was completed with `huggingface_hub.snapshot_download`
  at `revision=15852e8c16360a2fea060d615a32b45270f8a8fc` using the same
  `allow_patterns` the experiment loader uses.

> The model revision was pinned **before the first successful empirical
> measurement**.

## 2. Frozen design (unchanged)

- Cases: the 15 fixed three-way choice cases (`billing` / `shipping` /
  `technical`) from `experiments/choice_signal/cases.json`.
- Split: TRAIN 9, TEST 6, AUDIT 0 (`three-way-synthetic-3-train-2-test-per-category` v1).
- Anchor: `sha256-case-id-candidate-set-anchor` v1 (anchors unchanged from the
  pre-measurement plan).
- Measurement A (CAT): `direct-categorical-anchor-probability` v1 —
  `S_CAT = probabilities[anchor]`, never the winner's mass.
- Measurement B (OVR): `independent-binary-anchor-probability` v1 — one
  independent binary judgment per candidate, `S_OVR = p_true(anchor)`; **never
  renormalized**.
- Research target / input: `fixed-decision-correctness` v1 /
  `fixed-decision-semantic-probability` v1 (not `winner_correctness`, not
  `uncalibrated-selected-probability`).
- Calibrator: research-only `research-l2-logistic-fixed-decision-probability` v1,
  `l2_strength = 0.01`. No `CalibrationProfile` is used.
- Eligibility: paired-fit iff both measurements are `SCORED`.

Model configuration:

```
model            Qwen/Qwen3.5-2B
revision         15852e8c16360a2fea060d615a32b45270f8a8fc
dtype            bfloat16
rendering        {"enable_thinking": false}
local_files_only true (official run)
```

## 3. Official run

```
uv run python experiments/calibration_transport/run_pilot.py \
  --model Qwen/Qwen3.5-2B \
  --revision 15852e8c16360a2fea060d615a32b45270f8a8fc \
  --dtype bfloat16
```

- Attempts: 1 (successful; no partial/discarded artifact).
- Evaluations: 15 CAT + 45 OVR = 60 (exactly the frozen budget).
- Wall time: ~48 s.
- No smoke test was needed; the official run itself loaded the model and scored.

Loader report: no critical text-tower weights missing; non-text towers (`visual`,
`mtp`) were dropped by the experiment-side text-tower adapter as designed. This
matches the existing adapter contract.

## 4. Completeness

```
planned           15        CAT scored   15 (missing 0, ineligible 0)
train planned      9        OVR scored   15 (missing 0, ineligible 0)
test planned       6
paired scored train 9       paired scored test 6
train Y            3 ×1 / 6 ×0
test  Y            4 ×1 / 2 ×0
```

No row was dropped or substituted.

## 5. Exact paired rows

`Y = 1[anchor is correct]`; scores are each measurement's score for the SAME
frozen anchor.

| case_id | split | anchor | Y | CAT anchor score | CAT winner | OVR anchor score | OVR winner |
|---|---|---:|---:|---:|---|---:|---|
| 3w-billing-01 | train | billing | 1 | 0.9980 | billing | 0.5927 | billing |
| 3w-billing-02 | train | billing | 1 | 0.9986 | billing | 0.4688 | billing |
| 3w-billing-03 | train | shipping | 0 | 0.0022 | billing | 0.3775 | billing |
| 3w-billing-04 | test | billing | 1 | 0.9960 | billing | 0.5622 | billing |
| 3w-billing-05 | test | billing | 1 | 0.9979 | billing | 0.4688 | billing |
| 3w-shipping-01 | train | technical | 0 | 0.0008 | shipping | 0.4378 | shipping |
| 3w-shipping-02 | train | shipping | 1 | 0.9979 | shipping | 0.6225 | shipping |
| 3w-shipping-03 | train | billing | 0 | 0.0028 | shipping | 0.3775 | shipping |
| 3w-shipping-04 | test | shipping | 1 | 0.9989 | shipping | 0.7549 | shipping |
| 3w-shipping-05 | test | technical | 0 | 0.3329 | shipping | 0.4378 | shipping |
| 3w-technical-01 | train | billing | 0 | 0.0019 | technical | 0.3486 | technical |
| 3w-technical-02 | train | shipping | 0 | 0.0021 | technical | 0.4073 | technical |
| 3w-technical-03 | train | shipping | 0 | 0.0191 | technical | 0.2689 | technical |
| 3w-technical-04 | test | billing | 0 | 0.1962 | technical | 0.4073 | billing |
| 3w-technical-05 | test | technical | 1 | 0.9966 | technical | 0.7058 | shipping |

Note the frozen-anchor discipline is visible: e.g. for `3w-shipping-05` the
anchor is `technical` (Y=0) while CAT's own winner is `shipping`.

## 6. Measurement diagnostics

```
CAT anchor score          min 0.0008  mean 0.5028  max 0.9989
OVR anchor score          min 0.2689  mean 0.4826  max 0.7549
CAT scoring_label_mass    min 0.9859  mean 0.9936  max 0.9972
OVR verbalizer_mass       min 0.9829  mean 0.9866  max 0.9921
OVR candidate_score_sum   min 0.9118  mean 1.3671  max 2.0758
items with >1 OVR candidate > 0.5 : 2 / 15
```

The OVR candidate scores are neither a simplex nor renormalized, as designed. The
label/verbalizer masses are high (all > 0.98), so no measurement-validity concern
from low mass is flagged here.

## 7. Research-only fitted calibrators (train, n = 9)

```
g_CAT  slope 4.186955863991465   intercept -2.249787497465592
       fingerprint a7e1840ff0602d86b315b83bed841a9c3d7837bcd06414d0aa3ffcc4e574856e
g_OVR  slope 2.747840821278629   intercept -1.8157659296084625
       fingerprint a15a44529001f48e26ae2d00184a629204ad39e4f096577871d7986380f91ec8
l2_strength 0.01
```

`CalibrationProfile` used: **no**. Both calibrators are fitted on the SAME 9
training item IDs.

## 8. Raw Brier (held-out TEST, n = 6)

```
raw CAT anchor-score Brier   0.02489555803298782
raw OVR anchor-score Brier   0.16301864056888113
```

Raw CAT anchor scores already track anchor correctness very closely; raw OVR
anchor scores are compressed toward 0.5 and much less discriminative.

## 9. 2×2 Brier matrix (TEST)

```
                     eval CAT        eval OVR
fit CAT              0.03183805      0.17254842
fit OVR              0.07560034      0.22691209
```

```
Delta CAT→OVR = Brier(CAT→OVR) - Brier(OVR→OVR) = 0.17254842 - 0.22691209 = -0.05436367
Delta OVR→CAT = Brier(OVR→CAT) - Brier(CAT→CAT) = 0.07560034 - 0.03183805 = +0.04376229
```

Both directions are reported. The two directions have **opposite signs**:
transporting the CAT-fitted map onto OVR *reduces* Brier relative to the
OVR-fitted map, while transporting the OVR-fitted map onto CAT *increases* Brier
relative to the CAT-fitted map.

## 10. Exact LogLoss (TEST, no clipping, no smoothing)

```
fit CAT / eval CAT   0.18552362757017724
fit CAT / eval OVR   0.5321254310258411
fit OVR / eval CAT   0.3205240096444196
fit OVR / eval OVR   0.64532152272775
raw CAT              0.10564630312111169
raw OVR              0.5103659760780112
```

All cells are finite; no `{"state": "positive_infinity"}` cell occurs.

## 11. Observed-range diagnostics (empirical only)

```
CAT train anchor-score range   min 0.0008018  median 0.0027984  max 0.9985519
OVR train anchor-score range   min 0.2689414  median 0.4073334  max 0.6224593

fraction of OVR TEST scores outside CAT train observed range : 0.8333
fraction of CAT TEST scores outside OVR train observed range : 0.0000
```

The CAT score distribution is strongly bimodal (near 0/1); the OVR score
distribution is narrow and near the middle. This is an observed-range
observation only — it is not used to filter or exclude items.

## 12. End-to-end descriptive diagnostics (secondary only)

```
CAT winner accuracy (TEST)   1.0000
OVR winner accuracy (TEST)   0.6667
CAT/OVR winner agreement     0.6667
```

These are secondary and never entered row eligibility. They show the two
measurements are **not** matched on task accuracy in this pilot.

## 13. OVR non-simplex diagnostics

```
candidate_score_sum  min 0.9118015288669297  mean 1.367145957070238  max 2.075751488965772
items with >1 candidate over 0.5 : 2 / 15
```

Reported as a measurement-semantics diagnostic, not a validity test.

## 14. Exploratory interpretation

Facts only, no universal claim:

- CAT→OVR delta is **negative** (`-0.0544`); OVR→CAT delta is **positive**
  (`+0.0438`).
- The directions are **not symmetric** in sign.
- Magnitudes are of the same order as the self-risk of the affected target
  (`OVR→OVR = 0.2269`, `CAT→CAT = 0.0318`), i.e. not negligible relative to
  self-risk for CAT, and comparable to a substantial fraction of self-risk for
  OVR.
- Observed-range mismatch is one-sided: 83% of CAT test scores fall outside the
  OVR training range, while 0% of OVR test scores fall outside the CAT training
  range. The two mechanisms the spec asks to separate (a changed conditional
  relation vs. target scores moving into poorly-supported regions) cannot be
  separated from a 6-item test set.
- Own-decision accuracies differ substantially (CAT 1.0 vs OVR 0.67), so this
  pilot does **not** cleanly isolate a pure measurement shift. The measurement
  protocol and its own decision behavior are confounded here.

This is a positive-vs-negative-direction observation on one model and 6 test
items. It is not an incompatibility proof in either direction, and it is not a
compatibility proof in either direction.

## 15. Research Gate Evidence

Facts only:

- Were all 15 pairs measurable? **Yes** (CAT 15/15, OVR 15/15 scored).
- Paired train/test counts? **9 / 6**.
- CAT→OVR delta? **-0.05436** (negative).
- OVR→CAT delta? **+0.04376** (positive).
- Same sign? **No** — opposite signs.
- Magnitude relative to self-risk? CAT→OVR vs OVR self-risk `0.2269`: sizeable
  reduction. OVR→CAT vs CAT self-risk `0.0318`: increase larger than CAT self-risk.
- Observed-range mismatch? OVR TEST outside CAT train range `0.833`, CAT TEST
  outside OVR train range `0.000`.
- CAT/OVR own-decision accuracy? **1.000 / 0.667** (not matched).
- OVR non-simplex behavior? sums in `[0.912, 2.076]`, 2/15 items with more than
  one candidate over 0.5.

**Human Research Gate decision: PENDING**

This report does not declare "proceed to R3", does not declare "abandon the
topic", and does not declare the thesis validated.

## 16. Reproducibility

- Raw artifact: `results/frozen-decision-cat-ovr-qwen35-2b.json`
  (`plan_fingerprint = 37aeb0862f89931207d2c60bcb9f41fac9ad6e05a254e94dd17822c232e6571e`,
  `paired_dataset_fingerprint = 46c9ed1353d71b87b21ded8cb81fb8f06bc6c1d6ab832fbbc1b5ffdb24b3582c`).
- Analysis artifact: `results/frozen-decision-cat-ovr-qwen35-2b-analysis.json`.
- The analysis artifact is a deterministic function of the raw artifact plus the
  research harness (`analysis.py`): rebuilding the plan and dataset from the raw
  records and re-running the analysis reproduces every fingerprint and matrix
  exactly (verified without re-running the model). The report is not the only
  data source.
