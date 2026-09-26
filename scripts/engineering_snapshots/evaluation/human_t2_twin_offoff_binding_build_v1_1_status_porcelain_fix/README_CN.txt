Human T2 Twin OFF/OFF Binding Build V1
=====================================

用途
----
在已经通过的 generic SELECT policy-artifact fixed-head 上，机械构建：

1. parent π1 SELECT policy condition/runtime；
2. candidate π2-human SELECT policy condition/runtime；
3. parent/candidate 共用的静态双-LoRA SELECT server runtime；
4. 两套 SELECT_SUMMARY_ONLY condition schedule；
5. twin protocol-equality proof；
6. OFF/OFF execution handoff candidate。

冻结评测网格
------------
Task access manifest:
134 total
117 DEV_VISIBLE
17 SELECT_SUMMARY_ONLY
0 CONFIRMATORY_SEALED
0 HISTORICALLY_EXPOSED

Evaluation seeds:
17, 31, 47, 73, 101

所以：
parent = 17 × 5 = 85 cells
candidate = 17 × 5 = 85 cells
paired comparison = 85 matched task/seed cells
total condition cells = 170

本包不会
--------
- 加载模型；
- 启动 vLLM；
- 运行 ALFWorld；
- 提交 Slurm；
- 执行 benchmark；
- 做 promotion；
- commit / push；
- 重新分类任务。

运行
----
sha256sum -c PACKAGE_FILES.sha256

chmod 700 00_VERIFY_AND_BUILD.sh

bash ./00_VERIFY_AND_BUILD.sh   2>&1 | tee twin_offoff_binding_build.log

成功会生成
----------
/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/
HUMAN_T2_TWIN_OFFOFF_BINDING_REVIEW_V1.zip

下一关
------
OFFOFF_EXECUTION_AUTHORIZATION_AND_RUNTIME_READINESS


V1.1 machine-readable Git status patch
--------------------------------------
The failed V1 stopped before fixed-head tests because changed-path authority was
derived from human-readable `git status --short` with positional slicing.

V1.1 derives it from `git status --porcelain=v1 -z` and preserves the failed V1
review root. No scientific identity, SELECT task grid, seed grid, evaluator,
protocol, or execution authorization is changed.
