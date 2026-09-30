# R4 Dataset Semantic Closure — HellaSwag + MedMCQA

Status:

```
STRUCTURAL / SEMANTIC GATE
NOT A POPULATION MANIFEST
NOT AN R4 FREEZE
NOT AN EXECUTION AUTHORIZATION
```

Scope of this document: dataset identity, dataset structural semantics, fixed-event
feasibility, strata feasibility, duplicate / overlap audit — for the two human-approved
non-MMLU R4 populations (`HellaSwag`, `MedMCQA`).

Explicitly out of scope: population manifest construction, TRAIN/TEST sampling, sample-size
selection, model inference, calibration, transport analysis, predictor development, R4
official execution.

No model was loaded, no tokenizer was loaded, no GPU was used, no forward or generation was
run, and no accuracy / Brier / LogLoss / calibration / transport / predictor outcome was
produced. The audit is a pure deterministic structural read of the pinned local parquet
snapshots.

---

## 1. Method and artifacts

| item | value |
| --- | --- |
| audit script | `experiments/calibration_transport/r4_dataset_semantic_audit.py` |
| script SHA256 | `13de90eaeba207ce6594805cb8b55ad1da96355ff4ac4946517028fb3e58fb11` |
| raw audit outputs | `/root/rivermind-data/r4-dataset-audit/hellaswag_semantic_audit.json` |
| | `/root/rivermind-data/r4-dataset-audit/medmcqa_semantic_audit.json` |
| output SHA256 (hellaswag) | `fe5be3b188fdf3fb0bb098873031a8bc37171794177247201cde78079e537572` |
| output SHA256 (medmcqa) | `bf73982c14c18211a89a0b8ad2d856f6d4375026b34c647eac95d3e8c2d137e3` |
| dataset cache root | `/root/rivermind-data/r4-datasets` |
| transport | `HF_ENDPOINT=https://hf-mirror.com`, `HF_HUB_DISABLE_XET=1` |
| parquet reader | `pyarrow 25.0.1` (installed to `/root/rivermind-data/r4-dataset-audit/pylibs`, project env untouched) |
| hashing primitive | `probvenance.fingerprint.fingerprint` (sha256 of canonical JSON) |

Normalization variants used for duplicate keys (both reported):

* **raw exact** — byte/string exact;
* **conservative normalized exact** — Unicode NFC + CRLF/CR → LF + outer whitespace strip.

No case folding, no punctuation removal, no stemming, no fuzzy matching, no embedding
similarity, no LLM dedup.

### 1.1 Revision identity gate

Both snapshots were requested at an explicit pinned revision and resolved offline afterwards;
`resolved revision == requested revision` for both.

| dataset | repo_id | requested = resolved revision | gated | license |
| --- | --- | --- | --- | --- |
| HellaSwag | `Rowan/hellaswag` | `218ec52e09a7e7462a5400043bb9a69a41d06b76` | false | MIT |
| MedMCQA | `openlifescienceai/medmcqa` | `91c6572c454088bf71b679ad90aa8dffcd0d5868` | false | apache-2.0 |

```
HELLASWAG IDENTITY = EXACT REVISION VERIFIED
MEDMCQA IDENTITY   = EXACT REVISION VERIFIED
```

Both are therefore `ELIGIBLE FOR HUMAN SOURCE-PIN FREEZE`. Neither is frozen by this
document.

Local snapshot paths:

```
/root/rivermind-data/r4-datasets/datasets--Rowan--hellaswag/snapshots/218ec52e09a7e7462a5400043bb9a69a41d06b76
/root/rivermind-data/r4-datasets/datasets--openlifescienceai--medmcqa/snapshots/91c6572c454088bf71b679ad90aa8dffcd0d5868
```

Downloaded files (sizes byte-exact against the revision tree):

| dataset | file | bytes |
| --- | --- | --- |
| HellaSwag | `data/train-00000-of-00001.parquet` | 24,365,524 |
| HellaSwag | `data/validation-00000-of-00001.parquet` | 6,315,951 |
| HellaSwag | `data/test-00000-of-00001.parquet` | 6,112,397 |
| HellaSwag | `README.md` / `.gitattributes` | 7,019 / 1,174 |
| MedMCQA | `data/train-00000-of-00001.parquet` | 85,899,025 |
| MedMCQA | `data/validation-00000-of-00001.parquet` | 1,476,104 |
| MedMCQA | `data/test-00000-of-00001.parquet` | 936,358 |
| MedMCQA | `README.md` / `.gitattributes` | 10,700 / 1,566 |

