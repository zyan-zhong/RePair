# Stage4E：156877 节点占用事故的单次受控恢复

## 范围
沿用已安装的 Stage4E V1.1、Stage4D V1.3 和已有科学授权。只为 156877 增加一条可审计的基础设施恢复记录，并在新提交中指定 `--exclude=d1n41a18g03`。四个 task 仍分别申请一张 A800。没有新 evaluator、没有模型修改、没有自动更换样本。

本工具是当前明确事故的一次恢复适配器，不声称已经建成通用故障自愈系统。新运行若 FAILED / TIMEOUT / 提交结果不确定，仍停止；正常完成但 graceful partial 则继承原有一次分片续跑预算。

## 运行
将目录置于既有 `pchsi_scripts` 下，在 tmux 中运行：

```bash
bash ./RUN_RECOVER_AND_FOLLOW.sh
```

可先执行 `bash ./RUN_RECOVER_AND_FOLLOW.sh --check-only`：会校验并写入事故恢复记录，但不提交作业。

不要删除原 `SUBMISSION_0.json`、原 PLAN、旧日志、lock、102 对 canonical receipts；不要重启旧 array 跟随器，不要手工重提四份 worker。无需重新跑 readiness 或 1930 项全仓测试。

## 严格入口条件
* 原 Stage4E 清单 SHA 必须为 `e34acc3e2254141ebe5297b643cbcc9d4aade383c627be9682128e2bc681f535`。
* 原 array PLAN SHA 必须为 `cea91dcfb65a6ddd7b1fd719cfaffedb9cfaa950287b19b776ac373260f9564a`。
* 原 SUBMISSION_0 必须精确绑定 156877 的四个分片。
* 服务器 accounting 须显示四个元素均为当前用户的 `st4d_select_shard`，`FAILED 1:0`，节点均为 d1n41a18g03。
* 四份 outer log、四组 inner log 和命令均须存在。每个分片必须具有相同类别的 vLLM 启动显存门错误以及 wait_ready 退出证据。当前上传只充分展示了 shard 0、1 的内层错误；脚本会补核对 2、3，不凭推测放行。
* canonical receipts 字节 SHA 和冻结 prefix 必须保持不变；所有 shard 目录必须没有文件产物，不能仅以 wc 行数为零代替检查。
* 有任何部分 cell/attempt、完成 marker 或不明新提交，保留现场并停止；不自行删掉后重跑。

## 恢复与兼容
使用原 `driver.lock` 和 `full_select_execution.lock`。恢复新增到原 `parallel_v1/independent_jobs_v1/node_recovery_156877_v1/`，保持原 PLAN 与 worker 的 controller identity。

失败的 `SUBMISSION_0` 永久保留。新提交使用空闲的 `SUBMISSION_2`；仅在新作业 COMPLETED 0:0 且原生状态明确 graceful partial 时，才对未完成分片使用 `SUBMISSION_3`。两个新提交均带节点排除。原 worker 本来通过 `SUBMISSION_*.json` 解析自己的身份，无需改变。

提交 intent 先落盘，返回的真实 job ID 后落盘。遇到不确定提交不重复 sbatch。恢复入口再次启动会复用已有提交与状态，不把新 job 指针倒退到前一代。

四个分片完成后，直接调用原 `load_worker_status`、`consolidate` 和 `driver.finalize`，仍由原完整性/科学审计控制发布。新恢复源码会追加到原独立 integration clone 的 engineering snapshot，并附 `NODE_RECOVERY_SOURCE_PROVENANCE.json`。不修改运行用旧包，不覆盖原代码地图；新增补充索引说明实际使用的恢复调用链。

## 不做的事情
不降低 GPU memory utilization；不修改 CUDA_VISIBLE_DEVICES；不杀任何其他进程；不重置 GPU；不清理 home/run 缓存；不改变任务、seed、训练数据、策略权重、晋级资格；不启用 Strong 主导轮次；不接触 benchmark。

## 本地验证边界
本工具测试使用真实文件、原 Stage4E JSON/哈希/no-clobber 工具，以及模拟 Slurm 返回。未在本环境执行真实 Slurm 或 GPU。服务器上的 job、归并、审计和远端发布成功必须由真实输出确认。
