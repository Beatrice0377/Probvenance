# Calibration Transportability under Probability-Measurement Shift

## Research Specification v2

### R3+ conditioned-compatibility semantics

Status: frozen semantic revision for R3+ protocol design
R3 experiment protocol status: not yet frozen

This document freezes the semantics that are required *before* an R3 protocol can
be designed. It does **not** itself authorize or define the final R3 experiment,
does not select a calibration procedure, does not select a method panel, and does
not select a model set or a confirmatory dataset.

The word **frozen** here means that future R3+ work is expected to follow these
semantics by default; if the research design has to change, it must change through
an explicit revision and an explicit version of this document, never through
silent drift. As with v1, frozen here is **not** a core artifact schema version, a
public API version, a `CalibrationProfile` version, or a runtime contract version.
Those live in the frozen Phase 4C contracts and are unrelated to this file.

---

## 0. Relation to Specification v1

```
v1 remains the immutable historical authority for R0/R1/R2.
v2 applies prospectively to R3 and later research claims.
```

v2 does **not** retroactively change:

- R1 artifacts (plan fingerprint, dataset fingerprint, `RESEARCH_SPEC_VERSION`);
- R2 estimands, results, reports, or result artifacts;
- production Phase 4C contracts.

Unless explicitly revised by v2, the semantic principles of v1 continue to apply
prospectively. In a conflict concerning an R3+ claim, **v2 controls**.

This document is an **explicit normative revision layer**, not a full-text copy of
v1. It exists so that the v1/v2 revisions cannot drift into two silently
inconsistent bodies of text. Where v2 says nothing, v1 governs.

---

## 1. Why v2 exists

R2C directly demonstrated the following: holding measurement A, measurement B, the
population, the test rows, the target semantics, and the metric fixed, a change of
**calibration procedure** can change the **sign and magnitude** of the empirical
transport excess risk. Under fixed procedures the R2A/R2B `CAT->OVR` direction was
negative; across the ten pre-declared procedure/regularization configurations it
was negative only 4/10 and positive 6/10.

Therefore:

> **Empirical transport compatibility is not a bare property of a measurement
> pair.**

This is the entire reason v2 exists. R2 did **not** prove CAT and OVR incompatible,
and R2 did **not** confirm the transport thesis. R2 produced a counterexample to
the simplest reading of transport compatibility — the reading in which a
measurement pair has a fixed directional compatibility — and that counterexample
forces a more precise contract.

---

## 2. Revised working statement

v1 froze:

> **Identity != compatibility.**

v2 keeps that and adds:

> **Compatibility is not a bare measurement-pair property.**

中文：

> **兼容性不是 measurement pair 的裸属性。**

And therefore:

> A calibration transport claim is a **conditioned empirical statement** about a
> source measurement, a target measurement, a model/source condition, a population,
> target semantics, an evaluation loss, an evidence protocol, and a **calibration
> procedure**.

The slogan still names **declared measurement identity**, not "all provenance
identity". The runtime selector's eligibility is not decided jointly by every
field of profile identity, and v2 does not change that.

---

## 3. Formal conditioned relation

v2 freezes the notation:

```
A  --[ M, P, T, L, E, F ; epsilon ]-->  B
```

mathematically:

```
         epsilon
A  ------------------------->  B
      ( M, P, T, L, E, F )
```

where:

| symbol | meaning |
| --- | --- |
| `A` | source probability-measurement protocol |
| `B` | target probability-measurement protocol |
| `M` | model / source-execution condition relevant to the empirical population |
| `P` | declared population |
| `T` | target / correctness semantics |
| `L` | evaluation loss / metric |
| `E` | evidence protocol |
| `F` | calibration procedure (section 5) |
| `epsilon` | a predeclared compatibility tolerance / decision criterion, **only when a study actually declares one** (section 4) |

The relation remains directional and not transitive by default, exactly as in v1:
`A -> B` does not imply `B -> A`, and `A -> B` with `B -> C` does not imply
`A -> C`.

