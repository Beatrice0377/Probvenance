# R3 Confirmatory Analysis — Execution Receipt

This is an append-only, machine-readable-plus-human-readable receipt recording the
official R3 confirmatory analysis execution. It records **execution/provenance metadata
only**. It contains no statistical outcome values, no calibration parameters, no risk or
loss values, no interval values, and no interpretation.

## Execution summary

```text
official R3 confirmatory execution:  COMPLETED
execution_attempt_count:             3
automatic_retry_count:               0
human_authorized_retry_count:        2
attempt 1:  externally terminated before artifact (outer shell-tool timeout)
attempt 2:  externally terminated before artifact (host system reboot / system update)
attempt 3:  completed, exit code 0, official artifacts created
```

## Attempts

| # | authorization | launcher | status | termination reason | exit code |
|---|---|---|---|---|---|
| 1 | initial-human-authorized-execution | shell-tool-background | externally-terminated-before-artifact | outer-shell-tool-timeout-process-group-termination | none |
| 2 | human-authorized-operational-retry | tmux-detached | externally-terminated-before-artifact | host-system-reboot-during-system-update | none |
| 3 | human-authorized-operational-retry | tmux-detached | completed | - | 0 |

Attempts 1 and 2 are recorded permanently. They are classified as externally terminated
before any artifact was produced. This does not assert that no transient computation ever
occurred; it asserts that no official statistical outcome was persisted, externalized, or
observed, and that no official artifact or temporary file remained.

## Detached supervision

The only approved detached supervisor is `tmux`. A harmless detached probe
(marker `probe-ok`) was validated before attempt 2 and survived the original 60-second
tool-lifecycle boundary. Attempt 3 reused the same validated detached mechanism.

```text
tmux version:        3.4
socket:              probvenance-r3-retry
probe status:        passed
probe survived 60s:  true
```

## Attempt-3 wrapper

```text
path:                         /tmp/probvenance-r3-attempt3/run.sh
sha256:                       be62f1c36053cf1a80e70ca6d3060ff63dcadfa4fae1b95be9713fc094b29e3f
--execute-official-r3 count:  1
contains retry/loop:          false
```

## Frozen identities

```text
execution code commit:        0c16ca2460de8b18433a9c677b3e6989b0736f9f
execution origin/main:        0c16ca2460de8b18433a9c677b3e6989b0736f9f
result artifact commit:       c68c7e3ac725de1bc5db369cb7c951a810ed80f9
protocol fingerprint:         3ef63056ae16b18ad65d9c87d1fbec5b43550873a0e3e25ec0a323f954ee974d
population manifest fp:       40cc9753a711314ff3b25ed6e234d0cbda11f3f60cd87f1d3915195a3d1780b8
measurement code commit:      8b1ea40aee0e7518c2ab3b25a8cc6d4ec2d0f800
raw index sha256:             b04351acd878161d21022f3e5f5f08da1443977a484f62c8ba465adba051c461
raw index fingerprint:        25fa4086e67a1cbd48cb8d857337092b132790ceb04925407649629c35d1bc51
MiniCPM raw sha256:           e7b45e921d35523f9fb6aabaefe10e585f43f35f25e5e4159bb2211cec8b999b
MiniCPM evidence fp:          726bb8340aecfa0c98e4d4b7fe1548278f3cc8ff391b9f6d14aa5215e84d7c71
Qwen raw sha256:              00a1d04e6cb308cf609ccf3cde69b761497c4a3a110704ea069f3e933cf9248a
Qwen evidence fp:             378b2676dad4b12be4d57c9030c9d44823df921dc62f4d9b7f73acf79f0d4887
analysis runner sha256:       2872e121fd3919f3dd0431dab3cf3ba7d7ddde82380d274f682d9ddc0aef18fd
analysis kernel sha256:       819f299304703d27ff89af7e8cfc00e6bffcb8d9ae11d8bb1724db0d7cc6a0c5
```

## Official artifacts (frozen)

```text
experiments/calibration_transport/results/r3-confirmatory-analysis-v1.json
  sha256: 27b945097a0b6156998a47112437c3b258037db2c9888cea20e97b52075be796

experiments/calibration_transport/results/r3-confirmatory-analysis-execution-v1.json
  sha256: 9992ceefba32f4d0f55e692a0c60472a05751bdca316993ed3f98e220b0f6deb
  execution_fingerprint: e738be013fd0f98a6b0ae635e09420e65de9c91b3b819aa11c1ff7ed2901f479
```

## Post-outcome invariants

```text
code_changed_after_outcome:                 false
analysis_rerun_after_outcome:               false
post_hoc_statistical_analysis_performed:    false
scientific_interpretation_performed:        false
official_result_frozen:                     true
push:                                       false
```

## Receipt fingerprint

```text
receipt_fingerprint: b49e2ac5c0809b727843468120bf3b15a695e981dd3556ca38fb20d1eca74da7
```

This receipt records execution provenance only. It does not authorize or perform any
scientific interpretation of the frozen official R3 results.
