# R4 Final Integrated Protocol — Semantic Candidate

```text
status                       = CANDIDATE
formal_execution_authorized  = false
```

This document is the human-readable companion to
`R4_FINAL_PROTOCOL_SEMANTIC_CANDIDATE.json`. It mechanically integrates the
already frozen R4 design layers into a single candidate authority for a future
formal execution. It is **not** a final freeze and **not** an execution
authorization.

```text
R4 FINAL INTEGRATED PROTOCOL = CANDIDATE
FINAL PROTOCOL STATUS        = NOT FROZEN
FORMAL R4 EXECUTION          = NOT AUTHORIZED
```

---

## 1. Integrated authorities

| Layer | Artifact | Identity |
| --- | --- | --- |
| Population | `R4_POPULATION_FREEZE.md` | `850b6b24da61f416b76d0bac83a4ba2775d3002e94894f003fd2e0a5488fee2a` |
| Calibration family | `R4_CALIBRATION_FAMILY_FREEZE.md` | `1fd06ad4804cb64cd9220cc86187e26f6d690fba977bd76918e057bab418cdff` |
| Calibration implementation environment | `R4_CALIBRATION_IMPLEMENTATION_ENVIRONMENT.md` | `69af279986353cdc9bce33dd175a1a1f7f198056e445281bc4d13849cc5e104c` |
| Calibration implementation engineering | `R4_CALIBRATION_FAMILY_IMPLEMENTATION_ENGINEERING.md` | recorded in the JSON authority block |
| Inference / multiplicity | `R4_INFERENCE_MULTIPLICITY_FREEZE.json` | freeze fingerprint `dcbb7ac9e931145fdee86ab984de1249c1b86ca36ee735b70dafc8cabc06c141` |
| Inference implementation provenance | `R4_INFERENCE_IMPLEMENTATION_PROVENANCE_CLOSURE.md` | `22f7f93c742cb7c1b1865c133e635b5e6903d6e879f4e5693bc1eaf2e28438df` |
| Predictor | `R4_PREDICTOR_FREEZE.json` | freeze fingerprint `c856fcc161910497a3431593639606682905adcb50fc443455468dfc295d73a9` |
| Predictor implementation provenance | `R4_PREDICTOR_IMPLEMENTATION_PROVENANCE_CLOSURE.md` | recorded in the JSON authority block |
| R3 protocol | frozen R3 | `3ef63056ae16b18ad65d9c87d1fbec5b43550873a0e3e25ec0a323f954ee974d` |

Every authority path and SHA256 recorded in the candidate JSON was re-verified
against the files on disk at generation time.

---

## 2. Evidence grid

### 2.1 Prospective R4 primary panel

```text
4 current-generation models x 3 populations x 2 directions
= 12 model-population cells
= 24 directional units
```

Models: `allenai/Olmo-3-7B-Instruct`, `tiiuae/Falcon-H1-7B-Instruct`,
`ibm-granite/granite-4.0-h-tiny`, `Qwen/Qwen3.5-9B`.
Populations: `r4-mmlu-57-subject`, `r4-hellaswag-activity-primary`,
`r4-medmcqa-subject-primary`.

### 2.2 R3 frozen MMLU continuity evidence

`openbmb/MiniCPM5-2B` and `Qwen/Qwen3.5-2B`. Status `FROZEN_EXISTING`,
`DO_NOT_RERUN`.

### 2.3 New-population legacy extension

```text
2 legacy models x {HellaSwag, MedMCQA} x 2 directions
= 4 model-population cells
= 8 secondary directional units
```

---

## 3. Formal measurement population roles

| Population | R3 legacy | Current generation |
| --- | --- | --- |
| MMLU | frozen historical evidence | future R4 measurement |
| HellaSwag | — | primary panel |
| MedMCQA | — | primary panel |

For HellaSwag and MedMCQA the two legacy models provide secondary lineage
continuity only.

---

## 4. Population TRAIN budgets

* Primary: `N456` for all primary calibration procedures.
* Secondary robustness: `N912`, with `TRAIN456 ⊂ TRAIN912` and the same TEST.
* `N912` cannot rescue `N456`.
* TEST is the full frozen eligible population, with no subsampling.

---

## 5. Fixed-event semantics

