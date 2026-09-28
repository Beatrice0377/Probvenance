# R3 Analysis Execution-Runner Re-audit

Append-only record. This re-audit supersedes nothing; it adds the closure for a
human patch-level finding against the runner frozen in
`R3_ANALYSIS_EXECUTION_ENTRY_GATE.md`. It does **not** authorize or run the
official R3 confirmatory statistical analysis.

```text
STATIC SEMANTIC CLOSURE:                    REMAINS PASS
OFFICIAL INGESTION RUNNER:                  ENTRYPOINT LOCKED TO CANONICAL PATH
OFFICIAL INPUT STRUCTURAL PREFLIGHT:        PASS
OFFICIAL STATISTICAL ANALYSIS:              NOT RUN
EXECUTION AUTHORIZATION:                    NOT GRANTED
NEXT GATE:                                  HUMAN PATCH-LEVEL RE-AUDIT
```

## 1. Human re-audit finding

The human patch-level audit of the runner implementation commit
`2d6c3553c650b948f348e1d7d216a7d93dd4326d` found:

```text
The public function named execute_official_r3() still accepted:
  - a PreparedInputs argument
  - a custom builder
  - a custom output_path
  - a custom provenance_path
```

Classification:

```text
execution-integrity MUST-FIX
```

Why this is an execution-integrity issue and not a scientific/statistical bug:

- The frozen design, the analysis kernel, the raw evidence, the population, and
  the protocol were all correct and unchanged.
- The defect was that the function *named* as the single official execution
  entrypoint could be programmatically called with injected inputs, a substitute
  analysis kernel, and alternate output paths. That breaks the provability that
  "official execution entrypoint == the unique frozen execution path".

Impact assessment:

```text
scientific design impact:    NONE
statistical kernel impact:   NONE
raw evidence impact:         NONE
official result impact:      NONE (the official analysis has never been run)
```

Secondary SHOULD-FIX found in the same audit:

```text
_write_text_pair() appended the temp path to cleanup tracking only AFTER
tmp.write_text() returned. If write_text created / partially wrote the temp
file and then raised, cleanup might not know the temp file existed.
```

## 2. Corrected official entrypoint

`execute_official_r3` is now a zero-argument public official entrypoint:

```python
def execute_official_r3() -> dict[str, Any]:
```

It no longer accepts any parameter. Inside it uses only canonical dependencies:

```text
verify_git_state(require_synchronized=True)
OFFICIAL_ANALYSIS_OUTPUT_PATH
OFFICIAL_EXECUTION_PROVENANCE_PATH
prepare_official_inputs()
r3_analysis.build_analysis_artifact
```

Execution order (contract):

```text
synchronized Git gate
        -> canonical output paths absent
        -> canonical official input preparation
        -> the single canonical analysis kernel
        -> canonical serialization
        -> canonical provenance
        -> canonical result/provenance pair write
```

## 3. Injection surfaces closed

```text
PreparedInputs injection:            FORBIDDEN
builder injection:                   FORBIDDEN
analysis output path override:       FORBIDDEN
provenance output path override:     FORBIDDEN
```

The kernel is still invoked with frozen defaults only; the runner never passes
`test_replicates` or `train_refit_replicates`, so official execution uses TEST
bootstrap = 20,000 and TRAIN-refit bootstrap = 2,000. Replicate counts are not
runtime knobs.

## 4. CLI wiring

```text
--execute-official-r3  ->  execute_official_r3()   # zero-argument call
--validate-inputs-only ->  verify_git_state(require_synchronized=False)
                           + prepare_official_inputs()
                           + structural preflight output
```

`main()` does not prepare inputs before the execute call: preparation is the
official wrapper's internal responsibility. Validate-only never enters the
statistical kernel and never calls `execute_official_r3`.

## 5. Temporary-file cleanup fix

`_write_text_pair` now registers the temp path in cleanup tracking **before**
attempting the write:

```python
temps.append(tmp)
tmp.write_text(text, encoding="utf-8")
os.replace(tmp, final)
finals.append(final)
temps.remove(tmp)
```

Synthetic tests prove that a partial write failure on the first or the second
temp file leaves neither the final files nor the temp files behind, and that a
second-finalize (`os.replace`) failure still removes the already-renamed first
final and both temps. The previously frozen second-finalize contract is
preserved.

## 6. Inherited verification exception (reported accurately)

```text
uv run ruff check .:
PASS

ruff format --check on this round's two Python files:
PASS (2 files already formatted)

uv run ruff format --check . (whole repo):
still reports exactly one inherited frozen Markdown formatting exception:
  experiments/calibration_transport/R3_ANALYSIS_ENTRY_AUDIT_ERRATUM.md

That file has not been modified since the static closure; this round did not
rewrite historical provenance in order to make the formatter pass.
```

This is not a runner failure and is not recorded as a whole-repo format PASS.

## 7. Structural validate-only preflight (observed)

After the entrypoint-fix commit, `--validate-inputs-only` was run against the
canonical frozen official inputs. It produced only provenance / completeness
data:

```text
protocol_fingerprint              = 3ef63056...
population_manifest_fingerprint   = 40cc9753...
raw_index_sha256                  = b04351...
raw_index_fingerprint             = 25fa4086...

primary      openbmb/MiniCPM5-2B @ 12a3808a...  raw_sha256 = e7b45e...
             total_items = 1596  train_items = 456  test_items = 1140
             subjects = 57  test_winner_records = 1140
replication  Qwen/Qwen3.5-2B @ 15852e8c...      raw_sha256 = 00a1d04e...
             total_items = 1596  train_items = 456  test_items = 1140
             subjects = 57  test_winner_records = 1140

cross_condition_population_pairing = true
official_confirmatory_statistical_outcome_computed = false
```

No accuracy, risk, Brier, LogLoss, winner agreement, score range, or support
fraction was produced. No official result or provenance file was created; the
working tree remained clean; both official output paths were confirmed absent.

## 8. Artifacts

```text
static semantic closure commit:      9d18f9f0efe6a6089f63e47ce15dc7cf218673db
runner initial implementation:       2d6c3553c650b948f348e1d7d216a7d93dd4326d
initial execution-entry gate:        77b07fc1e4e107f3026750fa8f9d5ca1d04cd5cd
entrypoint fix commit:               3f18b1bb4eeac9e92bac00f9c0ba8461867d83d5

runner file:        experiments/calibration_transport/run_r3_analysis.py
runner file SHA256: 2872e121fd3919f3dd0431dab3cf3ba7d7ddde82380d274f682d9ddc0aef18fd
kernel file:        experiments/calibration_transport/r3_analysis.py
kernel file SHA256: 819f299304703d27ff89af7e8cfc00e6bffcb8d9ae11d8bb1724db0d7cc6a0c5

machine-readable re-audit:
  experiments/calibration_transport/results/r3-analysis-execution-entry-reaudit-v1.json
reaudit_fingerprint: 986d7d02501a949e9aedda52b516f1606c8a8b6723c83a6c8d9469068157353e
```

The runner candidate is ready for human patch-level re-audit. Execution
authorization is not granted; the official `--execute-official-r3` path remains
unrun.
