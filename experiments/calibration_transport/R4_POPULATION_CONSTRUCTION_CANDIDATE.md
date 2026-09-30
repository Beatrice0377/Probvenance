# R4 Population Construction Candidate

**STATUS: `POPULATION CONSTRUCTION CANDIDATE / READY FOR HUMAN FREEZE REVIEW`**

本文件记录 R4 两个 non-MMLU population 的 **deterministic population construction
candidate**。它 **不是 FINAL POPULATION MANIFEST**，**不是 TRAIN/TEST freeze**，
**不是 R4 execution authorization**。

```text
R4 STATUS = DRAFT / NOT FROZEN / NOT EXECUTION-AUTHORIZED
```

---

## 1. Scope

```text
artifact class        : POPULATION CONSTRUCTION CANDIDATE
datasets              : Rowan/hellaswag, openlifescienceai/medmcqa
construction type     : deterministic, content-independent, stratified
budgets               : PRIMARY TRAIN 456（保持不变）
                        SECONDARY NESTED ROBUSTNESS TRAIN 912（= 456 + extension 456）
model execution       : NONE
calibration execution : NONE
scientific outcome    : NONE
commit status         : NOT COMMITTED（candidate artifacts 不入库）
```

本 candidate 由 human 在 dataset semantic closure（`R4_DATASET_SEMANTIC_CLOSURE.md`）
之后、任何 R4 model outcome 之前预先声明的规则机械生成。

## 2. Inputs（source identity）

```text
HellaSwag  repo_id  : Rowan/hellaswag
           revision : 218ec52e09a7e7462a5400043bb9a69a41d06b76
           snapshot : /root/rivermind-data/r4-datasets/datasets--Rowan--hellaswag/snapshots/218ec52e09a7e7462a5400043bb9a69a41d06b76
MedMCQA    repo_id  : openlifescienceai/medmcqa
           revision : 91c6572c454088bf71b679ad90aa8dffcd0d5868
           snapshot : /root/rivermind-data/r4-datasets/datasets--openlifescienceai--medmcqa/snapshots/91c6572c454088bf71b679ad90aa8dffcd0d5868
normalization       : Unicode NFC + CRLF/CR->LF + outer strip (no case folding, no stemming)
```

两个 revision 均为 `EXACT REVISION VERIFIED`（`resolved sha == requested sha`，
见 `R4_DATASET_SEMANTIC_CLOSURE.md`）。candidate 只读取本地 pinned snapshot，
不访问网络，不改变 revision identity。

## 3. Protocols

```text
population_protocol_id      = r4-stratified-population-construction
population_protocol_version = 1
selection_protocol_id       = r4-stratified-source-index-hash-selection
selection_protocol_version  = 1
anchor_protocol_id          = r4-fixed-event-anchor-deterministic-source-index-hash
anchor_protocol_version     = 1
extension_protocol_id       = r4-nested-residual-extension
extension_protocol_version  = 1
calibration TRAIN N         = 456（PRIMARY）
robustness TRAIN N          = 912（SECONDARY，nested；= 456 + 456）
candidate names             = option-0, option-1, option-2, option-3
```

```text
item_id = fingerprint({
    population_protocol_id, population_protocol_version,
    dataset_id, dataset_revision, source_split, source_row_index })

selection_rank = fingerprint({
    selection_protocol_id, selection_protocol_version,
    dataset_id, dataset_revision, source_split, stratum, source_row_index })

anchor_index = int(fingerprint({
    anchor_protocol_id, anchor_protocol_version,
    dataset_id, dataset_revision, source_split, source_row_index })[:16], 16) % 4
```

```text
FORBIDDEN as input to item_id / selection_rank / anchor_index:
  ground truth, label, cop, question text, candidate text,
  model output, CAT score, OVR score, any outcome
```

`item_id` 因此 answer-independent，不暴露 correctness。

## 4. Item record schema

```text
dataset_id, dataset_revision, source_split, source_row_index,
item_id, split (TRAIN|TEST), stratum, group_id,
question, candidate_names, candidate_descriptions,
ground_truth_index, anchor_index
+ HellaSwag structural metadata : split_type
+ MedMCQA   structural metadata : choice_type
```

candidate order 为 source order，不 permutation。

## 5. HellaSwag construction

```text
calibration TRAIN source : train
evaluation  TEST  source : validation
primary stratum          : activity_label
group identity           : source_id
```

```text
eligibility (both splits) : exactly 4 endings; all endings strings;
                            label parses to 0..3; source_id non-empty;
                            activity_label non-empty
allocation                : Hamilton / largest-remainder,
                            weight = eligible train rows per activity_label,
                            total quota = 456
within-stratum rank       : selection_rank, tie-break by source_row_index
group constraint          : at most one selected TRAIN row per source_id
                            (skip and take next ranked)
overlap guard             : skip TRAIN row whose ctx + ordered endings
                            exactly duplicates a TEST row
quota shortfall           : PopulationError / STOP（不跨 strata 偷补）
```

### 5.0 HellaSwag `source_id` structural gate（predeclared precondition）

构造 population 之前机械验证（只读 pinned snapshot）：

```text
train      : source_id=32220
             source_id -> activity_label 违反数 = 0
             source_id -> split_type     违反数 = 0
validation : source_id=8407
             source_id -> activity_label 违反数 = 0
             source_id -> split_type     违反数 = 0
=> SOURCE_ID STRUCTURAL GATE = PASS
```

即：在每一个 source split 内，每个 `source_id` 恰好映射到一个 `activity_label`；
在 validation 内，每个 `source_id` 恰好映射到一个 `split_type`。
因此 `source_id` 可以作为合法的 group identity 使用。

### 5.1 HellaSwag results

```text
TRAIN selected        : 456
TEST rows             : 10042
TRAIN strata selected : 174
TEST  strata          : 192
TRAIN unique source_id: 456
TEST  unique source_id: 8407
TRAIN n TEST source_id: 0
overlap exclusions    : 0
source_id skips       : 0
test ineligible rows  : 0
train ineligible rows : 0
```

```text
14 validation-only activity labels（在 source train split 中不存在，只出现在 validation）:
  Clean and jerk, Cutting the grass, Family Life, Gargling mouthwash, Having an ice cream, High jump, Ice fishing, Layup drill in basketball, Personal Care and Style, Playing harmonica, Playing violin, Running a marathon, Sharpening knives, Washing face

activity_label eligible 但 Hamilton quota = 0（strata 过小）:
  Home,Categories, Knitting, Spread mulch, Windsurfing
```

**措辞更正（documentation correction，不改变 manifest）**

准确语义是：

```text
14 validation-only activity labels are absent from the source train split.
They are target-only semantic strata,
NOT train strata with zero eligible rows.
```

```text
train unique      = 178
validation unique = 192
shared            = 178
validation-only   = 14
train-only        = 0
```

human decision：这 14 个 validation-only activity labels **KEEP IN PRIMARY TEST**（不删除），
角色为 **TARGET-ONLY SEMANTIC SUPPORT**，不是 sampling error、不是 invalid rows。
不得为了让 TRAIN/TEST strata 完全相同而删除。

### 5.2 HellaSwag group / subgroup diagnostics

```text
TEST rows in repeated source_id  : 2537
TEST repeated source_id count    : 902
TEST max rows per source_id      : 10
```

`split_type` 仅作为 **secondary subgroup diagnostic**（不是 primary strata，
不是 independent population）：