---

## 2. Exact split census (mechanically counted, not copied from the card)

| dataset | train | validation | test |
| --- | --- | --- | --- |
| HellaSwag | 39,905 | 10,042 | 10,003 |
| MedMCQA | 182,822 | 4,183 | 6,150 |

Both censuses agree with the dataset cards and with the previously recorded
`[STATIC REPO INSPECTION]` values.

---

## 3. Schema (actual pinned parquet)

HellaSwag:

```
ind            int32
activity_label string
ctx_a          string
ctx_b          string
ctx            string
endings        list<string>
source_id      string
split          string
split_type     string
label          string
```

MedMCQA:

```
id           string
question     string
opa          string
opb          string
opc          string
opd          string
cop          int64
choice_type  string
exp          string
subject_name string
topic_name   string
```

Both match the card-declared features. No schema coercion was applied.

---

## 4. Choice geometry

HellaSwag — `len(endings)` distribution:

| split | 4 | other |
| --- | --- | --- |
| train | 39,905 | 0 |
| validation | 10,042 | 0 |
| test | 10,003 | 0 |

```
100% fixed 4 in every split; no non-4 rows anywhere.
```

MedMCQA — declared option count is 4 (`opa`/`opb`/`opc`/`opd`), and:

| split | rows | missing option | empty option | duplicate option strings within item |
| --- | --- | --- | --- | --- |
| train | 182,822 | 0 | 0 | 693 (single 505 / multi 188) |
| validation | 4,183 | 0 | 0 | 21 (single 14 / multi 7) |
| test | 6,150 | 0 | 0 | 28 (single 21 / multi 7) |

Structural caveat: 693 train items (0.38%) declare the same option string twice, and in 310
of those the ground-truth index `cop` points at a string that occurs more than once. The
fixed event is still well defined (candidates are indices, ground truth is an index), but
two candidate descriptions would render identically. See §9.

---

## 5. Ground-truth semantics

HellaSwag (`label` is a string column):

| split | rows | empty label | unparseable | values |
| --- | --- | --- | --- | --- |
| train | 39,905 | 0 | 0 | 0–3 |
| validation | 10,042 | 0 | 0 | 0–3 |
| test | 10,003 | 10,003 | 0 | unlabeled (`""`) |

MedMCQA (`cop` is int64):

| split | rows | `cop == -1` | invalid (`not in 0..3` and not `-1`) | values |
| --- | --- | --- | --- | --- |
| train | 182,822 | 0 | 0 | 0–3 |
| validation | 4,183 | 0 | 0 | 0–3 |
| test | 6,150 | 6,150 | 0 | unlabeled |

```
HellaSwag: labeled = train, validation; unlabeled = test
MedMCQA:   labeled = train, validation; unlabeled = test
```

Documentation-vs-data discrepancy (MedMCQA card): the card states
"`cop` : Correct option, i.e., 1,2,3,4", but the pinned data uses **0-based** indices
`0,1,2,3`. This is a card-text issue only; the data is internally consistent.

---

## 6. Label balance (structural fact, not a model outcome)

HellaSwag train: `0: 9,986 (25.02%)`, `1: 10,031 (25.14%)`, `2: 9,867 (24.73%)`,
`3: 10,021 (25.11%)`.

HellaSwag validation: `0: 2,515 (25.04%)`, `1: 2,485 (24.75%)`, `2: 2,584 (25.73%)`,
`3: 2,458 (24.48%)`.

MedMCQA train: `0: 53,591 (29.31%)`, `1: 47,826 (26.16%)`, `2: 42,442 (23.22%)`,
`3: 38,963 (21.31%)`.

MedMCQA validation: `0: 1,348 (32.23%)`, `1: 1,085 (25.94%)`, `2: 925 (22.11%)`,
`3: 825 (19.72%)`.

---

## 7. HellaSwag structure

### 7.1 `activity_label` (primary strata candidate)

| split | unique | min | q1 | median | q3 | max | <5 | <10 | <20 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| train | 178 | 16 | 74.0 | 90.5 | 111.0 | 3,962 | 0 (0%) | 0 (0%) | 1 (0.56%) |
| validation | 192 | 1 | 8.0 | 11.0 | 18.0 | 2,627 | 17 (8.85%) | 79 (41.15%) | 147 (76.56%) |
| test | 207 | 1 | 8.0 | 13.0 | 25.0 | 2,442 | 19 (9.18%) | 75 (36.23%) | 144 (69.57%) |

