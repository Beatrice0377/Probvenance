# R4 Formal Analysis Dependency Graph

Status: `STRUCTURAL ONLY`
Graph fingerprint: `449c9b19d61e4edbe95ea856b1d13e3b373765f8a9d05931f20e4d12bf28ed9f`
Raw measurement freeze commit: `3aae4528a131ba32582fb015bd2f6a4d201da457`

本文件只描述 **结构依赖**。它不包含任何统计量、风险值、Delta 值、bootstrap
区间、predictor 值或科学结论。

```text
R4 FORMAL ANALYSIS DEPENDENCY GRAPH = COMPLETE
SCIENTIFIC OUTPUTS COMPUTED = NO
```

---

## 1. 节点表

| node | kind | status | members | depends on |
| --- | --- | --- | --- | --- |
| `raw_evidence` | source | READY | 16 | — |
| `directional_train_source` | binding | READY | 32 | `raw_evidence` |
| `directional_train_target` | binding | READY | 32 | `raw_evidence` |
| `directional_test_target` | binding | READY | 32 | `raw_evidence` |
| `core4_fit` | fit_dependency | READY | 128 | `directional_train_source`, `directional_train_target` |
| `ib_extension_fit` | fit_dependency | READY | 64 | `directional_train_source`, `directional_train_target` |
| `raw_risk` | risk_dependency | READY | 32 | `directional_test_target` |
| `native_risk` | risk_dependency | READY | 192 | `core4_fit`, `ib_extension_fit`, `directional_train_target`, `directional_test_target` |
| `cross_risk` | risk_dependency | READY | 192 | `core4_fit`, `ib_extension_fit`, `directional_test_target` |
| `delta_native` | estimand_dependency | READY | 192 | `native_risk`, `raw_risk` |
| `delta_deploy` | estimand_dependency | READY | 192 | `cross_risk`, `raw_risk` |
| `delta_transport` | estimand_dependency | READY | 192 | `cross_risk`, `native_risk` |
| `primary12` | multiplicity_family | READY | 12 | `delta_deploy`, `delta_transport`, `core4_fit` |
| `extension8` | multiplicity_family | READY | 8 | `ib_extension_fit`, `delta_deploy`, `delta_transport` |
| `direction6` | multiplicity_family | READY | 6 | `delta_deploy`, `delta_transport`, `core4_fit` |
| `native12` | multiplicity_family | READY | 12 | `delta_native`, `core4_fit`, `ib_extension_fit` |
| `n912_robustness` | robustness_dependency | READY | 0 | `raw_evidence`, `core4_fit`, `ib_extension_fit` |
| `predictor_development8` | predictor_units | READY | 8 | `raw_risk`, `delta_transport`, `delta_deploy` |
| `predictor_validation16` | predictor_units | READY | 16 | `raw_risk`, `delta_transport`, `delta_deploy`, `directional_train_target` |
| `predictor_legacy8` | predictor_units | READY | 8 | `raw_risk`, `delta_transport`, `delta_deploy` |

节点数 `20`，边数 `46`，
structurally unavailable 节点 `[]`。

---

## 2. 风险 / Delta 依赖方向

```text
raw_risk          <- directional_test_target

native_risk       <- same F fitted on TARGET TRAIN, applied to TARGET TEST
cross_risk        <- same F fitted on SOURCE TRAIN, applied to TARGET TEST

Delta_native(F)   = R_native(F) - R_raw
Delta_deploy(F)   = R_cross(F)  - R_raw
Delta_transport(F)= R_cross(F)  - R_native(F)
```

三个量在图上互不合并：deployment delta、transport penalty、native improvement
是三个不同的依赖路径。

---

## 3. Multiplicity family 依赖

```text
primary12   <- Delta_deploy / Delta_transport x 2 directions x 3 logistic-core effects
extension8  <- I-isotonic / B-beta x 2 directions x 2 estimands
direction6  <- 3 logistic-core effects x 2 estimands (direct replicate difference)
native12    <- 2 target directions x 6 procedures
```

`r3_continuity_subset = 6`（subset of primary12），不允许单独修正。

---

## 4. Predictor 依赖

```text
predictor_development8   <- MMLU current-generation units (NOT independent validation)
predictor_validation16   <- current models x {HellaSwag, MedMCQA} x 2 directions
predictor_legacy8        <- 2 legacy models x 2 populations x 2 directions
```

观测单位是 `model × population × direction`；procedure F 不是独立观测。

---

## 5. 未解析依赖

```text
NONE
```

---

## 6. Fingerprint

```text
graph_fingerprint = 449c9b19d61e4edbe95ea856b1d13e3b373765f8a9d05931f20e4d12bf28ed9f
fingerprint_version = 1
canonical regeneration x2 = byte-identical
```
