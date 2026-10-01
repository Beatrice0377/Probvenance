# R4 — Reference-vs-Fast Kernel Numerical Equivalence (PHASE F)

```text
STATUS: FAIL
R4 FAST-KERNEL NUMERICAL EQUIVALENCE = FAIL
FAST-KERNEL EXECUTION ENVIRONMENT = NOT ADOPTED
R4 EXECUTION READINESS — EPOCH 1 = BLOCKED
```

This document is an **outcome-blind operational artifact**. It contains no R4 study
item, no ground truth, no study probability, no calibration fit, no risk estimate,
no bootstrap, and no predictor value. Everything below was produced from an
**invented synthetic battery** pushed through the *production* measurement
primitives. No threshold in this document was changed after a result was seen.

---

## 1. Why this gate exists

Epoch 0 of the formal R4 raw measurement was aborted for a predeclared
operational performance reason (see `R4_FORMAL_EXECUTION_EPOCH0_ABORT_RECEIPT.md`)
and quarantined as `DO_NOT_USE`. The proposed remedy was an isolated fast-kernel
execution environment (`probvenance-r4-fast`) that activates the optional
`causal_conv1d` / `mamba_ssm` / `flash-linear-attention` kernels used by the
hybrid (SSM) architectures.

Adopting that environment would silently change the numbers that the frozen R4
protocol treats as raw evidence. Therefore the amendment predeclared a numerical
equivalence gate **before** any fast-kernel result was observed, and required a
STOP on any exceedance.

## 2. Predeclared thresholds (fixed in advance, never relaxed)

| Quantity | Threshold |
| --- | --- |
| all values finite | required |
| max abs restricted-probability difference | ≤ 0.005 |
| max abs designated-score difference | ≤ 0.005 |
| max abs centered restricted-logit difference | ≤ 0.10 |
| per-distribution total variation distance | ≤ 0.01 |

`centered logit` = natural log of each restricted verbalizer probability, minus
the mean over the four restricted candidates. `designated score` = the CAT anchor
probability and the OVR designated `probability_true` (the max of the two is
reported per item).

## 3. Synthetic battery

* `BATTERY_ID = "r4-fast-kernel-synthetic-equivalence-battery"`, version 1
* 12 invented items, tags: `short-plain`, `medium-narrative`, `long-descriptive`,
  `repeated-tokens`, `punctuation-heavy`, `yes-no-neutral`, `numeric`,
  `mixed-case`, `whitespace-dense`, `dashes-and-digits`, `dialogue`, `abstract`
* anchors balanced `option-0/1/2/3` × 3
* `battery_fingerprint = c1e9d6488ec68cb44afb4d32d7468dc6b4acb70822f8f019389183cc1e4699bd`
  (identical in both captures)
* forbidden-marker guard rejects any battery text mentioning a study dataset

Per item the probe performs exactly 2 logical forwards (1 CAT + 1 designated-only
OVR) through the production primitives
`measurements.build_cat_decision` / `build_ovr_proposition` →
`Probvenance(backend=..., capture_rendered_input=True).evaluate_with_trace` →
`measurements.build_cat_raw_record` / `build_ovr_raw_record`.

## 4. Environments compared

| | reference | fast |
| --- | --- | --- |
| prefix | `/root/rivermind-data/envs/probvenance-r4` | `/root/rivermind-data/envs/probvenance-r4-fast` |
| python | 3.11.13 | 3.11.13 |
| torch | 2.8.0+cu128 | 2.8.0+cu128 |
| cuda | 12.8 | 12.8 |
| transformers | 5.17.0 | 5.17.0 |
| tokenizers / safetensors | 0.23.2 / 0.8.0 | 0.23.2 / 0.8.0 |
| numpy / scipy / huggingface_hub | 2.3.2 / 1.16.3 / 1.32.0 | 2.3.2 / 1.16.3 / 1.32.0 |
| triton | 3.4.0 | 3.4.0 |
| `pip freeze` packages | 183 | 188 (the 5 added acceleration packages) |
| `pip freeze` sha256 | `649b919aa26184a94c5ed56711187d4042bea112be1a531774b8405b2bdf82ba` | `0ee0b8774c0ea5258d844526b042c0c6895842cc3a50373f5055c9c593f27f54` |
| fast path active | no (torch fallback) | yes (14/14 decorated sites) |

Device `cuda:0`, dtype `bfloat16`, batch size 1, `eval()`, `inference_mode()`.
Both runs used `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1`.

Fast-path activation evidence (PHASE E, mechanical, closure-based — `__module__`
is useless because `functools.wraps` copies it from the torch fallback):

* reference env logs emit the fallback warnings
  ``falling back to its reference PyTorch implementation because `causal_conv1d` is not installed``,
  ``… because `flash-linear-attention` is not installed``,
  ``… because `mamba_ssm` is not installed``;
