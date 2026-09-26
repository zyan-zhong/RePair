Human Pilot Stage 0 OFF/OFF Execution and Closeout V1.9
=======================================================

V1.9 post-publication reload fix
--------------------------------
Job 152173 证明 V1.8 的 attempt-ordinal recovery 已生效：

candidate a000.started        preserved
candidate a001.started        created
candidate a001.terminal       created
candidate scientific cell lock created

随后 Stage0 wrapper 在 post-publication reload audit 中触发：

UnboundLocalError: attempt_dir

根因：V1.8 只在“恢复已有 published attempt”分支设置 attempt_dir；
新 attempt 分支在 a001 执行完成后直接引用 attempt_dir，却没有先绑定
evaluator_root / attempts / attempt_id。

V1.9 只做一个控制流修复：
- 新 attempt id 确定后，立即绑定 attempt_dir；
- run_single_episode 返回 PUBLISHED 后，从该 exact attempt_dir 重新加载并
  核验 attempt bundle；
- 已 publish 的 candidate a001 若缺 Stage0 cell receipt，则下一次 resume
  直接 reload a001 并补 receipt，不重跑 a001；
- V1.8 的 a000 orphan、V1.7 Generic SELECT artifact patch、
  V1.8 attempt-ordinal recovery 全部保留。

V1.9 使用新的 preflight_v1_9 / authorization_v1_9 receipts。

不改变：
17 SELECT tasks × 5 seeds、85 matched pairs、170 cells、parent/candidate、
Memory OFF、Harness OFF、evaluator scientific semantics、training、
promotion 与 paper-efficacy boundary。

目标
----
用一个交付包完成当前受污染 Human pilot 的阶段 0 收尾：

1. 审核 Generic SELECT fixed head 与 Twin OFF/OFF binding；
2. 启动一个共享 vLLM server，静态注册 π1 parent 与 π2-human candidate；
3. 在 17 个 SELECT_SUMMARY_ONLY 任务、5 个冻结评测 seed 上执行：
   - parent 85 cells；
   - candidate 85 cells；
   - 共 170 condition cells；
4. 复用现有 run_single_episode、ALFWorld adapter、Runtime Core、PolicyClient、ArtifactPublisher；
5. 做 paired result audit；
6. 将本轮封为 PILOT_ENGINEERING_ROUND_V1；
7. 输出阶段 1 自动化工作流 handoff。

科学边界
--------
- 本轮结果不进入论文 efficacy 结论；
- candidate 不具备 promotion 资格；
- 不 commit、不 push、不修改 main；
- 不执行 full valid_unseen 134；
- 不重写第二套 evaluator；
- 117 个 valid_unseen 任务已 development-exposed；本轮 17-task 结果仅作内部工程诊断。

运行
----

上传 ZIP 到：

/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts

解压后：

sha256sum -c PACKAGE_FILES.sha256

export HUMAN_PILOT_STAGE0_EXECUTION_APPROVAL="APPROVE_HUMAN_PILOT_STAGE0_OFFOFF_V1"

bash ./RUN_PREFLIGHT_AND_SUBMIT.sh   2>&1 | tee submit_stage0.log

任务可恢复
----------
Runner 对每个 cell 使用不可变 attempt bundle 和 append-only receipt。

两小时 Slurm job 会在约 100 分钟处、且只在一个 parent/candidate matched pair 完整结束后，主动输出：

STAGE0_GRACEFUL_PARTIAL_COMPLETE
RESUBMIT_SAME_PACKAGE=true

确认旧 job 已终止后，重新运行同一个提交命令即可；已完成 cell 会先重新审核，再跳过，不会重新执行。

这个保证只覆盖计划内的 pair-boundary 停止。节点故障、强制杀死或单个 cell 执行中崩溃时，必须先审核 attempt ledger、staging 和 cell lock，不能直接假定该 cell 可安全重跑。

成功产物
--------
/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/
HUMAN_PILOT_STAGE0_OFFOFF_CLOSEOUT_REVIEW_V1.zip

下一关
------
GENERIC_ROUND_ORCHESTRATOR_AND_ROLE_HANDOFF_AUTOMATION
