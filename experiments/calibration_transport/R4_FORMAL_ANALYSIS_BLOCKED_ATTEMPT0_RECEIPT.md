# R4 Formal Scientific Analysis — Blocked Attempt 0 Receipt

Status: **BLOCKED — FORMAL_ANALYSIS_CODE_DEFECT**

This receipt documents blocked formal-analysis **attempt 0**. The success-path
receipt name (`R4_FORMAL_ANALYSIS_EXECUTION_RECEIPT.md`) is intentionally not
occupied by this document and must not be reused here.

Nature: execution-provenance receipt only. This document contains **no numerical
scientific estimate** of any kind (no Brier, no LogLoss, no risk, no Delta, no
interval endpoint, no factorial effect, no direction contrast, no predictor X/Y,
no Spearman value, no calibration coefficient).

---

## 1. Authorization context

```text
task:                 R4 FORMAL SCIENTIFIC ANALYSIS EXECUTION
                      CALIBRATION + RISK + DELTAS + BOOTSTRAP + PREDICTOR
                      FROZEN FULL DAG / NO SCIENTIFIC INTERPRETATION
authorized:           FORMAL R4 CALIBRATION / INFERENCE / PREDICTOR VALIDATION
not authorized:       scientific interpretation
mode:                 execution-only
```

## 2. Entry authority (all verified before execution)

```text
branch:                    main
HEAD:                      b2b94b8175584e517ec011ac53581b9e6c02bc8c
origin/main:               b2b94b8175584e517ec011ac53581b9e6c02bc8c
ahead / behind:            0 / 0
worktree:                  clean
runner source SHA256:      5b4ab21d262afe1b1755120f83afaa37798df3a41dbef8274cd00ede1350f176
runner contract SHA256:    2d8405a145ff416846326913fc403146c7ca8d66a0038b8103eb43c37e7b3335
runner contract fingerprint: 2fe5d962a706c822a63573bbd8e553a44b6b0fd082dd582af8cdaa25bc6c7c60
qualification SHA256:      0ccf0ea20a607cd4f78973eca43f55aa69891893d0850839630bb38251f6fea9
qualification fingerprint: 405f3ffcbf2cc67ff179c75ed157437045c6a726a63ae6b81dede28bcfede5ac
calibration impl SHA256:   e5b00548429b5b0999d5847db47e1f4c1ae113ee19854c053aeaca1058536ec3
inference impl SHA256:     44f8ac3fe3ca0e138beb4f755e9ee65582ed0b09c14ba253bb01062d8ffda554
predictor impl SHA256:     ccbfbbd681cf55d0cb1f7d3f12ba19e5cd68aa4c65d0ebf52045dc8f0fb2787e
r3_protocol SHA256:        46a7c0ec8e5da95a37868d89f5fc110687e66e65599ee4ac3d0602100435197e
r3_analysis SHA256:        819f299304703d27ff89af7e8cfc00e6bffcb8d9ae11d8bb1724db0d7cc6a0c5
raw ledger SHA256:         146ad254dda64778cb684283e24ae1dca2987bc6827652c448739b75ae2e1a6a
raw ledger fingerprint:    2ed383f67be4476024d12a03c26699a1a50ed8656d75bb089986ce558d1be541
input registry fingerprint: b0051d96eaeea693a37a0116ced4eecc7e7a7fcd34d93049b074a7010c8cb355
dependency graph fingerprint: 449c9b19d61e4edbe95ea856b1d13e3b373765f8a9d05931f20e4d12bf28ed9f
analysis preflight fingerprint: 500ae1cb5ee19d030dad6c27a164b84650adbd79d81451f416126892d2e48873
measurement contract fingerprint: 7b126d300e774cb44d2c47fcb12513865d03c2b08ffd03a5ce409b2ea976e1e5
final protocol fingerprint: d1b56d702e1f260cef47eee05b7d878ace07a15168e89408e15e7eb741c0ad34
execution manifest fingerprint: f32381c51db24f5dbeb240b5e0fdf73c59a56a615c8607ad8979e2a7e2586775
inference freeze fingerprint: dcbb7ac9e931145fdee86ab984de1249c1b86ca36ee735b70dafc8cabc06c141
predictor freeze fingerprint: c856fcc161910497a3431593639606682905adcb50fc443455468dfc295d73a9
raw evidence:              16 / 16 cells, 100728 committed rows, paired_complete = true
dependency graph:          20 nodes, unresolved_dependency_count = 0,
                           structurally_unavailable_nodes = []
```

