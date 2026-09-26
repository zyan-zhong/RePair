# V212 统一终端进度窗

在服务器沿用同一入口，当前验证和后续正式轮次使用同一显示器：

```bash
bash /data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/package_runs/FORMAL_MAX10_STAGE_STATUS.sh --watch
```

已经打开的旧观察窗按 Ctrl-C 后用原命令重新打开一次；Ctrl-C 只结束观察窗，resident 和 Slurm 作业继续运行。新窗口每次刷新读取登记指针和当前轮次，后续轮次无需重开。无人值守训练不依赖观察窗进程存活；SSH 断开后重新打开同一命令即可，不会重启训练或重复提交作业。服务器后台无法替已断开的客户端创建可见 terminal。

`--formal` 强制查看正式 campaign；`--validation` 查看当前登记的单轮验证；默认在验证结束且正式 owner 已登记新轮次时自动切换。`--details` 展开完整说明及证据位置，`--json` 输出机器可读快照，`--color never` 输出纯文本，`--color always` 强制 ANSI 背景色，`--interval 5` 控制刷新间隔。非终端输出、NO_COLOR 和 TERM=dumb 默认不使用控制码。

固定显示 Rollout、Analyzer L/G/C/P/X、PRE 来源审核与最终决策、F0/F1、POST、Training、父模型与候选评估、Acceptance、Memory closure、Paper export。绿色 RUN/DONE；黄色 WAIT/CHECK/UNKNOWN；红色 ERROR；青色 REUSED；灰色 PENDING。关闭的调用包含接受、拒绝和隔离，接受数另列。进度 100% 只代表本行计数完成，验收需独立 receipt。未知总量显示 ?，零任务显示 n/a，不臆造 100%；PRE/POST 单次模型生成显示 0/1 和等待状态，不伪造 token 百分比。

所有工作量来自现有 authority、typed index、冻结 schedule 和 receipt；没有文件系统扫描、latest/mtime 推断、训练副作用或额外服务。实现复用登记 V5.9 cognitive/lifecycle/select readers；未编辑原执行包、源数据、训练入口、parser、provider 配置、模型、seed 或晋升门槛。

初次核验发现 V211 原评估错误采用 `replicate_seeds=[17,31,47,73,101]`、每侧1775条，与此前已登记的单seed配置不一致。用户随后明确要求停止多余seed，4个原评估作业已取消；原证据保留，seed17两侧各355条已全部发布。单seed恢复记录通过活动索引的 `evaluation_recovery_ref` 绑定；窗口读取修订后的真实355任务分母，并单列目标完成比例恢复进度。该恢复只复用既有动作轨迹，不产生新模型episode；观察窗仍为只读显示器。

单包 VERIFY 检查 SHA 和观察窗测试；服务器验证另外核验原读取器和真实 JSON/文本/TTY watch 输出。替换统一入口前备份其原字节，只原子替换观察入口；旧执行包 SHA、训练请求与作业提交回执应保持一致。Git 为 staging cache/delta，无 add/commit/push。