* the fast env logs emit **none** of them;
* the decorator closure free variable `is_new_implementation` is `False` at all
  14 sites in the reference env and `True` at all 14 sites in the fast env.

## 5. Cross-environment equivalence result

| model | affected by fast path | max prob diff | max designated diff | max centered-logit diff | max TV | status |
| --- | --- | --- | --- | --- | --- | --- |
| `olmo-3-7b-instruct` | no | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 | PASS |
| `falcon-h1-7b-instruct` | yes | 6.437e-02 | 6.437e-02 | 4.121e-01 | 6.437e-02 | **FAIL** |
| `granite-4-0-h-tiny` | yes | 1.493e-01 | 1.306e-01 | 1.062e+00 | 1.493e-01 | **FAIL** |
| `qwen3-5-9b` | yes | 3.328e-02 | 3.328e-02 | 1.875e-01 | 3.328e-02 | **FAIL** |
| `minicpm5-2b` | no | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 | PASS |
| `qwen3-5-2b` | yes | 2.976e-02 | 2.979e-02 | 1.250e-01 | 3.030e-02 | **FAIL** |

The two models with **no** fast path (`olmo-3`, `minicpm5-2b`) are **bit-identical**
across the two environments. This is a load-bearing control: it proves that the
tokenizer revision, the rendered input, the resolved verbalizer token ids, the
model revision and the measurement pipeline are identical in both environments,
so the differences for the other four models cannot be attributed to any of them.

Mechanically verified as identical across the two captures for all six models:

* `snapshot_path` and `revision` (all six pinned snapshots);
* `resolved_token_ids` for CAT (A/B/C/D) and `positive/negative_token_id` for OVR;
* `cat_rendered_input` and `ovr_rendered_input` strings;
* the `verify_verbalizers` report.

⇒ The divergence is **purely numerical**, not semantic.

## 6. Controls — is this noise or is it the kernels?

Three controls were run after the first comparison, using the same battery and
the same four affected models.

### C1 — reference vs reference repeat (reference determinism)

| model | status | max prob diff | max logit diff | max TV |
| --- | --- | --- | --- | --- |
| falcon-h1-7b-instruct | PASS | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| granite-4-0-h-tiny | PASS | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| qwen3-5-9b | PASS | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| qwen3-5-2b | PASS | 0.000e+00 | 0.000e+00 | 0.000e+00 |

The reference (torch fallback) path is **bit-exact reproducible** run to run.

### C2 — fast vs fast repeat (fast-kernel determinism)

| model | status | max prob diff | max logit diff | max TV | max designated diff |
| --- | --- | --- | --- | --- | --- |
| falcon-h1-7b-instruct | **FAIL** | 1.592e-01 | 7.451e-01 | 1.592e-01 | 6.503e-02 |
| granite-4-0-h-tiny | **FAIL** | 1.203e-01 | 4.687e-01 | 1.203e-01 | 1.750e-01 |
| qwen3-5-9b | PASS | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| qwen3-5-2b | PASS | 0.000e+00 | 0.000e+00 | 0.000e+00 | 0.000e+00 |

The `mamba_ssm` / `causal_conv1d` triton path is **non-deterministic run to run**
for Falcon-H1 and Granite-4 (`causal_conv1d` / `mamba_ssm` kernels). The
`flash-linear-attention` gated-delta-rule path used by Qwen3.5 is deterministic.

### C3 — reference repeat vs fast repeat (reproducibility of the failure)

| model | status | max prob diff | max logit diff | max TV |
| --- | --- | --- | --- | --- |
| falcon-h1-7b-instruct | FAIL | 1.137e-01 | 3.740e-01 | 1.137e-01 |
| granite-4-0-h-tiny | FAIL | 1.465e-01 | 9.688e-01 | 1.465e-01 |
| qwen3-5-9b | FAIL | 3.328e-02 | 1.875e-01 | 3.328e-02 |
| qwen3-5-2b | FAIL | 2.976e-02 | 1.250e-01 | 3.030e-02 |

The cross-environment failure reproduces. For Qwen3.5-9B the cross-environment
figure is **identical** to the first comparison (3.328e-02) — a stable,
systematic kernel-vs-reference numerical difference, not run-to-run noise.

## 7. Findings

1. **The fast path is genuinely active** in `probvenance-r4-fast` (14/14 decorated
   sites; no fallback warnings), and genuinely inactive in the reference env.
2. **Falcon-H1 and Granite-4 became non-deterministic.** Their optimized
   conv/SSM kernels change the same synthetic input to different values on two
   consecutive runs in the same process environment. A measurement contract that
   requires deterministic raw evidence cannot use a non-deterministic execution
   path.