| split_type | rows | anchor==GT |
|---|---|---|
| indomain | 5001 | 0.255149 |
| zeroshot | 5041 | 0.249355 |

### 5.3 HellaSwag anchor / ground-truth distributions（structural diagnostics only）

| index | TRAIN anchor | TEST anchor | TRAIN GT | TEST GT |
|---|---|---|---|---|
| 0 | 115 | 2420 | 112 | 2515 |
| 1 | 95 | 2548 | 128 | 2485 |
| 2 | 116 | 2542 | 97 | 2584 |
| 3 | 130 | 2532 | 119 | 2458 |

anchor==GT fraction：TRAIN 0.230263，TEST 0.252241。

以上 GT 统计**只用于结构描述**，不用于修改任何 selection rule。

### 5.4 HellaSwag per-stratum allocation

| activity_label | eligible TRAIN rows | TRAIN quota | TRAIN selected | TEST rows |
|---|---|---|---|---|
| Applying sunscreen | 73 | 1 | 1 | 20 |
| Archery | 89 | 1 | 1 | 9 |
| Arm wrestling | 133 | 2 | 2 | 20 |
| Assembling bicycle | 78 | 1 | 1 | 8 |
| BMX | 109 | 1 | 1 | 9 |
| Baking cookies | 184 | 2 | 2 | 33 |
| Ballet | 65 | 1 | 1 | 7 |
| Bathing dog | 57 | 1 | 1 | 11 |
| Baton twirling | 120 | 1 | 1 | 14 |
| Beach soccer | 71 | 1 | 1 | 12 |
| Beer pong | 91 | 1 | 1 | 15 |
| Blow-drying hair | 96 | 1 | 1 | 9 |
| Blowing leaves | 72 | 1 | 1 | 11 |
| Braiding hair | 109 | 1 | 1 | 6 |
| Breakdancing | 92 | 1 | 1 | 2 |
| Brushing teeth | 74 | 1 | 1 | 3 |
| Building sandcastles | 102 | 1 | 1 | 5 |
| Bullfighting | 111 | 1 | 1 | 8 |
| Calf roping | 115 | 1 | 1 | 27 |
| Camel ride | 97 | 1 | 1 | 16 |
| Canoeing | 107 | 1 | 1 | 14 |
| Capoeira | 83 | 1 | 1 | 14 |
| Cars & Other Vehicles | 646 | 7 | 7 | 65 |
| Carving jack-o-lanterns | 89 | 1 | 1 | 18 |
| Cheerleading | 94 | 1 | 1 | 23 |
| Chopping wood | 89 | 1 | 1 | 9 |
| Clean and jerk | 0 | 0 | 0 | 137 |
| Cleaning shoes | 84 | 1 | 1 | 11 |
| Cleaning sink | 69 | 1 | 1 | 8 |
| Cleaning windows | 79 | 1 | 1 | 16 |
| Clipping cat claws | 97 | 1 | 1 | 22 |
| Computers and Electronics | 3715 | 42 | 42 | 454 |
| Cricket | 91 | 1 | 1 | 5 |
| Croquet | 82 | 1 | 1 | 11 |
| Cutting the grass | 0 | 0 | 0 | 131 |
| Decorating the Christmas tree | 109 | 1 | 1 | 7 |
| Disc dog | 137 | 2 | 2 | 32 |
| Discus throw | 117 | 1 | 1 | 12 |
| Dodgeball | 58 | 1 | 1 | 9 |
| Doing a powerbomb | 87 | 1 | 1 | 12 |
| Doing crunches | 77 | 1 | 1 | 15 |
| Doing fencing | 85 | 1 | 1 | 8 |
| Doing karate | 73 | 1 | 1 | 11 |
| Doing kickboxing | 66 | 1 | 1 | 4 |
| Doing motocross | 83 | 1 | 1 | 7 |
| Drinking beer | 46 | 1 | 1 | 11 |
| Drinking coffee | 87 | 1 | 1 | 5 |
| Drum corps | 73 | 1 | 1 | 8 |
| Education and Communications | 1604 | 18 | 18 | 201 |
| Elliptical trainer | 75 | 1 | 1 | 15 |
| Family Life | 0 | 0 | 0 | 980 |
| Finance and Business | 2046 | 23 | 23 | 265 |
| Fixing bicycle | 114 | 1 | 1 | 6 |
| Fixing the roof | 85 | 1 | 1 | 4 |
| Food and Entertaining | 3962 | 45 | 45 | 500 |
| Fun sliding down | 84 | 1 | 1 | 5 |
| Futsal | 128 | 1 | 1 | 25 |
| Gargling mouthwash | 0 | 0 | 0 | 63 |
| Getting a haircut | 159 | 2 | 2 | 8 |
| Getting a piercing | 105 | 1 | 1 | 18 |
| Getting a tattoo | 104 | 1 | 1 | 2 |
| Grooming dog | 111 | 1 | 1 | 11 |
| Hand car wash | 159 | 2 | 2 | 23 |
| Hand washing clothes | 72 | 1 | 1 | 8 |
| Hanging wallpaper | 116 | 1 | 1 | 11 |
| Having an ice cream | 0 | 0 | 0 | 116 |
| Health | 3415 | 39 | 39 | 427 |
| High jump | 0 | 0 | 0 | 117 |
| Hitting a pinata | 143 | 2 | 2 | 16 |
| Holidays and Traditions | 258 | 3 | 3 | 38 |
| Home and Garden | 2813 | 32 | 32 | 390 |
| Home,Categories | 16 | 0 | 0 | 2 |
| Hopscotch | 71 | 1 | 1 | 7 |
| Horseback riding | 82 | 1 | 1 | 12 |
| Hula hoop | 79 | 1 | 1 | 8 |
| Hurling | 106 | 1 | 1 | 8 |
| Ice fishing | 0 | 0 | 0 | 127 |
| Installing carpet | 61 | 1 | 1 | 11 |
| Ironing clothes | 77 | 1 | 1 | 15 |
| Javelin throw | 66 | 1 | 1 | 5 |
| Kayaking | 86 | 1 | 1 | 7 |
| Kite flying | 59 | 1 | 1 | 2 |
| Kneeling | 94 | 1 | 1 | 11 |
| Knitting | 44 | 0 | 0 | 5 |
| Laying tile | 74 | 1 | 1 | 12 |
| Layup drill in basketball | 0 | 0 | 0 | 111 |
| Long jump | 91 | 1 | 1 | 7 |
| Longboarding | 117 | 1 | 1 | 11 |
| Making a cake | 207 | 2 | 2 | 30 |
| Making a lemonade | 145 | 2 | 2 | 32 |
| Making a sandwich | 145 | 2 | 2 | 12 |
| Mixing drinks | 160 | 2 | 2 | 13 |
| Mooping floor | 104 | 1 | 1 | 9 |
| Mowing the lawn | 90 | 1 | 1 | 9 |
| Paintball | 84 | 1 | 1 | 10 |
| Painting | 87 | 1 | 1 | 1 |
| Painting furniture | 65 | 1 | 1 | 19 |
| Personal Care and Style | 0 | 0 | 0 | 2627 |
| Pets and Animals | 1843 | 21 | 21 | 255 |
| Philosophy and Religion | 228 | 3 | 3 | 24 |
| Ping-pong | 54 | 1 | 1 | 9 |
| Plastering | 73 | 1 | 1 | 7 |
| Plataform diving | 77 | 1 | 1 | 13 |
| Playing accordion | 45 | 1 | 1 | 6 |
| Playing badminton | 63 | 1 | 1 | 15 |
| Playing bagpipes | 64 | 1 | 1 | 10 |
| Playing beach volleyball | 54 | 1 | 1 | 17 |
| Playing blackjack | 55 | 1 | 1 | 6 |
| Playing congas | 115 | 1 | 1 | 8 |
| Playing drums | 108 | 1 | 1 | 15 |
| Playing guitarra | 74 | 1 | 1 | 18 |
| Playing harmonica | 0 | 0 | 0 | 97 |
| Playing ice hockey | 98 | 1 | 1 | 8 |
| Playing kickball | 61 | 1 | 1 | 2 |
| Playing lacrosse | 67 | 1 | 1 | 15 |
| Playing piano | 65 | 1 | 1 | 9 |
| Playing polo | 83 | 1 | 1 | 12 |
| Playing pool | 95 | 1 | 1 | 26 |
| Playing rubik cube | 100 | 1 | 1 | 3 |
| Playing saxophone | 75 | 1 | 1 | 9 |
| Playing squash | 77 | 1 | 1 | 4 |
| Playing violin | 0 | 0 | 0 | 121 |
| Playing water polo | 107 | 1 | 1 | 15 |
| Pole vault | 91 | 1 | 1 | 6 |
| Polishing forniture | 79 | 1 | 1 | 9 |
| Polishing shoes | 69 | 1 | 1 | 14 |
| Powerbocking | 85 | 1 | 1 | 14 |
| Preparing pasta | 164 | 2 | 2 | 12 |
| Preparing salad | 125 | 1 | 1 | 10 |
| Putting in contact lenses | 115 | 1 | 1 | 12 |
| Putting on makeup | 95 | 1 | 1 | 7 |
| Putting on shoes | 90 | 1 | 1 | 2 |
| Raking leaves | 55 | 1 | 1 | 11 |
| Relationships | 1060 | 12 | 12 | 113 |
| Removing curlers | 96 | 1 | 1 | 9 |
| Removing ice from car | 108 | 1 | 1 | 6 |
| River tubing | 103 | 1 | 1 | 11 |
| Rock climbing | 64 | 1 | 1 | 9 |
| Rock-paper-scissors | 73 | 1 | 1 | 6 |
| Rollerblading | 84 | 1 | 1 | 13 |
| Roof shingle removal | 64 | 1 | 1 | 14 |
| Rope skipping | 122 | 1 | 1 | 21 |
| Running a marathon | 0 | 0 | 0 | 140 |
| Sailing | 83 | 1 | 1 | 4 |
| Scuba diving | 122 | 1 | 1 | 23 |
| Sharpening knives | 0 | 0 | 0 | 138 |
| Shaving | 95 | 1 | 1 | 9 |
| Shaving legs | 91 | 1 | 1 | 5 |
| Shot put | 91 | 1 | 1 | 12 |
| Shoveling snow | 101 | 1 | 1 | 18 |
| Shuffleboard | 57 | 1 | 1 | 13 |
| Skateboarding | 80 | 1 | 1 | 9 |
| Skiing | 109 | 1 | 1 | 17 |
| Slacklining | 123 | 1 | 1 | 12 |
| Smoking a cigarette | 61 | 1 | 1 | 7 |
| Smoking hookah | 60 | 1 | 1 | 10 |
| Snatch | 100 | 1 | 1 | 6 |
| Snow tubing | 109 | 1 | 1 | 18 |
| Spinning | 72 | 1 | 1 | 18 |
| Sports and Fitness | 1242 | 14 | 14 | 144 |
| Spread mulch | 38 | 0 | 0 | 6 |
| Starting a campfire | 84 | 1 | 1 | 14 |
| Sumo | 110 | 1 | 1 | 3 |
| Surfing | 112 | 1 | 1 | 20 |
| Swimming | 100 | 1 | 1 | 14 |
| Table soccer | 76 | 1 | 1 | 7 |
| Tai chi | 82 | 1 | 1 | 9 |
| Tango | 100 | 1 | 1 | 9 |
| Tennis serve with ball bouncing | 78 | 1 | 1 | 13 |
| Throwing darts | 86 | 1 | 1 | 4 |
| Travel | 344 | 4 | 4 | 60 |
| Trimming branches or hedges | 112 | 1 | 1 | 4 |
| Triple jump | 96 | 1 | 1 | 11 |
| Tumbling | 88 | 1 | 1 | 7 |
| Uncategorized | 51 | 1 | 1 | 7 |
| Using parallel bars | 111 | 1 | 1 | 21 |
| Using the pommel horse | 91 | 1 | 1 | 10 |
| Using the rowing machine | 81 | 1 | 1 | 10 |
| Using uneven bars | 65 | 1 | 1 | 8 |
| Vacuuming floor | 95 | 1 | 1 | 9 |
| Volleyball | 69 | 1 | 1 | 4 |
| Wakeboarding | 106 | 1 | 1 | 13 |
| Walking the dog | 85 | 1 | 1 | 8 |
| Washing face | 0 | 0 | 0 | 136 |
| Washing hands | 122 | 1 | 1 | 5 |
| Waterskiing | 116 | 1 | 1 | 19 |
| Welding | 83 | 1 | 1 | 8 |
| Windsurfing | 41 | 0 | 0 | 7 |
| Work World | 746 | 9 | 9 | 86 |
| Wrapping presents | 149 | 2 | 2 | 17 |
| Youth | 1176 | 13 | 13 | 161 |
| Zumba | 69 | 1 | 1 | 10 |