`activity_label` is genuine and dense in TRAIN, but structurally sparse in
validation/test. Any stratified use of it on the labeled TEST source (validation) requires a
predeclared minimum-count rule.

### 7.2 `split_type`

| split | indomain | zeroshot |
| --- | --- | --- |
| train | 39,905 | 0 |
| validation | 5,001 | 5,041 |
| test | 5,002 | 5,001 |

Train is 100% `indomain`; validation/test are a near-even `indomain`/`zeroshot` mix.
Therefore `activity_label × split_type` compound strata cannot be formed identically across
TRAIN and TEST.

### 7.3 `activity_label × split_type` cells

| split | cells | min | median | max | cells <5 | cells <10 |
| --- | --- | --- | --- | --- | --- | --- |
| train | 178 | 16 | 90.5 | 3,962 | 0 | 0 |
| validation | 192 | 1 | 11.0 | 2,627 | 17 | 79 |

No extremely sparse cells in TRAIN; validation has 17 cells below 5. Reported as fact only —
no compound strata are adopted here.

### 7.4 `source_id`

`source_id` has the form `activitynet~v_<video-id>`, i.e. it identifies the source video /
context instance. Multiple rows can share one `source_id`:

| split | rows | unique `source_id` | repeated ids | rows in repeated ids | max rows per id |
| --- | --- | --- | --- | --- | --- |
| train | 39,905 | 32,220 | 4,141 | 11,826 | 12 |
| validation | 10,042 | 8,407 | 902 | 2,537 | 10 |
| test | 10,003 | 8,173 | 972 | 2,802 | 14 |

`source_id` is a genuine source-group identifier and is **not** disjoint at the row level.
It is, however, fully disjoint across TRAIN/TEST (§8.2).

---

## 8. Duplicate / overlap audit

### 8.1 Within-split duplicates

HellaSwag — `ctx + ordered endings`:

| split | raw duplicate keys | normalized duplicate keys | max multiplicity |
| --- | --- | --- | --- |
| train | 0 | 0 | 1 |
| validation | 0 | 0 | 1 |
| test | 0 | 0 | 1 |

MedMCQA — `question + ordered opa/opb/opc/opd`:

| split | raw duplicate keys | normalized duplicate keys | question-only duplicate keys |
| --- | --- | --- | --- |
| train | 0 | 0 | 0 |
| validation | 0 | 0 | 0 |
| test | 0 | 0 | 0 |

No within-split duplicate keys exist in either dataset, under either normalization.

### 8.2 Cross-split overlap (TRAIN source vs TEST source = train vs validation)

HellaSwag:

| key | shared keys | same label | conflicting label | train rows | validation rows |
| --- | --- | --- | --- | --- | --- |
| A raw exact `ctx + ordered endings` | 0 | 0 | 0 | 0 | 0 |
| B `source_id` | 0 | 0 | 0 | 0 | 0 |
| C normalized exact `ctx + ordered endings` | 0 | 0 | 0 | 0 | 0 |

MedMCQA:

| key | shared keys | same `cop` | conflicting `cop` |
| --- | --- | --- | --- |
| raw exact `question + ordered options` | 0 | 0 | 0 |
| question-only exact | 0 | — | — |

```
CROSS-SPLIT EXACT OVERLAP = 0 for both datasets (all key variants)
CROSS-SPLIT CONFLICTING-LABEL DUPLICATES = 0
WITHIN-SPLIT CONFLICTING-LABEL DUPLICATES = 0 (HellaSwag train/validation)
```

This means an R3-style `TEST pristine / TRAIN excludes exact TEST duplicates` policy would
currently exclude **nothing** for either dataset. The policy remains applicable as a
forward guard, but it is not load-bearing for these two sources at these revisions.

---

## 9. Fixed-event feasibility

### 9.1 Candidate mapping (measurement-neutral, proposed not frozen)

HellaSwag:

```
question              = ctx
context               = dataset/task metadata (if needed)
candidate names       = option-0 / option-1 / option-2 / option-3
candidate descriptions= endings[0..3] in source order
ground truth          = label (0..3)
```

MedMCQA:

