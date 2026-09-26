Round Data Plane Reuse Census + Strong Trace V1
=================================================

用途
----
与当前 Human T2 工作并行，做完全只读的历史资产复用普查。

重点回答：
1. Evidence / Memory / Analyzer / Research Planner / F0F1 / Training /
   Evaluation / Policy-lineage 已经有哪些正式实现？
2. Round Artifact Registry、Stage Receipt、training request/receipt、
   accounting、closeout 等是否已经存在？
3. Strong Analyzer 与 Strong Research Planner 每轮的 raw request、
   raw response、validated output、adjudication、environment alignment、
   training-result alignment 是否已经保存？
4. 后续本地化蒸馏真正缺的是 schema、adapter、index，还是完全缺失？
5. 哪些拟议模块存在重复造轮子的风险？

输出
----
- ROUND_DATA_PLANE_REUSE_CENSUS_STRONG_TRACE_REPORT_BUNDLE_V1.zip
- REPOSITORY_REF_INDEX_V1.json
- EXISTING_ASSET_INDEX_V1.json
- SEMANTIC_ROLE_TO_ARTIFACT_MAP_V1.json
- STRONG_ROLE_TRACE_CANDIDATE_INDEX_V1.json
- REUSE_GAP_MATRIX_V1.json
- DUPLICATE_IMPLEMENTATION_RISK_REPORT_V1.json
- CENSUS_SUMMARY_V1.md

保守语义
--------
本包只标记：
- CANDIDATE_FOUND_CURRENT_HEAD
- CANDIDATE_FOUND_HISTORY_ONLY
- CANDIDATE_FOUND_FILESYSTEM
- NOT_FOUND
- REVIEW_REQUIRED

它不会自动宣布 REUSE_DIRECT，也不会创建新 schema。

运行
----
    sha256sum -c SHA256SUMS.txt
    chmod 700 RUN_READ_ONLY_CENSUS_V1.sh
    bash ./RUN_READ_ONLY_CENSUS_V1.sh 2>&1 | tee census_driver.log

完成后上传输出 ZIP。
