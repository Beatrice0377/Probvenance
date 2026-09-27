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
relative to the CAT-fitted map. The baseline here is the **target self-fitted
calibrator**, which is a finite-sample estimator and not an oracle map (see
§9.1 and §14).

## 9.1 Raw-target-relative Brier changes (different baseline)

These compare each fitted application against the **raw target score**, not the
target self-fitted calibrator. Sign convention: `positive` means the fitted map
has higher held-out Brier risk than the raw target score (worse on this held-out
set); `negative` means lower risk (better).

```
CAT  self  − raw CAT   0.03183805 − 0.02489556 = +0.00694249
OVR  self  − raw OVR   0.22691209 − 0.16301864 = +0.06389345
CAT→OVR    − raw OVR   0.17254842 − 0.16301864 = +0.00952978
OVR→CAT    − raw CAT   0.07560034 − 0.02489556 = +0.05070478
```

All four are positive: every fitted-calibrator application has **higher** held-out
Brier risk than the corresponding raw target measurement on this six-item slice.
This baseline answers a different question than the transport excess risk in §9
and the two must not be conflated.

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

Direction convention: for `SOURCE → TARGET`, the fraction counts **TARGET TEST**
scores that fall outside the **SOURCE TRAIN** observed range. In this pilot
`A = CAT` and `B = OVR`.

```
CAT train anchor-score range   min 0.0008018  median 0.0027984  max 0.9985519
OVR train anchor-score range   min 0.2689414  median 0.4073334  max 0.6224593

CAT→OVR: OVR TEST scores outside CAT TRAIN range   0 / 6 = 0.0000
OVR→CAT: CAT TEST scores outside OVR TRAIN range   5 / 6 = 0.8333
```

The CAT score distribution is strongly bimodal (near 0/1); the OVR score
distribution is narrow and near the middle. This is an observed-range observation
only — it is not used to filter or exclude items, and it is not a support theorem.
The two directions are strongly asymmetric: every OVR test score lies inside the
CAT training range, while five of six CAT test scores lie outside the OVR training
range.

## 12. End-to-end descriptive diagnostics (secondary only)

```
CAT winner accuracy (TEST)   1.0000
OVR winner accuracy (TEST)   0.6667
CAT/OVR winner agreement     0.6667
```

These are **secondary** end-to-end diagnostics and never entered row eligibility.
They show that, when each protocol chooses its own winner, the two measurements
also differ in decision behavior on this fixture. A secondary own-winner accuracy
difference does **not** invalidate the primary Frozen-decision comparison, which
uses the same frozen anchor and label for both protocols (§14).

## 13. OVR non-simplex diagnostics

```
candidate_score_sum  min 0.9118015288669297  mean 1.367145957070238  max 2.075751488965772
items with >1 candidate over 0.5 : 2 / 15
```

Reported as a measurement-semantics diagnostic, not a validity test.

## 14. Exploratory interpretation

Facts only, no universal claim:

- CAT→OVR delta is **negative** (`-0.0544`) and OVR→CAT delta is **positive**
  (`+0.0438`): the two directions are **not symmetric** in sign.
- The transport excess risks are measured against the **target self-fitted
  calibrator** (`Delta = cross fitted − target self-fitted`). They are **not**
  measured against raw target scores.
- Raw-target-relative changes are all **positive** here: both self-fitted maps and
  both cross-applied maps have higher held-out Brier risk than the corresponding
  raw target score. On this test slice the OVR risk ordering is
  `raw OVR < CAT→OVR < OVR→OVR`.
- Therefore the negative `Delta CAT→OVR` does **not** establish that CAT
  calibration improves OVR scores. It means only that, on these six items, the
  CAT-fitted map has lower Brier risk than the independently fitted OVR
  self-calibrator when both are evaluated on OVR scores — while still being worse
  than the raw OVR score.
