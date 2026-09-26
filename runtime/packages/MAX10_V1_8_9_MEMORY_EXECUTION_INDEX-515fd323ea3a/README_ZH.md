# 记忆读取清单接线补充包

复用 V1.8.8 已通过的 POST 压缩续接及下一科学轮 PRE 正文接线。当前 POST 已 ACCEPTED / NO_TRAIN，110 个因果分支不重跑。

原 memory_binding.api 从旧 local/strong_local_runtime/execution_manifest.json 读取未完成前缀，导致 accepted local call 不唯一。新 REGISTERED_MEMORY_LOCAL_EXECUTION_INDEX_V1 由实际执行返回值和已登记 manifest 的字节相等校验生成，随后按 exact ref 读取全部唯一调用。原 raw response、same-call boundary、verifier、tokenizer、memory eligibility 和 shadow-event 规则保持原生校验。缺失 episode condition 复用 V1.8.7 的当前 request/profile 解析，不改历史 bundle。

VERIFY.py 运行 3 个回归；--server 运行完整 11 状态原生记忆生产器，输出隔离验证目录，不发送模型请求、不提交作业、不写本轮 active memory。RUN.sh 验证后单次登记并接续原 resident。已运行的启动不得重复。

Git 仅生成 staging 文件，不 add/commit/push。运行 shell 不启用 -e/-u/pipefail；外部 tee 后须立即读取 PIPESTATUS[0]。环境与资产位置由已登记 authority 获取。

V1.8.8 封存 README 的“7个”是测试数量文字旧值；最终日志实际为 8 个全部通过。本补充包不修改前驱包字节。
