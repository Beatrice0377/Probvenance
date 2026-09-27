# R3 Analysis Execution-Entry Gate

Append-only record. This gate freezes the official R3 raw → analysis ingestion /
execution runner and records its structural preflight. It does **not** authorize
or run the official R3 confirmatory statistical analysis.

```text
STATIC SEMANTIC CLOSURE:                    PASS
OFFICIAL INGESTION RUNNER:                  IMPLEMENTED / FROZEN CANDIDATE
OFFICIAL INPUT STRUCTURAL PREFLIGHT:        PASS
OFFICIAL STATISTICAL ANALYSIS:              NOT RUN
EXECUTION AUTHORIZATION:                    NOT GRANTED
NEXT GATE:                                  HUMAN RUNNER AUDIT
```

Verdict wording: **RUNNER CANDIDATE READY FOR HUMAN EXECUTION-GATE AUDIT**.

## 1. Scope

This gate covers the execution chain that will later transform the already-frozen
R3 raw evidence into the already-frozen R3 analysis kernel:

```text
frozen protocol / population
        -> raw evidence index
        -> raw file byte-hash verification
        -> raw-evidence structural validation
        -> condition/model provenance validation
        -> raw item -> R3Item / raw item -> R3WinnerRecord
        -> exact TRAIN / TEST partition
        -> primary / replication condition assembly
        -> build_analysis_artifact()
        -> canonical official analysis output + execution-provenance sidecar
```

The runner reimplements no statistic. Brier, LogLoss, calibration fitting, the
factorial contrasts, the TEST bootstrap, the native-reference assessment, the
TRAIN-refit stability, and the winner/support diagnostics live exclusively in
`experiments/calibration_transport/r3_analysis.py`.

## 2. Frozen identities verified by the runner

```text
protocol fingerprint:            3ef63056ae16b18ad65d9c87d1fbec5b43550873a0e3e25ec0a323f954ee974d
population manifest fingerprint: 40cc9753a711314ff3b25ed6e234d0cbda11f3f60cd87f1d3915195a3d1780b8
measurement code commit:         8b1ea40aee0e7518c2ab3b25a8cc6d4ec2d0f800
raw index SHA256:                b04351acd878161d21022f3e5f5f08da1443977a484f62c8ba465adba051c461
raw index internal fingerprint:  25fa4086e67a1cbd48cb8d857337092b132790ceb04925407649629c35d1bc51
primary raw SHA256:              e7b45e921d35523f9fb6aabaefe10e585f43f35f25e5e4159bb2211cec8b999b
primary evidence fingerprint:    726bb8340aecfa0c98e4d4b7fe1548278f3cc8ff391b9f6d14aa5215e84d7c71
replication raw SHA256:          00a1d04e6cb308cf609ccf3cde69b761497c4a3a110704ea069f3e933cf9248a
replication evidence fingerprint: 378b2676dad4b12be4d57c9030c9d44823df921dc62f4d9b7f73acf79f0d4887
```

Every gate fails closed on mismatch. Raw bytes are hashed before their parsed
content is trusted.

## 3. Audited data flow (with implementing functions)

| Leg | Implementing function | Module |
| --- | --- | --- |
| protocol / design load | `r3_protocol.load_design`, `verify_protocol_identity` | `run_r3_analysis.py` |
| population manifest load | `r3_population.load_manifest`, `verify_manifest_identity` | `run_r3_analysis.py` |
| raw index bytes + SHA256 | `load_index` | `run_r3_analysis.py` |
| raw index structure / provenance | `validate_index` | `run_r3_analysis.py` |
| filename / traversal guard | `guard_raw_filename` | `run_r3_analysis.py` |
| raw artifact bytes + SHA256 | `load_raw_artifact` | `run_r3_analysis.py` |
| raw artifact identity | `verify_raw_identity` | `run_r3_analysis.py` |
| child-plan rebuild + fingerprint | `r3_protocol.build_child_plan`, `verify_child_plan` | `r3_protocol.py` / `run_r3_analysis.py` |
| raw structural validation | `r3_raw_evidence.validate_raw_evidence` (via `map_validated_condition`) | `r3_raw_evidence.py` |
| raw item → `R3Item` | `r3_item_from_evidence` | `run_r3_analysis.py` |
| TEST item → `R3WinnerRecord` | `r3_analysis.winner_record_from_evidence` (via `build_test_winner_records`) | `r3_analysis.py` |
| TRAIN / TEST partition | `partition_evidence_items` | `run_r3_analysis.py` |
| cross-model structural pairing | `verify_cross_condition_pairing` | `run_r3_analysis.py` |
| condition assembly | `prepare_official_inputs` | `run_r3_analysis.py` |
| kernel invocation (once) | `r3_analysis.build_analysis_artifact` (via `execute_official_r3`) | `r3_analysis.py` |
| canonical serialization | `_canonical_text` | `run_r3_analysis.py` |
| execution-provenance sidecar | `build_execution_provenance` | `run_r3_analysis.py` |
| safe two-file write | `_write_text_pair` | `run_r3_analysis.py` |

Order of operations is a contract: hash bytes → validate index metadata → parse
JSON → validate raw evidence structurally → only then map rows. A synthetic spy
test proves mapping never occurs before structural validation.

### Adapter semantics

```text
R3Item.item_id = raw item["item_id"]
R3Item.subject = raw item["subject"]
R3Item.label   = 1.0 if raw item["anchor_correct"] is True else 0.0
R3Item.cat_score = raw item["cat"]["record"]["anchor_score"]
R3Item.ovr_score = raw item["ovr"]["record"]["anchor_score"]
```

