Human T2 Training Result Audit + OFF/OFF Reuse Census V1
========================================================

用途
----
本包在服务器上完成两件只读工作：

1. 对 recovered formal-training Review ZIP 做完整审计；
2. 扫描现有仓库 / Human Reference worktree 中可复用的 OFF/OFF
   evaluator / policy-runtime / schedule 资产。

它不会：
- 调用模型；
- 启动 ALFWorld；
- 提交 Slurm；
- 执行 OFF/OFF evaluation；
- 修改 candidate adapter；
- 创建 promotion decision。

输入
----
- ROUND_HUMAN_T2_FORMAL_TRAINING_REVIEW_V1_RECOVERED.zip
- 当前训练 output / stage attempt
- 当前仓库和 Human Reference worktree

关键固定身份
------------
parent adapter:
b296f2254b1fa1f2e141dffd3f6b5af903f839df4790ffcb245fd8dd57773ace

candidate adapter:
908acf081e80008800284653c3340c397353eef0de08ee044f06810cab2a251e

输出
----
HUMAN_T2_FORMAL_TRAINING_RESULT_AUDIT_V1.json
POLICY_ARTIFACT_NODE_CANDIDATE_V1.json
OFF_OFF_EVALUATOR_REUSE_CENSUS_V1.json
OFF_OFF_EVALUATION_HANDOFF_DRAFT_V1.json
REVIEW_MANIFEST_V1.json

以及：
HUMAN_T2_TRAINING_RESULT_AUDIT_OFFOFF_REUSE_CENSUS_V1.zip

运行
----
    sha256sum -c PACKAGE_FILES.sha256

    chmod 700 00_VERIFY_AND_RUN.sh

    bash ./00_VERIFY_AND_RUN.sh       2>&1 | tee audit_offoff_reuse.log

成功终态
--------
HUMAN_T2_FORMAL_TRAINING_RESULT_AUDIT_PASS
EVALUATION_EXECUTION_AUTHORIZED=false
EVALUATION_EXECUTION_COUNT=0
NEXT_GATE=OFF_OFF_EVALUATOR_REUSE_BINDING_REVIEW