- **Finite-sample self-calibrator caution.** Both target calibrators are fitted on
  only 9 training rows and evaluated on 6 test rows, so `g_CAT` and `g_OVR` are
  finite-sample estimators, not oracle maps `q_target`. The self-fitted maps
  themselves worsen held-out Brier relative to raw target scores in this pilot, so
  cross-vs-self excess risk must be read together with raw-target-relative risk.
- Observed-range mismatch is strongly one-sided: `0/6` OVR test scores fall outside
  the CAT training range, while `5/6` CAT test scores fall outside the OVR training
  range. This directional range mismatch is a useful **hypothesis-generating
  diagnostic**, not a causal explanation; a min/max observed range over 6 test
  items is not a distribution support, and it does not explain the transport
  asymmetry.
- **The primary Frozen-decision comparison remains measurement-controlled.** CAT
  and OVR score the same pre-frozen anchor `D_i` under the same correctness label
  `Y_i`; the primary rows (`D_i`, `Y_i`, `S_CAT(D_i)`, `S_OVR(D_i)`) are unchanged
  by either protocol's own winner choice. The differing end-to-end winner
  accuracies therefore do **not** invalidate the primary measurement-shift
  estimand.

This is a sign/direction observation on one model and 6 test items. It is neither
an incompatibility proof nor a compatibility proof in either direction.

## 15. Research Gate Evidence

Facts only:

- Were all 15 pairs measurable? **Yes** (CAT 15/15, OVR 15/15 scored).
- Paired train/test counts? **9 / 6**.
- Primary condition measurement-controlled? **Yes** — same frozen anchor `D_i` and
  same `Y_i` for both protocols; own-winner accuracy differences are secondary.
- CAT→OVR delta (vs OVR self-fitted)? **-0.05436** (negative).
- OVR→CAT delta (vs CAT self-fitted)? **+0.04376** (positive).
- Same sign? **No** — opposite signs.
- Raw-target-relative Brier changes? CAT self `+0.00694`, OVR self `+0.06389`,
  CAT→OVR `+0.00953`, OVR→CAT `+0.05070` (all positive).
- OVR risk ordering on TEST? `raw OVR (0.1630) < CAT→OVR (0.1725) < OVR→OVR (0.2269)`.
- Observed-range mismatch (CAT→OVR)? OVR TEST outside CAT TRAIN range **0/6 = 0.000**.
- Observed-range mismatch (OVR→CAT)? CAT TEST outside OVR TRAIN range **5/6 = 0.833**.
- CAT/OVR own-decision accuracy (secondary)? **1.000 / 0.667** (not matched).
- OVR non-simplex behavior? sums in `[0.912, 2.076]`, 2/15 items with more than
  one candidate over 0.5.

**Human Research Gate decision: PENDING**

This report does not declare "proceed to R3", does not declare "abandon the
topic", and does not declare the thesis validated.

## 16. Reproducibility

- Raw artifact: `results/frozen-decision-cat-ovr-qwen35-2b.json`
  (`sha256 = 7b65e8085f3fe38d76f23ad50fc03c19b633cf872717c126e41115770dd66354`,
  `plan_fingerprint = 37aeb0862f89931207d2c60bcb9f41fac9ad6e05a254e94dd17822c232e6571e`,
  `paired_dataset_fingerprint = 46c9ed1353d71b87b21ded8cb81fb8f06bc6c1d6ab832fbbc1b5ffdb24b3582c`).
  The raw artifact is frozen evidence: this analysis round did not modify it.
- Analysis artifact: `results/frozen-decision-cat-ovr-qwen35-2b-analysis.json`.
- The analysis artifact is a deterministic function of the raw artifact plus the
  research harness (`analysis.py`) and can be regenerated from the raw evidence
  alone, with no model and no network:

  ```
  uv run python experiments/calibration_transport/analysis.py \
    results/frozen-decision-cat-ovr-qwen35-2b.json
  ```

  Regeneration re-checks the plan and paired-dataset fingerprints against the
  recorded lineage and fails closed on any mismatch. Running it twice on the same
  raw artifact produces byte-identical output. The report is not the only data
  source.
