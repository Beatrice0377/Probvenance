# R4 Epoch 1 — Pre-Row1 MMLU Row Adapter Fix

**Status:** `R4 EPOCH 1 PRE-ROW1 CODE DEFECT CORRECTION = PASS`
**Classification:** pre-row1 implementation defect correction (one field).
**Scientific protocol impact:** `NONE` — `scientific semantics changed = false`.

---

## 1. Defect

`experiments/calibration_transport/run_r4_measurements.py::_mmlu_rows()` built
the normalized measurement row without the frozen `question` field.
`measure_item()` requires `row["question"]`, so the first MMLU cell failed
closed with `KeyError: 'question'` before any model forward.

See `R4_EPOCH1_PRE_ROW1_CODE_DEFECT_RECEIPT.md` for the containment record.

## 2. Exact fix

Single insertion in `_mmlu_rows()`:

```diff
@@ -437,6 +437,7 @@ def _mmlu_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
             "split": str(item["split"]),
             "stratum": str(item["subject"]),
             "group_id": None,
+            "question": str(item["question"]),
             "candidate_names": list(r3_population.R3_CANDIDATE_NAMES),
             "candidate_descriptions": [str(choice) for choice in item["choices"]],
             "ground_truth_index": int(item["answer_index"]),
```

```text
path:      experiments/calibration_transport/run_r4_measurements.py
function:  _mmlu_rows()
insertion: 1 line (line 440)
```

The value is a direct string pass-through of the frozen manifest item's
`question`. Nothing is reconstructed, whitespace-normalized, stripped, or
rewritten.

Not done (deliberately): no loader refactor, no adapter unification, no schema
rename, no `measure_item` change, no scorer/backend/prompt-rendering change, no
registry change, no change to candidate text, `D_i`, ground truth, `item_id`,
population order, or split identity.

## 3. Why scientific semantics are unchanged

Mechanical diff of the fix: exactly **one added line**, no removals, no
modifications.

Pre/post equivalence was verified model-free over the full frozen MMLU
population:

```text
MMLU TRAIN normalized rows = 456
MMLU TEST  normalized rows = 1140
TOTAL                      = 1596

rows with a present, non-empty string `question` = 1596 / 1596
missing_question = 0
```

Per-row assertions over all 1596 rows (and against the frozen source manifest):

```text
item_id                unchanged (identity and order preserved)
source_split           unchanged
source_row_index       unchanged
split                  unchanged (TRAIN / TEST)
stratum (subject)      unchanged
group_id               unchanged (None)
candidate_names        unchanged (option-0..option-3)
candidate_descriptions unchanged (source choices, in source order)
ground_truth_index     unchanged (source answer_index)
anchor_index           unchanged (frozen anchor rule)
```

The only schema difference is the presence of the `question` field.

Anchor rule re-verified against the frozen manifest; no anchor, ground truth,
candidate, split, or stratum value moved.

## 4. Cross-population row contract

A shared contract test now pins the fields `measure_item()` depends on for
every population adapter, so an adapter omission is caught **before** a model is
loaded:

```text
MEASUREMENT_REQUIRED_ROW_FIELDS = (
    "item_id", "question", "candidate_names", "candidate_descriptions",
    "anchor_index", "ground_truth_index", "split",
)
```

Covered: `mmlu`, `hellaswag`, `medmcqa` — all PASS.

## 5. Tests added

In `tests/test_r4_measurements.py`, section
`Pre-row1 defect closure: population adapter -> measurement row contract`:

| test | covers |
| --- | --- |
| `test_mmlu_normalized_rows_carry_the_frozen_question` | TRAIN + TEST; `question` is a non-empty `str` and equals the source manifest question |
| `test_mmlu_normalized_rows_are_structurally_complete` | full 1596-row structural scan (identity, split, candidates, anchor, ground truth) |
| `test_mmlu_normalized_row_order_and_identity_are_stable` | item-id order, candidate descriptions, ground truth, stratum, source row index vs the frozen manifest |
| `test_every_population_adapter_exposes_the_measurement_row_contract` | parametrized `mmlu` / `hellaswag` / `medmcqa` |
| `test_mmlu_normalized_row_measures_through_the_fake_backend` | a real MMLU normalized row driven through the measurement path with a fake runtime — exactly 1 CAT + 1 OVR = 2 logical calls, no real model |