---

## 4. Do not invent a default epsilon

v2 defines **no** default `epsilon`. In particular it does **not** define
`epsilon = 0`, and it defines no universal threshold.

If a study declares no compatibility criterion, it may report only **descriptive
transport quantities**. A negative `Delta` is a descriptive comparison; it does
**not** by itself make the relation "compatible". This is the v2 restatement of
the v1 rule that compatibility is evidence-dependent.

---

## 5. Calibration procedure `F` is an explicit conditioning axis

This is the principal new content of v2. `F` is a **statistical procedure
contract**. It must include at least:

1. **calibration family** — e.g. "L2 logistic".
2. **feature / score transform** — e.g. raw `p`, or `logit(p)`.
3. **objective** — e.g. mean Bernoulli NLL plus the declared regularization.
4. **regularization and hyperparameter rule** — e.g. fixed `lambda`, or a
   predeclared selection rule.
5. **endpoint policy / mathematically relevant input treatment** — e.g. how exact
   `0`/`1` scores are handled (fail closed vs. some declared treatment).
6. **fitting-data protocol** — which items are used to fit, and under what
   pairing and split discipline (section 10).
7. **model-selection / calibration-selection rule, if any** — declared before
   confirmatory outcomes (section 15).

### 5.1 `F` is not a generic provenance blob

`F` must **not** be defined as "everything about the run". It is the statistical
procedure, not the execution-environment identity. A run's environment, library
versions, hardware, and wall-clock details are provenance, not `F`.

### 5.2 `F` is not the fitted map

`F` is the **fitting procedure**. The **actual fitted map** it produces is a
different object (section 7). Writing "`F` is the fitted calibration map" is
wrong.

---

## 6. Solver / version boundary

```
numerical solver
solver version
arithmetic precision
device
library version
```

belong to **execution provenance** by default. They are **not** a core
conditioning axis of the statistical compatibility relation `F` — as long as the
implementation correctly realizes the same declared statistical procedure.

### 6.1 Numerical implementation failure semantics

If a numerical implementation fails to realize `F` — fails closed, or cannot
certify a fit — that must be recorded as an **operational / numerical execution
limitation**. It must **not** automatically redefine `F`, and it must **not**
automatically become a measurement incompatibility.

### 6.2 But provenance still matters

Solver, version, and precision remain **required research provenance**, because
operational completeness and reproducibility may depend on them. The distinction
is:

```
not a statistical conditioning axis by default  !=  irrelevant
```

R2C.1 is exactly the case that motivates this distinction: the objective was
well-defined and high-precision solvable, but the frozen binary64 solver path did
not uniformly reach a certifiable point under the observed `lambda = 1e-6`
resamples. That is an operational completeness limitation recorded in provenance,
not a redefinition of the statistical procedure.

---

## 7. Exact fitted-map claim vs procedure-level claim

v2 separates two different claim levels.

### 7.1 Exact fitted-map transport

An exact source fit `g_A` is the concrete empirical map obtained under measurement
A, an exact training dataset `D_A`, and procedure `F`. v2 denotes it:

```
g_(A, F, D)
```

The question

```
What happens when THIS exact map  g_(A,F,D_A)  is applied to target measurement B?
```

is an **exact fitted-map transport claim**. Cross application is written:

```
g_(A,F,D_A)(S_B)
```

and answers "this exact fitted map on this target evidence".

### 7.2 Procedure-level generalization

The stronger claim is:

> maps generated by procedure `F`, when fit under declared source-measurement
> conditions, tend to transport to `B` under a declared population/evidence regime.

This is a **procedure-level generalization**. It does not follow automatically
from one exact map.

### 7.3 One fitted map does not establish procedure compatibility

Frozen:

> **One fitted map does not establish a procedure-level calibration compatibility
> relation.**

A procedure-level claim needs replication, resampling / repeated-fitting evidence,
cross-condition evidence, or a confirmatory protocol designed for that claim. The
concrete inference contract is deferred to the R3 protocol.

