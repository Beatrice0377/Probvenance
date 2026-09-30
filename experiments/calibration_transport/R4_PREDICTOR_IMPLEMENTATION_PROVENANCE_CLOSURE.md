# R4 Target-Label-Free Predictor — Implementation Provenance Closure Candidate

Status: `IMPLEMENTATION PROVENANCE CLOSURE CANDIDATE`
Closure verdict: `IMPLEMENTATION PROVENANCE CLOSURE CANDIDATE = PASS`

This artifact records the provenance of the R4 target-label-free predictor
**implementation engineering** work. It is a candidate closure: the human /
ChatGPT scientific review has not yet confirmed it, and the final integrated R4
protocol is not frozen.

```text
R4 PREDICTOR SEMANTICS = FROZEN
R4 PREDICTOR IMPLEMENTATION ENGINEERING = COMPLETE
R4 FINAL INTEGRATED PROTOCOL = NOT YET INTEGRATED
FORMAL R4 EXECUTION = NOT AUTHORIZED
```

---

## 1. Frozen authority inputs

| Authority | Identity | Verified |
| --- | --- | --- |
| Predictor candidate artifact | `R4_PREDICTOR_SEMANTIC_CANDIDATE.json` sha256 `31aa9e0b4bf1a95fddd4cad3250ffe3cbb27fb9ac334129c19e020f791f6bcce` | yes |
| Predictor candidate document | `R4_PREDICTOR_SEMANTIC_CANDIDATE.md` sha256 `b82e87c4b2ce8142bd7d9dd7fa8d8c9cb1a46e901625f6a4289c001c50cd3bef` | yes |
| Predictor candidate fingerprint | `d3625912fadb5e6c68e20495256aa1f90b53686f13c9d25d1eb9ceb212dfbb06` (recomputed from payload minus `candidate_fingerprint`) | yes |
| Predictor candidate commit | `ed2ba62ffdae7b1c9890682e3550b54021df6c99` | yes |
| Predictor freeze artifact | `R4_PREDICTOR_FREEZE.json` sha256 `423c5cdaf68ce7cdbbb80cf704ed18f67692995e418d0dc8f707871322554f8c` | yes |
| Predictor freeze fingerprint | `c856fcc161910497a3431593639606682905adcb50fc443455468dfc295d73a9` | yes |
| Predictor freeze commit | `bc2562104a7e84b52aaf76fec613b874c431760d` | yes |
| Predictor freeze semantic equivalence | `EXACT_SEMANTIC_EQUIVALENCE`, differing keys `[]` | yes |
| Population freeze | `R4_POPULATION_FREEZE.md` sha256 `850b6b24da61f416b76d0bac83a4ba2775d3002e94894f003fd2e0a5488fee2a` | yes |
| Calibration-family freeze | `R4_CALIBRATION_FAMILY_FREEZE.md` sha256 `1fd06ad4804cb64cd9220cc86187e26f6d690fba977bd76918e057bab418cdff` | yes |
| Calibration scientific fingerprints | I-isotonic `cd13bc07bf92f3375bcd16d57fa5f515cd40f68199b57181791f85c58be8c244`, B-beta `f4b710fb98f7c3056794aa709d53309f462a8f598cef8089d2f9c0ed6f7e37ff` | yes |
| Inference freeze artifact | `R4_INFERENCE_MULTIPLICITY_FREEZE.json` sha256 `fdc07904056fd72bdd702e275743839eea741364324bd169ec2bf97504a45ad1` | yes |
| Inference freeze document | `R4_INFERENCE_MULTIPLICITY_FREEZE.md` sha256 `a08b8c14d462a348ce6be4d46513f9703126f313758d334e05c085661075cf88` | yes |
| Inference freeze fingerprint | `dcbb7ac9e931145fdee86ab984de1249c1b86ca36ee735b70dafc8cabc06c141` | yes |
| Inference implementation provenance closure | `R4_INFERENCE_IMPLEMENTATION_PROVENANCE_CLOSURE.md` sha256 `22f7f93c742cb7c1b1865c133e635b5e6903d6e879f4e5693bc1eaf2e28438df` | yes |
| Inference amendment commit | `bdaa088a1f5b508c47875039d2cf2be5df1595a1` | yes |
| R3 protocol fingerprint | `3ef63056ae16b18ad65d9c87d1fbec5b43550873a0e3e25ec0a323f954ee974d` | yes |

---

## 2. Commit chain

```text
PREDICTOR_IMPLEMENTATION_COMMIT   (this work)
  -> bc2562104a7e84b52aaf76fec613b874c431760d   docs: freeze R4 target-label-free predictor semantics
  -> ed2ba62ffdae7b1c9890682e3550b54021df6c99   experiments: specify R4 target-label-free predictor semantics
  -> bdaa088a1f5b508c47875039d2cf2be5df1595a1   experiments: harden R4 inference dependency isolation
  -> 8c3bb0f0e4367bf7194f22a3f38d66aff3cbbbf7   experiments: implement R4 inference infrastructure
  -> 8fc2f3ae465708aa12b108e838377e745e36116b   docs: freeze R4 inference and multiplicity semantics
  -> 2ef9d31cda96dfc3bb326625dad0df061bb7063e   experiments: specify R4 inference and multiplicity semantics
```

