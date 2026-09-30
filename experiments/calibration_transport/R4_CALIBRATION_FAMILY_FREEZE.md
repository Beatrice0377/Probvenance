# R4 Calibration-Family Freeze

**R4 CALIBRATION-FAMILY SCIENTIFIC SEMANTICS: `FROZEN`**

```text
R4 OVERALL:
NOT FULLY FROZEN
NOT EXECUTION-AUTHORIZED
```

```text
freeze date  : 2026-09-30
freeze scope : the six-procedure calibration panel
               the four R3 continuity procedure identities
               the two new-family semantic identities (I-isotonic, B-beta)
               fitting budgets and sample-size roles
               output / clipping policy
               no-rescue rule
```

本文件只冻结 **calibration-family scientific semantics**。它 **不是** 最终
numerical solver / tolerance 契约，**不是** predictor inference 规范冻结，
**不是** multiplicity 决策，**不是** R4 execution authorization。

冻结的 semantic fingerprint 只描述 **数学程序身份**；solver、库版本、CPU、
迭代次数、wall-clock 等属于 implementation provenance，见 §4。

---

## 1. Frozen six-procedure panel

```text
P-low
P-historical
L-low
L-historical
I-isotonic
B-beta
```

No seventh procedure。No temperature scaling。No vector scaling。No Dirichlet
calibration。No family added, removed, renamed, or reparameterized without a new
human freeze gate。

---

## 2. R3 continuity fingerprints（frozen）

四个 continuity procedure 直接继承 frozen R3 identity；本 gate 不重建、不改写。

| label | scientific fingerprint |
|---|---|
| P-low | `7a8e13d51e131f2102cca4e00b172c8bbb2eb49e591acd3746aeb64d003c8857` |
| P-historical | `a44e9217dd43e5e29d859c8dd2dc510a5876db4d46a8e0cc2fd4f1df3121a423` |
| L-low | `91d7d506275aade7d4676c39722ac2c4d975de7967a25a808395c056307ad619` |
| L-historical | `23ec12bbf4a809ba2f419491df80d1f228d3fd778d848115839aab3697f9dd58` |

三方比对（expected / declared / 由 payload 重算）在
`experiments/calibration_transport/r4_calibration_family_semantic_audit.py` 的
`_r3_continuity()` 中执行，`r3_continuity.all_match = true`。

Continuity core 语义（不变）：

```text
feature (P)   : identity-raw-probability
feature (L)   : exact-logit-probability
objective     : mean-bernoulli-nll-plus-l2
L2 strength   : P-low / L-low = 1e-4 ；P-historical / L-historical = 1e-2
endpoint (P)  : exact-raw-probability-accepted
endpoint (L)  : reject-exact-probability-endpoints
regularization: fixed-l2-strength
```

---

## 3. New-family semantic fingerprints（frozen）

| label | scientific fingerprint |
|---|---|
| I-isotonic | `cd13bc07bf92f3375bcd16d57fa5f515cd40f68199b57181791f85c58be8c244` |
| B-beta | `f4b710fb98f7c3056794aa709d53309f462a8f598cef8089d2f9c0ed6f7e37ff` |

B-beta 的 Gate A 前 fingerprint 为
`d7ee7aa9b4c611866ddedfcf66cf8735882324f4f20be9706a8637291feddfb5`，因补齐
identifiability / distinct-score / monotone-separation / reversed-orientation /
precise finite-optimum 语义而 **必须改变**。旧值不再有效。

完整 payload 与 synthetic probe 结果见：

```text
experiments/calibration_transport/R4_CALIBRATION_FAMILY_SEMANTIC_CANDIDATE.json
```

---

## 4. Scientific procedure identity vs implementation / solver provenance

本文件冻结的 fingerprint 属于 **SCIENTIFIC PROCEDURE IDENTITY**。

它们 **不** 包含：

```text
SciPy version
NumPy version
CPU model
optimizer iteration count
wall-clock time
absolute host path
```

