# R4 Final Integrated Protocol Freeze

```text
status                      = FROZEN
formal_execution_authorized = false
```

本文件冻结 R4 final integrated protocol 与 execution manifest 的 **candidate**
payload，使 scientific execution contract 完整且不可静默漂移。

它 **不** 授权正式执行。

---

## 1. Freeze artifacts

| artifact | path | sha256 |
|---|---|---|
| protocol freeze | `experiments/calibration_transport/R4_FINAL_PROTOCOL_FREEZE.json` | `8d105b2010227b0b6467f3384ca471e536f2ae877ba351546bf4088f501d0fb6` |
| manifest freeze | `experiments/calibration_transport/R4_EXECUTION_MANIFEST_FREEZE.json` | `8b56f62bfe053ddbc92518f92f7aac9da9f6b02af342699eb4db0ee12e61721d` |

```text
final_protocol_fingerprint     = d1b56d702e1f260cef47eee05b7d878ace07a15168e89408e15e7eb741c0ad34
execution_manifest_fingerprint = f32381c51db24f5dbeb240b5e0fdf73c59a56a615c8607ad8979e2a7e2586775
fingerprint_version            = 1
```

两个 fingerprint 在两次独立生成中一致。

---

## 2. Frozen source payload

freeze 直接嵌入 amendment 之后的 candidate payload：

```text
R4_FINAL_PROTOCOL_FREEZE.json   -> freeze["protocol"]  == R4_FINAL_PROTOCOL_SEMANTIC_CANDIDATE.json
R4_EXECUTION_MANIFEST_FREEZE.json -> freeze["manifest"] == R4_EXECUTION_MANIFEST_CANDIDATE.json
```

semantic equivalence audit：

```text
protocol payload identical: True
manifest payload identical: True
```

允许新增的只有 freeze identity / provenance / awaiting-human-review state；没有任何
其它 drift。若出现 drift：

```text
STOP / FINAL_FREEZE_SEMANTIC_DRIFT
```

---

## 3. No fingerprint cycle

```text
manifest freeze  -> references the protocol freeze by PATH only
protocol freeze  -> embeds the amended candidate (which embeds the amended
                    manifest fingerprint 2195d283b7666a37593a312f4f6abbf8b7d2bd3a4b88737c151255981057f724)
manifest         -> embeds NO candidate fingerprint
```

因此不存在 fingerprint cycle。

---

## 4. Measurement execution contract（本 freeze 内含）

```text
measurement_call_contract_id   = r4-fixed-event-two-forward-measurement
measurement_contract_status    = FROZEN
measurement_contract_fingerprint = 7b126d300e774cb44d2c47fcb12513865d03c2b08ffd03a5ce409b2ea976e1e5

calls_per_item:
  cat_forwards_per_item  = 1
  ovr_forwards_per_item  = 1
  ovr_scope              = designated-candidate-only
  total_forwards_per_item = 2

r3_call_contract_inheritance = REJECTED

required_unique_model_item_rows = 100728
required_cat_forwards           = 100728
required_ovr_forwards           = 100728
required_total_forwards         = 201456
```

candidate / manifest 中已不再存在：

```text
r4_call_count_freeze_status = NOT_YET_MECHANICALLY_DERIVABLE
inherited 5-call-per-item cells
previous totals 104376 / 521880
```

---

## 5. Amended candidate identities

```text
candidate_fingerprint
  old = 179d052318b9eb080261d6ffaf922d95c62c1f73f1b38f32e4e410afae7a2186
  new = f3a96b7c2847060b1b5422dae800d0871e5bdf6aa9b83ba88cb102c83e44a0b6

manifest_fingerprint
  old = 65db650429dfe0dd6ec0439a3140a9db99cf93aab7eb744d37f7a2b53e8373c1
  new = 2195d283b7666a37593a312f4f6abbf8b7d2bd3a4b88737c151255981057f724

change reason = measurement execution contract closure only
```

candidate JSON `d9aea47de816f4513a624dd9a4a2c9467a7f8278d334be5629fd97925135d735`；
candidate MD `29dfdf5a706568413bdfe25b5412581a5ee16c94157558230674dc37f463672b`；
manifest JSON `8c60f12d9022221db89f5b5266030459ea917440e004952c64aef845f3f30761`。

---

## 6. Status

```text
R4 FINAL INTEGRATED PROTOCOL = FROZEN
R4 EXECUTION MANIFEST         = FROZEN
FORMAL R4 EXECUTION           = NOT AUTHORIZED
```

正式执行授权必须由 human / ChatGPT 在本任务结束后单独给出。

本文件不得被读作 execution authorization。
