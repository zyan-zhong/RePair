# RePair 中文阅读入口

本仓库整理了框架源码、实验程序、配置、提示词、登记的部署快照、测试，以及论文
v4.3 的源码和数值证据。请先阅读根目录 README，再按下面的顺序使用。

1. **核对论文数字**：`python paper/reproduce_results.py`。无需 GPU、API 或环境数据。
2. **核对代码文件**：`python tools/verify_registered_sources.py` 和
   `python tools/verify_release.py`。公开版明确列出未公开的私有运维记录。
3. **阅读方法接线**：[METHOD.md](repair/METHOD.md)。包含 Analyzer L/G/C/P/X、
   Planner PRE/POST、F0/F1、Dual-View、记忆和轮次控制的代码位置。
4. **阅读实验设置**：[EXPERIMENTS.md](repair/EXPERIMENTS.md)。F0/F1 为 5 个配对
   seed；本次 TRAIN_SELECT 为 1 个 seed（17），不能混用。
5. **运行测试与部署**：[INSTALLATION.md](repair/INSTALLATION.md) 和
   [REPRODUCIBILITY.md](repair/REPRODUCIBILITY.md)。完整测试用 Linux/Python 3.12；
   真实训练还需要合法获取的模型、ALFWorld 数据、GPU、凭据及登记的部署绑定。

当前论文报告的是：后续策略验证获得 4/5 个稳定 Benefit 来源，但 8 条双视图数据
训练后，独立选择评估仍为 3/355；按规则保留父模型。不要把程序完成任务的效果
当成模型能力提升，也不要把软件测试通过当成科研结果。

运行快照中的绝对路径是原部署的历史记录，不是可在其他机器直接复制的命令。
部署应通过 status/manifest → registered typed index → exact asset/SHA 定位；
不能通过目录递归搜索、latest/mtime 或手工猜版本选择运行资产。

本账号下的公开仓库不是匿名审稿链接。匿名投稿材料及限制见
[REVIEW_MATERIALS.md](repair/REVIEW_MATERIALS.md)。
