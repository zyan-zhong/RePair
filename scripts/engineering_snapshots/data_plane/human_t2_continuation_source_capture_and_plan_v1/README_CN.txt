Human T2 Continuation Source Capture V1
=======================================

用途
----
优先推进当前人工参考轮，但不猜测、不重新实现历史 Trainer。

本包只读捕获并审计以下现有资产：
- frozen Train17 formal_train.py 与训练配置；
- Train17 adapter identity 与 manifests（不复制权重文件）；
- 当前 T2 trainer-native dataset / preflight / review；
- Human PRE/POST、Strong PRE/POST、F0/F1、Research Planner plan 的现有引用；
- 当前代码符号、常量和训练入口。

输出：
- HUMAN_T2_CONTINUATION_SOURCE_REVIEW_BUNDLE_V1.zip
- SOURCE_CAPTURE_MANIFEST_V1.json
- FORMAL_TRAIN_SYMBOL_CENSUS_V1.json
- CURRENT_T2_CONTRACT_SUMMARY_V1.json
- PARENT_TRAIN17_IDENTITY_V1.json
- HUMAN_T2_EXISTING_HANDOFF_CANDIDATES_V1.json

边界
----
- 不修改 Git 仓库；
- 不调用模型；
- 不运行 ALFWorld；
- 不提交 Slurm；
- 不训练；
- 不复制 adapter_model.safetensors，只记录其 SHA/size；
- 不创建新 Training/Artifact Registry schema。

运行
----
把本包放在科学 package 目录之外：

    sha256sum -c SHA256SUMS.txt
    chmod 700 RUN_HUMAN_T2_SOURCE_CAPTURE_V1.sh
    bash ./RUN_HUMAN_T2_SOURCE_CAPTURE_V1.sh 2>&1 | tee source_capture_driver.log

完成后上传脚本输出的 HUMAN_T2_CONTINUATION_SOURCE_REVIEW_BUNDLE_V1.zip。
