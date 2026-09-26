# Stage4E 原归并函数单一锁持有者续接

## 当前依据与范围

本入口针对已登记的恢复 array **156934**，使用原 PLAN
`cea91dcfb65a6ddd7b1fd719cfaffedb9cfaa950287b19b776ac373260f9564a`，
原 scientific authorization
`978ab39389d447b74b1a1acf653619ff437c0d341c9fe76b72236dd8f5fd865b`。
服务器须重新验证四个元素都 COMPLETED 0:0、四份原生 shard status 均完整。
不是发现任意新 array 后自动接管的通用工具，也没有任务重试或模型执行功能。

Stage5D 日志已经报告本地提交 `a0b58f5291d9879c9903f28f795b1c2024c38e18` 与 2043 项完整仓库测试。
该提交不被本入口读取、修改或发布。本入口解决人工轮尚未完成的 Stage4E 归并/审计链；
原 Stage4E 发布成功后，Stage5B/C/D 的代码整合仍需单独核对实际分支祖先和差异。

## 根因

已上传的 `STAGE4E_NODE_EXCLUDED_ARRAY_RECOVERY_V1/recover.py` 第 306–310 行：
外层重新打开 `full_select_execution.lock` 并加独占锁，然后调用 `ad.consolidate()`。
原 `stage4d_full/live.py` 第 401–414 行的 `consolidate_shards()` 又独立打开同一锁文件并加独占锁。
第二次打开的文件描述符并不共享第一把锁，因而触发
`FULL_SELECT_CONSOLIDATION_ALREADY_ACTIVE`。

本包测试对真实 Linux flock 和原 native consolidation 函数复现该冲突。
标准语义来源：https://man7.org/linux/man-pages/man2/flock.2.html

## 修正路径

```
原 driver.lock（仍由控制器持有）
→ 已登记 submission / recovery proof / Slurm 四分片完整状态核验
→ 原 array_driver.consolidate()
→ 原 live.consolidate_shards()（唯一持有 full_select_execution.lock）
→ 原 completion_gate
→ 追加本入口源码身份与调用链
→ 原 driver.finalize：原审计、汇总、候选处置、受控 Git 发布
```

不修改旧 recovery、Stage4E、Stage4D 的任何文件，因此旧 proof 和归档的 SHA 仍有效。
不删除锁文件，不伪造解锁标记。真实并发进程持锁时仍停止。
不重新提交 sbatch，不取消作业，不重跑已经执行的 cell，不读取 benchmark。
不创建新 clone，不改变任务/seed/候选模型/训练/统计规则。

原程序的发布步骤仍只在原审计真实通过后执行，且包含原有远端 fast-forward 检查；
本包没有新增强制推送或扩大原发布范围，不将 Strong 执行授权设为 true。
原 T2 的 diagnostic_only / promotion_eligible=false 不改变。

## 运行

保留所有原目录。不要同时运行旧 `RUN_RECOVER_AND_FOLLOW.sh` 或另一份 Stage4E 跟随器。
在新包目录运行：

```bash
bash ./RUN_CONTINUE.sh
```

只做状态/身份预检（不归并、不发布）时使用：

```bash
bash ./RUN_CONTINUE.sh --check-only
```

依赖包固定在原 `pchsi_scripts` 下，不从“最新目录”选取。
主入口没有替换脚本根目录的参数；测试专用环境变量仅供包测试使用。
日志进入原 `new_human_pi1/logs/stage4e_automatic_closeout_v1/`。
新增续接记录是原 control root 内的 `SINGLE_OWNER_CONTINUATION.json`。
原 canonical、shard、receipt、lock、protocol、readiness 路径全部不动。

## 停止和恢复

四元素状态不明确、原生 shard 结果未完整、出现未登记新 submission、指针变更、原文件 SHA
变更、真实 controller 或 execution 锁冲突时停止，不自动重试或删文件。
`CONSOLIDATION.intent.json` 的存在不等于完成；原归并函数会逐项核验并继续原幂等复制与追加。
发生半途退出后，保留现场并重新运行本入口；数据相同才会复用，发生差异仍由原函数拒绝。
如果 source archive 留下未提交修改，原 prepare 会停止，不自动清理或接受未知 dirty tree。
如果已经存在 FINAL_PUBLICATION_RECEIPT，只调用原远端核验，不追加新的 commit。

成功标记沿用原 Stage4D / Stage4E，不预写成功结果：

```
STAGE4D_FULL_SELECT_EXECUTION_COMPLETE
T0_CELL_COUNT=1775
T2_CELL_COUNT=1775
TOTAL_CONDITION_CELL_COUNT=3550
...
STAGE4E_EVALUATION_DISPOSITION_AND_SOURCE_PUBLICATION_COMPLETE
PUBLISHED_HEAD=服务器实际提交
```

任何后续原审计报错都必须单独核对，不因本次锁修正而放宽。

## 验证边界

21 项新测试包括真实 flock 自锁复现、原函数保持互斥、独立进程互斥、锁文件不删除、
精确 submission 和完整四分片要求、未知新提交拒绝、check-only 不归并/发布、失败不进入审计。
依赖使用本会话上传的原代码。调度器状态与科学 context 使用标注合成输入；没有真实模型、
ALFWorld、HPC 调度写入或远端发布。原 Stage4E 59 项、Stage4D 18 项、恢复包 34 项本地测试另行复跑。
不声称这里已经独立运行服务器 2043 项全仓测试，也不声称真实 3550-cell 审计已完成。