```
question              = question
context               = dataset/task metadata (if needed)
candidate names       = option-0 / option-1 / option-2 / option-3
candidate descriptions= opa / opb / opc / opd in source order
ground truth          = cop (0..3)
```

At least one mechanical, lossless mapping is available for each dataset. No wording is
frozen by this document.

### 9.2 Anchor rule tested (EXACTLY ONE predeclared rule)

```
ANCHOR_PROTOCOL_ID      = "r4-fixed-event-anchor-deterministic-source-index-hash"
ANCHOR_PROTOCOL_VERSION = 1
anchor_index            = int(fingerprint({
                              "protocol_id", "protocol_version",
                              "dataset_id", "dataset_revision",
                              "source_split", "source_row_index"})[:16], 16) % 4
```

The anchor input contains **no** label, ground truth, question text, option/ending text, CAT
score, OVR score, or model output. Exactly one rule was evaluated; no rule was tuned, and no
rule was selected for balance.

Every row receives exactly one anchor; the assignment is deterministic and
content-independent.

### 9.3 Anchor distribution and `anchor == GT` fraction

| dataset | split | anchor 0 | anchor 1 | anchor 2 | anchor 3 | anchor == GT |
| --- | --- | --- | --- | --- | --- | --- |
| HellaSwag | train | 10,027 | 9,891 | 9,886 | 10,101 | 24.70% |
| HellaSwag | validation | 2,420 | 2,548 | 2,542 | 2,532 | 25.22% |
| MedMCQA | train | 45,496 | 45,887 | 45,981 | 45,458 | 24.96% |
| MedMCQA | validation | 1,010 | 1,062 | 1,070 | 1,041 | 25.15% |

The `anchor == GT` fraction is a **structural diagnostic of the anchor rule**. It is not a
model accuracy and it is not an R4 outcome. It was not used to tune the rule.

```
FIXED-EVENT CONSTRUCTION = STRUCTURALLY FEASIBLE (FEASIBILITY ONLY, NOT FROZEN)
```

Whether R4 reuses the exact R3 fingerprint machinery, and what protocol id/version it
carries, remains a human decision.

---

## 10. Strata capacity

Capacity = how many strata can support a per-stratum quota of N. This is **capacity only**,
not a sample-size decision.

HellaSwag, `activity_label` (TRAIN total 178 strata / validation total 192 strata):

| N per stratum | TRAIN strata able to support | TEST-source (validation) strata able to support |
| --- | --- | --- |
| 5 | 178 | 175 |
| 10 | 178 | 113 |
| 20 | 177 | 45 |
| 40 | 176 | 27 |

HellaSwag, `split_type`:

| N per stratum | TRAIN | validation |
| --- | --- | --- |
| 5 / 10 / 20 / 40 | 1 | 2 |

MedMCQA, `subject_name` (21 strata in both splits):

| N per stratum | TRAIN strata able to support | TEST-source (validation) strata able to support |
| --- | --- | --- |
| 5 | 21 | 20 |
| 10 | 21 | 20 |
| 20 | 21 | 18 |
| 40 | 21 | 16 |

MedMCQA, `topic_name`:

| N per stratum | TRAIN | validation |
| --- | --- | --- |
| 5 | 1,758 of 2,389 | 5 |
| 10 | 1,276 of 2,389 | 4 |
| 20 | 752 of 2,389 | 4 |
| 40 | 374 of 2,389 | 4 |

### 10.1 HellaSwag `activity_label` intersection (TRAIN vs TEST source)

| metric | value |
| --- | --- |
| train unique | 178 |
| validation unique | 192 |
| intersection | 178 |
| train-only | 0 |
| validation-only | 14 |
| min TRAIN count among shared strata | 16 |
| min validation count among shared strata | 1 |

Validation-only labels: `Clean and jerk`, `Cutting the grass`, `Family Life`,
`Gargling mouthwash`, `Having an ice cream`, `High jump`, `Ice fishing`,
`Layup drill in basketball`, `Personal Care and Style`, `Playing harmonica`,
`Playing violin`, `Running a marathon`, `Sharpening knives`, `Washing face`.

Because all 178 TRAIN labels also appear in validation, a "same strata in TRAIN and TEST"
requirement is satisfiable — but only if a minimum-count rule removes the sparsely populated
validation strata.

### 10.2 MedMCQA `subject_name` intersection (TRAIN vs TEST source)

21 train subjects, 21 validation subjects, intersection 21, no train-only, no
validation-only. Per-subject counts:

