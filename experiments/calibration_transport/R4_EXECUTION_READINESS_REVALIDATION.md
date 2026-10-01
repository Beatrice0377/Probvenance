# R4 Execution Readiness Revalidation

本文件记录 R4 execution readiness 从 `BLOCKED` 变为 `PASS` 的**机械证据**。

```text
status = PASS
date   = 2026-10-01
```

它 **不** 改变任何 frozen scientific artifact；只记录 operational 层面的
revalidation 结果。

---

## 1. Clone-instance revalidation

见 `R4_CLONE_INSTANCE_AUDIT.md`。摘要：

```text
Git        branch=main
           HEAD == origin/main == 55a396a9e0339f29becb8fae2821d2bf8031a54a
           HEAD^ == aaea894803d5b2981998554a04316033a1f867a8
           raw behind/ahead = 0/0；normalized ahead/behind = 0/0
           worktree clean

Filesystem 所有 frozen path 存在且可写
            /root/rivermind-data 246G total / 67G used / 179G avail

Runtime    Python 3.11.13；torch 2.8.0+cu128；transformers 5.17.0
           huggingface_hub 1.32.0；scipy 1.16.3；numpy 2.3.2

GPU        1 × NVIDIA GeForce RTX 4090；driver 580.119.02
           49140 MiB total；0 MiB used；no running processes

Frozen     9 个 frozen artifact 全部 byte-identical
authority  5 个 fingerprint 全部 recompute 一致
```

---

## 2. Legacy cache acquisition

human 决定：

```text
KEEP legacy secondary cells
DO NOT revise frozen plan
COMPLETE exact pinned caches instead
```

`hf-mirror` 实测限速（0.67–2.0 MB/s）；改用 `ai.gitcode.com` 的
exact-revision 路径（实测 6.9–16.7 MB/s）。**只换传输通道，不换 revision。**

| repo | file | size | sha256 | vs tree `lfs_sha256` |
|---|---|---|---|---|
| `openbmb/MiniCPM5-2B` | `model-00000-of-00001.safetensors` | 5,033,557,096 | `14fb8e7f0a18d53d1f239773758bf581cee7e456a4523a54622c3a245b64402c` | MATCH |
| `Qwen/Qwen3.5-2B` | `model.safetensors-00001-of-00001.safetensors` | 4,548,221,488 | `aa33250c4fc64891ddfaba3a314fd9542ea371843c387178b425fbcc5ed680b1` | MATCH |

blob 落盘后建立 snapshot symlink；`find … -name "*.incomplete"` = 空。

---

## 3. Offline local-only resolution

条件：`HF_HUB_OFFLINE=1`、`TRANSFORMERS_OFFLINE=1`、
`HF_DATASETS_OFFLINE=1`、`local_files_only=True`、
`trust_remote_code=False`。

| model | revision | config class | model_type | `_commit_hash` |
|---|---|---|---|---|
| `allenai/Olmo-3-7B-Instruct` | `6e5971d9eba42665f5bd5a0fcf047f299ce1dccc` | `Olmo3Config` | `olmo3` | `6e5971d9…` MATCH |
| `tiiuae/Falcon-H1-7B-Instruct` | `41e72f27effbab80cd45b6e884688452253a3686` | `FalconH1Config` | `falcon_h1` | `41e72f27…` MATCH |
| `ibm-granite/granite-4.0-h-tiny` | `791e0d3d28c86e106c9b6e0b4cecdee0375b6124` | `GraniteMoeHybridConfig` | `granitemoehybrid` | `791e0d3d…` MATCH |
| `Qwen/Qwen3.5-9B` | `c202236235762e1c871ad0ccb60c8ee5ba337b9a` | `Qwen3_5Config` | `qwen3_5` | `c2022362…` MATCH |
| `openbmb/MiniCPM5-2B` | `12a3808a956f869c767195e9266b59c4d21d92e2` | `LlamaConfig` | `llama` | `12a3808a…` MATCH |
| `Qwen/Qwen3.5-2B` | `15852e8c16360a2fea060d615a32b45270f8a8fc` | `Qwen3_5Config` | `qwen3_5` | `15852e8c…` MATCH |

6/6 `auto_map = None` —— 没有任何一个需要 `trust_remote_code=True`。

---

## 4. Six-model synthetic preflight

命令：

