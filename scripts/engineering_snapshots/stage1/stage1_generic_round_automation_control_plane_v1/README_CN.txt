Stage 1 Generic Round Automation Control Plane V1
=================================================

作用
----
这个大包在当前 Stage 0 已完成的 detached Generic SELECT worktree 上，
只新增一层 round_control 控制平面，不重写 Analyzer、Memory、Research
Planner、F0/F1、Trainer 或 evaluator。

本包一次完成：
1. Stage 0 closeout / handoff / Generic SELECT patch 权威复核；
2. round lifecycle；
3. Human → Strong → Local authority switch；
4. ALFWorld train-only clean data gate；
5. Strong / Local structured trace handoff；
6. benchmark result sealing；
7. cross-round retention policy；
8. TRAIN_SELECT-only promotion / rollback provenance；
9. existing component reuse binding；
10. 兼容现有 takeover / reference-round / distillation / benchmark API 的
    synthetic control-plane dry run；
11. Review ZIP。

不执行
------
- 模型调用；
- ALFWorld；
- F0/F1 环境实验；
- 训练；
- benchmark；
- git commit；
- git push。

Stage 0 结果只作为 engineering provenance，不进入论文 efficacy claim。

服务器运行
----------
将 ZIP 上传到：

/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts

解压后：

export STAGE1_CONTROL_PLANE_BUILD_APPROVAL="APPROVE_STAGE1_GENERIC_ROUND_CONTROL_PLANE_V1"

bash ./RUN_STAGE1_CONTROL_PLANE_BUILD.sh 2>&1 | tee stage1_control_plane_build.log

成功标志
--------
STAGE1_PRECONDITION_PASS
STAGE1_CONTROL_PLANE_BUILD_PASS
STAGE1_GENERIC_ROUND_CONTROL_PLANE_REVIEW_READY

最终 Review：
/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/
STAGE1_GENERIC_ROUND_AUTOMATION_CONTROL_PLANE_REVIEW_V1.zip

下一关
------
STAGE1_CONCRETE_COMPONENT_RUNNER_BINDING_AND_HUMAN_STRONG_LOCAL_DRY_RUN

说明
----
当前包不会把 valid_seen / valid_unseen 接到任何 adaptive component。
clean-data gate 明确要求未来 Analyzer、Memory、Research Planner、F0/F1、
policy training 和 localization supervision 只消费 ALFWorld train-side authority。