## 6. MedMCQA construction

```text
calibration TRAIN source : train
evaluation  TEST  source : validation
primary stratum          : subject_name（topic_name 不采用）
choice_type              : KEEP ALL（single 与 multi 均保留）
```

```text
structural eligibility    : opa/opb/opc/opd 均为非空字符串；
                            conservative-normalized 四个 option 两两不同；
                            cop in {0,1,2,3}
                            （排除规则只看 candidate strings，不读 cop / correctness）
allocation                : Hamilton / largest-remainder,
                            weight = eligible train rows per subject_name,
                            total quota = 456
within-stratum rank       : selection_rank, tie-break by source_row_index
overlap guard             : skip TRAIN row whose question + ordered options
                            exactly duplicates a TEST row；
                            conflicting cop for the same event =>
                            PopulationError / STOP FOR HUMAN REVIEW
quota shortfall           : PopulationError / STOP
```

### 6.1 MedMCQA results

```text
TRAIN selected : 456
TEST rows      : 4162（validation 4183 − 21 duplicate-option）
TRAIN strata   : 21
TEST  strata   : 21
overlap exclusions : 0
```

### 6.2 MedMCQA structural exclusions

```text
TRAIN duplicate-option rows : 693
  by choice_type            : {'multi': 188, 'single': 505}
TEST  duplicate-option rows : 21
  by choice_type            : {'multi': 7, 'single': 14}
```

排除原因为 `duplicate-option-string`：同一 item 的四个 option 在 conservative
normalization 后不是两两不同。index-level event 技术上仍可定义，但相同 candidate
description 会给 OVR fixed-event 解释带来可避免的语义歧义，因此按预声明规则做
structural exclusion（不是 outcome filtering）。

### 6.3 MedMCQA choice_type diagnostic

