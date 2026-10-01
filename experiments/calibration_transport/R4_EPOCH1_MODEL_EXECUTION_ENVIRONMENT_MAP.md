# R4 — Epoch 1 Model → Execution Environment Map (PHASE H)

```text
STATUS: FROZEN (operational)
DISTINCT SELECTED ENVIRONMENTS: 1 (R0, the reference environment)
QUALIFIED ACCELERATION = NONE
FORMAL R4 EPOCH 1 EXECUTION = NOT AUTHORIZED
```

Companion machine-readable artifact:
`experiments/calibration_transport/R4_EPOCH1_MODEL_EXECUTION_ENVIRONMENT_MAP.json`
(`environment_map_fingerprint aebeb528b6db1d09d23c83ff8078e5a9cb0b779c8fbada0f19617c878cfb45eb`).

---

## 1. What this map is

The operational binding of each frozen R4 model to exactly one execution
environment for Epoch 1. It is produced by applying the **predeclared selection
rule** to the bounded-kernel-ablation qualification. It is an operational
execution-environment map: it does **not** modify the measurement contract, the
final protocol, the execution manifest, the populations, the anchors, the
verbalizers or any other scientific artifact.

The map is *not* a scientific statement about model quality.

## 2. Selected environment

| field | value |
| --- | --- |
| environment id | `R0` (reference) |
| path | `/root/rivermind-data/envs/probvenance-r4` |
| interpreter | `/root/rivermind-data/envs/probvenance-r4/bin/python` |
| added acceleration packages | none |
| active fast-kernel sites | none (pure torch fallback) |
| `execution_environment_fingerprint` | `46424eac4c734ee9adece0fc6e1e5394421ccdb1e50718b94144010fbf61c5c7` |

Protected core (identical to every candidate environment, unchanged):
Python 3.11.13, torch 2.8.0+cu128, CUDA 12.8, transformers 5.17.0,
tokenizers 0.23.2, safetensors 0.8.0, huggingface_hub 1.32.0, numpy 2.3.2,
scipy 1.16.3, triton 3.4.0.

## 3. Per-model map

| model key | model id | revision | selected env | fast sites | C1 | C2 | C3 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `olmo-3-7b-instruct` | `allenai/Olmo-3-7B-Instruct` | `6e5971d9eba42665f5bd5a0fcf047f299ce1dccc` | `R0` | — | n/a | n/a | n/a |
| `falcon-h1-7b-instruct` | `tiiuae/Falcon-H1-7B-Instruct` | `41e72f27effbab80cd45b6e884688452253a3686` | `R0` | — | FAIL | FAIL | n/a |
| `granite-4-0-h-tiny` | `ibm-granite/granite-4.0-h-tiny` | `791e0d3d28c86e106c9b6e0b4cecdee0375b6124` | `R0` | — | FAIL | FAIL | n/a |
| `qwen3-5-9b` | `Qwen/Qwen3.5-9B` | `c202236235762e1c871ad0ccb60c8ee5ba337b9a` | `R0` | — | FAIL | n/a | FAIL |
| `qwen3-5-2b` | `Qwen/Qwen3.5-2B` | `15852e8c16360a2fea060d615a32b45270f8a8fc` | `R0` | — | FAIL | n/a | FAIL |
| `minicpm5-2b` | `openbmb/MiniCPM5-2B` | `12a3808a956f869c767195e9266b59c4d21d92e2` | `R0` | — | n/a | n/a | n/a |

`n/a` = no hub-kernel site exists for that model in that environment, so the
candidate is not applicable (not a failure).

`repeatability` is `PASS` for every tested model × candidate, and `memory` is
`PASS`; the selection is decided solely by the numerical-equivalence gate.

## 4. Unselected candidates

| id | status |
| --- | --- |
| `C1` | `NOT_FORMALLY_ADOPTED` (failed numerical equivalence on all four affected models) |
| `C2` | `INELIGIBLE_DIAGNOSTIC_ONLY_NOT_SELECTABLE` (degenerate — identical to C1) |
| `C3` | `NOT_FORMALLY_ADOPTED` (failed numerical equivalence on both Qwen3.5 models) |
| `F0` | `REJECTED_AND_REMAINS_REJECTED` (historical control; not rebuilt, not re-evaluated) |

`R0` is itself a legitimate formal execution environment, so an all-reference
map is a valid, fully qualified outcome — not a failure of the run.

## 5. Selection-rule reason

```text
eligible = numerical PASS AND repeatability PASS AND performance threshold PASS AND memory PASS
result   = the eligible set is empty for every model
action   = select R0 for every model and record NO QUALIFIED ACCELERATION
```

No model is split across environments: every population and every cell of a
given model runs under exactly one environment fingerprint.

## 6. Operational use

Formal Epoch 1 execution is dispatched through
`experiments/calibration_transport/r4_epoch1_launch.py`, which reads this map,
resolves the frozen interpreter for a model key, sets
`HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1`, and invokes the
scientifically unchanged `run_r4_measurements.py`. With a single selected
environment, the dispatcher resolves all 16 frozen cells to
`/root/rivermind-data/envs/probvenance-r4/bin/python`.

`FORMAL R4 EPOCH 1 EXECUTION = NOT YET AUTHORIZED` — this map must be reviewed
and pushed before any real study row is measured.
