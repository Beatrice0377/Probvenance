# R4 Measurement Resume Policy

```text
RESUME_POLICY_ID      = r4-measurement-resume-policy
RESUME_POLICY_VERSION = 1
status                = OPERATIONAL EXECUTION POLICY (not a scientific estimand)
```

本文件定义 R4 formal measurement 的 **crash-safe / resume** 运行契约。

它 **不修改** 任何 frozen scientific artifact：

```text
R4_MEASUREMENT_EXECUTION_CONTRACT.json     unchanged
R4_FINAL_PROTOCOL_FREEZE.json              unchanged
R4_EXECUTION_MANIFEST_FREEZE.json          unchanged
R4_POPULATION_FREEZE.md                    unchanged
R4_CALIBRATION_FAMILY_FREEZE.md            unchanged
R4_INFERENCE_MULTIPLICITY_FREEZE.json      unchanged
R4_PREDICTOR_FREEZE.json                   unchanged
```

它只规定：一个长时运行在中断后如何 **不改变** 以下任一量而继续：

```text
D_i、Y_i、CAT semantics、OVR semantics、model revision、population、
row set、row order、verbalizers、measurement contract
```

实现位于：

```text
experiments/calibration_transport/r4_staging.py       （staging / locking / atomic IO）
experiments/calibration_transport/run_r4_measurements.py::run_cell_resumable
```

---

## 1. Cell 作为执行单元

raw artifact 单元保持：

```text
one model × population
```

共 16 个 formal cells（4 MMLU current + 6 Hella + 6 Med）。

每个 cell 有独立 staging directory：

```text
<staging_root>/<model_key>__<population_id>/
  cell_identity.json        不可变 identity header
  runtime_provenance.json   不可变 runtime 描述
  LOCK                      single-writer exclusive lock
  operations.json           纯 operational sidecar（不入 scientific fingerprint）
  rows/<item_id>.json       per-row durable commit
  rows/<item_id>.inflight   in-flight marker
  raw-evidence.json         final artifact（只在 cell 完整后原子发布）
```

---

## 2. Immutable cell identity header

`cell_identity.json` 在 cell 首次创建时写入，之后 resume 必须 **exact match**：

```text
resume_policy_id / resume_policy_version
final_protocol_fingerprint
execution_manifest_fingerprint
measurement_contract_fingerprint
measurement_code_commit
model_key / model_id / model_revision / model_role / adapter
population_key / population_id / population_manifest_fingerprint
dataset_id / dataset_revision
required_train_budget / required_test_identity
expected_item_count / expected_item_ids
```

任一字段不符：

```text
STOP → R4ResumeIdentityMismatch
```

不得 resume、不得 merge。

---

## 3. Committed row 语义

一个 durable row 只有在：

```text
CAT attempt terminal
AND OVR attempt terminal
AND row schema validated
```

之后才成为 `COMMITTED_ROW`。

terminal 可以是：

```text
SCORED
or frozen / classified failure state
```

terminal failure **也是** terminal evidence，因此：

```text
terminal failure row MUST NOT be retried
```

---

## 4. Outcome-blind pending set

resume 时：

```text
pending_items = expected_frozen_items − valid_committed_item_ids
```

只由 **item identity + transaction state** 决定。禁止根据 score、probability、Y、
correctness、CAT/OVR agreement 或「failure 看起来不好」决定是否重跑。

pending 集合仍按 frozen manifest order 运行；resume **不得** 重新 shuffle。

---

## 5. Interrupted uncommitted row → RECOVERY_REPLAY

若 process 在一个 row 完整 durable commit **之前** 中断，该 row 视为
`UNCOMMITTED`。resume 时允许 **整行从零重放**：

```text
RECOVERY_REPLAY
```

约束：

```text
不得 merge 旧 partial attempt 的 CAT 与 新 attempt 的 OVR
整个 uncommitted row 重新执行
不合并任何 interrupted row 的 partial evidence
```

`rows/<item_id>.inflight` marker 在测量前写入、commit 后清除；resume 时残留的
inflight marker 正是 RECOVERY_REPLAY 的判定依据（transaction-state-only）。

---

## 6. Planned logical forwards vs operational attempts

frozen protocol 的 `2 forwards/item` 表示：

```text
2 accepted logical measurement calls per committed row
```

