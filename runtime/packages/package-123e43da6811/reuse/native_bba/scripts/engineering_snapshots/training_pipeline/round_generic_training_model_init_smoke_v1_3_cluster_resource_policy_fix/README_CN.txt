Round Generic Training Model-Initialization Smoke V1
====================================================

用途
----
本包只授权一次针对已审核 Generic Training Stage V2.1 fixed head 的
GPU 模型初始化 smoke。

它会：
- 复核 V2.1 Review manifest 的全部文件、大小、SHA 与 freeze root；
- 运行当前 Human-T2 profile 的无模型离线 preflight；
- 在单张 A800 上加载冻结 Qwen base；
- 使用 `is_trainable=True` 加载 Train17 parent adapter；
- 验证初始 trainable-parameter SHA 与 parent final SHA 精确一致；
- 验证只有 LoRA 参数可训练，并验证 target-module boundary；
- 验证没有 gradient、没有参数变化；
- 卸载模型并记录显存；
- 生成 input/output artifact index、STARTED/terminal stage receipt；
- 自动生成 smoke Review Bundle。

它不会：
- 执行 forward；
- 执行 backward；
- 构造 optimizer 或 scheduler；
- 执行 optimizer step；
- 保存新 adapter/checkpoint；
- 授权或执行正式训练；
- 运行 ALFWorld；
- 改写 Human / Strong / F0F1 / Research Planner 结果。

必须解压到
------------
/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/
round_generic_training_model_init_smoke_v1

运行
----
    sha256sum -c PACKAGE_FILES.sha256

    chmod 700 RUN_PREPARE_AND_SUBMIT_SMOKE.sh

    bash ./RUN_PREPARE_AND_SUBMIT_SMOKE.sh       2>&1 | tee submit_driver.log

查看任务
--------
    JOB_ID="$(cat logs/LAST_MODEL_INIT_SMOKE_JOB_ID.txt)"
    squeue -j "$JOB_ID"

    cat "logs/model_init_smoke_${JOB_ID}.out"
    cat "logs/model_init_smoke_${JOB_ID}.err"

成功后生成
----------
/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/
ROUND_GENERIC_TRAINING_MODEL_INIT_SMOKE_REVIEW_V1.zip

成功边界
--------
MODEL_LOAD_COUNT=1
FORWARD_COUNT=0
BACKWARD_COUNT=0
OPTIMIZER_STEP_COUNT=0
TRAINING_EXECUTION_COUNT=0
FORMAL_TRAINING_AUTHORIZED=false


V1.1 path-alias patch
---------------------
This patch changes only package-path identity handling.

- Logical `/data/home/...` and physical `/data/run01/...` aliases are accepted
  only when Bash `-ef` confirms they refer to the same directory identity.
- The expected logical path is canonicalized with `realpath -e`.
- Slurm receives `--chdir=<physical package root>`.
- The batch script derives its package root from `pwd -P`.

The scientific smoke contract, V2.1 fixed head, smoke binding,
smoke authorization, model-load scope, and formal-training authorization
are byte-identical to V1.


V1.2 packaging-hygiene patch
----------------------------
This patch removes transient Python bytecode-cache artifacts from package
identity and distribution:

- `__pycache__/` is forbidden;
- `*.pyc` is forbidden;
- `PACKAGE_FILES.sha256` contains stable source/config/artifact files only;
- package verification checks cache absence before and after tests;
- test/compile verification is configured not to pollute the package tree.

The V1.1 path-alias fix remains active.
The V2.1 fixed head, smoke binding, smoke authorization, model-load scope,
and formal-training authorization are unchanged.


V1.3 cluster-resource-policy patch
----------------------------------
This patch changes only Slurm resource requests for the GPU partition:

- explicit CPU requests are removed;
- explicit memory requests are removed;
- the one-GPU model-load-only smoke time limit is reduced from 30 minutes
  to 10 minutes;
- partition and GPU count remain explicit.

CPU and memory allocation are left to the cluster's GPU-partition policy.

The V1.1 path-alias fix and V1.2 cache-hygiene fix remain active.
The V2.1 fixed head, smoke binding, smoke authorization, model-load scope,
and formal-training authorization are unchanged.