`Y_i` remains the frozen externally selected anchor's correctness. Winners,
candidate probabilities, argmax, and any 0.5 threshold never define `Y_i`. CAT /
OVR scores are mapped positionally and never swapped; a synthetic oracle asserts
CAT = 0.17 and OVR = 0.83 map without swap. Winner diagnostics reuse the audited
`winner_record_from_evidence` adapter; the runner writes no second winner adapter.

## 4. The two modes

```text
--validate-inputs-only   byte / structural / wiring preflight only; never enters statistical code
--execute-official-r3    eventual official execution path; calls the frozen kernel exactly once
```

Exactly one mode is required; parsing no mode or both modes fails. `main` in
validate-only mode requires `branch == main` and a clean working tree, and
records `HEAD`, `origin/main`, and ahead/behind. It does not require ahead = 0,
because a clean unpushed local candidate commit is permitted for preflight.
Official execute mode additionally requires `HEAD == origin/main` at `0/0` and
fails closed before analysis otherwise. The runner never fetches.

## 5. CLI scientific configuration surface: NONE

The official CLI exposes no scientific option. There is no `--model`,
`--condition`, `--procedure`, `--family`, `--feature`, `--lambda`,
`--regularization`, `--test-replicates`, `--train-refit-replicates`,
`--bootstrap`, `--metric`, `--loss`, `--direction`, `--population`,
`--manifest`, `--dataset`, `--raw-file`, `--primary-raw`, `--replication-raw`,
`--protocol`, or `--protocol-design`. All model conditions, procedures,
population, replicate counts, and output paths are frozen constants. A
structural parser test asserts the option surface is exactly
`{-h, --help, --validate-inputs-only, --execute-official-r3}`.

The official kernel is invoked with frozen defaults only: the runner never
passes `test_replicates` or `train_refit_replicates`, so official execution uses
TEST bootstrap = 20,000 and TRAIN-refit bootstrap = 2,000.

## 6. Structural preflight result (observed)

`--validate-inputs-only` was run against the canonical frozen official inputs
after the implementation commit. It produced only provenance / completeness
data:

```text
protocol_fingerprint              = 3ef63056...
population_manifest_fingerprint   = 40cc9753...
raw_index_sha256                  = b04351...
raw_index_fingerprint             = 25fa4086...

primary      openbmb/MiniCPM5-2B @ 12a3808a...
             raw_sha256 = e7b45e...  evidence_fingerprint = 726bb834...
             child_plan_fingerprint = 787c6682...
             total_items = 1596  train_items = 456  test_items = 1140
             subjects = 57  test_winner_records = 1140

replication  Qwen/Qwen3.5-2B @ 15852e8c...
             raw_sha256 = 00a1d04e...  evidence_fingerprint = 378b2676...
             child_plan_fingerprint = dc2f5873...
             total_items = 1596  train_items = 456  test_items = 1140
             subjects = 57  test_winner_records = 1140

cross_condition_population_pairing = true
official_confirmatory_statistical_outcome_computed = false
```

No accuracy, risk, Brier, LogLoss, winner agreement, score range, or support
fraction was produced. The preflight created no official result or provenance
file; the working tree remained clean.

## 7. Output, overwrite, and failure contract

Fixed official output paths (never CLI-selectable, never written in this gate):

```text
experiments/calibration_transport/results/r3-confirmatory-analysis-v1.json
experiments/calibration_transport/results/r3-confirmatory-analysis-execution-v1.json
```

Official execute mode fails closed if either path already exists. There is no
`--force`, no overwrite flag, and no auto-numbering. The full analysis payload is
built in memory first; if any gate, fit, endpoint, bootstrap, or write step
raises, no official output or provenance file is created. The two files are
written via same-directory temporary files and rename, with cleanup of any file
created by the invocation if the second finalization fails. Canonical
serialization is UTF-8, sorted keys, indent 2, `allow_nan=False`, trailing
newline.

## 8. Execution-provenance sidecar design

The eventual sidecar records `artifact_type = r3-confirmatory-analysis-execution`,
version 1, the git branch/head/origin_main, the protocol and manifest
fingerprints, the measurement code commit, the raw index filename/SHA256/
fingerprint, both raw inputs (filename, SHA256, evidence fingerprint, model id,
model revision, child-plan fingerprint), the analysis kernel and runner
repo-relative file paths with their SHA256, the Python/platform execution
environment, the frozen replicate counts (20,000 / 2,000) as provenance
statements, the analysis output filename and SHA256, and a canonical provenance
fingerprint. No wall-clock timestamp, duration, or machine-local absolute path
enters the scientific identity, and no outcome interpretation is recorded.

## 9. What this gate does NOT do

- It does not run the official R3 confirmatory statistical analysis.
- It does not compute or print any official R3 statistical outcome.
- It does not load a model, require a GPU, or use the network.
- It does not modify the frozen analysis kernel, protocol, design, population
  manifest, measurement runner, or raw evidence.
- It does not grant execution authorization. The official `--execute-official-r3`
  path remains unrun.

## 10. Artifacts

```text
static semantic closure commit:  9d18f9f0efe6a6089f63e47ce15dc7cf218673db
runner implementation commit:    2d6c3553c650b948f348e1d7d216a7d93dd4326d
runner file:                     experiments/calibration_transport/run_r3_analysis.py
runner file SHA256:              5dfcf531507b447c52e42286784b137676bad8c1fc1b95fcae9735c729167537
analysis kernel file:            experiments/calibration_transport/r3_analysis.py
analysis kernel file SHA256:     819f299304703d27ff89af7e8cfc00e6bffcb8d9ae11d8bb1724db0d7cc6a0c5
machine-readable gate:           experiments/calibration_transport/results/r3-analysis-execution-entry-gate-v1.json
gate fingerprint:                092f6beb8b3d0aabd3680c0bb9b083cd4dcf529ece276cfbe92ea61b387a4419
```
