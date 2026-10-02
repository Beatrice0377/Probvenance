# R4 Epoch 1 Raw Measurement Execution Receipt

```text
EXECUTION = R4 FORMAL EPOCH 1 POST-FIX ALL-REFERENCE RAW MEASUREMENT
STATUS = COMPLETE
COMPLETED CELLS = 16 / 16
COMMITTED ROWS = 100728
PLANNED LOGICAL FORWARDS = 201456
R4 EPOCH 1 RAW MEASUREMENT COMPLETENESS = PASS
FORMAL R4 CALIBRATION / INFERENCE = NOT AUTHORIZED
PUSH PERFORMED = NO
```

## 1. Authority at execution time

```text
branch              = main
HEAD                = 100c918345ff829dd6fdb96bf99cd14285d6472f
origin/main         = 100c918345ff829dd6fdb96bf99cd14285d6472f
repository_execution_authority = 100c918345ff829dd6fdb96bf99cd14285d6472f
measurement_code_commit        = 100c918345ff829dd6fdb96bf99cd14285d6472f
production_code_equivalence_anchor = 65eb75ceabecbd5f30c07135b62c184d028b4f0f
worktree at launch  = clean
```

The human provenance ruling accepted the existing runtime-provenance schema
unchanged: `measurement_code_commit = git rev-parse HEAD`. No code, schema, or
documentation patch was applied for provenance.

## 2. Execution window

```text
first cell start  = 2026-10-01T13:52:19+00:00
last cell end     = 2026-10-02T02:52:48+00:00
wall clock        = 13h00m29s
sum of cell times = 12h59m12s
```

## 3. Cell-by-cell execution timeline

| # | cell_id | start | end | elapsed | rows | rc |
|---|---|---|---|---|---|---|
| 1 | `olmo-3-7b-instruct__r4-mmlu-57-subject` | 2026-10-01T13:52:19+00:00 | 2026-10-01T13:55:41+00:00 | 3m22s | 1596 | 0 |
| 2 | `olmo-3-7b-instruct__r4-hellaswag-activity-primary` | 2026-10-01T13:55:46+00:00 | 2026-10-01T14:13:38+00:00 | 17m52s | 10954 | 0 |
| 3 | `olmo-3-7b-instruct__r4-medmcqa-subject-primary` | 2026-10-01T14:13:44+00:00 | 2026-10-01T14:21:24+00:00 | 7m40s | 5074 | 0 |
| 4 | `falcon-h1-7b-instruct__r4-mmlu-57-subject` | 2026-10-01T14:21:29+00:00 | 2026-10-01T14:49:37+00:00 | 28m08s | 1596 | 0 |
| 5 | `falcon-h1-7b-instruct__r4-hellaswag-activity-primary` | 2026-10-01T14:49:42+00:00 | 2026-10-01T18:38:48+00:00 | 3h49m06s | 10954 | 0 |
| 6 | `falcon-h1-7b-instruct__r4-medmcqa-subject-primary` | 2026-10-01T18:38:53+00:00 | 2026-10-01T19:55:28+00:00 | 1h16m35s | 5074 | 0 |
| 7 | `granite-4-0-h-tiny__r4-mmlu-57-subject` | 2026-10-01T19:55:33+00:00 | 2026-10-01T20:21:12+00:00 | 25m39s | 1596 | 0 |
| 8 | `granite-4-0-h-tiny__r4-hellaswag-activity-primary` | 2026-10-01T20:21:17+00:00 | 2026-10-01T23:33:59+00:00 | 3h12m42s | 10954 | 0 |
| 9 | `granite-4-0-h-tiny__r4-medmcqa-subject-primary` | 2026-10-01T23:34:04+00:00 | 2026-10-02T00:48:16+00:00 | 1h14m12s | 5074 | 0 |
| 10 | `qwen3-5-9b__r4-mmlu-57-subject` | 2026-10-02T00:48:21+00:00 | 2026-10-02T00:56:52+00:00 | 8m31s | 1596 | 0 |
| 11 | `qwen3-5-9b__r4-hellaswag-activity-primary` | 2026-10-02T00:56:58+00:00 | 2026-10-02T01:35:06+00:00 | 38m08s | 10954 | 0 |
| 12 | `qwen3-5-9b__r4-medmcqa-subject-primary` | 2026-10-02T01:35:11+00:00 | 2026-10-02T01:52:38+00:00 | 17m27s | 5074 | 0 |
| 13 | `minicpm5-2b__r4-hellaswag-activity-primary` | 2026-10-02T01:52:43+00:00 | 2026-10-02T02:08:51+00:00 | 16m08s | 10498 | 0 |
| 14 | `minicpm5-2b__r4-medmcqa-subject-primary` | 2026-10-02T02:08:56+00:00 | 2026-10-02T02:15:57+00:00 | 7m01s | 4618 | 0 |
| 15 | `qwen3-5-2b__r4-hellaswag-activity-primary` | 2026-10-02T02:16:02+00:00 | 2026-10-02T02:42:09+00:00 | 26m07s | 10498 | 0 |
| 16 | `qwen3-5-2b__r4-medmcqa-subject-primary` | 2026-10-02T02:42:14+00:00 | 2026-10-02T02:52:48+00:00 | 10m34s | 4618 | 0 |