| subject | TRAIN | validation |
| --- | --- | --- |
| Anaesthesia | 3,172 | 34 |
| Anatomy | 14,560 | 234 |
| Biochemistry | 8,282 | 171 |
| Dental | 8,938 | 1,318 |
| ENT | 4,919 | 53 |
| Forensic Medicine | 5,900 | 67 |
| Gynaecology & Obstetrics | 10,013 | 224 |
| Medicine | 17,887 | 295 |
| Microbiology | 11,314 | 122 |
| Ophthalmology | 6,932 | 58 |
| Orthopaedics | 2,999 | 20 |
| Pathology | 14,884 | 337 |
| Pediatrics | 8,037 | 234 |
| Pharmacology | 13,758 | 243 |
| Physiology | 8,830 | 171 |
| Psychiatry | 4,442 | 16 |
| Radiology | 4,395 | 69 |
| Skin | 1,771 | 17 |
| Social & Preventive Medicine | 11,882 | 129 |
| Surgery | 16,862 | 369 |
| Unknown | 3,045 | 2 |

`Unknown` (validation n = 2) is the binding constraint for a "same subject in TRAIN and
TEST" requirement.

---

## 11. `choice_type = multi` semantic audit (MedMCQA)

Card definition: `single` = "Single-choice question, where each choice contains a single
option"; `multi` = "Multi-choice question, where each choice contains a combination of
multiple suboptions". The card also states `cop` remains a single index.

Distribution: train single 120,765 / multi 62,057; validation single 2,816 / multi 1,367;
test single 4,134 / multi 2,016.

Deterministic sample (first 20 by source-row fingerprint, train split; 20 multi + 20 single)
was inspected structurally. Every sampled `multi` item has:

* exactly 4 distinct option strings (`opa`…`opd`),
* one single ground-truth index `cop ∈ {0,1,2,3}`,
* no visible "combination of multiple suboptions" inside the option strings.

