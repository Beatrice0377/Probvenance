# R2 — Final Research-Contract Closure

```
R2 STATUS:
CLOSED — EXPLORATORY PROGRAM COMPLETE

R3:
NOT STARTED
NOT AUTHORIZED BY THIS FILE
```

This file closes the R2 exploratory program. It does not modify any historical
report or artifact. It is a closure and evidence-map document, not a new result.

The R2 program is the exploratory empirical work carried out under Research
Specification v1 (`docs/research/calibration-transport-research-spec-v1.md`). R2
comprises four completed, mutually-dependent rounds, all recorded in this
directory:

```
REPORT.md         R2A  — the tiny frozen-decision CAT<->OVR pilot
R2B_REPORT.md     R2B  — the stability / deconfounding round
R2C_REPORT.md     R2C  — the calibration-method adequacy / sensitivity study
R2C1_REPORT.md    R2C.1 — the low-regularization numerical closure
```

The forward-looking semantics that R2 forces onto any future R3+ study are frozen
separately in `docs/research/calibration-transport-research-spec-v2.md`. This
closure document does not restate v2 and does not revise v1.

---

## 1. Canonical R2 closure finding (English)

> **Under one model and exploratory synthetic populations, CAT and OVR produce
> markedly different frozen-decision score geometries. Cross-measurement
> calibration behavior is nontrivial and directional under fixed procedures, but
> its sign and magnitude can depend materially on the calibration procedure.
> Consequently, empirical calibration compatibility cannot be inferred from
> measurement identity alone, nor from a single cross-vs-self comparison.**

## 2. Canonical R2 closure finding (Chinese)

> **在当前单模型、探索性合成总体中，CAT 与 OVR 对同一冻结决策产生了显著不同的
> 概率测量几何。在固定校准程序下，跨测量校准表现呈现非平凡且有方向的结构；但这
> 种结构的符号与幅度又会显著依赖校准程序。因此，经验校准兼容性既不能仅由
> measurement identity 推断，也不能由单一的 cross-vs-self 比较判定。**

---

## 3. What R2 provides counterexamples to

R2 does **not** support these simplified interpretations. It provides
counterexamples to them, and that is the useful part of the exploratory result:

1. **"CAT->OVR and OVR->CAT have procedure-independent fixed directional
   compatibility."** R2C shows the R2A/R2B `CAT->OVR < 0` direction is *not*
   robust to the calibration procedure — it flips to positive for the
   low-`lambda` / logit-family configurations (`CAT->OVR`: negative 4/10,
   positive 6/10 across the ten pre-declared configurations). Holding measurement
   A, measurement B, population, test rows, target semantics, and metric fixed
   while changing only the calibration procedure can change the *sign* and
   magnitude of the empirical transport excess risk.

2. **"A negative cross-vs-native delta automatically means transport success."**
   The R2A `Delta CAT->OVR` is negative, yet the CAT-fitted map is still *worse*
   than the raw OVR target score (`raw OVR 0.1630 < CAT->OVR 0.1725`). A negative
   cross-vs-self delta can simply reflect a poor target self-calibrator, not a
   good cross map.

These are the two ways R2's evidence bears on interpretation. The point is the
counterexample, not a philosophical claim about falsification.

---

## 4. Non-claims

R2 does **not** establish, and this closure does **not** claim:

```
CAT is incompatible with OVR
OVR universally fails to transport to CAT
CAT universally transports / universally fails to transport to OVR
score-range mismatch causes transport failure
similar / different end-to-end accuracy determines transportability
R2 confirms the final paper thesis
production cross-measurement reuse is safe
```

The observed-range asymmetry and the end-to-end accuracy differences are
exploratory, hypothesis-generating diagnostics. They are not causal mechanisms and
not validated determinants of transportability.

---

## 5. Evidence map

| round | report | what it contributes |
| --- | --- | --- |
| R2A | `REPORT.md` | tiny pilot (9 train / 6 test): first observed opposite-signed directional transport; establishes the finite-sample self-calibrator caution and the raw-target-relative reading |
| R2B | `R2B_REPORT.md` | 150-item population, 90/60 split: the R2A directions persist descriptively; adds paired test bootstrap, paired train-refit stability, and the empirical in-range / outside-range loss decomposition |
| R2C | `R2C_REPORT.md` | offline 2x5 method/`lambda` sensitivity: native adequacy and transport sign depend on the calibration procedure; no configuration improves **both** measurements |
| R2C.1 | `R2C1_REPORT.md` | independent high-precision closure of the 15 uncertifiable `lambda = 1e-6` fits: the objective is well-defined and high-precision solvable; the frozen binary64 solver path does not uniformly reach a certifiable point |

Read the reports for the numbers; this map only records what each round is for.

---

## 6. Why the program stops here

Further analysis on the same R2B / R2C evidence now has diminishing confirmatory
value, because the method choices and hypotheses have already been informed by
those very outcomes (R2C is explicitly a post-R2B exploratory study). Additional
mining of the same one-model, synthetic-population evidence cannot become
confirmatory no matter how it is re-sliced.

Therefore:

```
NO R2D
```

The next empirical step, if and when it is human-authorized, must be a new,
untouched R3 protocol with its own untouched population and confirmatory
separation — designed under Research Specification v2. R2's evidence is
permanently exploratory: it may inform design decisions and pilot comparisons, but
it cannot serve as R3 confirmatory TEST evidence.

---

## 7. Status and authorization

```
R2:  CLOSED (exploratory program complete)
R3:  NOT STARTED; NOT AUTHORIZED BY THIS FILE
Research Spec v1: immutable historical authority for R0/R1/R2
Research Spec v2: prospective semantic revision for R3+ protocol design
```

The subsequent decisions flow is:

```
push this closure
    -> external review
    -> human decides whether and how to design R3
```

External review opinion (for example, a conditional pass) is valuable input. It is
**not** a repository normative authorization, and this repository does not record
the research gate as passed. Declared measurement identity remains the default
fail-closed authorization boundary; empirical compatibility is a research result,
not a runtime entitlement.
