# R4 Measurement Operational Hardening

```text
status = PASS
scope  = operational execution hardening (crash-safe resume)
```

本文件记录 formal R4 measurement 在 **长时运行** 场景下的 operational hardening：
现有 runner 的 resume 能力审计、必要的实现补强、以及 crash-injection 测试证据。

本文件 **不是** scientific artifact。

---

## 1. 背景

formal R4 workload：

```text
100,728 unique model×item rows
201,456 planned logical forwards
```

如此长时运行必须具备 crash-safe、deterministic、outcome-blind 的 resume 语义。
本任务先审现有实现，不默认它已具备。

---

## 2. 现有 runner 的 resume 审计（审计前）

审计对象：

```text
experiments/calibration_transport/run_r4_measurements.py
experiments/calibration_transport/r4_raw_evidence.py
```

| 问题 | 审计结果 |
|---|---|
| 1. 是否只在整 cell 完成后一次写最终 artifact？ | 是。`run_cell` 在内存中一次性测量全部 row，`main` 最后 `write_json` 一次 |
| 2. 中断后是否可安全 resume？ | 否 |
| 3. 是否存在 per-row durable checkpoint？ | 否 |
| 4. 是否会重复 terminal rows？ | 无 duplicate guard |
| 5. 是否会 merge incompatible attempts？ | 无 guard |
| 6. 是否有 single writer protection？ | 无 |
| 7. final artifact 是否原子完成？ | 否。`r4_raw_evidence.write_json` 直接 `Path(path).write_text(...)` |

结论：现有实现 **不满足** resume contract，需要最小补强。

```text
EXISTING_RUNNER_RESUME_CONTRACT = NOT SATISFIED
```

---

## 3. 实现补强

### 3.1 新增 operational staging 模块

```text
experiments/calibration_transport/r4_staging.py   （NEW）
```

职责：cell staging 目录、immutable identity、single-writer lock、atomic per-row
commit、inflight marker、outcome-blind pending set、atomic finalization、operations
sidecar。

关键 API：

```text
dump_canonical / read_json / write_atomic
cell_dir_name / cell_dir / rows_dir / row_path / inflight_path / final_path
identity_path / runtime_path / operations_path / ensure_cell_dir
acquire_cell_lock / release_cell_lock
verify_or_write_identity / verify_or_write_runtime / load_runtime
commit_row / load_committed_rows / committed_item_ids
mark_inflight / clear_inflight / load_inflight_item_ids
compute_pending / publish_final / load_final
load_operations / save_operations
```

`write_atomic` 的持久化序列：

```text
mkstemp in target dir → write → flush → fsync → os.replace → fsync(parent dir)
```

`acquire_cell_lock` 使用 `fcntl.flock(fd, LOCK_EX | LOCK_NB)`。

该模块 **只** 承载 operational 状态，**绝不** 进入 scientific evidence fingerprint。

### 3.2 runner 接线

`run_r4_measurements.py` 新增：

```text
load_frozen_authority() 额外返回
  final_protocol_fingerprint / final_protocol_status
  execution_manifest_fingerprint / execution_manifest_status
  （4 个既有 key 不变 → 既有测试保持通过）

cell_identity_header(cell, authority, measurement_code)
_cell_model_meta(cell)
_build_cell_payload(...)
_validate_row_shape(item)
_verify_existing_final(final, identity, directory)
run_cell_resumable(...)
```

CLI 新增 operational controls：

```text
--staging-root <path>
--resume
```

`main` 现在要求 `--output` 或 `--staging-root`，并要求：

```text
measurement_contract_status == "FROZEN"
final_protocol_status       == "FROZEN"
execution_manifest_status   == "FROZEN"
```

`run_cell_resumable` 的流程：

```text
ensure cell dir → acquire lock → verify_or_write_identity
→ 若 final 已存在且匹配 → ALREADY_COMPLETE（0 new forwards）
→ 拒绝 frozen item set 之外的 row → 拒绝 resume=False 时的既有 committed rows
→ compute_pending → 更新 operations
→ 若 pending 非空：
     verify cache / environment / offline
     load_backend → verify_verbalizers → verify_or_write_runtime（mismatch ⇒ STOP）
     对每个 pending item：
        mark_inflight → measure_item → _validate_row_shape → commit_row → clear_inflight
→ 按 frozen order 组装 items → _build_cell_payload
→ validate_raw_evidence → publish_final → COMPLETE
```

lock 始终在 `finally` 释放。

---

## 4. Crash-injection 测试

`tests/test_r4_measurements.py` 新增一节：

```text
Crash-safe resume / staging semantics (operational, outcome-blind)
```

覆盖：

| 测试 | 覆盖的外部审查要求 |
|---|---|
| `test_pending_set_is_derived_only_from_transaction_state` | outcome-blind pending set |
| `test_resumable_fresh_run_completes_the_cell` | 正常完成 |
| `test_already_complete_cell_is_not_rerun` | 不重复运行已完成 cell |
| `test_resume_after_committed_rows_skips_them` | crash after committed rows |
| `test_mid_row_crash_recovery_replays_the_whole_row` | mid-row crash → 整行 RECOVERY_REPLAY，不 merge CAT/OVR |
| `test_finalize_after_crash_uses_zero_new_forwards` | crash before finalize → 0 new forwards |
| `test_terminal_failure_row_is_never_retried` | anti-selection：terminal failure 永不重试 |
| `test_fresh_run_refuses_to_inherit_partial_staging` | 无 `--resume` 不得继承 partial staging |
| `test_duplicate_committed_row_fails_closed` | duplicate committed row fail-closed |
| `test_identity_mismatch_fails_closed` | identity mismatch fail-closed |
| `test_single_writer_lock_blocks_a_second_writer` | single-writer lock |
| `test_atomic_finalization_leaves_no_partial_json` | atomic finalization |
| `test_resume_is_deterministic` | resume determinism（byte-identical final） |
| `test_frozen_authority_exposes_the_freeze_fingerprints` | freeze fingerprint 暴露 |
| `test_cell_identity_header_records_the_frozen_identities` | identity header 内容 |
| `test_cli_exposes_operational_staging_controls` | CLI operational controls |

---

## 5. 验证结果

```text
py_compile           PASS（runner / raw-evidence / staging / tests）
ruff check           All checks passed!
pytest -q -p no:randomly tests/test_r4_measurements.py   → 87 passed（连续两次一致）
```

crash-injection 全部通过；resume determinism 得到 byte-identical final artifact。

---

## 6. 科学边界确认

补强 **未** 改变：

```text
D_i / Y_i / CAT semantics / OVR semantics / model revision / population
row set / row order / verbalizers / measurement contract
```

**未** 修改任何 frozen scientific artifact。**未** 读取或产生任何 real study outcome。

```text
RESUME_REQUIRES_SCIENTIFIC_PROTOCOL_CHANGE = NO
OUTCOME_FIREWALL = INTACT
```

---

## 7. Status

```text
R4 MEASUREMENT CRASH-SAFE RESUME HARDENING = PASS
```