The sampled `multi` items are instead recognisable by question form ("All of the following
are true … EXCEPT", "True about X include the following except"), i.e. the label appears to
describe the *logical form* of the item rather than a multi-answer option structure.

Mechanical whole-train probe over the 62,057 `multi` items:

| signal | count | fraction |
| --- | --- | --- |
| an option contains `;` | 94 | 0.15% |
| an option contains a sub-option enumerator pattern (`(a)`, `a)`, `1.`, …) | 190 | 0.31% |

Conclusion:

```
choice_type=multi  =>  SEMANTICALLY COMPATIBLE with
                        "4 mutually exclusive declared candidate strings
                         + one unique correct candidate index"
                       (based on structural evidence)
```

with the caveat that the card's "combination of multiple suboptions" wording is not
observable in the option strings for ~99.7% of `multi` items. Whether to keep all, restrict
to `single`, or require further review is a human decision (Q6).

No filtering was applied and no filtering is proposed by this document.

---

## 12. Semantic caveats

1. **HellaSwag `source_id` grouping** — rows are grouped by source video/context
   (max 12 rows per id in TRAIN). Group-aware handling may matter for TRAIN/TEST
   independence. No group-aware decision is made here.
2. **HellaSwag `activity_label` sparsity in validation/test** — 8.85% of validation strata
   have < 5 rows; 41.15% have < 10.
3. **HellaSwag `split_type`** — TRAIN is 100% `indomain`, TEST source is ~50/50
   `indomain`/`zeroshot`; compound `activity_label × split_type` strata are not
   TRAIN/TEST-comparable.
4. **MedMCQA `choice_type = multi`** — card wording not matched by observed option strings
   (§11).
5. **MedMCQA `topic_name` is not a stable stratum field** — TRAIN has 2,389 clinical topics
   (26.41% with < 5 rows), but validation carries only 5 distinct values, of which 3,760 of
   4,183 rows are `None` and the remainder are exam tags (`AIIMS 2017`, `AIIMS 2018`,
   `AIIMS 2019`, `AIIMS 2020`), and test is 100% `None`. `topic_name` is therefore not
   usable as a cross-split stratum.
6. **MedMCQA validation subject sparsity** — `Unknown` has 2 rows; `Psychiatry` 16;
   `Orthopaedics` 20; `Anaesthesia` 34.
7. **MedMCQA duplicate option strings within an item** — 693 train / 21 validation items;
   in 310 train items `cop` points at a duplicated string.
8. **MedMCQA test split is unlabeled and stripped** — `cop == -1`, `exp` empty,
   `topic_name` `None` for 100% of test rows.
9. **Public benchmark contamination cannot be excluded.** The structural duplicate audit
   proves the *absence of exact intra-dataset duplicate keys*; it does **not** prove absence
   of pretraining contamination. No contamination-free claim is made.

---

## 13. Dataset statuses

```
HellaSwag: SEMANTICALLY_ELIGIBLE
  identity            : PASS (exact revision verified)
  license             : MIT
  choice geometry     : PASS (100% fixed 4)
  ground truth        : PASS (train/validation labeled 0-3; test unlabeled)
  split labels        : PASS (test unlabeled, so TRAIN=train / TEST=validation)
  duplicate status    : PASS (0 within-split, 0 cross-split, 0 conflicting labels)
  strata feasibility  : PASS with caveat (activity_label dense in train, sparse in validation)
  fixed-event         : PASS (feasibility only, not frozen)
  source-group issue  : NEEDS_REVIEW (source_id groups up to 12 train rows; disjoint across
                        TRAIN/TEST, but group-aware handling is a human choice)

MedMCQA: SEMANTICALLY_ELIGIBLE
  identity            : PASS (exact revision verified)
  license             : apache-2.0
  choice geometry     : PASS with caveat (4 options always present; 693 train items repeat
                        an option string)
  ground truth        : PASS (train/validation cop 0-3; test cop == -1)
  split labels        : PASS (test unlabeled, so TRAIN=train / TEST=validation)
  duplicate status    : PASS (0 within-split, 0 cross-split, 0 conflicting cop)
  strata feasibility  : PASS for subject_name; topic_name too sparse / not cross-split stable
  fixed-event         : PASS (feasibility only, not frozen)
  choice_type=multi   : SEMANTICALLY COMPATIBLE with the fixed-event contract (see §11)
```

---

## 14. Human decision table (structural evidence only; no selection made)

| # | question | structural evidence | options |
| --- | --- | --- | --- |
| Q1 | HellaSwag source revision | `218ec52e09a7e7462a5400043bb9a69a41d06b76` resolved == requested; MIT; 0 gated | exact revision verified → eligible to freeze |
| Q2 | MedMCQA source revision | `91c6572c454088bf71b679ad90aa8dffcd0d5868` resolved == requested; apache-2.0; 0 gated | exact revision verified → eligible to freeze |
| Q3 | HellaSwag strata | `activity_label` 178 train strata (min 16, 0% <5); validation 192 strata (8.85% <5, 41.15% <10); all 178 train labels appear in validation; `split_type` not TRAIN/TEST-comparable | `activity_label` with a predeclared minimum-count rule / coarser activity grouping / other |
| Q4 | HellaSwag `source_id` | group id over source video; train 4,141 repeated ids covering 11,826 rows (max 12); 0 shared ids with validation | group-aware handling required? yes / no |
| Q5 | MedMCQA strata | `subject_name` 21/21 in both splits, min validation n = 2 (`Unknown`); `topic_name` 2,389 train strata but only 5 distinct validation values (mostly `None`, rest exam tags) and 100% `None` in test | `subject_name` usable; `topic_name` NOT viable as a cross-split stratum |
| Q6 | MedMCQA `multi` | 62,057 train multi items; sampled items structurally identical to single (4 distinct options, single `cop`); sub-option enumerators in only 0.31% | keep all / restrict to `single` / needs further review |
| Q7 | overlap policy | 0 within-split and 0 cross-split exact duplicates in either dataset under raw and conservative normalization | R3-style `TEST pristine, TRAIN excludes exact TEST duplicates` applies and currently excludes nothing |
| Q8 | sample-size gate | capacity tables in §10 | human must decide TRAIN fitting budget, TEST evaluation budget, per-stratum allocation |

---

## 15. Prohibitions observed

```
model load              : NO
tokenizer load          : NO
GPU used                : NO
model forward           : NO
generation              : NO
study dataset inference : NO
accuracy                : NO
Brier                   : NO
LogLoss                 : NO
calibration             : NO
calibration transport   : NO
winner agreement        : NO
deployment delta        : NO
transport penalty       : NO
predictor outcome       : NO
frozen R3 modification  : NO
existing probe report modification : NO
planning authority modification    : NO
commit                  : NO
push                    : NO
```