| split | single | multi |
|---|---|---|
| TRAIN | 298 | 158 |
| TEST | 2802 | 1360 |

### 6.4 MedMCQA anchor / ground-truth distributions（structural diagnostics only）

| index | TRAIN anchor | TEST anchor | TRAIN GT | TEST GT |
|---|---|---|---|---|
| 0 | 111 | 1002 | 138 | 1341 |
| 1 | 109 | 1056 | 131 | 1079 |
| 2 | 124 | 1065 | 103 | 921 |
| 3 | 112 | 1039 | 84 | 821 |

anchor==GT fraction：TRAIN 0.188596，TEST 0.250841。

### 6.5 MedMCQA per-stratum allocation

| subject_name | eligible TRAIN rows | TRAIN quota | TRAIN selected | TEST rows |
|---|---|---|---|---|
| Anaesthesia | 3161 | 8 | 8 | 34 |
| Anatomy | 14491 | 36 | 36 | 232 |
| Biochemistry | 8251 | 21 | 21 | 170 |
| Dental | 8925 | 22 | 22 | 1312 |
| ENT | 4910 | 12 | 12 | 52 |
| Forensic Medicine | 5890 | 15 | 15 | 66 |
| Gynaecology & Obstetrics | 9992 | 25 | 25 | 224 |
| Medicine | 17822 | 45 | 45 | 293 |
| Microbiology | 11274 | 28 | 28 | 122 |
| Ophthalmology | 6914 | 17 | 17 | 58 |
| Orthopaedics | 2997 | 8 | 8 | 20 |
| Pathology | 14836 | 37 | 37 | 333 |
| Pediatrics | 8010 | 20 | 20 | 233 |
| Pharmacology | 13698 | 34 | 34 | 243 |
| Physiology | 8753 | 22 | 22 | 171 |
| Psychiatry | 4416 | 11 | 11 | 16 |
| Radiology | 4383 | 11 | 11 | 69 |
| Skin | 1761 | 4 | 4 | 17 |
| Social & Preventive Medicine | 11835 | 30 | 30 | 127 |
| Surgery | 16806 | 42 | 42 | 368 |
| Unknown | 3004 | 8 | 8 | 2 |

## 7. Candidate manifest artifacts

```text
hellaswag:
  path                : /root/rivermind-data/r4-population-candidates/hellaswag_population_candidate.json
  bytes               : 15523140
  manifest_fingerprint: 5c45043ba4f0ec436c16dcf494ff26be435c7857244bcbefa321d1678129c400
  file_sha256         : 0724128b9168b15a8796f260441c89025c3a224faf079cf7177b1c2faaec53cc
  train/test          : 456 / 10042
  role                : PRIMARY
medmcqa:
  path                : /root/rivermind-data/r4-population-candidates/medmcqa_population_candidate.json
  bytes               : 3892497
  manifest_fingerprint: 4a4718438d46ab1ba27c59ca46806756ffb62efa05e6103981dffec4dc48c218
  file_sha256         : a3db913227c8b6b32e45d6d6555423fdf6fa34d2b1700bd38fb06515226418f7
  train/test          : 456 / 4162
  role                : PRIMARY
hellaswag (secondary nested robustness):
  path                : /root/rivermind-data/r4-population-candidates/hellaswag_population_robustness912_candidate.json
  bytes               : 16239549
  manifest_fingerprint: 6817496f227d9cd57759bf55489cbf8a1dc4dfd27db0ae551e9223d21d02a096
  file_sha256         : 9920c74071953df24fef760a2878942a17344974bdd341a77e2007f96feb8c4b
  train/test          : 912 / 10042
  role                : SECONDARY SAMPLE-SIZE ROBUSTNESS
medmcqa (secondary nested robustness):
  path                : /root/rivermind-data/r4-population-candidates/medmcqa_population_robustness912_candidate.json
  bytes               : 4308862
  manifest_fingerprint: e48c37293f196e16d8fba42e7fc255e4ac2e77f81c270ed6f71320981968af12
  file_sha256         : f56b09836da06d88f0be0915a9ebbd2bb01de54b2e48cafbeeb5554deab415fc
  train/test          : 912 / 4162
  role                : SECONDARY SAMPLE-SIZE ROBUSTNESS
```

`manifest_fingerprint = fingerprint(payload without its own manifest_fingerprint)`，
使用 `probvenance.fingerprint` 的 canonical JSON 语义。
candidate manifests 位于 repo 之外，**不入库**。

## 8. Determinism

```text
construction 运行两次（四个 manifest：2 primary + 2 robustness-912）：
  byte-identical manifest   : YES（cmp 通过）
  same manifest_fingerprint : YES
  same file_sha256          : YES
=> DETERMINISM = PASS
```

## 9. Scientific guardrails

| guardrail | status |
|---|---|
| model load / forward / generation | NO |
| tokenizer / GPU use | NO |
| study-dataset inference | NO |
| accuracy / Brier / LogLoss | NO |
| calibration fitting (logistic/isotonic/beta) | NO |
| calibration transport | NO |
| predictor outcome | NO |
| selection rule depends on ground truth | NO |
| selection rule depends on model output | NO |
| anchor rule depends on ground truth or content | NO |
| primary 456 resampled / rebalanced | NO |
| anchor-balance optimization | NO |
| secondary 912 used to rescue / override / redefine primary | NO |
| R4 freeze / execution authorization | NO |

## 10. What this is NOT

```text
NOT FINAL POPULATION MANIFEST
NOT TRAIN/TEST FREEZE
NOT R4 FREEZE
NOT R4 EXECUTION AUTHORIZATION
NOT a model selection
NOT a calibration design freeze
```

## 11. Human review questions

```text
Q1  是否接受 source pins 作为 R4 dataset source freeze？
Q2  是否接受 CALIBRATION TRAIN N = 456（与 frozen R3 fitting budget 一致）？
Q3  是否接受 TEST = all eligible labeled validation rows（不 subsample）？
Q4  是否接受 HellaSwag primary stratum = activity_label？
Q5  是否接受 HellaSwag at-most-one-row-per-source_id（TRAIN）？
Q6  是否接受 HellaSwag split_type 仅为 secondary subgroup diagnostic？
Q7  是否接受 MedMCQA duplicate-option structural exclusion？
Q8  是否接受 MedMCQA KEEP ALL choice_type？
Q9  是否接受 anchor protocol v1 作为 PLANNED R4 fixed-event anchor protocol？
Q10 是否接受 TRAIN/TEST overlap guard 为 R3-style（conflict => STOP）？
Q11 是否要求 bootstrap / inference 层额外的 group-aware 规则冻结？
Q12 是否要求为 HellaSwag quota=0 的小 strata 调整 allocation 规则？
Q13 是否接受 PRIMARY TRAIN = 456 保持不变（不接受任何 resample / rebalance）？
Q14 是否接受 HellaSwag quota=0 的 4 个 strata（Home,Categories / Knitting / Spread mulch / Windsurfing）不强制 minimum-one？
Q15 是否接受 14 个 validation-only activity labels 保留在 PRIMARY TEST（target-only semantic support）？
Q16 是否接受 secondary nested robustness TRAIN = 912（= primary 456 + extension 456，nestedness 强制）？
Q17 是否接受 N=912 仅为 secondary robustness、不得 rescue / override / redefine primary N=456 结论？
```

### 11.1 Anchor-balance 决策（NO ANCHOR-BALANCE OPTIMIZATION）

