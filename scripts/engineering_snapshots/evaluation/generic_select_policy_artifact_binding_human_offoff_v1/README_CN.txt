Generic SELECT Policy-Artifact Binding for Human OFF/OFF V1
==========================================================

批准口令：
APPROVE_GENERIC_SELECT_POLICY_ARTIFACT_BINDING_FOR_HUMAN_OFFOFF_V1

本包在新的 detached worktree 中，以 TDD 方式把历史仅支持 pi0/pi1 的
P4 Harness-OFF SELECT identity/runtime 最小泛化为可绑定任意冻结 LoRA
policy artifact 的循环兼容层。

它会：
- 验证 Human Reference 源 worktree exact HEAD 与 tracked-clean；
- 创建 detached worktree，不修改原 Human worktree；
- 先写 RED test 并要求按旧 pi1-only 约束失败；
- 再修改 SELECT runtime/identity/result-audit 与两份 V1 JSON schema；
- 跑 focused GREEN、历史 SELECT regression、整个 tests/evaluation；
- 机械统计冻结 task-access manifest 四类数量；
- 输出 git diff、测试日志、census 和 fixed-head review ZIP。

它不会：
- 调用模型；
- 启动 vLLM；
- 运行 ALFWorld；
- 提交 Slurm；
- 执行 OFF/OFF benchmark；
- commit 或 push；
- 修改原 Human Reference worktree；
- 重新分类 task access。

运行：

  sha256sum -c PACKAGE_FILES.sha256
  chmod 700 00_VERIFY_AND_BUILD.sh
  bash ./00_VERIFY_AND_BUILD.sh 2>&1 | tee generic_select_binding_build.log

成功生成：
/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/
GENERIC_SELECT_POLICY_ARTIFACT_BINDING_HUMAN_OFFOFF_REVIEW_V1.zip
