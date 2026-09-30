# R4 Inference Implementation Provenance Closure

**Status:** `IMPLEMENTATION PROVENANCE CLOSURE CANDIDATE = PASS` (pending human / ChatGPT review)

This artifact records the provenance closure of the R4 inference + multiplicity
implementation: the frozen semantics it implements, the two commits that carry it, the
dependency-isolation amendment, and the evidence that no frozen semantic value changed.

It is a provenance record only. It is **not** a formal R4 execution authorization, not a
model-selection decision, and not a predictor freeze.

---

## 1. Frozen authority identities

```text
R4 inference freeze fingerprint   dcbb7ac9e931145fdee86ab984de1249c1b86ca36ee735b70dafc8cabc06c141
R4 inference candidate fingerprint 5e10be53c8151d10992b70f4940d0e6f6a7aa83dfe4d5cd49e62b485b0c5e267
R3 protocol fingerprint           3ef63056ae16b18ad65d9c87d1fbec5b43550873a0e3e25ec0a323f954ee974d
```

Frozen family sizes (unchanged): primary 12, secondary extension 8, secondary
direction-difference 6, secondary native-reference 12.

Frozen confirmatory family tails (unchanged): `1/480`, `1/320`, `1/240`, `1/480`
(audit ranks 42/19959, 63/19938, 84/19917, 42/19959 at 20000 replicates).

---

## 2. Commit chain

```text
ORIGINAL_INFERENCE_IMPLEMENTATION_COMMIT  8c3bb0f0e4367bf7194f22a3f38d66aff3cbbbf7
  parent                                  8fc2f3ae465708aa12b108e838377e745e36116b
  message                                 experiments: implement R4 inference infrastructure
  paths (exactly 3)                       experiments/calibration_transport/r4_inference.py
                                          tests/test_r4_inference.py
                                          experiments/calibration_transport/R4_INFERENCE_IMPLEMENTATION_ENGINEERING.md

FREEZE_COMMIT                             8fc2f3ae465708aa12b108e838377e745e36116b
  parent                                  2ef9d31cda96dfc3bb326625dad0df061bb7063e
  message                                 docs: freeze R4 inference and multiplicity semantics
  paths (exactly 2)                       experiments/calibration_transport/R4_INFERENCE_MULTIPLICITY_FREEZE.json
                                          experiments/calibration_transport/R4_INFERENCE_MULTIPLICITY_FREEZE.md

CANDIDATE_COMMIT                          2ef9d31cda96dfc3bb326625dad0df061bb7063e
  parent                                  5185f5044fdccf0d976f953a0ff2d6c93c91a08a
  message                                 experiments: specify R4 inference and multiplicity semantics
```

`git show --format=fuller --name-status` on both commits confirms the exact path sets
above. The earlier report line "3 files changed ... 2 files" was a **REPORTING TYPO
ONLY**; the freeze commit has exactly the two freeze paths.

---

## 3. Dependency-isolation amendment

**Old issue.** `run_panel_test_bootstrap` assembled the extension and native-reference
panels by indexing `panel_values[(direction, procedure)]` for every procedure in
`ALL_PROCEDURES` after the replicate loop, so a caller that omitted `I-isotonic` /
`B-beta` raised a raw `KeyError`.

**Scientific reason.** The frozen dependency doctrine is that primary logistic-core
inference depends only on the four continuity procedures; `I-isotonic` / `B-beta` are a
standalone secondary extension. An unavailable extension must not fail an otherwise
complete primary block, and a secondary failure must not silently shrink a multiplicity
family. Conversely an unavailable core procedure must block only dependent hypotheses.

**New behaviour.** Availability is derived from what was actually computed. The primary
12 and direction-difference 6 are built iff all four core procedures are present; the
extension 8 contains only computed standalone procedures; the native-reference family
keeps all 12 members with unavailable ones marked `INCOMPLETE`.

**Domain states / errors.** `DependencyUnavailable(R4InferenceError)` with
`code = "DEPENDENCY_UNAVAILABLE"` and `family` / `dependency` attributes. It is not a
`KeyError` subclass, so expected scientific incompleteness
(`isinstance(exc, DependencyUnavailable)`) is machine-distinguishable from a programming
bug (`isinstance(exc, KeyError)`). No formal API path leaks a raw `KeyError`.

**Family behaviour.** `PanelBootstrapResult.family_status()` reports every frozen member
as `COMPLETE` / `INCOMPLETE` against the frozen sizes; `_family_block` raises
`BootstrapContractViolation` if a declared member count ever differs from the frozen
size, so a family can never silently shrink.

