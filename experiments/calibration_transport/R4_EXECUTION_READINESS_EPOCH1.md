# R4 Execution Readiness — Epoch 1

```text
STATUS: TECHNICALLY PASS / OPERATIONAL DECISION REQUIRED
R4 EXECUTION READINESS — EPOCH 1 = TECHNICALLY PASS / OPERATIONAL DECISION REQUIRED
QUALIFIED ACCELERATION = NONE
ALL-REFERENCE EXECUTION REMAINS THE ONLY QUALIFIED PATH
FORMAL R4 EPOCH 1 EXECUTION = NOT AUTHORIZED
EPOCH 1 REAL STUDY ROWS EXECUTED = 0
```

This document is the Epoch 1 readiness closure. It covers two consecutive
operational amendments:

1. *"R4 Formal Measurement Epoch 0 Abort + Fast-Kernel Dependency Audit +
   Reference-vs-Fast Numerical Equivalence + Performance / Memory Qualification +
   Epoch 1 Execution Environment Freeze + Restart Readiness Closure"* (result:
   fast environment rejected, readiness BLOCKED);
2. *"R4 Bounded Synthetic Kernel Ablation + Determinism Diagnosis +
   Model-Specific Fast-Path Selection + Mixed Execution Environment
   Qualification + Epoch 1 Readiness Candidate"* (result: no qualified
   acceleration, all-reference map frozen, readiness technically pass with an
   open operational decision).

Both are **outcome-blind operational artifacts**. No scientific outcome was
inspected; no model, revision, population, manifest, anchor, ground truth, prompt,
verbalizer, measurement contract, calibration family, estimand, metric,
multiplicity rule or predictor semantic was changed.

---

## 1. What happened

| epoch | event |
| --- | --- |
| — | The reference environment had previously been declared `R4 EXECUTION READINESS = PASS` with a 6/6 synthetic preflight. |
| 0 | Formal raw measurement was started, then **aborted for a predeclared operational performance reason** and quarantined as `DO_NOT_USE` (`R4_FORMAL_EXECUTION_EPOCH0_ABORT_RECEIPT.md`). |
| — | An isolated fast-kernel environment (`F0`) was proposed to remove the throughput problem, subject to a **predeclared** reference-vs-fast numerical-equivalence gate. |
| 1 (first) | `F0` was built, audited, activated and tested — but **failed the equivalence gate** and was non-deterministic for Falcon-H1 / Granite-4. Readiness BLOCKED. |
| 1 (second) | A **bounded package-subset ablation** (R0 / C1 / C2 / C3) was run to localize the drift and the non-determinism. Every candidate failed the immutable numerical gate. The eligible set is empty, so the predeclared rule selects the reference environment `R0` for **every** model. |

The governing form was followed exactly:

```text
ABORT TRANSPARENTLY -> PRESERVE -> REQUALIFY -> FREEZE -> PUSH -> RESTART CLEANLY
```

It stopped at **FREEZE of an all-reference map**, because requalification found no
qualified acceleration. No Epoch 1 study row was executed.

## 2. Phase-by-phase result (both amendments)

| phase | subject | result | artifact |
| --- | --- | --- | --- |
| A | stop Epoch 0, quarantine, receipt | **PASS** | `R4_FORMAL_EXECUTION_EPOCH0_ABORT_RECEIPT.md` (`d140a1f0…`) |
| B | preserve reference env + package receipt | **PASS** | `R4_REFERENCE_ENVIRONMENT_PACKAGE_RECEIPT.txt` (`a7d78012…`) |
| C | six-model fast-kernel dependency audit | **PASS** | `R4_FAST_KERNEL_DEPENDENCY_AUDIT.md` (`4f30ddf5…`) |
| D | isolated fast env + package lock | **PASS** | `R4_FAST_KERNEL_PACKAGE_LOCK.json` (`d68da19d…`) |
| E | full-stack fast-path activation matrix | **PASS** | in the audit doc |
| F | reference-vs-fast numerical equivalence | **FAIL** | `R4_FAST_KERNEL_NUMERICAL_EQUIVALENCE.md` |
| G/H | full-stack performance / preflight | **NOT EXECUTED** | conditioned on F PASS |
| — | **ablation** activation matrix (R0/C1/C2/C3) | **PASS** | `R4_KERNEL_ABLATION_ACTIVATION_MATRIX.md`/`.json` (`ab43db8f…`) |
| — | **ablation** repeatability (3 fresh processes per cell) | **PASS** (all bit-exact) | `R4_KERNEL_ABLATION_QUALIFICATION.json` (`1f5ebec…`) |
| — | **ablation** numerical equivalence | **FAIL** for every candidate | `R4_KERNEL_ABLATION_QUALIFICATION.md`/`.json` |
| — | **ablation** performance | **NOT EXECUTED** | no numerically eligible candidate |
| — | model → environment map | **FROZEN (all R0)** | `R4_EPOCH1_MODEL_EXECUTION_ENVIRONMENT_MAP.md`/`.json` (`aebeb528…`) |
| I | selected-path six-model preflight | **PASS** (6/6) | reference environment `R0` |
| J | operational dispatcher | **PASS** | `r4_epoch1_launch.py` + `tests/test_r4_epoch1_dispatch.py` |
| K | this readiness closure | **TECHNICALLY PASS / OPERATIONAL DECISION REQUIRED** | this document |