Entry gate (verified before any PHASE B write):

```text
branch                    main
HEAD                      ed2ba62ffdae7b1c9890682e3550b54021df6c99
HEAD^                     bdaa088a1f5b508c47875039d2cf2be5df1595a1
origin/main               2ef9d31cda96dfc3bb326625dad0df061bb7063e
raw behind/ahead          0 / 4
normalized ahead/behind   4 / 0
worktree                  clean
origin/main ancestor      exit 0
```

---

## 3. Implementation file identities

| Path | Lines | SHA256 |
| --- | --- | --- |
| `experiments/calibration_transport/r4_predictor.py` | 1162 | `ccbfbbd681cf55d0cb1f7d3f12ba19e5cd68aa4c65d0ebf52045dc8f0fb2787e` |
| `tests/test_r4_predictor.py` | 1062 | `f6282b624988a55777be5410b5e6c3d2b50d1f0706c5db0b492a316f7bcfd040` |
| `experiments/calibration_transport/R4_PREDICTOR_IMPLEMENTATION_ENGINEERING.md` | 476 | `93db1636ae250e2fc28058f288a52f414c8ec67d240a6988d83f7a40ab5ebbc9` |

No file under `src/probvenance/*` was modified.

---

## 4. Frozen-identity continuity

* The implementation module hard-codes `PREDICTOR_FREEZE_FINGERPRINT`
  `c856fcc1…`, `PREDICTOR_CANDIDATE_FINGERPRINT` `d3625912…` and
  `R4_INFERENCE_FREEZE_FINGERPRINT` `dcbb7ac9…`.
* A test re-derives the freeze fingerprint from
  `R4_PREDICTOR_FREEZE.json` payload minus `freeze_fingerprint`.
* A test asserts the inference freeze fingerprint equals the value stored in
  `R4_INFERENCE_MULTIPLICITY_FREEZE.json`.
* A test asserts the candidate semantic payload equals the freeze
  `frozen_semantic_payload` exactly and that the recorded audit result is
  `EXACT_SEMANTIC_EQUIVALENCE` with no differing keys.
* The freeze document is scanned for the frozen predictor ids, outcome ids,
  validation protocol id, the undefined-constant-input state and the verbatim
  fixed-panel inferential-scope statement.

---

## 5. Tests

```text
python -m py_compile experiments/calibration_transport/r4_predictor.py \
                       tests/test_r4_predictor.py          exit 0
ruff check               experiments/calibration_transport/r4_predictor.py \
                         tests/test_r4_predictor.py        All checks passed!
pytest -q tests/test_r4_predictor.py                      69 passed  (run twice)
pytest -q tests/test_r4_inference.py                      115 passed
pytest -q tests/test_r4_calibration_families.py           53 passed
pytest -q                                                 2158 passed, 4 skipped
git diff --check                                          exit 0
```

---

## 6. Determinism

A temporary cross-process probe (not a deliverable) built a fully synthetic
predictor state — 16-unit panel, X values, outcome summaries, a 50-replicate
bootstrap interval, the validation audit, the secondary statistics and the
artifact skeleton — and printed its canonical SHA256. Two independent processes
produced identical output:

```text
PREDICTOR_SYNTHETIC_STATE_SHA256 = b053f1dc49c1d7cea1c52fccc3a4534ed7b011db9d67bc66f142576adc1f674c
ARTIFACT_FINGERPRINT             = 87e41e4a8a6b2db5109d33653d6352e934f866e28c9262443b8c9e6d491a6903
CANONICAL_BYTES                  = 3751
```

---

## 7. Static scans

* Sampling / clipping token scan on `r4_predictor.py` for
  `clip(`, `nextafter(`, `np.clip`, `random.Random`, `numpy.random`,
  `secrets.`, `time.time`, `hash(` → **no hits**.
* Label-firewall signature scan: `range_exceedance_warning` and
  `wasserstein1_warning` each accept exactly
  `(source_train_scores, target_test_scores)`.
* Label-firewall code scan: the executable body of the feature path (docstrings
  excluded via `ast`) contains none of `ground_truth`, `correctness`, `brier`,
  `logloss`, `delta_transport`, `delta_deploy`, `calibrator`.
* Import scan: stdlib plus `r4_inference` plus `probvenance.fingerprint` only —
  no `numpy`, `scipy`, `random`, `torch`, `transformers`.

---

## 8. Outcome firewall

No real R4 CAT probability, OVR probability, model logit, calibration fit,
Brier value, LogLoss value, `Delta_native`, `Delta_deploy`, `Delta_transport`,
predictor value or predictor correlation was accessed or produced. No model
load, no GPU work, no Hugging Face execution, no formal 20000-replicate
bootstrap and no formal 2000-replicate refit bootstrap was run. All fixtures are
hand-written synthetic score vectors, synthetic rows and tiny synthetic draws.

---

## 9. Closure verdict

```text
IMPLEMENTATION PROVENANCE CLOSURE CANDIDATE = PASS
```

Remaining human / ChatGPT decisions (not made here):

* confirm this provenance closure;
* decide the final integrated R4 protocol candidate;
* decide whether any further engineering layer is required before a final R4
  protocol freeze;
* decide when (and whether) formal R4 execution is authorized.
