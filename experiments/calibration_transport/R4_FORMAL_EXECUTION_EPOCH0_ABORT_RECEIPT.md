# R4 Formal Measurement — Execution Epoch 0 Abort Receipt

Status: **R4 FORMAL EXECUTION EPOCH 0 = ABORTED_FOR_PREDECLARED_OPERATIONAL_PERFORMANCE_REASON**
Scientific eligibility of every Epoch 0 row: **DO_NOT_USE**

This is an **outcome-blind operational amendment**. No model, revision, population, manifest,
anchor, ground truth, prompt, verbalizer, measurement contract, calibration family, estimand,
metric, multiplicity rule or predictor semantic was changed. No scientific outcome was inspected.

---

## 1. Remote pre-outcome freeze

| field | value |
| --- | --- |
| branch | `main` |
| remote pre-outcome HEAD | `5654f799f28b918c9bc23761e79f440ab52e8111` |
| origin/main at abort | `5654f799f28b918c9bc23761e79f440ab52e8111` |
| raw behind/ahead | `0 / 0` |
| worktree at abort | clean |

## 2. Frozen scientific authority (unchanged, re-read only)

| fingerprint | value |
| --- | --- |
| `measurement_contract_fingerprint` | `7b126d300e774cb44d2c47fcb12513865d03c2b08ffd03a5ce409b2ea976e1e5` |
| `final_protocol_fingerprint` | `d1b56d702e1f260cef47eee05b7d878ace07a15168e89408e15e7eb741c0ad34` |
| `execution_manifest_fingerprint` | `f32381c51db24f5dbeb240b5e0fdf73c59a56a615c8607ad8979e2a7e2586775` |

## 3. Abort reason (predeclared, operational)

```text
reference/slow kernel path produced operational throughput
that made the full frozen workload impractical;
decision made without scientific outcome inspection.
```

The active cell ran Falcon-H1 through Transformers' reference PyTorch implementations because the
optional optimized kernels were absent from the reference environment. The model loader emitted,
verbatim:

```text
[transformers] `causal_conv1d_fn` is falling back to its reference PyTorch implementation because
`causal_conv1d` is not installed. This is correct but much slower; install `causal_conv1d` for the
optimized kernel.

[transformers] `mamba_chunk_scan_combined` is falling back to its reference PyTorch implementation
because `mamba_ssm` is not installed. This is correct but much slower; install `mamba_ssm` for the
optimized kernel.
```

This is **not** a claim that the model failed, that the scientific measurement was invalid, or that
Falcon-H1 is scientifically problematic. It is a statement about operational throughput only.

## 4. Decision time

```text
decision taken before any scientific outcome inspection
abort executed 2026-10-01T07:09:32+00:00 (UTC)
```

## 5. Active cell at abort

| field | value |
| --- | --- |
| cell_id | `falcon-h1-7b-instruct__r4-hellaswag-activity-primary` |
| model | `tiiuae/Falcon-H1-7B-Instruct` @ `41e72f27effbab80cd45b6e884688452253a3686` |
| population | `r4-hellaswag-activity-primary` (`Rowan/hellaswag` @ `218ec52e09a7e7462a5400043bb9a69a41d06b76`) |
| planned rows | 10954 |
| committed rows at abort | **1852** |
| pending rows at abort | 9102 |
| inflight markers at abort | 1 (cleared by the runner on shutdown; 0 remain) |
| planned logical forwards | 21908 |
| recorded `operational_attempts` | 0 (see §7 note) |
| recorded `recovery_replay_count` | 0 |
| process elapsed | 2067.469 s |
| observed throughput | ≈ 0.93 rows/s |
| peak host RSS | 16,442,896 KiB (≈ 15.7 GiB) |
| stop signal | `SIGINT` (graceful; no `SIGTERM`, no `SIGKILL`) |
| process exit | `KeyboardInterrupt`, exit code `-2` / shell `254` |
| lock | released by the runner `finally` path; `LOCK` file remains as an inert, unlocked artifact |

No study probabilities were read, summarised, averaged or compared.

## 6. Quarantine

The entire Epoch 0 staging tree was preserved, never deleted, and moved after all writers stopped:

```text
/root/rivermind-data/r4-formal-measurements-aborted/epoch0-reference-path/
```

| field | value |
| --- | --- |
| file count | 1859 |
| total bytes | 10,770,086 |
| `QUARANTINE_MANIFEST.json` sha256 | `9ea0fc793692961b2a216aa2ecec2933dab79dcc81a034615034096f1a2a04b6` |
| `QUARANTINE_MANIFEST.json` fingerprint | `ae6920d95947cd94d206c5593b45e3ab7c9750e9550e6986039075c430393502` |

Preserved: committed rows, uncommitted transaction remnants, `operations.json`, `cell_identity.json`,
`runtime_provenance.json`, the loader log including the slow-path warnings, and the released lock.
No partial data was deleted in order to manufacture a "never executed" appearance.

### Quarantine policy

```text
READ-ONLY BY POLICY
DO_NOT_RESUME
DO_NOT_MERGE
DO_NOT_COPY_ROWS_INTO_EPOCH_1
DO_NOT_ANALYZE
```

## 7. Provenance note on the operational counter

`operations.json` was last persisted when the cell started, so it still reads
`operational_attempts = 0` and `finalizations = 0` even though 1852 rows were durably committed.
The authoritative Epoch 0 structural record is therefore the committed-row count on disk
(1852 `rows/<item_id>.json` files), not the persisted operations counter. This discrepancy is
recorded rather than reconciled.

## 8. Epoch 0 provenance statement

```text
Epoch 0 is not part of the R4 scientific raw-evidence set.

Its rows are not eligible for:
calibration,
risk estimation,
bootstrap,
predictor validation,
or paper results.
```

Epoch 1 restarts from the first frozen item of the first frozen cell. No Epoch 0 row, probability
or terminal-failure state is inherited.

## 9. Outcome firewall

No Brier, no LogLoss, no Delta, no bootstrap, no predictor value, no accuracy, no mean score, no
model comparison and no interpretation was computed at any point during the abort or the
quarantine. Only structural counts, transaction states, filesystem hashes, process runtime,
throughput and memory figures were read.

## 10. Final status

```text
R4 FORMAL EXECUTION EPOCH 0 = ABORTED_FOR_PREDECLARED_OPERATIONAL_PERFORMANCE_REASON
EPOCH 0 SCIENTIFIC ELIGIBILITY = DO_NOT_USE
EPOCH 0 QUARANTINE = COMPLETE
EPOCH 1 REAL STUDY ROWS EXECUTED = 0
```
