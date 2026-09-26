# Formal Max-10 V1.8.2

用户已授权修复并恢复现有campaign。新包精确接纳已经结束的旧invalid尝试，保留全部旧证据，并在原预算内重新执行同一科学轮。只运行一次 `bash RUN.sh`；活跃writer由原campaign锁排他控制。

终端查看：`bash STATUS.sh --watch`；一次查看 `bash STATUS.sh`，机器JSON `bash STATUS.sh --json`。查看器只读，关闭查看窗口不终止训练。显示采样/Analyzer与Planner/因果验证/训练/TRAIN_SELECT评测/Memory闭合，以及有效轮进度。

验证：`python VERIFY.py`；服务器精确登记预检 `bash VERIFY.sh --server`；软件fixture `python TESTS.py --groups 1 2 3 4`。实际Linux并发socket继承另有测试。无set -e/-u/pipefail；RUN的tee后立即读PIPESTATUS[0]。

晋升沿用既有TRAIN_SELECT完整有效OFF/OFF配对网格：候选成功数严格大于父模型；辅助状态指标解释用，不新增门槛。最多10个有效轮、连续3个有效未晋升轮停止、基础设施恢复预算2。canary不算正式轮。

每个完成或invalid尝试按既有论文合同导出四类证据并发布精确索引；缺失字段显式null。实际API成本不可凭token估算冒充账单；最终134/140benchmark及独立对照不由本入口伪造。

完整历史总账、append-only proof及Git staging在包内。staging-only，未commit/push；以实际执行回执区分预检/提交/采样/优化器执行。
