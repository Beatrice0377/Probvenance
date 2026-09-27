# Calibration Transport — Paired Experiment-Integrity Harness (R1)

This directory implements **R1**, the paired experiment-integrity harness for the
research track specified in
[`docs/research/calibration-transport-research-spec-v1.md`](../../docs/research/calibration-transport-research-spec-v1.md).

R1 protects the *structure* of a paired frozen-decision experiment. It generates
no measurements and answers no research question. Its goal is that when R2
starts producing CAT/OVR (or any other) measurement data, a researcher can no
longer silently change the anchor, the split, the item pairing, the missing
rows, or the A/B measurement identity without leaving explicit evidence.

## 1. What R1 is and is not

- It **is** experiment integrity: declared plans, explicit outcomes, deterministic
  canonical identities, and strict fail-closed validation.
- It is **not** transport analysis. It does not fit a calibrator, compute Brier
  or LogLoss transport, build a transport matrix, analyze support overlap, audit
  compatibility, or certify anything.

## 2. Frozen-decision is not the Phase 4C winner object

The frozen Phase 4C runtime measures the measurement's *own selected winner*:

```
measurement's own winner -> selected probability -> winner_correctness
```

R1 serves the research **frozen-decision** object:

```
pre-frozen anchor decision D_i -> protocol-specific score of D_i -> same anchor correctness Y_i
```

These are different statistical objects. R1 uses the research-only semantics
`fixed-decision-correctness` v1 and `fixed-decision-semantic-probability` v1; it
does **not** reuse `winner_correctness` or `uncalibrated-selected-probability`,
and it never touches the frozen production `probvenance` package.

## 3. Plan and outcomes are separated

- `PairedFixedDecisionPlan` is a pre-measurement declaration: model, population,
  ground-truth semantics reference, the two declared measurement identities, the
  anchor-selection and split-protocol identities, and every planned item with its
  frozen anchor, ground-truth value, split membership, and declared correctness
  label.
- `PairedFixedDecisionDataset` holds the explicit A/B outcomes for one exact plan.

The plan structurally does not accept A/B scores or winners, so it cannot
condition anchor selection on them at the object level.

## 4. Item IDs are paired across A/B

Items are paired by **exact `item_id`**, never by position. The same planned item
carries one frozen anchor, one `Y`, one split, one A outcome, and one B outcome.

## 5. Splits are disjoint by exact item ID

`item_id` must be globally unique across the whole plan, which mechanically
enforces `train ∩ audit = ∅`, `train ∩ test = ∅`, `audit ∩ test = ∅`. A usable
plan requires at least one `TRAIN` and one `TEST` item; `AUDIT` may be empty.

## 6. Missing and ineligible rows are preserved

Every planned item must have exactly one A outcome and exactly one B outcome. A
measurement that produced no score is recorded explicitly as `MISSING` or
`INELIGIBLE` with a non-empty reason and a source record id. Rows are never
dropped, and no `drop_missing()` / `complete_cases()` / `eligible_only()` style
analysis policy exists. Missingness and eligibility policy for confirmatory
analysis is deferred; R1 only preserves the evidence.

## 7. Winner/anchor equality is never used for filtering

Whether the frozen anchor equals `winner_A`, equals `winner_B`, equals both, or
equals neither is a post-hoc coincidence. None of these equalities invalidates,
drops, resamples, reassigns, or reweights a row. `winner_value` is diagnostic
only and never affects inclusion.

## 8. Fingerprints are structural provenance, not attestation

Both artifacts expose `canonical_payload()` and a deterministic SHA-256
`fingerprint` (plan FP v1, dataset FP v1), built on the existing
`probvenance.fingerprint` helper. Item/row order does not change a fingerprint;
A/B roles are directional and swapping them changes the fingerprint.

The plan fingerprint is structural research provenance. It does **not**
cryptographically or causally prove that the caller never peeked at A/B outcomes
before constructing the plan. R1 cannot prove a caller's independence.

## 9. Explicit non-claims

- R1 does not prove the anchor-selection mechanism really ignored A/B outcomes.
- R1 does not prove statistical independence beyond exact item-ID disjointness.
- R1 does not validate transportability, declare CAT/OVR compatible or
  incompatible, or certify any compatibility.
- R1 does not choose anchors and does not split data; it records declared
  decisions and verifies them.

## 10. Status

R1 is complete and unchanged. R2 (the tiny frozen-decision CAT↔OVR pilot) is
**implemented** in this directory but its exploratory evidence is produced only
by an actual local-model run; until that run is recorded, no empirical result
and no compatibility claim exists. Nothing beyond the research gate is started
here.