```text
D_i  = externally frozen designated candidate
GT_i = source ground truth
Y_i  = 1[D_i = GT_i]
```

Both CAT and OVR measure `P(D_i correct)`. The winner event must not be
redefined.

---

## 6. Anchor identity

```text
protocol_id      = r4-fixed-event-anchor-deterministic-source-index-hash
protocol_version = 1
```

The rule and its forbidden inputs are recorded in the JSON. The manifest records
the frozen anchor protocol identity per population. A different anchor rule must
never be generated.

---

## 7. Measurement protocol integration

* CAT: restricted categorical probability for the frozen designated candidate
  `D_i`.
* OVR: an independent proposition for the same designated candidate `D_i`.
* Verbalizer gate (exact single-token continuation, distinct ids, no
  leading-space fallback, no capitalization fallback, no multi-token sum, no
  alternate verbalizer, no tokenizer monkey-patch). The frozen Olmo-3 reference
  ids are CAT `A=32, B=33, C=34, D=35` and OVR `yes=9891, no=2201`; every model
  in the panel must pass its own exact tokenizer gate before measurement.

---

## 8. Models

| Role | Model | Revision |
| --- | --- | --- |
| current-generation primary | `allenai/Olmo-3-7B-Instruct` | `6e5971d9eba42665f5bd5a0fcf047f299ce1dccc` |
| current-generation primary | `tiiuae/Falcon-H1-7B-Instruct` | `41e72f27effbab80cd45b6e884688452253a3686` |
| current-generation primary | `ibm-granite/granite-4.0-h-tiny` | `791e0d3d28c86e106c9b6e0b4cecdee0375b6124` |
| current-generation primary | `Qwen/Qwen3.5-9B` | `c202236235762e1c871ad0ccb60c8ee5ba337b9a` |
| legacy lineage continuity | `openbmb/MiniCPM5-2B` | `12a3808a956f869c767195e9266b59c4d21d92e2` |
| legacy lineage continuity | `Qwen/Qwen3.5-2B` | `15852e8c16360a2fea060d615a32b45270f8a8fc` |

---

## 9. Calibration family panel

Exactly six procedures:

```text
P-low, P-historical, L-low, L-historical, I-isotonic, B-beta
```

The core four keep their factorial role; `I-isotonic` and `B-beta` keep their
standalone-extension role. A seventh procedure is `FORBIDDEN`. This is not a
six-cell factorial.

Frozen scientific fingerprints:

| Procedure | Fingerprint |
| --- | --- |
| P-low | `7a8e13d51e131f2102cca4e00b172c8bbb2eb49e591acd3746aeb64d003c8857` |
| P-historical | `a44e9217dd43e5e29d859c8dd2dc510a5876db4d46a8e0cc2fd4f1df3121a423` |
| L-low | `91d7d506275aade7d4676c39722ac2c4d975de7967a25a808395c056307ad619` |
| L-historical | `23ec12bbf4a809ba2f419491df80d1f228d3fd778d848115839aab3697f9dd58` |
| I-isotonic | `cd13bc07bf92f3375bcd16d57fa5f515cd40f68199b57181791f85c58be8c244` |
| B-beta | `f4b710fb98f7c3056794aa709d53309f462a8f598cef8089d2f9c0ed6f7e37ff` |

---

## 10. Primary metrics

```text
Primary       = Brier
Secondary     = exact LogLoss
Reliability   = descriptive
```

No additional confirmatory metric. No post-calibration epsilon clipping; exact
`0.0` / `1.0` are preserved and exact LogLoss may be `+infinity`.

---

## 11. Inference integration

* TEST bootstrap: 20000 replicates, population-specific resampling semantics.
* TRAIN-refit stability: 2000 replicates, separate from the TEST interval.
* Family sizes: primary 12, extension 8, direction-difference 6,
  native-reference 12.
* Deltas: `Delta_deploy = R_cross - R_raw`,
  `Delta_transport = R_cross - R_native`, `Delta_native = R_native - R_raw`.

---

## 12. Predictor integration

* Primary predictor: `r4-target-range-exceedance-warning` (X_range).
* Primary validation: the 16 held-out HellaSwag + MedMCQA current-generation
  units.
* R4 MMLU: development / continuity.
* Primary predictor target: `r4-core4-mean-transport-penalty`.
* Fixed panel, target-label-free.

