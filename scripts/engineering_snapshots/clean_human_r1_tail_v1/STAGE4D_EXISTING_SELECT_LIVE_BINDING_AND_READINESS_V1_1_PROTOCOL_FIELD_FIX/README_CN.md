# Stage4D Existing SELECT Live Binding + Readiness V1.1 — Protocol Field Fix

## 定位

本包只完成 Stage4C frozen SELECT 到既有 live runtime 的最小接线与非科学 server-route readiness。V1.1 仅修复 V1 prepare 对 Stage4C canonical grid 字段名的错误读取：Stage4C 冻结字段为 `paired_cells`，不是 `paired_task_seed_cells`。

它不会运行 3550 个 SELECT episodes，不会调用 ALFWorld 环境，不会生成 scientific outcome，也不会签发 evaluation execution authority。

固定上游：

- fixed head: `ede426ffb069bd887bd3caf847add8193c801d60`
- fixed tree: `4460d1dd9b653258906ef0e625e5af7d7edbc338`
- SELECT protocol: `fcc798b70317d544dd205bb454c2e5017a7460473bd390a13af38b857ab0e1bf`
- TRAIN_SELECT: 355 tasks
- seeds: `17,31,47,73,101`
- paired task-seed cells: 1775
- T0/T2 total condition episodes: 3550
- interface: `I1_EXECUTION_PROFILE_V1`
- Memory OFF / Harness OFF

## 复用资产

本包不实现第二套 SELECT 系统。它直接实例化 fixed-head 中已有的：

- `SelectServerRuntimeManifestV1`
- `SelectPolicyRuntimeManifestV1`
- `PolicyConditionManifestV1`
- `build_condition_run_schedule()`
- `EnvironmentRuntimeManifestV1`
- existing `episode_evaluator`
- existing `select_result_audit`
- existing I1 SELECT execution profile

server 采用单实例静态注册：

- base: `Qwen2.5-3B-Instruct-E1`
- LoRA: `PI1_HUMAN_T2_DIAGNOSTIC_CANDIDATE`
- dynamic LoRA updates: disabled

## 路径原则

不创建新的 scientific root。

正式 binding 继续写入既有 control tree：

`/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/control/stage4d_existing_select_live_binding_v1/<content-sha>/`

日志继续写入既有 round logs tree：

`/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/logs/stage4d_existing_select_live_binding_v1/`

本包自身放在既有 scripts root：

`/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/STAGE4D_EXISTING_SELECT_LIVE_BINDING_AND_READINESS_V1_1_PROTOCOL_FIELD_FIX/`

## 运行

```bash
cd /data/run01/scwb204/sdar_repro/badcase/pchsi_scripts

unzip -o \
  STAGE4D_EXISTING_SELECT_LIVE_BINDING_AND_READINESS_V1_1_PROTOCOL_FIELD_FIX.zip \
  -d .

cd STAGE4D_EXISTING_SELECT_LIVE_BINDING_AND_READINESS_V1_1_PROTOCOL_FIELD_FIX

export STAGE4D_PYTHON=/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python

bash ./00_VERIFY_PACKAGE.sh

bash ./RUN_PREPARE_AND_SUBMIT_READINESS.sh \
  2>&1 | tee stage4d_readiness_submit.log
```

submit driver 会打印 `READINESS_JOB_ID`。readiness job 只启动 1×A800 vLLM，静态注册 base + exact T2 LoRA，并做两个与 ALFWorld 无关的 routing probes。

readiness job 预期最终输出：

```text
STAGE4D_STATIC_SERVER_ROUTE_READINESS_PASS
MODEL_PROBE_COUNT=2
ALFWORLD_ENVIRONMENT_EXECUTION_COUNT=0
SCIENTIFIC_SELECT_CELL_EXECUTION_COUNT=0
EVALUATION_EXECUTION_AUTHORIZED=false
EXECUTION_AUTHORIZATION_READY=true
NEXT_GATE=EXPLICIT_FULL_SELECT_EXECUTION_AUTHORIZATION
```

## 这一步通过后仍不能做什么

不要自行提交 3550 episodes。下一关仍需将已经验证的 binding + readiness receipt 绑定到既有 resumable SELECT live driver，并签发一次明确的 full SELECT execution authorization。

T2 始终是 diagnostic candidate；本包不会把它改成 promotion-eligible policy。
