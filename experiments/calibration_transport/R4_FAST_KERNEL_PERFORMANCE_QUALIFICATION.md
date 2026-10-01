# R4 — Fast-Kernel Performance Qualification (PHASE G)

```text
STATUS: NOT EXECUTED
REASON: PHASE G IS CONDITIONED ON PHASE F PASS
R4 FAST-KERNEL PERFORMANCE QUALIFICATION = NOT EXECUTED
```

This is an **outcome-blind operational artifact**. It contains no R4 study item,
no ground truth, no study probability, no calibration fit, no risk estimate, no
bootstrap and no predictor value.

---

## 1. Why it was not executed

The amendment states that PHASE G (performance qualification) runs **only after**
PHASE F (reference-vs-fast numerical equivalence) passes. PHASE F **failed**:

```text
R4 FAST-KERNEL NUMERICAL EQUIVALENCE = FAIL
  falcon-h1-7b-instruct   max prob 6.437e-02   max centered logit 4.121e-01
  granite-4-0-h-tiny      max prob 1.493e-01   max centered logit 1.062e+00
  qwen3-5-9b              max prob 3.328e-02   max centered logit 1.875e-01
  qwen3-5-2b              max prob 2.976e-02   max centered logit 1.250e-01
  predeclared thresholds: prob <= 0.005, designated <= 0.005,
                          centered logit <= 0.10, TV <= 0.01
```

See `R4_FAST_KERNEL_NUMERICAL_EQUIVALENCE.md`.

Because the fast environment is not eligible for adoption, a synthetic
throughput benchmark of that environment would serve no purpose: no adoption
decision can follow from it. Per the amendment, PHASE G was therefore **not
executed**, and PHASE H (the fast-environment six-model preflight) was not
executed either.

Consequently:

* the Falcon-H1 speed-up criterion (≥ 2.0×) was never measured;
* the no-affected-model-slower-by-more-than-10% criterion was never measured;
* the performance gate is `NOT EXECUTED`, not `PASS` and not `FAIL`.

No threshold was relaxed, no benchmark was run on a subset, and no additional
speculative kernel library was installed to try to change the outcome.

## 2. Harness (prepared, not run)

`experiments/calibration_transport/fast_kernel_performance_probe.py`
(sha256 `651405ed93ce8b7b73cffd7878747b816145c3c07f8c96dc716168b4c3c8940d`) was
written and lint-checked so that PHASE G could be executed mechanically if a
future amendment re-qualifies the fast environment. Its fixed parameters:

| parameter | value |
| --- | --- |
| processes | one model per process |
| warmup items | 3 |
| measured items | 12 |
| batch size | 1 |
| logical forwards per item | 2 |
| dtype | bfloat16 |
| device | `cuda:0` |
| mode | `eval()` + `inference_mode()` |
| recorded | rows/sec, logical forwards/sec, median/mean/min/max seconds per row, elapsed, peak host RSS, peak GPU allocated, MemAvailable before/after |

Predeclared adoption gate (unchanged): Falcon-H1 speed-up ≥ 2.0× **and** no
affected model slower by more than 10% **and** no host-memory-floor violation,
no CUDA OOM, no process instability.

## 3. Host-memory gate (incidental observation only)

No benchmark process was run, so the memory gate was not exercised as a gate.
The PHASE F captures did incidentally observe that the cgroup-v2-aware available
memory (limit 58.00 GiB) stayed around 34 GiB, far above the 12 GiB floor.
`/proc/meminfo` `MemAvailable` is host-wide in this container and was **not** used
as the gate measure.

## 4. Status

```text
R4 FAST-KERNEL PERFORMANCE QUALIFICATION = NOT EXECUTED
REASON = PHASE F FAILED; PHASE G IS CONDITIONED ON PHASE F PASS
FALCON SPEED-UP MEASURED = NO
FAST-KERNEL EXECUTION ENVIRONMENT = NOT ADOPTED
```