Pre-execution `--validate-only`:

```text
status = PASS
cells = 16, rows = 100728
current directional units = 24, legacy directional units = 8
calibrator fits = 0, metrics computed = 0, bootstrap draws = 0, predictor values = 0
scientific_outputs_computed = false
problems = []
```

## 3. Formal output root start-state

```text
/root/rivermind-data/r4-formal-analysis
start-state: did not exist (clean)
```

## 4. Formal execution invocation

```text
command:
  /root/rivermind-data/envs/probvenance-r4/bin/python \
    experiments/calibration_transport/run_r4_analysis.py --execute-formal-analysis

operational arguments: --execute-formal-analysis only
overrides supplied:    none
  (no bootstrap count, no seed, no PRNG, no family size, no CI level,
   no calibration procedure, no metric, no predictor panel, no threshold,
   no N456/N912 definition)
```

```text
start (UTC):   2026-10-02T04:23:59Z
end   (UTC):   2026-10-02T04:24:08Z
elapsed:       9 seconds
exit code:     1
```

## 5. Block timeline

```text
authority_validation:  COMPLETE   (recorded in runner-checkpoints.json)
input_load:            NOT REACHED
point_estimates:       NOT REACHED
n912_robustness:       NOT REACHED
test_bootstrap:        NOT REACHED
train_refit:           NOT REACHED
predictor:             NOT REACHED
final_assembly:        NOT REACHED
```

The only checkpoint recorded is:

```text
block:            authority_validation
identity:         b0051d96eaeea693a37a0116ced4eecc7e7a7fcd34d93049b074a7010c8cb355
output_fingerprint: 7b126d300e774cb44d2c47fcb12513865d03c2b08ffd03a5ce409b2ea976e1e5
status:           COMPLETE
```

## 6. Abort condition (structural)

Uncaught exception raised by the frozen calibration implementation while the
runner was building the **primary** panel inputs (first `build_panel_inputs`
call, `budget = N456`):

```text
Traceback (most recent call last):
  File "experiments/calibration_transport/run_r4_analysis.py", line 1915, in <module>
    raise SystemExit(main())
  File "experiments/calibration_transport/run_r4_analysis.py", line 1151, in main
    return execute_formal_analysis(args)
  File "experiments/calibration_transport/run_r4_analysis.py", line 1775, in execute_formal_analysis
    primary = build_panel_inputs(
  File "experiments/calibration_transport/run_r4_analysis.py", line 697, in build_panel_inputs
    fits[cross_key] = fit_procedure(
  File "experiments/calibration_transport/run_r4_analysis.py", line 640, in fit_procedure
    fit = r4_calibration_families.fit_beta_fixed_decision_probability(scores, labels)
  File "experiments/calibration_transport/r4_calibration_families.py", line 584, in fit_beta_fixed_decision_probability
    raise BetaImplementationError("no constraint face produced an accepted optimum")
r4_calibration_families.BetaImplementationError: no constraint face produced an accepted optimum
```

### 6.1 Structural classification

`BetaImplementationError` is a **declared frozen error class**
(`r4_calibration_families.py:161`, `class BetaImplementationError(RuntimeError)`).
It is raised when no constraint face produced an optimum accepted under the
frozen KKT/convergence contract — i.e. frozen fitting gate 9
("unique finite accepted optimum", `R4_CALIBRATION_FAMILY_FREEZE.md:239`) was
not satisfied on real data.

The frozen implementation distinguishes:

```text
BetaFitIneligible            → eligibility gate (SINGLE_CLASS /
                               INSUFFICIENT_DISTINCT_SCORES /
                               MONOTONE_SEPARATION); the runner maps this to INELIGIBLE
BetaContractViolation        → structural input violation; the runner maps this to FAILED
BetaImplementationError      → "no constraint face produced an accepted optimum";
                               the runner has no frozen status mapping for it
```

`run_r4_analysis.py::fit_procedure` (lines 636-648) catches only
`BetaFitIneligible` and `BetaContractViolation` for the `B-beta` procedure, so
`BetaImplementationError` propagated and terminated the run.

