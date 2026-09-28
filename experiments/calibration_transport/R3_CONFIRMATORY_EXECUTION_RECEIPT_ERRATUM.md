# R3 Confirmatory Execution Receipt — Governance Erratum

本文件是一份 **append-only provenance correction**（追加式历史纠正）。

它**不**修改以下任何内容：

- official result artifact：`experiments/calibration_transport/results/r3-confirmatory-analysis-v1.json`
- execution sidecar：`experiments/calibration_transport/results/r3-confirmatory-analysis-execution-v1.json`
- original execution receipt：`experiments/calibration_transport/R3_CONFIRMATORY_EXECUTION_RECEIPT.md`
  与 `experiments/calibration_transport/results/r3-confirmatory-analysis-execution-receipt-v1.json`

它也**不**重新运行 official R3 confirmatory analysis。

它只纠正原 execution receipt 对 attempt 3 授权历史的描述。

---

## 1. 原 receipt 的问题

原 receipt 把 attempt 3 描述为：

```text
human-authorized operational retry
```

该表述过强（too strong）。

真实情况是：

```text
Attempt 3 had already been launched before the
human reviewer learned that execution had progressed
to a third attempt.
```

也就是说，attempt 3 是 **启动之后** 才进入人类 review 的；人类当时接受的是「让已经运行的 attempt 3
继续完成」，而不是「启动前的 retry 授权」。把 attempt 3 记成
`human-authorized-operational-retry` 会让人误以为 attempt 3 在启动之前就已经获得人工 retry 授权。

本 erratum 不否定结果、不否定执行，只把这段授权历史改回真实。

---

## 2. prior governance contract

attempt 2 之前有效的治理合同明确规定：

```text
maximum total official execution attempts = 2
```

并且：

```text
attempt 3 was explicitly outside that frozen contract.
```

---

## 3. 真实 attempt 1 历史

```text
attempt_number = 1
authorization = initial-human-authorized-execution
status = externally-terminated-before-artifact
termination_reason = outer-shell-tool-timeout-process-group-termination
official_artifacts_created = false
observable_statistical_outcome = false
```

attempt 1 在产出任何 artifact 之前被外层 shell-tool timeout / process-group termination
外部终止。**这不声称「没有发生任何 computation」**，只声称没有 persisted / observable 的官方统计结果。

---

## 4. 真实 attempt 2 历史

```text
attempt_number = 2
authorization = pre-launch-human-authorized-operational-retry
status = externally-terminated-before-artifact
termination_reason = host-system-reboot-during-windows-update
execution_environment = WSL process terminated with host reboot
official_artifacts_created = false
observable_statistical_outcome = false
```

attempt 2 是在 attempt 1 失败、经人工 failure/retry review 之后，**启动前**明确获得一次
human-authorized operational retry。它随后因 Windows host system update、用户点击立即重启、
WSL 进程随宿主机重启而终止。同样：**不声称没有发生任何 computation**，只声称没有
persisted / observable 的官方统计结果。

对 attempt 2 的环境，我们**不**声称 “WSL runtime definitely unchanged”（没有 attempt 2 的
完整 runtime byte-level snapshot）；只记录有证据的事实：

```text
repository code/raw/protocol identities remained unchanged
```

---

## 5. 真实 attempt 3 历史

attempt 3 **不得**再用单一 `human-authorized-operational-retry` 描述。真实治理状态是：

```text
attempt_number = 3
initiation = operator-initiated-retry-after-exogenous-host-reboot
pre_launch_human_authorization = false
prior_attempt_contract_permitted_this_attempt = false
governance_contract_deviation = true
continuation_review = human-accepted-after-launch
status = completed
exit_code = 0
official_artifacts_created = true
```

即：

```text
NOT:
pre-launch human-authorized retry

BUT:
operator-initiated retry outside the previously frozen
two-attempt governance contract

followed by:
human acceptance of continuation after launch
```

---

## 6. attempt 3 的 continuation 不是 retrospective preauthorization

