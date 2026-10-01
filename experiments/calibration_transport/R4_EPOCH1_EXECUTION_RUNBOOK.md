# R4 — Epoch 1 Execution Runbook (operational)

```text
STATUS: READY (operational only)
R4 EPOCH 1 EXECUTION READINESS = TECHNICALLY PASS / OPERATIONAL DECISION REQUIRED
FORMAL R4 EPOCH 1 EXECUTION = NOT AUTHORIZED
```

This runbook is operational. It changes no scientific semantic: the measurement
contract, final protocol, execution manifest, populations, anchors, verbalizers,
calibration families, estimands, metrics, multiplicity rule and predictor
semantics are untouched. `run_r4_measurements.py` is scientifically unchanged.

---

## 1. Environment map

`R4_EPOCH1_MODEL_EXECUTION_ENVIRONMENT_MAP.json`
(`environment_map_fingerprint aebeb528b6db1d09d23c83ff8078e5a9cb0b779c8fbada0f19617c878cfb45eb`)
binds every frozen model to exactly one execution environment. The bounded kernel
ablation found no numerically eligible acceleration candidate, so **all six
models are bound to `R0`**, the frozen reference environment:

```text
/root/rivermind-data/envs/probvenance-r4/bin/python
```

`execution_environment_fingerprint` (R0):
`46424eac4c734ee9adece0fc6e1e5394421ccdb1e50718b94144010fbf61c5c7`.

## 2. Dispatcher

`experiments/calibration_transport/r4_epoch1_launch.py` is an **operational-only**
launcher. It resolves a model key to its frozen interpreter, sets the offline
flags, and invokes the scientifically unchanged runner. It never reads a score,
a probability or any study outcome, and it never changes the runner's scientific
CLI configuration.

```bash
# list every frozen cell and the environment it resolves to
<env>/bin/python experiments/calibration_transport/r4_epoch1_launch.py --list-cells

# print the frozen interpreter for one model
<env>/bin/python experiments/calibration_transport/r4_epoch1_launch.py \
    --model-key falcon-h1-7b-instruct --print-interpreter

# dispatch one cell (runner arguments after --)
# NOTE: --model-role is the runner's model-key flag (it selects the frozen
# model cell); it is required by run_r4_measurements.main(). The dispatcher's
# --model-key is used only to resolve the frozen interpreter and is NOT
# forwarded to the runner.
<env>/bin/python experiments/calibration_transport/r4_epoch1_launch.py \
    --model-key falcon-h1-7b-instruct -- \
    --model-role falcon-h1-7b-instruct \
    --population hellaswag --staging-root /root/rivermind-data/r4-formal-measurements --resume
```

Offline flags applied by the dispatcher:

```text
HF_HUB_OFFLINE=1  TRANSFORMERS_OFFLINE=1  HF_DATASETS_OFFLINE=1
```

Runner guarantees that remain in force: `trust_remote_code=False`,
`local_files_only=True`, dtype `bfloat16`, device `cuda:0`, batch size 1,
`eval()` / `inference_mode()`.

## 3. Frozen grid and workload

16 frozen cells (`run_r4_measurements.resolve_cell`, with the legacy × MMLU
combination rejected as `R4MeasurementDomainError`).

| workload | rows |
| --- | --- |
| unique model × item rows | 100 728 |
| CAT forwards | 100 728 |
| OVR forwards (designated-only) | 100 728 |
| planned logical forwards | 201 456 |

Projected relative runtime of the selected map versus all-reference is `1.000×`
by construction; no synthetic speed-up ratio exists because no candidate was
eligible for adoption benchmarking.

## 4. Execution discipline

* **One cell = one process.** Do not run two cells in one process.
* **Single writer per cell**, enforced by `r4_staging.acquire_cell_lock`.
* **Single GPU worker.** `MULTI-WORKER = NOT AUTHORIZED`.
* **Crash-safe resume** per `R4_MEASUREMENT_RESUME_POLICY` v1: the pending set is
  derived only from transaction state; a mid-row crash replays the whole row; a
  terminal failure is never retried.
* **Staging root** `/root/rivermind-data/r4-formal-measurements`, which is
  currently empty. Epoch 1 must start from the first frozen item of the first
  frozen cell.
* **No Epoch 0 inheritance.** The quarantined Epoch 0 tree is `READ_ONLY` /
  `DO_NOT_RESUME` / `DO_NOT_MERGE` / `DO_NOT_COPY_ROWS` / `DO_NOT_ANALYZE`; no
  row, probability or terminal-failure state may be carried into Epoch 1.
* **Memory.** Use the cgroup v2 view (`/sys/fs/cgroup/memory.max`,
  `memory.current`, `memory.stat`), never host `/proc/meminfo`. Keep ≥ 12 GiB
  effective headroom.

## 5. Preconditions before the first row

```text
[ ] human / ChatGPT review of this map and of R4_KERNEL_ABLATION_QUALIFICATION.md
[ ] normal push to remote and remote SHA verification
[ ] explicit execution authorization for Epoch 1
[ ] staging root confirmed empty
[ ] git worktree clean at the authorized commit
```

Until all of these hold:

```text
FORMAL R4 EPOCH 1 EXECUTION = NOT AUTHORIZED
EPOCH 1 REAL STUDY ROWS EXECUTED = 0
```