## 11. R2 — the minimal Frozen-Decision CAT↔OVR pilot

R2 is an **exploratory pilot**, not a benchmark and not confirmatory evidence.
It answers no question about which protocol is better.

Modules:

- `pilot_plan.py` — loads the frozen `choice_signal` three-way fixture, applies
  the pre-declared 9 TRAIN / 6 TEST / 0 AUDIT split, computes the deterministic
  `sha256-case-id-candidate-set-anchor` anchors, declares the synthetic
  ground-truth semantics, and builds the R1 plan. It never runs a model.
- `measurements.py` — the two frozen research measurement adapters and the OVR
  proposition transformation.
- `analysis.py` — research-only eligibility, the L2 logistic calibrator, the
  2×2 Brier/LogLoss matrices, empirical transport excess risk, and descriptive
  diagnostics.
- `run_pilot.py` — the fixed orchestration pipeline (`--plan-only` prints the
  plan without a model). The official run pins `Qwen/Qwen3.5-2B` to revision
  `15852e8c16360a2fea060d615a32b45270f8a8fc` and loads it offline
  (`local_files_only=True`); an unpinned revision is rejected.

Frozen measurement identities:

- `direct-categorical-anchor-probability` v1 (CAT): ``S_CAT =
  probabilities[anchor]``, never the categorical winner's mass.
- `independent-binary-anchor-probability` v1 (OVR): ``S_OVR = p_true(anchor)``
  from one independent binary judgment per candidate. The OVR scores are **never
  renormalized**: they are not a categorical distribution and need not sum to 1.

Both scores are for the SAME pre-frozen anchor ``D_i``; neither is that
measurement's own winner score. The research target/inputs are
`fixed-decision-correctness` v1 and `fixed-decision-semantic-probability` v1,
which are deliberately NOT `winner_correctness` or
`uncalibrated-selected-probability`.

Paired-fit eligibility is frozen before results: a row is eligible iff BOTH
measurements are `SCORED`. Winner agreement, anchor/winner equality, score
magnitude, label mass, and ground-truth class never affect inclusion. The pilot
uses one model (`Qwen/Qwen3.5-2B` pinned to revision
`15852e8c16360a2fea060d615a32b45270f8a8fc`), one pre-declared `l2_strength = 0.01`, one
split, and one anchor protocol, with no sweep and no fallback.

## 12. R2B — the stability / deconfounding round

R2B asks whether the directional transport structure R2A saw was mostly an
artifact of fitting two calibrators on nine rows and evaluating them on six. It
is still exploratory: it was designed after R2A, so it is not confirmatory
evidence.

- `r2b_cases.json` — 150 hand-written three-way cases: 3 categories x 5 declared
  strata x 10 items, with opaque `r2b-0001..r2b-0150` ids. The 5 strata are
  declared synthesis styles, not a difficulty score; no case is intentionally
  ambiguous.
- `r2b_plan.py` — loads and structurally validates the fixture, applies the
  pre-declared 6-train/4-test-per-cell split (90/60/0), reuses the SAME R2A
  anchor function, and reuses the R2A ground-truth semantics. It never rebalances
  the anchor or the split.
- `r2b_provenance.py` — the run-level parent identity: it commits the source
  case-set content fingerprint (so question/context/description changes change
  the run identity), the plan, the model, both measurement identities, the
  protocols, the research target/input-score ids, and the pre-measurement git
  commit + clean tree. No wall-clock timestamp is part of the identity.
- `r2b_stability.py` — full-N 2x2 Brier/LogLoss, raw-relative changes, the
  observed-range diagnostics and loss decomposition, descriptive per-stratum
  summaries, and two pre-declared DETERMINISTIC bootstraps: a paired test
  bootstrap (2000 replicates, exploratory percentile intervals — not confidence
  intervals, no p-values) and a paired train-refit bootstrap (1000 replicates,
  the same resampled training multiset for both calibrators, fail-closed on
  solver failure).
- `run_r2b.py` — the fixed orchestration pipeline. The official run pins
  `Qwen/Qwen3.5-2B` to revision `15852e8c16360a2fea060d615a32b45270f8a8fc`, loads
  it offline (`local_files_only=True`), and FAILS CLOSED if the git working tree
  is dirty before the first score.