---

## 4. Final file identities

| Path | Lines | SHA256 |
| --- | --- | --- |
| `experiments/calibration_transport/r4_inference.py` | 2368 | `44f8ac3fe3ca0e138beb4f755e9ee65582ed0b09c14ba253bb01062d8ffda554` |
| `tests/test_r4_inference.py` | 2249 | `65eb099b48f3e37296efe30cd44275a2b9b1ba56e3e3b304e161c5ca45d7d0fa` |
| `experiments/calibration_transport/R4_INFERENCE_IMPLEMENTATION_ENGINEERING.md` | 711 | `7c391f87662e0ebbb4bb4bddd792520e544e0133067d0a6dac5df4de92942151` |
| `experiments/calibration_transport/R4_INFERENCE_MULTIPLICITY_FREEZE.json` | 1278 | `fdc07904056fd72bdd702e275743839eea741364324bd169ec2bf97504a45ad1` |
| `experiments/calibration_transport/R4_INFERENCE_MULTIPLICITY_FREEZE.md` | 593 | `a08b8c14d462a348ce6be4d46513f9703126f313758d334e05c085661075cf88` |

The two freeze artifacts are **byte-for-byte unchanged** from the freeze commit.

The amendment commit (`experiments: harden R4 inference dependency isolation`) records
the four changed/added paths; its SHA is recorded in the final report rather than here,
because this file is one of the committed paths and cannot contain its own commit hash.

---

## 5. Tests

```text
python -m py_compile r4_inference.py tests/test_r4_inference.py   exit 0
ruff check r4_inference.py tests/test_r4_inference.py             All checks passed! exit 0
pytest tests/test_r4_inference.py  (run 1)                        115 passed
pytest tests/test_r4_inference.py  (run 2)                        115 passed
pytest tests/test_r4_calibration_families.py                       53 passed
pytest (full repository)                                           2089 passed, 4 skipped, exit 0
git diff --check                                                   exit 0
```

Dependency-isolation regression tests:

- `test_primary_bootstrap_does_not_require_extension_procedures`
- `test_extension_incompleteness_does_not_block_primary`
- `test_missing_core_blocks_primary_but_not_complete_extension`
- `test_native_reference_preserves_fixed_family_when_member_incomplete`
- `test_missing_dependency_uses_domain_state_not_keyerror`

Percentile representation test: `test_refit_level_representation_is_normalization_only`
asserts `Fraction(1,40) == 0.025`, `Fraction(1,2) == 0.5`, `Fraction(39,40) == 0.975`,
the n=2000 refit ranks 50 / 1000 / 1950, and that the confirmatory tail `Fraction(1,480)`
is rank 42 of 20000 — a representation normalization only, with no frozen semantic change.

No test was deleted; the previous 109 inference tests and 53 calibration tests all remain.

---

## 6. Determinism

```text
STATE_SHA256         = 07b37954eeb4e4b1a920de10b06cc18727d70c1c6b0afe2d370184a13b66c83a
ARTIFACT_FINGERPRINT = 691e91222c36ec68ff4ed3f45eebff9536ef89e4ca28b296a0612d82c3c96dcf
CANONICAL_BYTES      = 25381
```

Identical to the pre-amendment probe, and identical across two separate processes. The
probe payload exercises `primary_interval`, `extension_interval`, `direction_interval`
and `native_interval` for every frozen member with all six procedures present; because
the amendment only changes behaviour when a dependency is absent, the sampling identity
and every numerical result are unchanged.

---

## 7. Outcome firewall

This closure read no study outcome: no real CAT/OVR probability, no fitted calibration
state, no Brier result, no LogLoss result, no transport delta and no predictor value. No
model was loaded, no dataset was downloaded and no GPU was opened. No real 20000-replicate
bootstrap and no real 2000-replicate TRAIN refit were executed. Every fixture is synthetic.

---

## 8. Formal execution status

```text
R4 INFERENCE + MULTIPLICITY SEMANTIC FREEZE = FROZEN
R4 INFERENCE IMPLEMENTATION ENGINEERING = PASS (synthetic-only)
R4 INFERENCE IMPLEMENTATION PROVENANCE CLOSURE CANDIDATE = PASS
FORMAL R4 INFERENCE EXECUTION = NOT AUTHORIZED
```

Human / ChatGPT review is still required before any formal execution.