---

## 13. Execution DAG

```text
 1. verify all frozen authorities / hashes
 2. verify environment / model revisions / tokenizer verbalizers
 3. perform formal raw fixed-event measurement
 4. freeze raw measurement evidence artifact
 5. verify 100% required paired completeness
 6. fit primary N456 calibrators
 7. fit secondary N912 robustness calibrators where declared
 8. compute primary Brier unit risks / deltas
 9. execute frozen TEST bootstrap inference
10. execute TRAIN-refit stability analysis separately
11. compute exact LogLoss secondary
12. compute descriptive reliability / subgroup diagnostics
13. construct frozen predictor X values without target labels
14. validate predictor against frozen inference outcomes
15. assemble official R4 result artifact
16. interpret only after artifact identities are fixed
```

Predictor tuning must never be inserted after outcomes, and the protocol may not
change after outcome access.

---

## 14. Formal execution stage barriers

```text
PRE_MEASUREMENT
RAW_MEASUREMENT_COMPLETE
CALIBRATION_FITS_COMPLETE
PRIMARY_ANALYSIS_COMPLETE
SECONDARY_ANALYSIS_COMPLETE
PREDICTOR_VALIDATION_COMPLETE
FINAL_RESULT_COMPLETE
```

A later stage may consume only immutable artifacts produced by an earlier stage.
The protocol may never be edited while results are visible.

---

## 15. Raw measurement provenance contract

Every future `model × population × item` raw record must carry: model id, model
revision, population identity, item identity, split, anchor `D_i`, ground truth
identity, `Y`, CAT score/state, OVR score/state, measurement protocol
identities, and runtime provenance. This candidate must **not** generate these
outcomes.

---

## 16. Completeness gate before fitting

* Before formal calibration fitting: verify required TRAIN rows complete.
* Before formal TEST analysis: verify required TEST paired measurements
  complete.
* Forbidden: row substitution, complete-case deletion, winner agreement
  filtering.

---

## 17. Calibration fit artifact contract

Every future fitted-map artifact must record model, population, budget,
measurement, procedure, procedure scientific fingerprint, implementation id,
training manifest identity, training row identities, fitted state, fit status
and failure status. Solver provenance is never written as a scientific
procedure identity.

---

## 18. Analysis artifact contract

Every future official inference artifact must reference the final protocol
fingerprint, population fingerprints, measurement evidence fingerprints,
calibration fit fingerprints, inference freeze fingerprint and predictor freeze
fingerprint, and must contain unit-level estimates, panel-level estimates,
multiplicity states, bootstrap provenance, refit stability, secondary
diagnostics, and completeness / failures.

---

## 19. No silent recovery

```text
no procedure fallback
no row fallback
no score clipping
no successful-subset refit CI
no complete-case panel aggregation
no validation-unit dropping
```

---

## 20. Execution manifest candidate

`R4_EXECUTION_MANIFEST_CANDIDATE.json` mechanically enumerates model roles,
population roles, population manifest identities, dataset sources, TRAIN
budgets, TEST identities, directions, the procedure panel, analysis roles and
predictor roles. It contains no outcomes.

### 20.1 Cell registry

```text
current-generation primary      : 4 models x 3 populations = 12 cells, 24 directional units
legacy new-population secondary : 2 models x 2 populations =  4 cells,  8 directional units
R3 legacy MMLU                  : FROZEN_EXISTING / DO_NOT_RERUN
```

---

## 21. Measurement workload audit

Derived from the frozen measurement cell counts and the frozen R4 measurement
call-count contract
(`experiments/calibration_transport/R4_MEASUREMENT_EXECUTION_CONTRACT.json`,
fingerprint `7b126d300e774cb44d2c47fcb12513865d03c2b08ffd03a5ce409b2ea976e1e5`):
each unique model × item row requires **exactly two** forward evaluations.

```text
calls per item (R4 frozen contract) = 2  (1 CAT + 1 designated-candidate-only OVR)
inherited calls per item (R3 semantics) = 5  (1 CAT + 4 OVR)  ->  REJECTED
```

The nested N912 robustness union is measured **once** and reused: the primary
N456 fit consumes the frozen subset of those same raw rows, so no row is
forwarded twice.

