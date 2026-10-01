# R4 Execution Readiness — Epoch 1

```text
STATUS: BLOCKED
R4 EXECUTION READINESS — EPOCH 1 = BLOCKED
FORMAL R4 EPOCH 1 EXECUTION = NOT AUTHORIZED
EPOCH 1 REAL STUDY ROWS EXECUTED = 0
```

This document is the Epoch 1 readiness closure for the operational amendment
*"R4 Formal Measurement Epoch 0 Abort + Fast-Kernel Dependency Audit +
Reference-vs-Fast Numerical Equivalence + Performance / Memory Qualification +
Epoch 1 Execution Environment Freeze + Restart Readiness Closure"*.

It is an **outcome-blind operational artifact**. No scientific outcome was
inspected; no model, revision, population, manifest, anchor, ground truth, prompt,
verbalizer, measurement contract, calibration family, estimand, metric,
multiplicity rule or predictor semantic was changed.

---

## 1. What happened

| epoch | event |
| --- | --- |
| — | The reference environment had previously been declared `R4 EXECUTION READINESS = PASS` with a 6/6 synthetic preflight. |
| 0 | Formal raw measurement was started, then **aborted for a predeclared operational performance reason** and quarantined as `DO_NOT_USE` (`R4_FORMAL_EXECUTION_EPOCH0_ABORT_RECEIPT.md`). |
| — | An isolated fast-kernel environment was proposed to remove the throughput problem, subject to a **predeclared** reference-vs-fast numerical-equivalence gate. |
| 1 | The fast environment was built, audited, activated and tested — but **failed the equivalence gate**. No Epoch 1 environment is frozen. |

The amendment's governing form was followed exactly:

```text
ABORT TRANSPARENTLY -> PRESERVE -> REQUALIFY -> FREEZE -> PUSH -> RESTART CLEANLY
```

The chain stopped at **REQUALIFY** because the requalification gate failed. It did
not proceed to FREEZE, and it did not run a single Epoch 1 study row.

## 2. Phase-by-phase result

| phase | subject | result | artifact |
| --- | --- | --- | --- |
| A | stop Epoch 0, quarantine, receipt | **PASS** | `R4_FORMAL_EXECUTION_EPOCH0_ABORT_RECEIPT.md` (`d140a1f0…`) |
| B | preserve reference env + package receipt | **PASS** | `R4_REFERENCE_ENVIRONMENT_PACKAGE_RECEIPT.txt` (`a7d78012…`) |
| C | six-model fast-kernel dependency audit | **PASS** | `R4_FAST_KERNEL_DEPENDENCY_AUDIT.md` (`4f30ddf5…`) |
| D | isolated fast env + package lock | **PASS** | `R4_FAST_KERNEL_PACKAGE_LOCK.json` (`d68da19d…`) |
| E | fast-path activation matrix | **PASS** | in the audit doc |
| F | reference-vs-fast numerical equivalence | **FAIL** | `R4_FAST_KERNEL_NUMERICAL_EQUIVALENCE.md` |
| G | performance qualification | **NOT EXECUTED** | conditioned on F PASS |
| H | fast-env six-model preflight | **NOT EXECUTED** | conditioned on F PASS |
| I | fast-env regression tests | **PASS** | 87 / 69 / 115 / 53 + full suite |
| J | Epoch 1 execution-environment record | **BLOCKED** | `R4_EXECUTION_ENVIRONMENT_EPOCH1_FAST_FREEZE.json` (`48017ae2…`) / `.md` |
| K | this readiness closure | **BLOCKED** | this document |
| L | commits | see §6 | no push |

## 3. The Epoch 1 PASS checklist

`R4 EXECUTION READINESS — EPOCH 1 = PASS` may be written only if **all** of the
following hold. Actual state:

| # | condition | state |
| --- | --- | --- |
| 1 | Epoch 0 quarantine complete | PASS |
| 2 | reference environment preserved | PASS (`pip freeze` sha256 unchanged) |
| 3 | dependency audit complete | PASS |
| 4 | fast environment isolated | PASS (clone, not the reference env) |
| 5 | protected core unchanged | PASS (identical in both envs) |
| 6 | fast path activation proven | PASS (14/14 sites) |
| 7 | numerical equivalence PASS | **FAIL** |
| 8 | Falcon speed-up ≥ 2.0× | NOT EXECUTED |
| 9 | no affected model slower by > 10% | NOT EXECUTED |
| 10 | host-memory gate PASS | PASS (incidental, ≈34 GiB vs 12 GiB floor) |
| 11 | six-model fast-env preflight PASS | NOT EXECUTED |
| 12 | full repository tests PASS | PASS |
| 13 | scientific freezes unchanged | PASS (byte-identical) |
| 14 | Epoch 1 staging root clean | PASS (empty, no cell directories) |

