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

R1 only. R2 (the tiny frozen-decision CAT↔OVR pilot) is **not implemented**, and
nothing beyond the research gate is started here.

## 11. Running the tests

No model, no GPU, and no network are required:

```
uv run pytest experiments/calibration_transport/tests
```