The original defect is therefore closed by a direct test: the MMLU adapter
output now measures without `KeyError`, using a synthetic backend only.

## 6. Tests passed

```text
tests/test_r4_measurements.py            94 passed (twice: 12.11 s / 12.25 s)
tests/test_r4_epoch1_dispatch.py         13 passed
tests/test_r4_predictor.py               69 passed
tests/test_r4_inference.py              115 passed
tests/test_r4_calibration_families.py    53 passed
pytest -q -p no:randomly (full repo)     RC = 0
py_compile                               OK
ruff check experiments/calibration_transport tests   All checks passed!
git diff --check                         OK
```

## 7. Sixteen-command structural audit

All 16 frozen dispatcher cells were validated model-free (no forward):

```text
cell_count               = 16
structural_commands_ok   = 16/16
interpreters             = ['/root/rivermind-data/envs/probvenance-r4/bin/python']
environments             = ['R0']
```

Each command: contains `--model-role <model>` and `--population <population>`,
resolves to the R0 interpreter, carries the offline flags, and parses cleanly
through the runner's own `parse_args` with the expected model role, population,
staging root, and `--resume`. Legacy × MMLU combinations are absent.

## 8. Runbook correction (documentation only)

`R4_EPOCH1_EXECUTION_RUNBOOK.md` §2 dispatcher example omitted `--model-role`,
which `run_r4_measurements.main()` requires. The example now includes it, with a
note that the dispatcher's `--model-key` is used only to resolve the frozen
interpreter and is **not** forwarded to the runner.

The dispatcher's automatic behaviour was not changed and the runner's CLI
contract was not changed.

## 9. Frozen protocol and environment integrity

Unchanged and re-hashed byte-identical:

```text
R4_POPULATION_FREEZE.md                  850b6b24da61f416
R4_CALIBRATION_FAMILY_FREEZE.md          1fd06ad4804cb64c
R4_INFERENCE_MULTIPLICITY_FREEZE.json    fdc07904056fd72b
R4_PREDICTOR_FREEZE.json                 423c5cdaf68ce7cd
R4_MEASUREMENT_EXECUTION_CONTRACT.json   c9d61ed3011a3d42
R4_FINAL_PROTOCOL_FREEZE.json            8d105b2010227b0b
R4_EXECUTION_MANIFEST_FREEZE.json        8b56f62bfe053ddb
r3_protocol.py                           46a7c0ec8e5da95a
r3_protocol_design.json                   cb54090f08c99c1a
```

All-reference environment map unchanged:

```text
R4_EPOCH1_MODEL_EXECUTION_ENVIRONMENT_MAP.json
environment_map_fingerprint = aebeb528b6db1d09d23c83ff8078e5a9cb0b779c8fbada0f19617c878cfb45eb  (recomputed match)
distinct_selected_environments = ["R0"]
all six models -> /root/rivermind-data/envs/probvenance-r4
```

R0 runtime unchanged (no install, no uninstall):

```text
python 3.11.13
torch 2.8.0+cu128 (cuda 12.8, available True)
transformers 5.17.0
tokenizers 0.23.2
safetensors 0.8.0
huggingface_hub 1.32.0
numpy 2.3.2
scipy 1.16.3
triton 3.4.0
```

## 10. Outcome firewall

```text
EPOCH 1 REAL STUDY FORWARDS = 0
EPOCH 1 COMMITTED STUDY ROWS = 0
```

No real MMLU / HellaSwag / MedMCQA forward was executed during this task. No
calibration was fitted; no Brier, LogLoss, delta, bootstrap, or predictor value
was computed; no result was interpreted.

## 11. Measurement code identity

The production runner changed, so the former commit
`8121fcd4a802651a51bde76d1697ac2e50bdf5a5` is **no longer** the future formal
measurement code identity. The fix commit itself becomes the new code
provenance authority and must be recorded as `measurement_code_commit` for every
future formal cell.

No scientific protocol fingerprint was modified.