| Cell | models | TRAIN rows/model | TEST rows/model | unique rows/model | unique model × item rows |
| --- | --- | --- | --- | --- | --- |
| MMLU current generation | 4 | 456 | 1140 | 1596 | 6384 |
| HellaSwag current generation | 4 | 912 (N912 union) | 10042 | 10954 | 43816 |
| HellaSwag legacy secondary | 2 | 456 | 10042 | 10498 | 20996 |
| MedMCQA current generation | 4 | 912 (N912 union) | 4162 | 5074 | 20296 |
| MedMCQA legacy secondary | 2 | 456 | 4162 | 4618 | 9236 |
| R3 legacy MMLU | — | — | — | — | FROZEN_EXISTING / DO_NOT_RERUN |
| **total** | | | | | **100728** |

### 21.1 Frozen R4 call-count contract

```text
R4 CALL COUNT CONTRACT = FROZEN
```

| Quantity | Value |
| --- | --- |
| unique model × item rows | 100728 |
| CAT forwards | 100728 |
| OVR forwards | 100728 |
| **total forward evaluations** | **201456** |

Audit identities (primary-only, for cross-checking):

```text
primary-only unique rows  = 97080
primary-only forwards     = 194160
N912 extension rows       = 4 models x 2 populations x 456 = 3648
N912 extension forwards   = 7296
97080 + 3648 = 100728 ; 194160 + 7296 = 201456
```

The previously reported inherited-R3 numbers (104376 item-measurements /
521880 calls) are **NOT AUTHORITATIVE** and are recorded only as rejected
inputs inside the frozen measurement contract.

---

## 22. R3 frozen-result reuse rule

Do not rerun frozen R3 MMLU legacy cells. If R4 needs them, reference the frozen
R3 result artifact identity. Re-fitting or re-measuring R3 legacy cells and
calling it continuity is forbidden.

---

## 23. Final anti-leakage rules

* Predictor X may be computed after raw scores exist.
* Any predictor protocol change after outcome access is forbidden.
* Selecting a threshold or predictor after seeing the transport result is
  forbidden.

---

## 24. Fingerprints

```text
final protocol candidate fingerprint = 179d052318b9eb080261d6ffaf922d95c62c1f73f1b38f32e4e410afae7a2186
execution manifest fingerprint       = 65db650429dfe0dd6ec0439a3140a9db99cf93aab7eb744d37f7a2b53e8373c1
fingerprint_version                  = 1
```

### 24.1 Cycle resolution

The manifest references the protocol **semantic id / version** only; it does not
embed the protocol candidate fingerprint. The protocol candidate then records
the manifest fingerprint. No fingerprint cycle exists.

Both artifacts were generated twice and were byte-identical.

---

## 25. Cross-artifact consistency audit

Mechanically verified with no conflict:

* models and revisions identical between manifest and protocol candidate;
* population manifest fingerprints identical between manifest and candidate;
* the six procedure labels and their scientific fingerprints identical to the
  calibration-family freeze;
* inference freeze fingerprint identical to `R4_INFERENCE_MULTIPLICITY_FREEZE.json`;
* predictor freeze fingerprint identical to `R4_PREDICTOR_FREEZE.json`;
* every recorded authority path exists on disk and its SHA256 matches;
* `status = CANDIDATE` and `formal_execution_authorized = false` in both
  artifacts;
* the manifest embeds no protocol candidate fingerprint.

```text
FINAL_PROTOCOL_IDENTITY_CONFLICT = NONE
```

---

## 26. Non-claims

```text
Final candidate is not execution authorization.
R4 primary inference is conditional on its fixed declared panel.
R3 MMLU legacy results are historical continuity evidence.
N912 cannot rescue N456.
Predictor validation is conditional on its fixed 16-unit held-out panel.
Predictor association is not causal.
No calibration procedure is universally best.
No result establishes global CAT/OVR compatibility.
No result authorizes production calibration-profile transport.
```

---

## 27. Status

```text
R4 FINAL INTEGRATED PROTOCOL CANDIDATE = COMPLETE
FINAL PROTOCOL STATUS                  = NOT FROZEN
FORMAL R4 EXECUTION                    = NOT AUTHORIZED
PUSH PERFORMED                         = NO
```
