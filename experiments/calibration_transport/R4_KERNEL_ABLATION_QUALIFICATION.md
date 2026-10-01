# R4 — Bounded Kernel Ablation: Qualification (PHASE O)

```text
STATUS: COMPLETE
QUALIFIED ACCELERATION = NONE
PREDECLARED NUMERICAL THRESHOLDS = UNCHANGED
ALL-REFERENCE EXECUTION REMAINS THE ONLY QUALIFIED PATH
EPOCH 1 REAL STUDY ROWS EXECUTED = 0
```

Companion machine-readable artifact:
`experiments/calibration_transport/R4_KERNEL_ABLATION_QUALIFICATION.json`
(`qualification_fingerprint 1f5ebeceaee5b18d5a23be700ee049e76deb6d121749a75a2e17af649c98a556`).
Selection rule was predeclared in
`experiments/calibration_transport/R4_KERNEL_ABLATION_SELECTION_CONFIG.json`
before any benchmark result existed.

---

## 1. Scope

This is an **outcome-blind operational qualification**. It contains no study
item, no ground truth, no study probability, no calibration fit, no risk
estimate, no bootstrap and no predictor value. Every number below comes from an
**invented synthetic battery** pushed through the production measurement
primitives. No scientific semantic was changed and no frozen artifact was
touched.

## 2. Synthetic battery (reused unchanged)

| field | value |
| --- | --- |
| `battery_id` | `r4-fast-kernel-synthetic-equivalence-battery` |
| version | 1 |
| `battery_fingerprint` | `c1e9d6488ec68cb44afb4d32d7468dc6b4acb70822f8f019389183cc1e4699bd` |
| items | 12 (anchors balanced `option-0..3` × 3) |
| per item | 2 logical forwards (1 CAT + 1 designated-only OVR) |
| study rows | 0 |

Rendered text, resolved verbalizer token ids, plan/decision fingerprints and
model snapshots were mechanically verified identical across all environments;
the tokenization-identity gate did not fire.

## 3. Immutable thresholds (unchanged, never relaxed)

| quantity | threshold |
| --- | --- |
| all values finite | required |
| max abs restricted-probability difference | ≤ 0.005 |
| max abs designated-score difference | ≤ 0.005 |
| max abs centered restricted-logit difference | ≤ 0.10 |
| per-distribution total variation distance | ≤ 0.01 |

## 4. Candidate environments

| id | added packages | activation |
| --- | --- | --- |
| `R0` | — | none (pure torch fallback) |
| `C1` | `causal-conv1d==1.7.0` | conv1d fast on Falcon/Granite/Qwen3.5 |
| `C2` | `causal-conv1d==1.7.0`, `mamba-ssm==2.3.1` | **degenerate — identical to C1** |
| `C3` | `causal-conv1d==1.7.0`, `flash-linear-attention==0.5.2`, `fla-core==0.5.2`, `einops==0.8.2` | conv1d + FLA fast on Qwen3.5 |
| `F0` | all five | historical control, `REJECTED_AND_REMAINS_REJECTED` |

`C2` is `INELIGIBLE / DIAGNOSTIC_ONLY / NOT_SELECTABLE` by explicit human
adjudication: `mamba_ssm` cannot be imported without `einops`, and `einops` was
not in the declared C2 package set, so C2 never activates a mamba kernel and is
numerically indistinguishable from C1.

## 5. Repeatability (PHASE C) — 3 independent fresh processes per cell

| candidate | model | worst pairwise difference | status |
| --- | --- | --- | --- |
| `R0` | falcon-h1-7b-instruct | 0.000e+00 | PASS |
| `R0` | granite-4-0-h-tiny | 0.000e+00 | PASS |
| `R0` | qwen3-5-9b | 0.000e+00 | PASS |
| `R0` | qwen3-5-2b | 0.000e+00 | PASS |
| `C1` | falcon-h1-7b-instruct | 0.000e+00 | PASS |
| `C1` | granite-4-0-h-tiny | 0.000e+00 | PASS |
| `C1` | qwen3-5-9b | 0.000e+00 | PASS |
| `C1` | qwen3-5-2b | 0.000e+00 | PASS |
| `C2` | falcon-h1-7b-instruct | 0.000e+00 | PASS |
| `C2` | granite-4-0-h-tiny | 0.000e+00 | PASS |
| `C3` | qwen3-5-9b | 0.000e+00 | PASS |
| `C3` | qwen3-5-2b | 0.000e+00 | PASS |

All three repeat captures per candidate are **byte-identical**
(`R0 abaf4fa2…`, `C1 0d684f2e…`, `C2 1b3e08aa…`, `C3 31e49150…`).

**Determinism diagnosis.** Every candidate environment is bit-exact
reproducible run to run. The non-determinism observed in the previously rejected
full-stack environment `F0` for Falcon-H1 and Granite-4 is therefore **localized
to the `mamba_ssm` activation pattern**: `mamba_ssm` is absent from C1, whose
repeats are byte-identical, and present in F0, whose repeats were not.

## 6. Numerical equivalence (PHASE D) — reference `R0` vs candidate