真实 OS/process crash 时，physical operational attempts 可能因为 RECOVERY_REPLAY
超过 2。两者必须分开记录：

```text
planned_logical_forwards       = 2 × expected_item_count（每 cell）
operational_attempts           = 实际发出的 physical forwards（operational sidecar）
recovery_replay_count          = 发生过的整行重放次数
```

禁止把 crash replay 伪装成 normal scientific retry。

---

## 7. Atomic persistence

每个 committed row：

```text
write temp → flush → fsync → atomic os.replace → fsync parent directory
```

final cell artifact 同样原子发布；**不会** 直接覆盖一个部分写出的 final JSON。
partial temp 文件在 `os.replace` 成功后清理。

---

## 8. Finalization rule

只有当：

```text
every expected frozen item has exactly one valid committed row
```

才允许：

```text
assemble final artifact
validate raw evidence
compute evidence fingerprint
atomically publish final artifact
mark cell COMPLETE
```

否则 `cell != COMPLETE`，resume 继续 pending 集合。

---

## 9. Existing final artifact

如果 valid final artifact 已存在且 identity / fingerprint 全部匹配：

```text
DO NOT RERUN CELL → ALREADY_COMPLETE（new_forwards = 0）
```

如果 final artifact 存在但 identity / hash 不匹配：

```text
STOP → R4ExistingFinalArtifactConflict
```

---

## 10. Duplicate guard

```text
one item_id → at most one committed row
```

发现 duplicate：

```text
STOP → R4DuplicateCommittedRow
```

**不** 自动选择「最后一个」。

---

## 11. Single-writer policy

```text
single writer per model×population cell
```

实现使用 stdlib `fcntl.flock(LOCK_EX | LOCK_NB)`。第二个 writer 必须失败：

```text
STOP → R4CellLockedError
```

---

## 12. Multi-worker policy

```text
MULTI-WORKER = NOT AUTHORIZED
```

formal execution **不得** 启用 multiple workers / multiple GPUs / parallel cell
mutation。因此外部审查提出的 multi-worker equivalence 问题：

```text
NOT APPLICABLE TO AUTHORIZED FORMAL PATH
```

若未来另开 multi-worker 设计，需要新的 pre-outcome engineering review。

---

## 13. CLI operational controls

```text
--staging-root <path>   启用 resumable staging 模式（默认 /root/rivermind-data/r4-formal-measurements）
--resume                允许继承已有 committed rows
```

这些属于 operational controls。CLI **不得** 改变 model revision、population
identity、D_i、measurement semantics、verbalizers、TRAIN budget 或 TEST set。

不带 `--resume` 时，若 staging 已存在 committed rows：

```text
STOP → R4StagingError("staging already holds committed rows; pass --resume")
```

---

## 14. Operations sidecar

`operations.json` 只记录 operational metadata：

```text
resume_policy_id / resume_policy_version
planned_logical_forwards
operational_attempts
recovery_replay_count
finalizations
runs
```

它 **不进入** scientific evidence fingerprint。wall-clock / hostname 等 operational
metadata 同样不得污染 evidence fingerprint。

---

## 15. 科学边界

crash recovery 不得改变：

```text
D_i / Y_i / CAT semantics / OVR semantics / model revision / population
row set / row order / verbalizers / measurement contract
```

禁止：

```text
score-dependent resume
correctness-dependent retry
failure-result cherry-picking
partial successful-row analysis
```

如果 crash-safe recovery 无法在不改变 frozen semantics 的条件下实现：

```text
STOP → RESUME_REQUIRES_SCIENTIFIC_PROTOCOL_CHANGE
```

---

## 16. 与外部审查要求的一致性

| 外部审查要求 | 本 policy |
|---|---|
| crash-safe | per-row durable commit + atomic finalize |
| deterministic | frozen order + canonical bytes + resume determinism test |
| outcome-blind | pending set 只由 transaction state 决定 |
| partial attempts not merged | 整行 RECOVERY_REPLAY，不 merge CAT/OVR |
| no terminal-row retry | terminal failure 视为 committed |
| single writer | `fcntl.flock` exclusive lock |
| multi-worker equivalence | NOT APPLICABLE（single-worker authorized path） |

---

## 17. Status

```text
R4 MEASUREMENT RESUME POLICY = DEFINED (v1)
SCIENTIFIC PROTOCOL CHANGE REQUIRED = NO
```