---

## 8. If source and target procedures differ

By default, the R3 measurement-shift primary comparison should apply the **same
declared procedure `F`** to both the source native fit and the target native fit,
so that the calibration procedure itself does not become an uncontrolled variable.

If a future study deliberately uses

```
F_A != F_B
```

then the claim must explicitly write both `F_A` and `F_B`. A single symbol `F`
must not hide the difference.

---

## 9. Three-baseline contract

For source `A`, target `B`, procedure `F`, and metric `L`, the target `B` must
report **three** risks together:

```
1. RAW target risk
2. NATIVE target calibrated risk
3. CROSS source-map-on-target risk
```

Canonical notation:

```
R_raw(B)

R_native(B; F)

R_cross(A -> B; F)
```

More formally these may be conditioned on `M, P, T, L, E`, but tables may use the
short names.

### 9.1 Three required contrasts

```
Delta_native/raw   = R_native(B; F)   - R_raw(B)

Delta_cross/raw    = R_cross(A->B; F) - R_raw(B)

Delta_cross/native = R_cross(A->B; F) - R_native(B; F)
```

### 9.2 Fixed sign semantics

```
negative = lower risk than the baseline
positive = higher risk than the baseline
```

A negative value is only a **descriptive comparison**. It is not automatically
compatibility, transport success, or certification.

---

## 10. Paired fitting and evaluation discipline

v2 inherits and reinforces the v1 paired discipline. For the primary
Frozen-decision estimand, the source and target native calibrators MUST be fit on
the **same paired training item IDs** and evaluated on the **same paired held-out
item IDs**, within the explicitly defined eligible paired population. Split
membership must be disjoint at the observation / item level:

```
train ∩ audit = ∅
train ∩ test  = ∅
audit ∩ test  = ∅
```

and a future harness must verify this mechanically, not infer it from split names.

---

## 11. Hard interpretation rule

Frozen, verbatim:

> **A negative cross-vs-native delta alone MUST NEVER be described as transport
> success.**

Reason: the target native estimator may itself be poor. R2 observed exactly this —
the R2A `Delta CAT->OVR` was negative, yet the CAT-fitted map was still worse than
the raw OVR target score. `Delta_cross/native < 0` is meaningless without
`Delta_native/raw` and `Delta_cross/raw`.

---

## 12. Native reference is not oracle

Inherited from v1: `g_B != q_B`. The target self-fitted map `g_B` is a
**finite-data native reference**, not the oracle conditional calibration function
`q_B(s) = P(Y = 1 | S_B = s)`.

### 12.1 Reference adequacy contract

Before an R3 protocol begins, it must predeclare **how native-reference adequacy
will be assessed and reported**. v2 defines **no universal adequacy threshold**; it
explicitly refuses a rule such as "native adequate iff native-vs-raw < 0" as a
universal law. R3 must define its own rule **before** confirmatory TEST outcomes.

### 12.2 Required inadequate-reference disclosure

If the declared native-reference adequacy criterion is not met, R3 must explicitly
mark a **native reference adequacy concern** (or an equivalent predeclared state).
In that case `Delta_cross/native` may still be reported, but it must not by itself
support transport success or compatibility acceptance.

---

## 13. No automatic compatibility decision in v2

v2 freezes semantics only. It does **not** define `ACCEPT if ...` or `REJECT if
...`. The decision threshold, uncertainty rule, and multiplicity rule are deferred
to the R3 protocol.

---

## 14. R3 method protocol requirement

Before R3 measurement, the protocol must select and freeze exactly one of:

### Option A — fixed method panel

A predeclared finite calibration-procedure panel `F1 ... Fk`, each an explicit
experimental condition, with predeclared primary/secondary status and a
multiplicity policy.

### Option B — train/audit-only method selection

A predeclared candidate procedure set, selection metric, TRAIN/AUDIT partition,
selection rule, tie-break, failure rule, and a fallback rule or an explicit
no-fallback declaration — where