| candidate | model | max prob | max designated | max centered logit | max TV | status |
| --- | --- | --- | --- | --- | --- | --- |
| `C1` | falcon-h1-7b-instruct | 1.471892e-01 | 1.501828e-02 | 4.097290e-01 | 1.484454e-01 | **FAIL** |
| `C1` | granite-4-0-h-tiny | 1.029240e-01 | 1.029240e-01 | 5.937500e-01 | 1.029240e-01 | **FAIL** |
| `C1` | qwen3-5-9b | 2.762545e-02 | 2.762545e-02 | 1.562500e-01 | 3.092484e-02 | **FAIL** |
| `C1` | qwen3-5-2b | 2.946089e-02 | 2.889553e-02 | 9.375000e-02 | 3.030166e-02 | **FAIL** |
| `C2` | falcon-h1-7b-instruct | 1.471892e-01 | 1.501828e-02 | 4.097290e-01 | 1.484454e-01 | **FAIL** |
| `C2` | granite-4-0-h-tiny | 1.029240e-01 | 1.029240e-01 | 5.937500e-01 | 1.029240e-01 | **FAIL** |
| `C3` | qwen3-5-9b | 3.327517e-02 | 3.327517e-02 | 1.875000e-01 | 3.327517e-02 | **FAIL** |
| `C3` | qwen3-5-2b | 2.975624e-02 | 2.979273e-02 | 1.250000e-01 | 3.030166e-02 | **FAIL** |

`C1` and `C2` are **numerically identical to the last digit** for Falcon-H1 and
Granite-4 — independent confirmation of the C2 degeneration.

Reference self-consistency: the fresh `R0` capture is byte-identical to the
previously frozen reference capture, and `R0` vs `R0` historical is
`PASS 0.000e+00` on all four affected models.

## 7. Diagnostic attribution (PHASE E)

* **Falcon-H1 / Granite-4** — `causal_conv1d` alone (C1) already exceeds every
  predeclared threshold. The drift is **consistent with** the `causal_conv1d`
  activation pattern; it is **not** attributable to `mamba_ssm`, which never
  activates in C1 or C2. The F0 non-determinism is **localized to** `mamba_ssm`.
* **Qwen3.5-9B / Qwen3.5-2B** — C1 (conv only) fails, and C3 (conv + FLA) also
  fails. C3's Qwen3.5-9B figure (`3.327517e-02`) reproduces the previously
  rejected full-stack figure exactly. The permitted conclusion is: **the
  FLA-containing execution candidate is not numerically eligible under the
  frozen contract** — not that FLA is wrong.
* Worst per-item examples: Granite-4 `punctuation-heavy` (prob 1.029e-01),
  `whitespace-dense` (9.485e-02); Falcon-H1 `numeric` (1.472e-01),
  `dashes-and-digits` (4.055e-02); Qwen3.5-9B `whitespace-dense` (2.763e-02);
  Qwen3.5-2B `abstract` (2.946e-02).

No claim of "proved root cause" is made anywhere.

## 8. Numerically eligible candidates (PHASE G input)

```text
olmo-3-7b-instruct   : (none — no acceleration surface)
falcon-h1-7b-instruct: (none)
granite-4-0-h-tiny   : (none)
qwen3-5-9b           : (none)
qwen3-5-2b           : (none)
minicpm5-2b          : (none — no acceleration surface)
```

**The eligible set is empty.**

## 9. Performance (PHASE F) — not executed

Adoption benchmarking of an ineligible candidate is forbidden, so **no
performance benchmark was run**. There is consequently no synthetic speed-up
ratio, and the projected relative runtime of the selected map versus
all-reference is `1.000×` by construction.

## 10. Cgroup memory envelope (PHASE F memory gate)

| field | value |
| --- | --- |
| `memory.max` | 62 277 025 792 B (58.00 GiB) |
| peak `memory.current` during captures | 53 682 606 080 B |
| minimum effective headroom observed | 36 521 357 312 B (≈34.0 GiB) |
| hard gate | 12 884 901 888 B (12 GiB) |
| status | **PASS** |

Host `/proc/meminfo` `MemAvailable` was not used (it is host-wide and
meaningless inside the container).

## 11. Predeclared selection rule — execution

The rule was frozen in `R4_KERNEL_ABLATION_SELECTION_CONFIG.json` before any
benchmark result:

```text
eligible = numerical PASS AND repeatability PASS AND performance threshold PASS AND memory PASS
empty set -> select R0, record NO QUALIFIED ACCELERATION
exactly one -> select it
multiple -> highest median synthetic rows/sec; ties within 5% -> smaller dependency set
```

Applied outcome: **empty set ⇒ every model selects `R0`.**

## 12. Decision

```text
R4 BOUNDED KERNEL ABLATION = COMPLETE
QUALIFIED ACCELERATION = NONE
PREDECLARED NUMERICAL THRESHOLDS = UNCHANGED
ALL-REFERENCE EXECUTION REMAINS THE ONLY QUALIFIED PATH
```

This is **not** a statement that any model is scientifically problematic, and
**not** a re-interpretation of the earlier failed full-stack environment, which
remains rejected. No threshold was relaxed, no failing prompt was discarded, no
prompt was added, no package version was searched for, no extra acceleration
library was installed, and `trust_remote_code` was not enabled.

## 13. Open decision for the human reviewer

Because no affected model received qualified acceleration, the readiness gate
does **not** auto-reauthorise slow all-reference execution. The operational
decision is:

* **A** — authorise formal R4 Epoch 1 on the reference environment (`R0`) and
  accept its throughput; or
* **B** — amend the predeclared numerical-equivalence contract (with an explicit
  scientific justification) and re-run the ablation before any Epoch 1 row.

This artifact does not choose between them.