```text
MedMCQA TRAIN anchor==cop ≈ 0.188596
```

该数值是 **selection 完成之后**观察到的 structural diagnostic。

明确决策：

```text
NO ANCHOR-BALANCE OPTIMIZATION
```

即：不得据此 resample、rebalance、更换 hash、更换 anchor protocol 或更换 row selection。
理由：selection 与 anchor 均在**未使用 cop**的前提下冻结；
事后按 anchor 正确性平衡会引入 ground-truth-conditioned selection。

## 12. Reproduction

```bash
cd /root/rivermind-data/Probvenance
PYTHONPATH=/root/rivermind-data/r4-dataset-audit/pylibs \
  /root/rivermind-data/envs/probvenance-r4/bin/python \
  experiments/calibration_transport/r4_population_candidate.py
```

## 13. Artifact hashes

```text
r4_population_candidate.py          lines=1151  sha256=137be2912fc25dfb761352c3b284e31af666781c6425929958abc7ab7c64780f
R4_POPULATION_CONSTRUCTION_CANDIDATE.md  sha256 在最终汇报中给出（自引用不稳定）
```

candidate manifests（repo 外）：

```text
hellaswag_population_candidate.json                    sha256=0724128b9168b15a8796f260441c89025c3a224faf079cf7177b1c2faaec53cc
medmcqa_population_candidate.json                      sha256=a3db913227c8b6b32e45d6d6555423fdf6fa34d2b1700bd38fb06515226418f7
hellaswag_population_robustness912_candidate.json      sha256=9920c74071953df24fef760a2878942a17344974bdd341a77e2007f96feb8c4b
medmcqa_population_robustness912_candidate.json        sha256=f56b09836da06d88f0be0915a9ebbd2bb01de54b2e48cafbeeb5554deab415fc
```

script amendment 前的 entry hash（Gate C 原始版本）：

```text
r4_population_candidate.py  lines=674  sha256=3374555b7fb6b6369e4ebceaf4390e29e9f1f2b31d9a1cb7b315ebd0ad585a27
```
## 14. Nested secondary sample-size-robustness construction（N = 912）

human decision（pre-outcome，见 `R4_DESIGN_DRAFT.md` §20 E7–E10 与
`docs/research/calibration-transport-r3-r4-paper-strategy.md` §AE.7–AE.10）：

```text
role                 : secondary-sample-size-robustness
parent_primary_budget: 456（PRIMARY，保持不变）
train_budget         : 912
nested_primary       : true（TRAIN_456 ⊂ TRAIN_912，exact item-id subset）
robustness TEST      : 与 PRIMARY TEST 完全相同（不另建 robustness TEST）
extension protocol   : r4-nested-residual-extension v1
```

治理：

```text
N=456 remains the sole primary R3-continuity fitting budget.
N=912 cannot rescue, override, or redefine the primary conclusion.
912 仅用于评估 calibration-sample-size sensitivity
（尤其对 isotonic 这类高方差 calibration family）。
禁止在看到 calibration outcome 之后再决定是否报告 912。
```

构造方法（nested residual extension）：

```text
1. primary 456 先冻结（不重算）
2. remaining pool = source TRAIN 中所有未入选的 eligible rows
3. 对 remaining pool 的 strata eligible counts 做 Hamilton / largest-remainder
4. 分配 additional N = 456
5. within stratum 使用与 primary 相同的 deterministic rank doctrine
6. append 到 primary 456
TRAIN_912 = primary_456 + extension_456
```

HellaSwag 的 `source_id` group 约束跨**整个 912**生效（不是只在 extension 内唯一）。

### 14.1 HellaSwag（nested 912）

```text
primary TRAIN          : 456
extension TRAIN        : 456
TRAIN_912              : 912
TEST                   : 10042（与 primary TEST 相同）
parent primary fp      : 5c45043ba4f0ec436c16dcf494ff26be435c7857244bcbefa321d1678129c400
parent primary TRAIN fp: f5dd6072c731d5212435f6a4907321e37eedb29f088f3debed5177f988eee926
nestedness             : {'extension_unique_item_ids': 456, 'nested_primary': True, 'primary_ids_missing_from_train': 0, 'primary_train_count': 456, 'primary_unique_item_ids': 456, 'train_count': 912, 'train_unique_item_ids': 912}
train stratum count    : 175
test  stratum count    : 192
structural exclusions  : {'test_ineligible_rows': 0, 'train_ineligible_rows': 0}
overlap exclusions     : {'extension_rows_excluded_by_test_overlap': 0, 'extension_rows_skipped_for_source_id_reuse': 2}
group                  : {'field': 'source_id', 'note': 'at most one row per source_id across the entire 912', 'test_max_rows_per_source_id': 10, 'test_repeated_source_id': 902, 'test_rows_in_repeated_source_id': 2537, 'test_unique_source_id': 8407, 'train_max_rows_per_source_id': 1, 'train_test_source_id_intersection': 0, 'train_unique_source_id': 912}
anchor train           : {'0': 225, '1': 206, '2': 217, '3': 264}
anchor==GT train       : 0.248904
anchor==GT test        : 0.252241
ground truth train     : {'0': 226, '1': 251, '2': 197, '3': 238}
```

anchor distribution（TRAIN_912，structural diagnostic only）：

| index | TRAIN_912 anchor |
|---|---|
| 0 | 225 |
| 1 | 206 |
| 2 | 217 |
| 3 | 264 |

per-stratum allocation（TRAIN_912）：