```bash
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1 \
python experiments/calibration_transport/run_r4_measurements.py \
  --synthetic-preflight --device cuda:0
```

只用 invented synthetic item；**没有** 触碰任何 study row。exit code 0。

| model_key | model_class | tokenizer_class | CAT token ids | yes/no ids | forwards | status |
|---|---|---|---|---|---|---|
| `olmo-3-7b-instruct` | `Olmo3ForCausalLM` | `TokenizersBackend` | 32/33/34/35 | 9891/2201 | 2 | PASS |
| `falcon-h1-7b-instruct` | `FalconH1ForCausalLM` | `TokenizersBackend` | 1068/1069/1070/1071 | 5763/3257 | 2 | PASS |
| `granite-4-0-h-tiny` | `GraniteMoeHybridForCausalLM` | `TokenizersBackend` | 32/33/34/35 | 9891/2201 | 2 | PASS |
| `qwen3-5-9b` | `Qwen3_5ForCausalLM` | `Qwen2Tokenizer` | 32/33/34/35 | 9405/2083 | 2 | PASS |
| `minicpm5-2b` | `LlamaForCausalLM` | `TokenizersBackend` | 54/55/56/57 | 15876/3707 | 2 | PASS |
| `qwen3-5-2b` | `Qwen3_5ForCausalLM` | `Qwen2Tokenizer` | 32/33/34/35 | 9405/2083 | 2 | PASS |

```text
6 / 6 PASS
```

每个模型的 `cat_token_ids` 与 `positive/negative_token_id` 都与 frozen
6-model registry 中声明的 expected 值精确一致；dtype 全部 `bfloat16`。

resolved snapshot 全部落在 pinned revision 目录下：

```text
…/models--allenai--Olmo-3-7B-Instruct/snapshots/6e5971d9eba42665f5bd5a0fcf047f299ce1dccc
…/models--tiiuae--Falcon-H1-7B-Instruct/snapshots/41e72f27effbab80cd45b6e884688452253a3686
…/models--ibm-granite--granite-4.0-h-tiny/snapshots/791e0d3d28c86e106c9b6e0b4cecdee0375b6124
…/models--Qwen--Qwen3.5-9B/snapshots/c202236235762e1c871ad0ccb60c8ee5ba337b9a
…/models--openbmb--MiniCPM5-2B/snapshots/12a3808a956f869c767195e9266b59c4d21d92e2
…/models--Qwen--Qwen3.5-2B/snapshots/15852e8c16360a2fea060d615a32b45270f8a8fc
```

---

## 5. Resume hardening verification

```text
tests/test_r4_measurements.py            87 passed（run twice，identical）
tests/test_r4_predictor.py               PASS
tests/test_r4_inference.py               PASS
tests/test_r4_calibration_families.py    PASS
full repo pytest -p no:randomly          2245 passed, 4 skipped
ruff check                               All checks passed
py_compile                               OK
git diff --check                         exit 0
```

16 个 crash-injection tests 覆盖：resume-after-committed-rows、mid-row
recovery replay、no partial CAT/OVR merge、terminal failure never retried、
finalize-after-crash with zero new forwards、duplicate committed row fail、
identity mismatch fail、single-writer lock、atomic finalization、resume
determinism。

---

## 6. Outcome firewall

```text
real study logits / probabilities            NOT accessed
real CAT/OVR evidence                        NOT produced
calibration fits / Brier / LogLoss           NOT produced
Delta_native / Delta_deploy / Delta_transport NOT produced
predictor values / correlations              NOT produced
official results                             NOT produced
```

唯一执行的 model forward 是 synthetic preflight 的 12 次
（6 models × 2 forwards），全部使用 invented synthetic item。

---

## 7. Conclusion

```text
R4 CLONE-INSTANCE REVALIDATION = PASS
R4 LEGACY MODEL CACHE = COMPLETE
R4 SIX-MODEL SYNTHETIC PREFLIGHT = 6/6 PASS
R4 MEASUREMENT CRASH-SAFE RESUME HARDENING = PASS

R4 EXECUTION READINESS = PASS

FORMAL R4 EXECUTION = NOT YET AUTHORIZED
```

`NOT YET AUTHORIZED` 的原因是流程性的：本轮 commit 尚待 human / ChatGPT
review，尚待 push 到 remote，尚待 remote SHA 核对，尚待 explicit
execution authorization。