只要数学程序本身不变（feature map、objective、constraints、endpoint policy、
eligibility / failure rules、interpolation / extension policy），solver 或库版本
的变化不改变上述 scientific fingerprint；此类变化记录为
**IMPLEMENTATION / SOLVER PROVENANCE**（Gate C）。

反之，任何改变数学程序的改动都必须产生新的 scientific fingerprint 并重新经过
human freeze。

---

## 5. Family roles（frozen）

```text
continuity confirmatory core :
  P-low
  P-historical
  L-low
  L-historical

standalone preregistered family extensions :
  I-isotonic
  B-beta
```

这是一个 **continuity core + two standalone extensions** 的结构。
它不是 six-cell factorial，也不得被描述成 six-cell factorial。
两个 extension family 各自独立预注册，不互相替代，不构成 pairwise comparison
矩阵。

---

## 6. Fitting budgets（frozen）

```text
primary            : N = 456
secondary robustness: N = 912
                      nested（primary TRAIN_456 ⊂ TRAIN_912）
```

在给定 budget 内，**全部六个 procedure 使用完全相同的 fitting rows**。

```text
No family-specific data volume.
```

不同 family 不得获得额外 TRAIN 行。primary 与 secondary 的 population 身份
来自 frozen population layer
（`experiments/calibration_transport/R4_POPULATION_FREEZE.md`），本 gate 不修改。

---

## 7. No-rescue rule（frozen）

若 `I-isotonic` 或 `B-beta` 在 `N = 456` 下 fitting failure：

```text
N = 912 cannot replace / rescue the primary result
```

`912` 始终只是 secondary sample-size robustness。procedure failure 不提升
另一个 family，不替换 procedure，不追加 data，不切换 solver，不引入
regularization rescue。

---

## 8. Output / clipping policy（frozen，全部六个 procedure）

```text
NO post-calibration epsilon clipping
```

- 任何 calibrator 若数学上返回 exact `0.0` 或 `1.0`，该 exact output 被保留。
- Brier（primary）对 `q ∈ [0, 1]` 永远 finite，接受 exact `0/1`。
- Exact LogLoss（secondary）在 prediction 对 observed outcome 赋零概率时为
  `+infinity`，**必须保持 exact**，不得用 epsilon clipping 或任何截断替换。

---

## 9. Frozen procedure semantics（summary）

### 9.1 I-isotonic

```text
input domain        : raw fixed-decision probability s ∈ [0, 1]
fitting problem     : non-decreasing empirical least-squares step function
objective           : mean-squared-error（weight = 1，无 class weighting）
monotonic direction : increasing = True（hard fixed）
tie rule            : exact-score aggregation（count / sum_y / mean_y）
                      + weighted PAVA
interpolation       : piecewise-linear between observed thresholds
out-of-support      : nearest-endpoint constant extension
endpoint behavior   : s = 0 / s = 1 accepted as ordinary legal inputs
regularization      : no-regularization v1（l2_strength = null）
hyperparameters     : no-hyperparameter v1
failure rule        : structural-numerical-contract-violation v1
```

### 9.2 B-beta

```text
map                 : z(s) = a*ln(s) - b*ln(1-s) + c ; f(s) = sigmoid(z)
parameters          : a, b, c
constraints         : a >= 0, b >= 0（属于 scientific identity）
objective           : mean-bernoulli-nll（无 L2 / L1 / weighting / pseudo-count）
regularization      : no-regularization v1（l2_strength = null）
hyperparameters     : no-hyperparameter v1
TRAIN endpoints     : exact s = 0 / 1 → INELIGIBLE_ENDPOINT
application ends    : a>0 → f(0)=0 ；a==0 → sigmoid(c)
                      b>0 → f(1)=1 ；b==0 → sigmoid(c)
out-of-support      : parametric-application-no-clipping
finite optimum      : a unique finite constrained optimum accepted under the
                      later frozen numerical KKT/convergence contract
failure rule        : structural-numerical-contract-violation v1
```

Fitting eligibility 的 ordered hard gates（frozen）：