| stratum | eligible TRAIN rows | primary selected | eligible remaining | extension quota | extension selected | TRAIN_912 selected | TEST rows |
|---|---|---|---|---|---|---|---|
| Applying sunscreen | 73 | 1 | 72 | 1 | 1 | 2 | 20 |
| Archery | 89 | 1 | 88 | 1 | 1 | 2 | 9 |
| Arm wrestling | 133 | 2 | 131 | 2 | 2 | 4 | 20 |
| Assembling bicycle | 78 | 1 | 77 | 1 | 1 | 2 | 8 |
| BMX | 109 | 1 | 108 | 1 | 1 | 2 | 9 |
| Baking cookies | 184 | 2 | 182 | 2 | 2 | 4 | 33 |
| Ballet | 65 | 1 | 64 | 1 | 1 | 2 | 7 |
| Bathing dog | 57 | 1 | 56 | 1 | 1 | 2 | 11 |
| Baton twirling | 120 | 1 | 119 | 1 | 1 | 2 | 14 |
| Beach soccer | 71 | 1 | 70 | 1 | 1 | 2 | 12 |
| Beer pong | 91 | 1 | 90 | 1 | 1 | 2 | 15 |
| Blow-drying hair | 96 | 1 | 95 | 1 | 1 | 2 | 9 |
| Blowing leaves | 72 | 1 | 71 | 1 | 1 | 2 | 11 |
| Braiding hair | 109 | 1 | 108 | 1 | 1 | 2 | 6 |
| Breakdancing | 92 | 1 | 91 | 1 | 1 | 2 | 2 |
| Brushing teeth | 74 | 1 | 73 | 1 | 1 | 2 | 3 |
| Building sandcastles | 102 | 1 | 101 | 1 | 1 | 2 | 5 |
| Bullfighting | 111 | 1 | 110 | 1 | 1 | 2 | 8 |
| Calf roping | 115 | 1 | 114 | 1 | 1 | 2 | 27 |
| Camel ride | 97 | 1 | 96 | 1 | 1 | 2 | 16 |
| Canoeing | 107 | 1 | 106 | 1 | 1 | 2 | 14 |
| Capoeira | 83 | 1 | 82 | 1 | 1 | 2 | 14 |
| Cars & Other Vehicles | 646 | 7 | 639 | 7 | 7 | 14 | 65 |
| Carving jack-o-lanterns | 89 | 1 | 88 | 1 | 1 | 2 | 18 |
| Cheerleading | 94 | 1 | 93 | 1 | 1 | 2 | 23 |
| Chopping wood | 89 | 1 | 88 | 1 | 1 | 2 | 9 |
| Clean and jerk | 0 | 0 | 0 | 0 | 0 | 0 | 137 |
| Cleaning shoes | 84 | 1 | 83 | 1 | 1 | 2 | 11 |
| Cleaning sink | 69 | 1 | 68 | 1 | 1 | 2 | 8 |
| Cleaning windows | 79 | 1 | 78 | 1 | 1 | 2 | 16 |
| Clipping cat claws | 97 | 1 | 96 | 1 | 1 | 2 | 22 |
| Computers and Electronics | 3715 | 42 | 3673 | 42 | 42 | 84 | 454 |
| Cricket | 91 | 1 | 90 | 1 | 1 | 2 | 5 |
| Croquet | 82 | 1 | 81 | 1 | 1 | 2 | 11 |
| Cutting the grass | 0 | 0 | 0 | 0 | 0 | 0 | 131 |
| Decorating the Christmas tree | 109 | 1 | 108 | 1 | 1 | 2 | 7 |
| Disc dog | 137 | 2 | 135 | 2 | 2 | 4 | 32 |
| Discus throw | 117 | 1 | 116 | 1 | 1 | 2 | 12 |
| Dodgeball | 58 | 1 | 57 | 1 | 1 | 2 | 9 |
| Doing a powerbomb | 87 | 1 | 86 | 1 | 1 | 2 | 12 |
| Doing crunches | 77 | 1 | 76 | 1 | 1 | 2 | 15 |
| Doing fencing | 85 | 1 | 84 | 1 | 1 | 2 | 8 |
| Doing karate | 73 | 1 | 72 | 1 | 1 | 2 | 11 |
| Doing kickboxing | 66 | 1 | 65 | 1 | 1 | 2 | 4 |
| Doing motocross | 83 | 1 | 82 | 1 | 1 | 2 | 7 |
| Drinking beer | 46 | 1 | 45 | 1 | 1 | 2 | 11 |
| Drinking coffee | 87 | 1 | 86 | 1 | 1 | 2 | 5 |
| Drum corps | 73 | 1 | 72 | 1 | 1 | 2 | 8 |
| Education and Communications | 1604 | 18 | 1586 | 18 | 18 | 36 | 201 |
| Elliptical trainer | 75 | 1 | 74 | 1 | 1 | 2 | 15 |
| Family Life | 0 | 0 | 0 | 0 | 0 | 0 | 980 |
| Finance and Business | 2046 | 23 | 2023 | 23 | 23 | 46 | 265 |
| Fixing bicycle | 114 | 1 | 113 | 1 | 1 | 2 | 6 |
| Fixing the roof | 85 | 1 | 84 | 1 | 1 | 2 | 4 |
| Food and Entertaining | 3962 | 45 | 3917 | 45 | 45 | 90 | 500 |
| Fun sliding down | 84 | 1 | 83 | 1 | 1 | 2 | 5 |
| Futsal | 128 | 1 | 127 | 1 | 1 | 2 | 25 |
| Gargling mouthwash | 0 | 0 | 0 | 0 | 0 | 0 | 63 |
| Getting a haircut | 159 | 2 | 157 | 2 | 2 | 4 | 8 |
| Getting a piercing | 105 | 1 | 104 | 1 | 1 | 2 | 18 |
| Getting a tattoo | 104 | 1 | 103 | 1 | 1 | 2 | 2 |
| Grooming dog | 111 | 1 | 110 | 1 | 1 | 2 | 11 |
| Hand car wash | 159 | 2 | 157 | 2 | 2 | 4 | 23 |
| Hand washing clothes | 72 | 1 | 71 | 1 | 1 | 2 | 8 |
| Hanging wallpaper | 116 | 1 | 115 | 1 | 1 | 2 | 11 |
| Having an ice cream | 0 | 0 | 0 | 0 | 0 | 0 | 116 |
| Health | 3415 | 39 | 3376 | 39 | 39 | 78 | 427 |
| High jump | 0 | 0 | 0 | 0 | 0 | 0 | 117 |
| Hitting a pinata | 143 | 2 | 141 | 2 | 2 | 4 | 16 |
| Holidays and Traditions | 258 | 3 | 255 | 3 | 3 | 6 | 38 |
| Home and Garden | 2813 | 32 | 2781 | 32 | 32 | 64 | 390 |
| Home,Categories | 16 | 0 | 16 | 0 | 0 | 0 | 2 |
| Hopscotch | 71 | 1 | 70 | 1 | 1 | 2 | 7 |
| Horseback riding | 82 | 1 | 81 | 1 | 1 | 2 | 12 |
| Hula hoop | 79 | 1 | 78 | 1 | 1 | 2 | 8 |
| Hurling | 106 | 1 | 105 | 1 | 1 | 2 | 8 |
| Ice fishing | 0 | 0 | 0 | 0 | 0 | 0 | 127 |
| Installing carpet | 61 | 1 | 60 | 1 | 1 | 2 | 11 |
| Ironing clothes | 77 | 1 | 76 | 1 | 1 | 2 | 15 |
| Javelin throw | 66 | 1 | 65 | 1 | 1 | 2 | 5 |
| Kayaking | 86 | 1 | 85 | 1 | 1 | 2 | 7 |
| Kite flying | 59 | 1 | 58 | 1 | 1 | 2 | 2 |
| Kneeling | 94 | 1 | 93 | 1 | 1 | 2 | 11 |
| Knitting | 44 | 0 | 44 | 1 | 1 | 1 | 5 |
| Laying tile | 74 | 1 | 73 | 1 | 1 | 2 | 12 |
| Layup drill in basketball | 0 | 0 | 0 | 0 | 0 | 0 | 111 |
| Long jump | 91 | 1 | 90 | 1 | 1 | 2 | 7 |
| Longboarding | 117 | 1 | 116 | 1 | 1 | 2 | 11 |
| Making a cake | 207 | 2 | 205 | 2 | 2 | 4 | 30 |
| Making a lemonade | 145 | 2 | 143 | 2 | 2 | 4 | 32 |
| Making a sandwich | 145 | 2 | 143 | 2 | 2 | 4 | 12 |
| Mixing drinks | 160 | 2 | 158 | 2 | 2 | 4 | 13 |
| Mooping floor | 104 | 1 | 103 | 1 | 1 | 2 | 9 |
| Mowing the lawn | 90 | 1 | 89 | 1 | 1 | 2 | 9 |
| Paintball | 84 | 1 | 83 | 1 | 1 | 2 | 10 |
| Painting | 87 | 1 | 86 | 1 | 1 | 2 | 1 |
| Painting furniture | 65 | 1 | 64 | 1 | 1 | 2 | 19 |
| Personal Care and Style | 0 | 0 | 0 | 0 | 0 | 0 | 2627 |
| Pets and Animals | 1843 | 21 | 1822 | 21 | 21 | 42 | 255 |
| Philosophy and Religion | 228 | 3 | 225 | 3 | 3 | 6 | 24 |
| Ping-pong | 54 | 1 | 53 | 1 | 1 | 2 | 9 |
| Plastering | 73 | 1 | 72 | 1 | 1 | 2 | 7 |
| Plataform diving | 77 | 1 | 76 | 1 | 1 | 2 | 13 |
| Playing accordion | 45 | 1 | 44 | 0 | 0 | 1 | 6 |
| Playing badminton | 63 | 1 | 62 | 1 | 1 | 2 | 15 |
| Playing bagpipes | 64 | 1 | 63 | 1 | 1 | 2 | 10 |
| Playing beach volleyball | 54 | 1 | 53 | 1 | 1 | 2 | 17 |
| Playing blackjack | 55 | 1 | 54 | 1 | 1 | 2 | 6 |
| Playing congas | 115 | 1 | 114 | 1 | 1 | 2 | 8 |
| Playing drums | 108 | 1 | 107 | 1 | 1 | 2 | 15 |
| Playing guitarra | 74 | 1 | 73 | 1 | 1 | 2 | 18 |
| Playing harmonica | 0 | 0 | 0 | 0 | 0 | 0 | 97 |
| Playing ice hockey | 98 | 1 | 97 | 1 | 1 | 2 | 8 |
| Playing kickball | 61 | 1 | 60 | 1 | 1 | 2 | 2 |
| Playing lacrosse | 67 | 1 | 66 | 1 | 1 | 2 | 15 |
| Playing piano | 65 | 1 | 64 | 1 | 1 | 2 | 9 |
| Playing polo | 83 | 1 | 82 | 1 | 1 | 2 | 12 |
| Playing pool | 95 | 1 | 94 | 1 | 1 | 2 | 26 |
| Playing rubik cube | 100 | 1 | 99 | 1 | 1 | 2 | 3 |
| Playing saxophone | 75 | 1 | 74 | 1 | 1 | 2 | 9 |
| Playing squash | 77 | 1 | 76 | 1 | 1 | 2 | 4 |
| Playing violin | 0 | 0 | 0 | 0 | 0 | 0 | 121 |
| Playing water polo | 107 | 1 | 106 | 1 | 1 | 2 | 15 |
| Pole vault | 91 | 1 | 90 | 1 | 1 | 2 | 6 |
| Polishing forniture | 79 | 1 | 78 | 1 | 1 | 2 | 9 |
| Polishing shoes | 69 | 1 | 68 | 1 | 1 | 2 | 14 |
| Powerbocking | 85 | 1 | 84 | 1 | 1 | 2 | 14 |
| Preparing pasta | 164 | 2 | 162 | 2 | 2 | 4 | 12 |
| Preparing salad | 125 | 1 | 124 | 1 | 1 | 2 | 10 |
| Putting in contact lenses | 115 | 1 | 114 | 1 | 1 | 2 | 12 |
| Putting on makeup | 95 | 1 | 94 | 1 | 1 | 2 | 7 |
| Putting on shoes | 90 | 1 | 89 | 1 | 1 | 2 | 2 |
| Raking leaves | 55 | 1 | 54 | 1 | 1 | 2 | 11 |
| Relationships | 1060 | 12 | 1048 | 12 | 12 | 24 | 113 |
| Removing curlers | 96 | 1 | 95 | 1 | 1 | 2 | 9 |
| Removing ice from car | 108 | 1 | 107 | 1 | 1 | 2 | 6 |
| River tubing | 103 | 1 | 102 | 1 | 1 | 2 | 11 |
| Rock climbing | 64 | 1 | 63 | 1 | 1 | 2 | 9 |
| Rock-paper-scissors | 73 | 1 | 72 | 1 | 1 | 2 | 6 |
| Rollerblading | 84 | 1 | 83 | 1 | 1 | 2 | 13 |
| Roof shingle removal | 64 | 1 | 63 | 1 | 1 | 2 | 14 |
| Rope skipping | 122 | 1 | 121 | 1 | 1 | 2 | 21 |
| Running a marathon | 0 | 0 | 0 | 0 | 0 | 0 | 140 |
| Sailing | 83 | 1 | 82 | 1 | 1 | 2 | 4 |
| Scuba diving | 122 | 1 | 121 | 1 | 1 | 2 | 23 |
| Sharpening knives | 0 | 0 | 0 | 0 | 0 | 0 | 138 |
| Shaving | 95 | 1 | 94 | 1 | 1 | 2 | 9 |
| Shaving legs | 91 | 1 | 90 | 1 | 1 | 2 | 5 |
| Shot put | 91 | 1 | 90 | 1 | 1 | 2 | 12 |
| Shoveling snow | 101 | 1 | 100 | 1 | 1 | 2 | 18 |
| Shuffleboard | 57 | 1 | 56 | 1 | 1 | 2 | 13 |
| Skateboarding | 80 | 1 | 79 | 1 | 1 | 2 | 9 |
| Skiing | 109 | 1 | 108 | 1 | 1 | 2 | 17 |
| Slacklining | 123 | 1 | 122 | 1 | 1 | 2 | 12 |
| Smoking a cigarette | 61 | 1 | 60 | 1 | 1 | 2 | 7 |
| Smoking hookah | 60 | 1 | 59 | 1 | 1 | 2 | 10 |
| Snatch | 100 | 1 | 99 | 1 | 1 | 2 | 6 |
| Snow tubing | 109 | 1 | 108 | 1 | 1 | 2 | 18 |
| Spinning | 72 | 1 | 71 | 1 | 1 | 2 | 18 |
| Sports and Fitness | 1242 | 14 | 1228 | 14 | 14 | 28 | 144 |
| Spread mulch | 38 | 0 | 38 | 0 | 0 | 0 | 6 |
| Starting a campfire | 84 | 1 | 83 | 1 | 1 | 2 | 14 |
| Sumo | 110 | 1 | 109 | 1 | 1 | 2 | 3 |
| Surfing | 112 | 1 | 111 | 1 | 1 | 2 | 20 |
| Swimming | 100 | 1 | 99 | 1 | 1 | 2 | 14 |
| Table soccer | 76 | 1 | 75 | 1 | 1 | 2 | 7 |
| Tai chi | 82 | 1 | 81 | 1 | 1 | 2 | 9 |
| Tango | 100 | 1 | 99 | 1 | 1 | 2 | 9 |
| Tennis serve with ball bouncing | 78 | 1 | 77 | 1 | 1 | 2 | 13 |
| Throwing darts | 86 | 1 | 85 | 1 | 1 | 2 | 4 |
| Travel | 344 | 4 | 340 | 4 | 4 | 8 | 60 |
| Trimming branches or hedges | 112 | 1 | 111 | 1 | 1 | 2 | 4 |
| Triple jump | 96 | 1 | 95 | 1 | 1 | 2 | 11 |
| Tumbling | 88 | 1 | 87 | 1 | 1 | 2 | 7 |
| Uncategorized | 51 | 1 | 50 | 1 | 1 | 2 | 7 |
| Using parallel bars | 111 | 1 | 110 | 1 | 1 | 2 | 21 |
| Using the pommel horse | 91 | 1 | 90 | 1 | 1 | 2 | 10 |
| Using the rowing machine | 81 | 1 | 80 | 1 | 1 | 2 | 10 |
| Using uneven bars | 65 | 1 | 64 | 1 | 1 | 2 | 8 |
| Vacuuming floor | 95 | 1 | 94 | 1 | 1 | 2 | 9 |
| Volleyball | 69 | 1 | 68 | 1 | 1 | 2 | 4 |
| Wakeboarding | 106 | 1 | 105 | 1 | 1 | 2 | 13 |
| Walking the dog | 85 | 1 | 84 | 1 | 1 | 2 | 8 |
| Washing face | 0 | 0 | 0 | 0 | 0 | 0 | 136 |
| Washing hands | 122 | 1 | 121 | 1 | 1 | 2 | 5 |
| Waterskiing | 116 | 1 | 115 | 1 | 1 | 2 | 19 |
| Welding | 83 | 1 | 82 | 1 | 1 | 2 | 8 |
| Windsurfing | 41 | 0 | 41 | 0 | 0 | 0 | 7 |
| Work World | 746 | 9 | 737 | 9 | 9 | 18 | 86 |
| Wrapping presents | 149 | 2 | 147 | 2 | 2 | 4 | 17 |
| Youth | 1176 | 13 | 1163 | 13 | 13 | 26 | 161 |
| Zumba | 69 | 1 | 68 | 1 | 1 | 2 | 10 |