Human review accepted continuation of an already-running attempt 3.

This acceptance must not be represented as pre-launch authorization.

事后接受继续 ≠ 启动前授权。

---

## 7. no attempt 4

```text
attempt_4_authorized = false
attempt_4_occurred = false
```

人类 reviewer 当时的判断是：不要杀掉正在运行的 attempt 3，允许其继续完成，**禁止任何 attempt 4**。
没有 attempt 4 发生。

---

## 8. counts

```text
execution_attempt_count = 3
automatic_retry_count = 0
retry_invocation_count = 2

pre_launch_human_authorized_retry_count = 1   （对应 attempt 2）
post_launch_human_continuation_acceptance_count = 1   （对应 attempt 3）
```

历史不被重新压成 2。三次调用都不是程序自动 retry loop，故 `automatic_retry_count = 0`。

---

## 9. result-driven retry 判断

```text
attempt 1 official artifacts = none
attempt 2 official artifacts = none
attempt 1 observable statistical outcome = false
attempt 2 observable statistical outcome = false
code changes between attempts = none
scientific design changes between attempts = none
raw changes between attempts = none
```

因此：

```text
result_driven_retry = false
```

attempt 3 不是基于 attempt 1/2 的统计结果触发的。

---

## 10. scientific validity impact 判断

```text
scientific_validity_impact = none-identified
```

不写 “scientific validity guaranteed”。此判断基于：attempt 1/2 无 persisted / observable
official statistical outcome；attempt 1/2 后无 outcome-driven code modification；attempt 3
使用的 runner / kernel / raw / protocol / population 均保持冻结 identity；attempt 3 成功后
未再次运行分析。

---

## 11. frozen artifact 是否修改

```text
official_analysis_artifact_modified = false
execution_sidecar_modified = false
original_receipt_modified = false
```

## 12. result 是否需要 rerun

```text
result_rerun_required_by_this_erratum = false
```

## 13. post-outcome discipline 不变

```text
post_outcome_code_change = false
post_outcome_analysis_rerun = false
post_hoc_statistical_analysis_performed = false
scientific_interpretation_performed = false
```

---

## 14. frozen artifact identities

```text
official_analysis_sha256 = 27b945097a0b6156998a47112437c3b258037db2c9888cea20e97b52075be796
execution_sidecar_sha256 = 9992ceefba32f4d0f55e692a0c60472a05751bdca316993ed3f98e220b0f6deb
execution_fingerprint = e738be013fd0f98a6b0ae635e09420e65de9c91b3b819aa11c1ff7ed2901f479
original_receipt_fingerprint = b49e2ac5c0809b727843468120bf3b15a695e981dd3556ca38fb20d1eca74da7
```

## 15. commit identities

```text
execution_code_commit = 0c16ca2460de8b18433a9c677b3e6989b0736f9f
official_result_commit = c68c7e3ac725de1bc5db369cb7c951a810ed80f9
original_receipt_commit = a069882b0bef39f347ae26032428a731be9c5970
```

---

## 16. 本 erratum 的性质

```text
correction_class = governance-provenance-correction
```

本次修复的目的不是让 provenance “更漂亮”。恰恰相反，是永久保留一个不那么漂亮、但真实的事实：

```text
attempt 3 超出了此前冻结的 two-attempt governance contract。
```

同时也永久保留另一个同样重要的事实：

```text
attempt 3 不是基于 attempt 1/2 的统计结果而触发的；
attempt 1/2 没有 persisted / observable official outcome，
也没有 outcome-driven scientific/code modification。
```

因此：

```text
governance deviation ≠ scientific invalidation
```

我们修正的是历史描述，不是科学结果。

---

## 17. erratum fingerprint

```text
erratum_fingerprint = 47bdd2e8c4fdee2b06ec1aedeb7dd7b61f04fe171cf789c93296ea79057ec962
```

本 erratum 为 append-only；不修改 original receipt，也不创建 receipt v2。