## 3. Epoch 1 readiness checklist

| # | condition | state |
| --- | --- | --- |
| 1 | Epoch 0 quarantine complete and read-only | PASS |
| 2 | reference environment preserved | PASS (`pip freeze` unchanged; only the editable-VCS line moves with HEAD) |
| 3 | locked optional package artifacts hash-verified | PASS (all 5 wheels match `R4_FAST_KERNEL_PACKAGE_LOCK.json`) |
| 4 | candidate environments isolated from the reference | PASS (clones, never the reference env) |
| 5 | protected core unchanged in every environment | PASS (Python 3.11.13, torch 2.8.0+cu128, transformers 5.17.0, …) |
| 6 | activation proven mechanically | PASS (closure-based `is_new_implementation`) |
| 7 | repeatability PASS | PASS (all cells bit-exact over 3 fresh processes) |
| 8 | numerical equivalence PASS | **FAIL for every candidate** |
| 9 | performance thresholds | NOT EXECUTED (no eligible candidate) |
| 10 | cgroup memory gate ≥ 12 GiB | PASS (≈34.0 GiB observed headroom) |
| 11 | selected-path six-model preflight PASS | PASS — `run_r4_measurements.py --synthetic-preflight --device cuda:0` executed in the selected environment `R0` (offline flags set): **6/6 `status = PASS`**, 2 synthetic forwards each, all `dtype torch.bfloat16`, every `resolved_snapshot` under the pinned revision, and the frozen verbalizer ids exactly — olmo 32/33/34/35 + 9891/2201; falcon 1068/1069/1070/1071 + 5763/3257; granite 32/33/34/35 + 9891/2201; qwen3-5-9b 32/33/34/35 + 9405/2083; minicpm5-2b 54/55/56/57 + 15876/3707; qwen3-5-2b 32/33/34/35 + 9405/2083 |
| 12 | full repository tests PASS | PASS (0 failed) |
| 13 | scientific freezes unchanged | PASS (byte-identical) |
| 14 | Epoch 1 staging root clean | PASS (no cell directories, no rows) |

Conditions 1–7 and 10–14 pass; condition 8 fails for every candidate and
condition 9 is therefore not applicable. The map is nevertheless a **fully
qualified** all-reference map, because `R0` is itself a legitimate formal
environment. The verdict is therefore

```text
R4 EPOCH 1 EXECUTION READINESS = TECHNICALLY PASS / OPERATIONAL DECISION REQUIRED
```

and **not** an automatic re-authorisation of the slow all-reference plan.

## 4. Why no acceleration was adopted

```text
C1 (causal-conv1d only)             falcon 1.472e-01  granite 1.029e-01  qwen9b 2.763e-02  qwen2b 2.946e-02
C2 (causal-conv1d + mamba-ssm)      falcon 1.472e-01  granite 1.029e-01  (numerically identical to C1)
C3 (causal-conv1d + FLA)            qwen9b 3.328e-02  qwen2b 2.976e-02
F0 (all five, previously rejected)  falcon 6.437e-02  granite 1.493e-01  qwen9b 3.328e-02  qwen2b 2.976e-02

predeclared thresholds (immutable): prob <= 0.005, designated <= 0.005,
                                    centered logit <= 0.10, TV <= 0.01
```

Findings:

* `causal_conv1d` **alone** already exceeds every threshold on all four affected
  models — the drift is not caused by `mamba_ssm`.
* `C2` never activates a mamba kernel (`mamba_ssm` cannot be imported without
  `einops`, which is not in the declared C2 set) and is numerically identical to
  `C1`. It is `INELIGIBLE / DIAGNOSTIC_ONLY / NOT_SELECTABLE`.