R2B inherits every frozen R2A dimension unchanged: model, revision, dtype,
rendering (`enable_thinking=false`), CAT v1, OVR v1, the OVR proposition, the
anchor protocol, the research L2-logistic method, and `l2_strength = 0.01`. It
adds no method sweep, no second model, and no second measurement axis.

## 13. R2C — the calibration-method adequacy sensitivity

R2C asks one narrow question, offline and analysis-only, from the frozen R2B raw
evidence: is the observed native-calibration degradation specific to the frozen
`raw-p logistic + lambda = 1e-2` configuration, or does it persist across a
pre-declared, narrow sensitivity set? It NEVER reruns the model, never touches
the network or GPU, and never regrids after seeing results.

- `r2c_method_adequacy_design.json` — the pre-analysis declaration. It pins the
  frozen R2B raw artifact path and SHA256, the source identities, the two
  families, the exact five-value lambda grid, the two bootstrap contracts, and a
  `no_model_rerun` declaration.
- `r2c_method_adequacy.py` — the analysis. Family `P` is the existing raw-p
  logistic (`sigmoid(a*p + b)`); Family `L` is the same solver on the
  logit feature (`sigmoid(a*logit(p) + b)`), which fails closed on exact 0/1
  endpoints with no clipping or smoothing. Both reuse the production kernels
  `_solve_l2_logistic` and `_stable_sigmoid` without touching `src/`. It reports
  native Brier change vs raw, the 2x2 transport matrices and deltas,
  cross-vs-raw changes, exact LogLoss (no clipping), a shared paired TEST
  bootstrap (2000) and a shared paired train-refit bootstrap (1000), parameter
  stability, and transport-sign counts across all ten configurations. A refit
  that the reused solver cannot certify is recorded per measurement/replicate
  and the affected configuration's train-refit block is marked `failed` with no
  interval computed over the surviving replicates (PART 36 fail-closed); the
  round status becomes `incomplete`.
- `tests/test_r2c_method_adequacy.py` — locks the exact grid, the Family L
  identity-map property, endpoint rejection, artifact determinism, and the exact
  reproduction of the committed R2B `P:0.01` configuration.

R2C selects no method: it reports facts for a later human research gate.

## 14. R2C.1 — the low-regularization numerical closure

R2C.1 answers exactly one follow-up question about the frozen R2C evidence: were
the 15 `lambda = 1e-6` train-refit fits that the reused binary64 solver could not
certify a pathology of the objective, or a numerical limitation of the frozen
binary64 solver path (the objective being well-defined and high-precision solvable,
with a certifiable binary64 point that the frozen path does not uniformly reach)?
It resolves to the second: the predeclared A/B/C/D taxonomy had **no exact match**,
the closest family is A, and the preregistered A submechanism was falsified. It adds
NO data, model, GPU, network, lambda, or calibration family, and it does not modify
`src/`.

- `r2c1_numerical_closure_design.json` — the pre-analysis declaration. It pins the
  frozen R2B raw and R2C analysis artifacts by SHA256, the exact 15-failure set,
  the reference-solver contract (stdlib `decimal`, 80 digits, `ROUND_HALF_EVEN`,
  objective-gap tolerance `1e-24`, fixed zero start), the all-4000-fit reference
  policy, the cross-implementation agreement gate, and the rounded-reference and
  ULP-neighbourhood diagnostics.
- `r2c1_numerical_closure.py` — an independent, dependency-free Decimal reference
  optimizer for the exact same objective (`mean Bernoulli NLL + lambda/2 * (a^2 +
  b^2)`) with its own 2x2 Newton solve, Armijo backtracking line search, and
  strong-convexity objective-gap certificate. It reuses the production binary64
  kernel only to reproduce production behaviour (the agreement gate and the
  rounded-reference certificate diagnostics). Feature values are the exact
  binary64 R2C features (`Decimal.from_float` of the R2C float feature), so only
  the optimizer arithmetic changes.
- `tests/test_r2c1_numerical_closure.py` — locks the exact known optimum, agreement
  with the production solver on an ordinary lambda, the exact binary64 feature
  semantics for both families, deterministic bootstrap replay, the frozen
  15-failure set / source lineage, the numerical-projection immutability check, and
  the preregistered-vs-observed classification rules.

R2C.1 is a **numerical reference backend, not a new calibration family, not a new
R2C configuration, and not an R3 candidate**. It selects no method and authorizes
no R3 work; its evidence is recorded in `R2C1_REPORT.md`.

## 15. Running the tests

No model, no GPU, and no network are required:

```
uv run pytest experiments/calibration_transport/tests
```