Condition 7 fails, so the overall verdict is **BLOCKED**.

## 4. The blocker

```text
BLOCKER: FAST-KERNEL EXECUTION ENVIRONMENT = NOT ADOPTED

The fast environment diverges numerically from the frozen reference
environment on all four affected models, far beyond the predeclared
tolerance, and its mamba_ssm / causal_conv1d path is non-deterministic
run-to-run for Falcon-H1-7B-Instruct and granite-4.0-h-tiny.

  falcon-h1-7b-instruct   max prob 6.437e-02   max centered logit 4.121e-01
  granite-4-0-h-tiny      max prob 1.493e-01   max centered logit 1.062e+00
  qwen3-5-9b              max prob 3.328e-02   max centered logit 1.875e-01
  qwen3-5-2b              max prob 2.976e-02   max centered logit 1.250e-01

  predeclared thresholds: prob <= 0.005, designated <= 0.005,
                          centered logit <= 0.10, TV <= 0.01

  controls: reference-vs-reference-repeat PASS (bit-exact)
            fast-vs-fast-repeat FAIL (falcon, granite non-deterministic)
            reference-repeat-vs-fast-repeat FAIL (failure reproduces)

=> no Epoch 1 execution environment is frozen
```

No threshold was relaxed, no failing prompt was dropped, no passing model was
selected, no additional speculative kernel library was installed,
`trust_remote_code` was not enabled, and no quantization / CPU offload / dtype
change was used to force a pass.

## 5. What remains valid

* The **frozen reference environment** `/root/rivermind-data/envs/probvenance-r4`
  is preserved byte-identical and had already passed the 6/6 synthetic preflight.
  It is the only qualified R4 execution environment.
* All 13 frozen scientific artifacts are byte-identical; the Epoch 1 amendment
  changed no scientific semantic.
* Epoch 0 is fully quarantined and ineligible.
* Epoch 1 workload is unchanged: 100728 unique model×item rows, 100728 CAT,
  100728 OVR, 201456 planned logical forwards.

## 6. Commits (no push)

| # | message | contents |
| --- | --- | --- |
| 1 | `experiments: quarantine R4 measurement epoch 0` | `R4_FORMAL_EXECUTION_EPOCH0_ABORT_RECEIPT.md` |
| 2 | `experiments: qualify R4 fast-kernel execution environment` | `R4_REFERENCE_ENVIRONMENT_PACKAGE_RECEIPT.txt`, `R4_FAST_KERNEL_DEPENDENCY_AUDIT.md`, `R4_FAST_KERNEL_PACKAGE_LOCK.json`, `R4_FAST_KERNEL_NUMERICAL_EQUIVALENCE.md`, `R4_EXECUTION_ENVIRONMENT_EPOCH1_FAST_FREEZE.json`, `R4_EXECUTION_ENVIRONMENT_EPOCH1_FAST_FREEZE.md`, `fast_kernel_equivalence_probe.py`, `fast_kernel_performance_probe.py` |
| 3 | `docs: close R4 epoch 1 execution readiness` | `R4_EXECUTION_READINESS.md`, `R4_EXECUTION_READINESS_EPOCH1.md` |

```text
PUSH PERFORMED = NO
```

## 7. Decision required

The next decision belongs to the human reviewer:

* **A** — run formal R4 Epoch 1 on the frozen reference environment (torch
  fallback), accepting the throughput that caused the Epoch 0 abort; or
* **B** — amend the predeclared numerical-equivalence contract and re-run PHASE F
  before any Epoch 1 row.

This document does not choose between them, and it does not authorize any Epoch 1
execution.

## 8. Status block

```text
R4 FORMAL EXECUTION EPOCH 0 = ABORTED AND QUARANTINED
EPOCH 0 SCIENTIFIC ELIGIBILITY = DO_NOT_USE

R4 FAST-KERNEL DEPENDENCY AUDIT = PASS
R4 FAST-KERNEL NUMERICAL EQUIVALENCE = FAIL
FAST-KERNEL EXECUTION ENVIRONMENT = NOT ADOPTED

R4 EXECUTION ENVIRONMENT — EPOCH 1 = NOT FROZEN
R4 EXECUTION READINESS — EPOCH 1 = BLOCKED

FORMAL R4 EPOCH 1 EXECUTION = NOT AUTHORIZED
EPOCH 1 REAL STUDY ROWS EXECUTED = 0

PUSH PERFORMED = NO
AWAITING HUMAN DECISION
FINAL STOP
```