### 14.2 MedMCQA（nested 912）

```text
primary TRAIN          : 456
extension TRAIN        : 456
TRAIN_912              : 912
TEST                   : 4162（与 primary TEST 相同）
parent primary fp      : 4a4718438d46ab1ba27c59ca46806756ffb62efa05e6103981dffec4dc48c218
parent primary TRAIN fp: 6fd0787f97daedf2d67f1dff57cd298fb86529db57b206f883902ccd1dbec38f
nestedness             : {'extension_unique_item_ids': 456, 'nested_primary': True, 'primary_ids_missing_from_train': 0, 'primary_train_count': 456, 'primary_unique_item_ids': 456, 'train_count': 912, 'train_unique_item_ids': 912}
train stratum count    : 21
test  stratum count    : 21
structural exclusions  : {'test_rows': {'by_reason': {'duplicate-option-string': 21}, 'duplicate_option_by_choice_type': {'multi': 7, 'single': 14}, 'total': 21}, 'train_rows': {'by_reason': {'duplicate-option-string': 693}, 'duplicate_option_by_choice_type': {'multi': 188, 'single': 505}, 'total': 693}}
overlap exclusions     : {'extension_rows_excluded_by_test_overlap': 0}
choice_type            : {'extension': {'multi': 150, 'single': 306}, 'test': {'multi': 1360, 'single': 2802}, 'train': {'multi': 308, 'single': 604}}
anchor train           : {'0': 210, '1': 213, '2': 250, '3': 239}
anchor==GT train       : 0.214912
anchor==GT test        : 0.250841
ground truth train     : {'0': 275, '1': 253, '2': 213, '3': 171}
```