This is **not** a frozen scientific terminal status (`COMPLETE` / `INCOMPLETE` /
`UNDEFINED` / `DEPENDENCY_UNAVAILABLE`). It is an uncaught implementation
exception on valid frozen input, therefore a STOP condition under the task's
blocker rules (§45 operational blocker / §65 FORMAL_ANALYSIS_CODE_DEFECT).

### 6.2 Triggering unit (structural, inferred from frozen iteration order)

No scientific re-execution was performed. The triggering fit is determined
structurally: the exception propagates from the first uncaught raise, and the
iteration order is frozen and deterministic.

```text
panel:        primary (current-generation cells)
budget:       N456
cell index 0: falcon-h1-7b-instruct__r4-hellaswag-activity-primary
              (model_key falcon-h1-7b-instruct, population_id r4-hellaswag-activity-primary)
direction:    CAT->OVR        (authority.direction_order[0])
side:         cross           (fit on SOURCE measurement = CAT; fitted before native)
procedure:    B-beta          (authority.procedure_order[5], last)
```

## 7. Outcome firewall

```text
outcome inspection performed:   NO
committed-row counts read:      YES (structural only: 100728 rows, 16/16 cells)
transaction states read:        YES (structural only)
individual CAT/OVR scores read: NO
mean score / accuracy / Y rate: NOT COMPUTED
model / method comparison:      NOT COMPUTED
Brier / LogLoss:                NOT COMPUTED
risk / Delta / CI / predictor:  NOT COMPUTED
plots:                          NONE
```

No scientific output of any kind was produced. `scientific_outputs_computed = false`.

## 8. Preserved state — quarantine

The blocked attempt's live state was moved (not copied) into an isolated
read-only quarantine and the live formal root was removed:

```text
quarantine root: /root/rivermind-data/r4-formal-analysis-aborted/
                 attempt0-beta-gate9-runner-defect/
  formal-analysis-root/runner-checkpoints.json
    sha256 abe51ff413d9cb86a4ba1c624792ebff44db6d666d3e352b166632d34228f3c2
    size   306
  logs/formal-run.log
    sha256 d7280713053cbdff8ebbf4a05d654376ad60701a06e235784ccde1ea9c3297c6
    size   1501
  QUARANTINE_MANIFEST.json
    sha256 8eccaa06fa97c0215c1c21737f9e92a09e3993cc8fad756322c0c6c91d6da788
    quarantine_manifest_fingerprint
           52dc46f6093c75d30822d6ca79639e295da7c3717629162f7ac6ad0f88e2b3e1
    last_committed_block authority_validation
    scientific_outputs_computed false
    disposition READ_ONLY / DO_NOT_RESUME / DO_NOT_MERGE / DO_NOT_USE_AS_RESULT

live formal root: /root/rivermind-data/r4-formal-analysis
  state after quarantine: DOES NOT EXIST
```

## 9. Declarations

```text
NO CODE CHANGE                       (run_r4_analysis.py, r4_calibration_families.py,
                                      r4_inference.py, r4_predictor.py all byte-identical)
NO STATISTICAL CHANGE
NO RESULT-DEPENDENT RETRY
NO PATCH
NO CONTINUE
NO RERUN
NO FALLBACK
NO FAMILY SHRINKING
NO COMPLETE-CASE RESCUE
NO SCIENTIFIC INTERPRETATION
NO PUSH PERFORMED
```

## 10. Provenance statement

The formal R4 scientific analysis did not complete. No formal scientific
estimate (calibration, risk, Delta, bootstrap interval, factorial effect,
direction contrast or predictor statistic) was computed or frozen. The single
recorded block (`authority_validation`) is execution provenance only and
contains no scientific output. Nothing in this receipt may be used as a
scientific result.

## 11. Required adjudication (human / ChatGPT)

The frozen status contract has no mapping for frozen fitting gate 9 failure
(`BetaImplementationError`). Adjudication is required before any further action,
for example:

1. whether gate-9 failure must propagate as a frozen terminal scientific status
   (which would require an explicit amendment to the frozen status contract and
   the runner — not an on-site patch); and/or
2. whether the frozen beta numerical solver contract itself requires review.

Until that adjudication, the formal execution must not be resumed, patched or
rerun.
