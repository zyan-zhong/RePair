Human T2 Pretraining Handoff + Authorization Review V1
======================================================

用途
----
本包在 Model-Initialization Smoke PASS 之后，完成正式训练前的最后一层
离线 lineage closure：

1. 验证 Slurm job 151486 为 COMPLETED / 0:0；
2. 验证 Smoke Review Bundle 的精确 SHA、成员、receipt chain 和 result；
3. 复核 Generic Training Stage V2.1 fixed head；
4. 复核 F0/F1 authority、POST adjudicated evidence、Research Planner plan、
   T2 trainer-native dataset 和 parent Train17 identity；
5. 生成 ROUND_PRETRAINING_HANDOFF_RECEIPT_V1；
6. 生成 NOT_AUTHORIZED 的 formal-training authorization candidate；
7. 导出 review bundle，供下一关审核。

边界
----
本包不：
- 提交 Slurm；
- 加载模型；
- 执行 forward/backward；
- 构造 optimizer；
- 执行训练；
- 运行 ALFWorld；
- 授权正式训练；
- 将 T2 变成可 promotion 的 verified-positive arm。

服务器运行
----------
解压到任意仓库外目录即可。

    sha256sum -c PACKAGE_FILES.sha256

    chmod 700 00_VERIFY_AND_BUILD_REVIEW.sh

    bash ./00_VERIFY_AND_BUILD_REVIEW.sh       2>&1 | tee build_handoff_review.log

成功输出
--------
    PRETRAINING_HANDOFF_AUTHORIZATION_REVIEW_READY
    AUTHORIZATION_STATUS=NOT_AUTHORIZED
    FORMAL_TRAINING_AUTHORIZED=false
    TRAINING_EXECUTION_COUNT=0

会生成
------
/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/
ROUND_HUMAN_T2_PRETRAINING_HANDOFF_AUTHORIZATION_REVIEW_V1.zip