3. **All four affected models diverge from the reference beyond the predeclared
   tolerance.** Even the two models whose fast path *is* deterministic
   (Qwen3.5-9B / Qwen3.5-2B) diverge systematically (≈3.3e-2 and ≈3.0e-2 max
   restricted-probability difference; ≈1.9e-1 and ≈1.3e-1 max centered-logit
   difference).
4. **Precision signature.** In Granite-4 `synthetic-numeric` the fast path
   produces two *exactly equal* candidate probabilities (both `0.137889`) where
   the reference produces `0.101317` vs `0.130094`. Exactly-equal probabilities
   from two different verbalizer tokens indicate that the fast path collapses
   distinct logits at a coarser precision than the reference path.

Worst per-item examples (reference → fast, restricted probability):

| model / item | candidate | reference | fast | Δ |
| --- | --- | --- | --- | --- |
| granite-4-0-h-tiny / punctuation-heavy | option-0 (anchor) | 0.159531 | 0.028974 | −0.130557 |
| granite-4-0-h-tiny / punctuation-heavy | option-3 | 0.810168 | 0.959492 | +0.149324 |
| falcon-h1-7b-instruct / numeric | option-2 (anchor) | 0.121953 | 0.186323 | +0.064370 |
| falcon-h1-7b-instruct / numeric | option-3 | 0.555165 | 0.514454 | −0.040710 |

## 8. Decision

```text
R4 FAST-KERNEL NUMERICAL EQUIVALENCE = FAIL
FAST-KERNEL EXECUTION ENVIRONMENT = NOT ADOPTED FOR R4 EPOCH 1
R4 EXECUTION READINESS — EPOCH 1 = BLOCKED
```

Per the amendment's predeclared rules:

* the tolerance was **not** loosened;
* no failing prompt was dropped and no passing model was selected;
* no additional speculative kernel library was installed;
* `trust_remote_code` was **not** enabled;
* no quantization, no CPU offload, and no dtype change was used to force a pass;
* the formal reference environment `/root/rivermind-data/envs/probvenance-r4`
  was left byte-identical (its `pip freeze` sha256 is unchanged at
  `649b919aa26184a94c5ed56711187d4042bea112be1a531774b8405b2bdf82ba`).

PHASE G (performance qualification) was **not executed**, because the amendment
conditions it on `PHASE F = PASS`. PHASE H (fast-environment six-model preflight)
was likewise not executed. No Epoch 1 study row was executed.

The next decision belongs to the human reviewer. The two mechanically available
options are:

* **A** — run formal R4 Epoch 1 on the *frozen reference* environment (the torch
  fallback path), accepting the throughput that caused the Epoch 0 abort; or
* **B** — amend the predeclared numerical-equivalence contract (for example,
  separately qualify a deterministic subset, or re-predeclare thresholds with an
  explicit scientific justification) and re-run PHASE F before any Epoch 1 row.

This artifact does not choose between them.

## 9. Evidence artifacts (synthetic only)

Retained outside the repository at `/root/rivermind-data/r4-fast-kernel-equivalence/`:

| file | sha256 |
| --- | --- |
| `reference-capture.json` | `b1ae921cc6c6cf2c80bb84853e171d34d296a2f1a983945e8c76e80c1c15354b` |
| `fast-capture.json` | `c21701932c80fa0113777a496e9986c0876a7e2e409e181a9fa707d35a059d07` |
| `reference-capture-repeat.json` | `abaf4fa270b1c7744aa50fa74d03312754a6a7b3493158deb79770f1edf43d32` |
| `fast-capture-repeat.json` | `822b34e1d656fcd6697e20c5c79a77cb5900f914e9428123424f477953d06233` |
| `equivalence-comparison.json` (C0, FAIL) | `3e4691973ece3e6381790bcf335788c9d5e84f857e2ca7cc47ce25847408476d` |
| `cmp-ref-vs-refrepeat.json` (C1, PASS) | `f02065ad48d32cf9e2359f03edf841450c311c15b1acdb2d63e7aa4c91107c2d` |
| `cmp-fast-vs-fastrepeat.json` (C2, FAIL) | `1412e1c0a9693399740d3715e399d4ccf476889eec860cf8cd2623c4421bd33d` |
| `cmp-refrepeat-vs-fastrepeat.json` (C3, FAIL) | `48d13994f4c0a66d89dab2a77f9f6f9b7337418e08dfb48a95b4bc01af812936` |

Harness: `experiments/calibration_transport/fast_kernel_equivalence_probe.py`
(sha256 `b7faaf248d1410f0301a5e3cb4f36497526835bb1904d724d24df6e36b2f214c`).

## 10. Open items

* Human decision between option A and option B above.
* If option B is chosen, a new amendment must be predeclared and reviewed before
  any threshold is touched.
* PHASE G / H remain unexecuted by design.
* Formal R4 Epoch 1 execution remains **NOT AUTHORIZED**.