* The full-stack `F0` **non-determinism** for Falcon-H1 / Granite-4 is localized
  to `mamba_ssm`: `C1` (no mamba) is bit-exact reproducible across three fresh
  processes.
* `C3` reproduces the previously rejected Qwen3.5-9B figure exactly
  (`3.328e-02`), so the FLA-containing candidate is also not eligible.

No threshold was relaxed, no failing prompt was dropped, no prompt was added, no
package version was searched for, no extra acceleration library was installed,
`trust_remote_code` was not enabled, and no quantization / CPU offload / dtype
change was used to force a pass.

## 4b. Selected-path preflight (PHASE I)

`run_r4_measurements.py --synthetic-preflight --device cuda:0` was executed in the
selected environment `R0` with `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
HF_DATASETS_OFFLINE=1`. Result: **6/6 `status = PASS`**, two synthetic forwards per
model, every model loaded as `torch.bfloat16`, every `resolved_snapshot` under the
pinned revision, and the frozen verbalizer ids reproduced exactly.

| model | model class | CAT ids | OVR yes / no |
| --- | --- | --- | --- |
| olmo-3-7b-instruct | `Olmo3ForCausalLM` | 32/33/34/35 | 9891 / 2201 |
| falcon-h1-7b-instruct | `FalconH1ForCausalLM` | 1068/1069/1070/1071 | 5763 / 3257 |
| granite-4-0-h-tiny | `GraniteMoeHybridForCausalLM` | 32/33/34/35 | 9891 / 2201 |
| qwen3-5-9b | `Qwen3_5ForCausalLM` | 32/33/34/35 | 9405 / 2083 |
| minicpm5-2b | `LlamaForCausalLM` | 54/55/56/57 | 15876 / 3707 |
| qwen3-5-2b | `Qwen3_5ForCausalLM` | 32/33/34/35 | 9405 / 2083 |

The preflight used invented synthetic content only: `study_items_used = 0`.

## 5. What remains valid

* The **frozen reference environment** `/root/rivermind-data/envs/probvenance-r4`
  is preserved byte-identical and is the only qualified R4 execution environment.
* The frozen model → environment map is all-`R0`, so all 16 frozen cells resolve
  to one interpreter and one environment fingerprint.
* All frozen scientific artifacts are byte-identical; neither amendment changed a
  scientific semantic.
* Epoch 0 is fully quarantined and ineligible.
* Epoch 1 workload is unchanged: 100728 unique model×item rows, 100728 CAT,
  100728 OVR, 201456 planned logical forwards.
* Projected relative runtime of the selected map versus all-reference is
  `1.000×` by construction (no eligible acceleration exists).

## 6. Decision required

Because no affected model received qualified acceleration, slow all-reference
execution is **not** auto-reauthorised. The human reviewer must choose:

* **A** — authorise formal R4 Epoch 1 on the reference environment (`R0`),
  accepting its throughput; or
* **B** — amend the predeclared numerical-equivalence contract with an explicit
  scientific justification and re-run the ablation before any Epoch 1 row.

This document does not choose between them and does not authorize any Epoch 1
execution.

## 7. Status block

```text
R4 FORMAL EXECUTION EPOCH 0 = ABORTED AND QUARANTINED
EPOCH 0 SCIENTIFIC ELIGIBILITY = DO_NOT_USE

R4 FAST-KERNEL DEPENDENCY AUDIT = PASS
R4 FAST-KERNEL NUMERICAL EQUIVALENCE (FULL STACK) = FAIL
FAST-KERNEL EXECUTION ENVIRONMENT = NOT ADOPTED

R4 BOUNDED KERNEL ABLATION = COMPLETE
QUALIFIED ACCELERATION = NONE
PREDECLARED NUMERICAL THRESHOLDS = UNCHANGED
ALL-REFERENCE EXECUTION REMAINS THE ONLY QUALIFIED PATH

R4 EXECUTION ENVIRONMENT — EPOCH 1 = FROZEN (ALL-REFERENCE MAP)
R4 EPOCH 1 EXECUTION READINESS = TECHNICALLY PASS / OPERATIONAL DECISION REQUIRED

FORMAL R4 EPOCH 1 EXECUTION = NOT AUTHORIZED
EPOCH 1 REAL STUDY ROWS EXECUTED = 0

PUSH PERFORMED = NO
AWAITING HUMAN DECISION
FINAL STOP
```
