# Stage4E：原生 hash 合同接线修复及审计续接

## 当前范围

仅用于当前实验已经归并出 `STAGE4D_FULL_SELECT_EXECUTION_COMPLETE_V1.json`、T0/T2 各 1775 的现场。用户报告的 156934 四分片已完成。当前异常发生在后续审计而非推理或归并。

不重新运行 SELECT、训练、F0/F1、readiness、归并或排队跟随；不重建 binding；不修改已有 package 或 native validator；不触碰 Stage5D `a0b58f5291d9879c9903f28f795b1c2024c38e18`。不得并行启动其他 Stage4E 跟随入口。

## 原因

Stage4D 的 `stage4d_pkg.common.canonical_json_bytes` 返回无 LF 的 compact JSON。
`BINDING_IDENTITY.json.artifacts` 使用这种摘要。

原仓库 `pchsi.evaluation.canonical_evidence.canonical_json_bytes` 返回同一 JSON 加一个 LF。
`canonical_model_sha256`、执行时 schedule/runtime 身份以及原 SELECT auditor 使用后者。

旧 Stage4E `audit.py` 有两处误用：

- 将 binding entry hash 用作 `authorized_schedule_sha256`；
- 将 binding entry hash 用作 `authorized_policy_runtime_sha256`。

两种合同都保留，不通过比较失败后“接受另一种 hash”的 fallback，不把 observed hash 写回 authority。

## 实现

1. 复用已执行的 SINGLE_OWNER 续接包的精确依赖加载器，检查原包清单。
2. 复用原 `driver.prepare/base_gate`：冻结输入、原文件清单、原授权、code authority、readiness 和科学网格继续核验。
3. 核验 completion、`SINGLE_OWNER_CONTINUATION.json` 和原 `ARRAY_CONSOLIDATION_RECEIPT.json`，包括归并时固定的 canonical ledger 文件 SHA。
4. 先确认整个 binding identity 摘要与固定 `4ab794...` 一致，再确认 typed model 的无-LF payload hash 等于该 binding 中登记的 artifact hash。
5. 只有上述条件通过才调用原 `canonical_model_sha256(model)`，产生同一对象的原生身份，传给原 native audit。
6. 原 `audit.py` 在 SHA-pinned 的内存模块中只替换这两个调用点；原 driver 只替换审计子进程的入口。原生 evaluator、audit、attempt loader、统计和处置代码不更改。
7. 保持原 driver lock；审计的执行锁仍由原 audit 以共享方式取得。不删除锁文件、不重入归并。
8. 新源码、测试与桥接记录使用原归档/commit 工具追加到原 integration clone；随后使用原 finalizer 完成审计与受控原子发布。历史快照不覆盖。

## 运行

将本包解压到原 `pchsi_scripts`，在 tmux 中：

```bash
bash ./RUN_CONTINUE.sh
```

可选的 `bash ./RUN_CONTINUE.sh --check-only` 仅核验元数据与已经完成的交接，不进行审计产物写入、commit 或推送。默认入口则继续原审计及发布。

原控制根、结果根、日志根均不变。新增工程记录：

```text
new_human_pi1/control/stage4e_automatic_closeout_v1/978ab393.../
  verification/NATIVE_HASH_AUTHORITY_BRIDGE_V1.json
```

完整授权 SHA 仍为 `978ab39389d447b74b1a1acf653619ff437c0d341c9fe76b72236dd8f5fd865b`。

## 验证界限

本包测试使用真实上传的冻结类型、哈希函数和校验器，但任务/seed 记录为明确的合成 fixture。实际服务器 binding、3550 份 episode/trace、结果和远端未在本会话挂载，因此不宣称它们已经独立审计通过。服务器默认入口会执行原完整审计；其他真实不一致仍会停止。

当前 T2 的诊断资格、不可晋级限制、Strong 尚未授权均不改变。