anchor distribution（TRAIN_912，structural diagnostic only）：

| index | TRAIN_912 anchor |
|---|---|
| 0 | 210 |
| 1 | 213 |
| 2 | 250 |
| 3 | 239 |

per-stratum allocation（TRAIN_912）：

| stratum | eligible TRAIN rows | primary selected | eligible remaining | extension quota | extension selected | TRAIN_912 selected | TEST rows |
|---|---|---|---|---|---|---|---|
| Anaesthesia | 3161 | 8 | 3153 | 8 | 8 | 16 | 34 |
| Anatomy | 14491 | 36 | 14455 | 36 | 36 | 72 | 232 |
| Biochemistry | 8251 | 21 | 8230 | 21 | 21 | 42 | 170 |
| Dental | 8925 | 22 | 8903 | 22 | 22 | 44 | 1312 |
| ENT | 4910 | 12 | 4898 | 12 | 12 | 24 | 52 |
| Forensic Medicine | 5890 | 15 | 5875 | 15 | 15 | 30 | 66 |
| Gynaecology & Obstetrics | 9992 | 25 | 9967 | 25 | 25 | 50 | 224 |
| Medicine | 17822 | 45 | 17777 | 45 | 45 | 90 | 293 |
| Microbiology | 11274 | 28 | 11246 | 28 | 28 | 56 | 122 |
| Ophthalmology | 6914 | 17 | 6897 | 17 | 17 | 34 | 58 |
| Orthopaedics | 2997 | 8 | 2989 | 8 | 8 | 16 | 20 |
| Pathology | 14836 | 37 | 14799 | 37 | 37 | 74 | 333 |
| Pediatrics | 8010 | 20 | 7990 | 20 | 20 | 40 | 233 |
| Pharmacology | 13698 | 34 | 13664 | 34 | 34 | 68 | 243 |
| Physiology | 8753 | 22 | 8731 | 22 | 22 | 44 | 171 |
| Psychiatry | 4416 | 11 | 4405 | 11 | 11 | 22 | 16 |
| Radiology | 4383 | 11 | 4372 | 11 | 11 | 22 | 69 |
| Skin | 1761 | 4 | 1757 | 4 | 4 | 8 | 17 |
| Social & Preventive Medicine | 11835 | 30 | 11805 | 30 | 30 | 60 | 127 |
| Surgery | 16806 | 42 | 16764 | 42 | 42 | 84 | 368 |
| Unknown | 3004 | 8 | 2996 | 8 | 8 | 16 | 2 |

## 15. Primary immutability audit

script amendment 之后重新运行完整 construction，重新确认 primary manifest 身份：

```text
hellaswag primary:
  manifest_fingerprint: 5c45043ba4f0ec436c16dcf494ff26be435c7857244bcbefa321d1678129c400
  file_sha256         : 0724128b9168b15a8796f260441c89025c3a224faf079cf7177b1c2faaec53cc
  train / test        : 456 / 10042
medmcqa primary:
  manifest_fingerprint: 4a4718438d46ab1ba27c59ca46806756ffb62efa05e6103981dffec4dc48c218
  file_sha256         : a3db913227c8b6b32e45d6d6555423fdf6fa34d2b1700bd38fb06515226418f7
  train / test        : 456 / 4162
=> PRIMARY IMMUTABILITY = PASS
```

script 内置 guard：任何以 `_population_candidate.json` 结尾的 primary 输出，
若 `manifest_fingerprint` 与冻结值不一致，立即 raise
`PopulationError("… primary manifest fingerprint drifted …; BLOCKED")`。

nestedness audit（机械检查，script 内置 + 独立复核）：

```text
HellaSwag:
  primary_train_count        : 456
  primary_unique_item_ids    : 456
  primary_ids_missing_from_train: 0
  extension_unique_item_ids  : 456
  train_count                : 912
  train_unique_item_ids      : 912
  nested_primary             : True
MedMCQA:
  primary_train_count        : 456
  primary_unique_item_ids    : 456
  primary_ids_missing_from_train: 0
  extension_unique_item_ids  : 456
  train_count                : 912
  train_unique_item_ids      : 912
  nested_primary             : True
=> NESTEDNESS = PASS
```

determinism（完整 construction 两次，四个 manifest）：

```text
hellaswag_population_candidate.json                    : byte-identical
medmcqa_population_candidate.json                      : byte-identical
hellaswag_population_robustness912_candidate.json      : byte-identical
medmcqa_population_robustness912_candidate.json        : byte-identical
=> DETERMINISM = PASS（same fingerprint, same SHA256）
```