```
TEST MUST BE UNTOUCHED BY METHOD SELECTION
```

### 14.1 Neither option is selected here

v2 does **not** decide fixed panel vs selection protocol. That requires external
review and the human R3 design decision. v2 only freezes that the choice itself
must be explicit and frozen before TEST.

---

## 15. No method winner from R2

### 15.1 `P:lambda=0.01` is not an automatic R3 default

The R2 historical configuration `P:lambda=0.01` must not become the R3 primary
calibration procedure merely because it was the original pilot method. R2 already
showed its native OVR adequacy problem and its method sensitivity. This round also
selects no other configuration in its place.

### 15.2 No method winner from R2C

R2C is an exploratory sensitivity study. Its best configuration must not be picked
and then relabelled as preregistered for R3 after the fact. R2C may only be used to
**design** a future candidate panel or selection protocol.

---

## 16. Confirmatory-data separation

> R3 primary evidence must come from untouched confirmatory conditions and data.

All R2 evidence — R2A, R2B, R2C, R2C.1 — is **hypothesis-generating /
design-generating** only.

### 16.1 R2B TEST is permanently exploratory

In particular, the **60 R2B TEST items** must not be renamed "confirmatory TEST"
for R3. They may support design decisions, support pilot comparisons, and serve as
historical exploratory evidence; they must not support an R3 primary confirmatory
claim.

### 16.2 R3 model / population requirement

v2 does not freeze a concrete model count. The R3 protocol must specify a
model/source condition axis `M` and new untouched population(s). If
`Qwen/Qwen3.5-2B` appears again, it may be a **preregistered replication
condition**, but R2 observations/data must not become confirmatory TEST evidence.

---

## 17. R3 protocol fields required before TEST

Before the R3 official confirmatory TEST, the protocol must freeze all of:

```
measurement identities
model / source conditions
population construction
target semantics
anchor selection
split / partition
missingness / ineligibility rules
calibration procedure protocol F
method-selection rule, if any
primary metric
secondary metrics
all three baselines
primary estimand(s)
uncertainty / inference procedure
multiplicity policy
support / range diagnostics
end-to-end secondary diagnostics
exclusion policy
failure handling
code + source-data provenance
```

### 17.1 Multiplicity cannot be postponed

If R3 has multiple methods, directions, models, populations, or primary metrics,
then the **primary hypothesis family** and the **multiplicity policy** must be
declared before confirmatory outcomes. Which cells were primary must not be decided
after seeing results.

---

## 18. R3 implementation verification contract

Absorbing R2's process lessons, the R3 primary-analysis implementation must pass
the following **before** confirmatory TEST outcomes are observed:

- algebraic invariants (section 18.1-18.3);
- synthetic oracle cases;
- artifact replay tests.

### 18.1 Required algebraic invariant: raw Brier

```
raw Brier = mean_i((p_i - y_i)^2)
```

with at least one hand-computable synthetic case.

### 18.2 Required transport invariant

For `A -> B`:

```
mean_i[ loss(g_A(S_B_i), Y_i) - loss(g_B(S_B_i), Y_i) ]
    == R_cross(A->B) - R_native(B)
```

within a declared floating tolerance. This specifically prevents the R2C
"source map evaluated on source score" bootstrap leg bug from recurring.

### 18.3 Required raw-relative invariant

```
mean_i[ loss(g_A(S_B_i), Y_i) - loss(S_B_i, Y_i) ]
    == R_cross(A->B) - R_raw(B)
```

### 18.4 Frozen-decision pairing invariant

Confirm that the same TEST item IDs, the same frozen anchor `D_i`, and the same
`Y_i` enter every measurement comparison. Winner agreement must not affect
inclusion.

### 18.5 Paired resampling invariant

If R3 uses bootstrap, randomization, or paired inference, it must keep the A score,
the B score, `Y`, and the item identity as a single paired unit.

### 18.6 Method-selection leakage invariant