```text
1. non-empty
2. finite score in probability domain [0, 1]
3. score strictly interior (0, 1)          else INELIGIBLE_ENDPOINT
4. binary label 0/1
5. both classes present                     else BETA_FIT_INELIGIBLE_SINGLE_CLASS
6. >= 3 exact distinct interior scores      else
                                            BETA_FIT_INELIGIBLE_INSUFFICIENT_DISTINCT_SCORES
7. no increasing monotone separation        else
                                            BETA_FIT_INELIGIBLE_MONOTONE_SEPARATION
8. constrained optimization
9. unique finite accepted optimum
```

```text
identifiability      : three-parameter design (1, ln s, -ln(1-s)) must be
                       identifiable → no silent 2-parameter reduction,
                       no fixed a or b, no logistic fallback
distinctness         : exact binary64 score equality
                       no tolerance merging / rounding / binning / epsilon
monotone separation  : max{s : Y=0} <= min{s : Y=1} → INELIGIBLE_MONOTONE_SEPARATION
reversed orientation : max{s : Y=1} <= min{s : Y=0} is NOT that failure rule;
                       it may still admit a finite boundary optimum with
                       a = 0 and/or b = 0, handled by the constrained optimizer
```

Solver 与 tolerance 的最终数值契约属于 implementation provenance，见 §4 与 Gate C。

---

## 10. Frozen / not frozen

```text
FROZEN（本 gate）
  the six-procedure panel
  the four R3 continuity scientific identities
  the two new-family scientific identities
  fitting eligibility / failure / endpoint / support / clipping semantics
  family roles（continuity core + two standalone extensions）
  fitting budgets 456 / 912 nested and equal-rows rule
  no-rescue rule
  output / clipping policy

NOT FROZEN（仍 open）
  final numerical beta solver
  solver convergence / KKT tolerance contract
  production isotonic implementation provenance
  TRAIN-refit bootstrap count
  TEST bootstrap architecture
  cluster / group-aware bootstrap（含 HellaSwag source_id grouping）
  multiplicity
  family-extension hypothesis adjustment
  predictor inferential specification
  formal R4 execution protocol
  R4 execution authorization
```

---

## 11. Provenance commits（frozen chain）

```text
f92270c8510ca60d052062bab1b9f62662020cc6  docs: freeze R4 population identities
0fea72b3166b28ae6ff175cba774c3c1091a6cee  experiments: specify R4 calibration-family semantics
```

semantic candidate artifacts（frozen content）：

```text
experiments/calibration_transport/r4_calibration_family_semantic_audit.py
  lines  = 694
  sha256 = 5111d16504de9627a859ab4a4d305f8329cded0f817142b1e8b7ec485941f13d

experiments/calibration_transport/R4_CALIBRATION_FAMILY_SEMANTIC_CANDIDATE.json
  lines  = 469
  sha256 = 41eaf954cfd29eb870d75e59feae34a1af1700b0c0ba3f3984d713bbcc549fe4

experiments/calibration_transport/R4_CALIBRATION_FAMILY_SEMANTIC_CLOSURE.md
  lines  = 747
  sha256 = 10a3ab9e7d0849c0aeeeac29c3b7cb6f0bc1fcb54cac97b6c4ee585d2efe2085
```

population layer（上游 frozen identity）：

```text
experiments/calibration_transport/R4_POPULATION_FREEZE.md
```

---

## 12. Reproduction

```bash
cd /root/rivermind-data/Probvenance
/root/rivermind-data/envs/probvenance-r4/bin/python \
  experiments/calibration_transport/r4_calibration_family_semantic_audit.py
```

重复运行必须产生 byte-identical `R4_CALIBRATION_FAMILY_SEMANTIC_CANDIDATE.json`
（无 timestamp、无 host path、无 random id）。

---

本文件只冻结 calibration-family scientific semantics。
R4 仍为 DRAFT / NOT FULLY FROZEN / NOT EXECUTION-AUTHORIZED。
