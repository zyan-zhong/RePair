OFF/OFF Evaluator Targeted Binding Review V1
==========================================

用途
----
只读捕获现有 E1 evaluator 栈、P1/SELECT policy identity/runtime 适配层、
strict-134 schedule 以及服务器上已 materialize 的 runtime/schedule/checkpoint
资产，用于下一步精确绑定 π1 与 π2-human。

本包不：
- 运行 ALFWorld；
- 调用模型；
- 启动 vLLM；
- 提交 Slurm；
- 执行 OFF/OFF benchmark；
- 修改仓库；
- 自动选择 evaluator。

当前已收窄的 canonical stack
---------------------------
core:
src/pchsi/evaluation/episode_evaluator.py

CLI:
scripts/evaluation/run_e1_evaluator.py

result audit:
src/pchsi/evaluation/result_audit.py

schedule:
src/pchsi/evaluation/run_schedule.py

policy binding:
policy_runtime_manifest.py
policy_execution_profile.py
condition_execution_binding.py
condition_run_schedule.py
select_execution_identity.py
select_policy_runtime.py
select_result_audit.py

运行
----
    sha256sum -c PACKAGE_FILES.sha256

    chmod 700 00_VERIFY_AND_CAPTURE.sh

    bash ./00_VERIFY_AND_CAPTURE.sh       2>&1 | tee targeted_offoff_capture.log

输出
----
/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/
OFF_OFF_EVALUATOR_TARGETED_BINDING_REVIEW_V1.zip