If R3 uses train/audit-only selection, a test must demonstrate that the selection
code cannot consume confirmatory TEST outcomes — at minimum, through a structural
API / fixture regression.

### 18.7 Independent calculation check

For primary confirmatory metrics, the R3 protocol should require at least one
independent calculation path or an algebraically independent verification before
interpreting TEST results. This is a requirement on the R3 protocol, not an
implementation in v2.

---

## 19. Score geometry is a diagnostic, not a cause

Empirical range / score geometry is retained as a **predeclared explanatory
diagnostic**, exactly as in v1. It must not be called a causal mechanism or a true
support. The R2 observed-range asymmetry may generate an R3 hypothesis, but v2
does not write it as a confirmed mechanism.

---

## 20. Conditioned / multiplex graph semantics

Conceptually, if calibration transport is later represented as a graph:

> an edge is not a permanent property of two naked measurement nodes.

Any conceptual edge must be conditioned on at least:

```
source measurement
target measurement
M
P
T
L
E
F
```

### 20.1 Do not implement the graph

Neither this specification nor the R3 protocol implements:

```
TransportGraph
CompatibilityRegistry
transport store
runtime selector
automatic cross-identity reuse
```

That is future architecture. R2's evidence does not authorize it.

---

## 21. Production authorization boundary unchanged

Nothing in v2 relaxes the Phase 4C exact-identity runtime authorization. Even if a
future R3 finds empirical compatibility, it

```
DOES NOT automatically authorize
runtime cross-measurement profile reuse
```

The identity boundary remains fail-closed. Runtime identity and empirical
compatibility answer **different questions**: production continues explicit and
fail-closed; research compatibility is empirical and conditioned.

In particular, the fact that R2C showed the calibration procedure matters does
**not** mean the calibration procedure must become part of the Phase 4C
`CalibrationBinding`. A research conditioning axis is not a production runtime
binding change. Phase 4C remains frozen.

---

## 22. Non-claims and novelty guardrails

v2 inherits the v1 novelty guardrails and adds the following non-claims specific to
its new content:

- v2 does **not** claim that "calibration procedure matters" was first discovered
  here; it claims only that R2's own evidence forces `F` to be an explicit axis.
- v2 does **not** claim measurement identity is insufficient, and therefore does
  not conclude that exact runtime identity matching is too strict.
- v2 does **not** claim any compatibility relation for CAT and OVR.
- v2 does **not** claim that solver/version/precision is part of the statistical
  procedure `F`.
- v2 does **not** authorize any production contract change or dependency.

---

## 23. Relationship to the repository today

The R2 exploratory program is closed (see
`experiments/calibration_transport/R2_CLOSURE.md`). R3 is **not started** and is
**not authorized** by this document. The intended progression is:

```
Phase 4C final freeze                 (frozen)
Research Specification v1             (frozen; historical authority for R0/R1/R2)
R1 paired experiment-integrity harness (complete)
R2 exploratory program (R2A/R2B/R2C/R2C.1)  (closed)
Research Specification v2             (this document; frozen for R3+ semantics)
    |
external review -> human decides R3 design
    |
only if human-authorized, under v2:
R3 confirmatory transport study
R4 evidence-aware transport audit     (not started)
```

Nothing in this document is implemented. No R3 code, data, method panel, or model
set is selected here.

---

## 24. Scope and non-scope

### 24.1 In scope

- The conditioned-compatibility semantics required before R3 design.
- The calibration procedure `F` as an explicit conditioning axis.
- The exact-map vs procedure-level claim separation.
- The three-baseline interpretation contract.
- The confirmatory-analysis and implementation-verification discipline.

### 24.2 Out of scope

This document does not define, and no implementation may be started for:

- a fixed R3 method panel or a selection protocol (only the requirement is frozen);
- any transport graph, registry, store, or selector;
- any production contract change;
- any new dependency, scorer, runtime, or audit;
- any compatibility decision rule (`ACCEPT` / `REJECT`).
