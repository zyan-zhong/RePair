Human T2 Formal Training Execution V1
===================================

用途
----
本包只负责把已经通过的 pretraining handoff candidate 转成独立的正式
execution authorization，然后调用已经审核冻结的 Generic Training Stage
V2.1。

它不重写 Trainer、不修改训练合同、不运行 ALFWorld、不做 benchmark、
不做 promotion。

科学训练合同
------------
- parent: PILOT_DISTILLED_PI1 / Train17 adapter
- data: 12 T2 diagnostic rows
- 1 epoch
- 3 optimizer steps
- 151 target-loss tokens
- seed/data seed = 17
- fresh optimizer / fresh scheduler
- warmup = 0
- diagnostic_only = true
- promotion_eligible = false
- final checkpoint only

显式执行批准
------------
构建包本身不预先授权训练。提交前必须由用户显式设置：

    export HUMAN_T2_FORMAL_TRAINING_EXECUTION_APPROVAL=APPROVE_HUMAN_T2_FORMAL_TRAINING_V1

随后运行提交器。

Slurm 规则
----------
- partition: gpu_a800
- gpus: 1
- 不显式申请 CPU
- 不显式申请内存
- time: 00:10:00
- sbatch --export=NIL
- sbatch --chdir=<physical package root>

成功训练后
----------
会自动生成：

/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/
ROUND_HUMAN_T2_FORMAL_TRAINING_REVIEW_V1.zip

该 Review Bundle 只证明 T2 diagnostic training 是否按冻结合同执行成功；
它不证明 π2 比 π1 更强，也不允许自动 promotion。


V1.1 offline-preflight environment fix
--------------------------------------
The formal scientific contract is unchanged.

The submitter now runs the no-model offline preflight in a child process using
GNU `env -u` to remove only the seven stale output-routing variables forbidden
by the reviewed Generic Training Stage V2.1 contract.

The caller's interactive shell is not modified. The preflight itself remains
fail-closed and will still reject those variables if called directly from a
contaminated environment.

Existing exact approved authorization artifacts are reused; no new scientific
attempt identity is created.


V1.2 V2.1 preflight-summary binding fix
---------------------------------------
Generic Training Stage V2.1 intentionally reports
`direct_input_artifact_count=8` after the direct-input provenance hardening.

The Human-T2 wrapper previously compared that V2.1 result against an older
summary shape that omitted the field, causing a false fail-closed mismatch.

V1.2 requires the exact current value `direct_input_artifact_count=8`.

No scientific training contract, authorization, dataset, parent policy,
optimizer budget, Trainer runtime, Slurm resource policy, or attempt identity
is changed.