All 16 cells exited `rc=0`. No cell was aborted, retried, or terminally failed.

## 4. Execution policy actually enforced

```text
one cell == one process                : yes (16 sequential processes)
single writer per cell                 : yes (fcntl LOCK, released on exit)
crash-safe resume                      : enabled (--resume, per-row durable commits)
terminal-failure never retried         : yes (no terminal failures occurred)
cgroup headroom floor >= 12 GiB        : checked before every cell; never breached
offline execution                      : HF_HUB_OFFLINE/TRANSFORMERS_OFFLINE/HF_DATASETS_OFFLINE = 1
trust_remote_code                      : False
dtype / device / batch                 : bfloat16 / cuda:0 / batch 1
environment changed during execution   : no
kernel change during execution         : no
code change during execution           : no
outcome inspection                     : none
```

## 5. Memory envelope (cgroup v2, in-container)

```text
memory.max          = 62277025792 (58.00 GiB)
memory.swap.max     = 0
floor enforced      = 12884901888 (12 GiB)
breaches            = none
```

Headroom was measured as `memory.max - memory.current + inactive_file` before every
cell and after every cell completion. Host `/proc/meminfo` was never used.

## 6. Incidents

```text
infrastructure blocker  = NONE
CUDA / GPU anomaly      = NONE
code defect during run  = NONE
schema defect           = NONE
identity conflict       = NONE
filesystem corruption   = NONE
recovery replay events  = 0
terminal failures       = 0
```

## 7. Epoch provenance

```text
epoch 0 (reference path)      = ABORTED, quarantined, DO_NOT_USE
epoch 1 attempt 0             = BLOCKED pre-row1 (MMLU adapter defect), quarantined
epoch 1 attempt 1 (this run)  = COMPLETE, 16/16 cells, 100728 rows
```

No Epoch 0 row and no Epoch 1 attempt-0 state was inherited, copied, or merged.
Epoch 1 began from the first frozen item of the first frozen cell.

## 8. Verification performed after the run

```text
raw-evidence schema validation (all 16 cells) = PASS
expected item IDs exact, no extra, no duplicate = PASS
CAT/OVR status counts = scored only, missing 0, ineligible 0 = PASS
frozen scientific artifacts re-hashed = UNCHANGED
environment map re-hashed = UNCHANGED
post-run test suite = 0 failed
```

## 9. Outcome firewall

```text
calibration = NOT FIT
Brier = NOT COMPUTED
LogLoss = NOT COMPUTED
Delta_native = NOT COMPUTED
Delta_deploy = NOT COMPUTED
Delta_transport = NOT COMPUTED
bootstrap = NOT RUN
predictor = NOT COMPUTED
Spearman = NOT COMPUTED
scientific interpretation = NOT PERFORMED
```

## 10. Artifacts

```text
R4_EPOCH1_RAW_MEASUREMENT_EVIDENCE_LEDGER.json
R4_EPOCH1_RAW_MEASUREMENT_EVIDENCE_FREEZE.md
R4_EPOCH1_RAW_MEASUREMENT_EXECUTION_RECEIPT.md
```

Raw measurement rows (100728 committed row files) remain under
`/root/rivermind-data/r4-formal-measurements` and are NOT committed to the repository.

## 11. Final status

```text
R4 FORMAL EPOCH 1 RAW MEASUREMENT EXECUTION = COMPLETE
R4 EPOCH 1 RAW MEASUREMENT COMPLETENESS = PASS
FORMAL R4 CALIBRATION / INFERENCE = NOT AUTHORIZED
PUSH PERFORMED = NO
FINAL STOP
```

