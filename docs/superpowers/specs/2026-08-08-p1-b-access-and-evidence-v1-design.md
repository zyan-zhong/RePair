# P1-B Access and Complete Trajectory Evidence V1

## 1. 批准状态

设计批准口令：

`DESIGN_APPROVED_P1_B_ACCESS_AND_EVIDENCE_V1_FORCED_DEV_FROZEN_SPLIT_SEED17_NONADAPTIVE_LEGACY_REFERENCE_ONLY`

父级研究设计：

`P1–P4 Reduced Single-Round Distillation Pilot V1`

当前已审核工程基线：

- repository `main`:
  `effb7c0b25002321a7c123376c53890731ee19a9`;
- P1-A 任务权限、模型身份和运行调度治理代码：
  已合入 `main`;
- π0 条件：
  `P4-R0-PI0`;
- policy:
  `Qwen/Qwen2.5-3B-Instruct`;
- revision:
  `aa8e72537993ba99e69dfaafa59ed015b17504d1`;
- action protocol:
  `RAW_WITH_MENU_V1`;
- memory:
  `MEMORY_M0_V1`;
- Harness:
  OFF.

本文只批准 P1-B 的研究设计。

本文不批准：

- 运行 π0；
- 启动 ALFWorld；
- 启动 vLLM；
- 调用任何外部强模型；
- 自动划分 DEV / SELECT / confirmatory；
- 生成训练数据；
- 训练 π1；
- 执行 SELECT；
- 检查或解封最终确认任务。

## 2. P1-B 的目标

P1-B 在正式收集 π0 开发轨迹前完成两件事：

1. 用可追溯证据确定每个 task/gamefile 的历史访问状态，
   并一次性冻结当前 reduced pilot 的任务用途；
2. 审核当前 evaluator 是否能保存完整、同步、可复算、
   不遗漏关键事实且不会把未来信息泄漏给 student 的轨迹证据。

正式 P1 数据收集的批准链固定为：

```text
P1-B 历史访问审计
→ task-level 用途冻结
→ 当前数据血缘冻结
→ seed-17 DEV schedule 冻结
→ 完整轨迹证据缺口审计
→ 必要的证据层修复与小规模 smoke
→ EXECUTION_APPROVED_P1_PI0_DEV_COLLECTION
→ frozen DEV_VISIBLE π0 collection
```

禁止写成：

```text
EXECUTION_APPROVED_P1_PI0_COLLECTION
→ 自动 strict-134 collection
```

## 3. 大白话术语

### 3.1 开发可见任务：`DEV_VISIBLE`

允许：

- 查看完整轨迹；
- 给强模型做离线分析；
- 生成修复候选；
- 做 Q2 环境重放；
- 生成当前 pilot 的训练数据。

### 3.2 选择验收任务：`SELECT_SUMMARY_ONLY`

允许：

- 在冻结协议下运行 π0 和 π1；
- 用于 Harness-OFF 的公平比较；
- 输出预注册的汇总和 task-level 指标。

禁止：

- 给强模型查看详细轨迹；
- 用于训练；
- 根据详细失败反复修改方法；
- 在看到结果后移动到 DEV。

### 3.3 封存确认任务：`CONFIRMATORY_SEALED`

只允许在方法完全冻结后、经过另行批准时使用。

当前 reduced pilot 不要求从 strict-134 中强行制造
`CONFIRMATORY_SEALED`。

### 3.4 历史上已经接触的任务：`HISTORICALLY_EXPOSED`

表示该任务的历史访问事实不允许被包装成“从未见过”。

它可以按照审计后的显式权限用于开发或历史报告，
但不能静默成为 sealed confirmatory evidence。

## 4. 必须分开的四种概念

以下四件事不能混为一谈：

```text
A. ALFWorld 原始 split
   train / valid_seen / valid_unseen

B. 本项目的 task-level 访问权限
   DEV / SELECT / confirmatory / historically exposed

C. 历史访问证据
   以前是否执行、查看、用于设计或发给外部模型

D. 当前 pilot 数据
   当前协议下由 P4-R0-PI0 新生成的轨迹、候选和训练数据
```

`valid_unseen` 不自动等于 sealed confirmatory。

历史上运行过某个 task 也不自动等于当前实验数据。

## 5. 当前 strict-134 的角色

当前 strict-134 manifest 可以作为 P1-B 的候选任务池，
但它不能自动被整体归入任何一种用途。

冻结身份源：

```text
path:
data/manifests/alfworld_strict_valid_unseen_all134_v1.jsonl

manifest SHA-256:
6e480bb663a6f17207aa2c7a6e1b504adad8448f6e8a2615c5e62fea0b64c0f4

record count:
134

ordered:
true
```

P1-B 必须对每个 task/gamefile 逐条形成审计记录，
然后才决定当前用途。

## 6. 历史数据与当前数据的严格边界

### 6.1 旧 GPT / Claude / Gemini / V7B 数据的角色

旧数据固定为：

`LEGACY_REFERENCE_ONLY`

中文：

**只作历史访问证明。**

旧材料必须进一步分成：

```text
A. 旧 task-level 访问证据
B. 旧实验内容、轨迹语义与模型表现
```

旧 task-level 访问证据只允许用于：

- 写入历史访问标签；
- 判断某个 task 是否满足 forced DEV 条件；
- 判断某个 task 是否具备 confirmatory eligibility；
- 证明某个 task 是否曾被发送给外部模型；
- 证明某个具体 task 是否被人工详细检查；
- 证明某个具体 task 是否用于方法、规则或 Harness 设计。

因此，第 9 节规定的：

```text
TRAJECTORY_INSPECTED
或
USED_FOR_METHOD_DESIGN
→ forced DEV_VISIBLE
```

属于历史访问治理，不属于利用旧模型表现优化当前 split。

旧实验内容、轨迹语义与模型表现禁止用于：

- 计算或选择当前 split_key；
- 为非 forced-DEV task 挑选 DEV / SELECT；
- 调整 DEV / SELECT 比例或 family quota；
- 估计当前 π0 成功率；
- 形成当前 badcase taxonomy；
- 作为当前 teacher 输入；
- 生成当前修复候选；
- 生成当前 Q2 数据；
- 生成当前 SFT 数据；
- 决定是否增加 P1 DEV seed；
- 决定后续 SELECT evaluation seed；
- 评价当前 π1；
- 解释当前 reduced pilot 的主要结果。

尤其禁止根据旧 success/failure、旧轨迹长度、旧 failure taxonomy、
旧 teacher rationale 或旧方法表现移动 task 或重新拆分。

### 6.2 当前 pilot 的数据血缘

总合同冻结为：

`CURRENT_PILOT_DATA_LINEAGE_V1`

它包含两条彼此隔离的当前数据链。

#### 6.2.1 P1 开发数据血缘

冻结为：

`P1_DEV_DATA_LINEAGE_V1`

允许进入 P1 开发/蒸馏/训练链的数据只包括：

1. 当前冻结的 `DEV_VISIBLE` task/gamefile；
2. 当前冻结的 `P4-R0-PI0`；
3. 当前冻结的 P1 DEV seed `17`；
4. 当前 Runtime Core；
5. 当前 evaluator；
6. 当前完整 trajectory evidence；
7. 当前 teacher 输出；
8. 当前 Q2 replay 结果；
9. 当前生成的 BAD / MIX SFT 数据。

这里的 seed `17` 只约束 P1 DEV collection，
不约束后续 P4 Harness-OFF SELECT evaluation。

#### 6.2.2 P4 选择验收数据血缘

冻结为：

`P4_SELECT_EVALUATION_LINEAGE_V1`

P4 SELECT 只允许使用：

1. 当前冻结的 `SELECT_SUMMARY_ONLY` task/gamefile；
2. 当前冻结的 π0 / π1 policy conditions；
3. 在 SELECT 执行前独立预注册的 evaluation seed schedule；
4. 当前冻结的 Runtime Core / evaluator；
5. Harness OFF 的评测结果与预注册指标。

SELECT 数据禁止：

- 进入 teacher 输入；
- 进入 Q2 replay 数据；
- 进入 BAD / MIX 训练数据；
- 用于修改 teacher prompt、候选规则或 SFT recipe；
- 根据中期 SELECT 结果增加、删除或替换 evaluation seed。

P4 SELECT 的 evaluation seed schedule 必须在 SELECT 执行前一次性冻结，
同样禁止自适应扩展，但它不被限定为 seed `17`。

#### 6.2.3 当前 pilot 统一排除的 legacy 数据

以下旧数据不进入上述任一当前数据链：

- 旧 GPT trajectory；
- 旧 Claude trajectory；
- 旧 Gemini trajectory；
- V7B / V7B.3c trajectory；
- 旧 planner / guard / controller 输出；
- 旧 correction 数据；
- 旧 failure taxonomy；
- 旧 success/failure 标签；
- 旧 teacher rationale。

旧 task-level 访问证据仅按 6.1 节进入访问治理，
不进入当前模型训练或评测数据。

## 7. 旧任务与当前 task 的身份对照

旧仓库声称的 `all134` 不能仅凭名称自动视为与当前
strict-134 完全相同。

必须建立：

`LegacyCurrentTaskCrosswalkV1`

每条对照至少包含：

- legacy source repository；
- legacy task ID；
- legacy gamefile 或可用路径；
- current manifest index；
- current task ID；
- current gamefile；
- current gamefile SHA-1；
- match status；
- evidence source；
- confidence class。

允许的 `match_status`：

```text
EXACT_GAMEFILE_SHA1_MATCH
EXACT_TASK_ID_AND_PATH_MATCH
TASK_ID_ONLY_INSUFFICIENT
NO_MATCH
LEGACY_RECORD_INCOMPLETE
```

只有以下情况可以自动写入：

`SENT_TO_EXTERNAL_MODEL`

```text
EXACT_GAMEFILE_SHA1_MATCH
```

或者：

```text
EXACT_TASK_ID_AND_PATH_MATCH
且人工审计确认 legacy/current 指向同一 gamefile
```

如果只能确认名称相似，必须使用：

`ACCESS_HISTORY_INCOMPLETE`

不能猜测为完全相同。

## 8. 历史访问标签

允许的历史访问标签：

```text
NO_KNOWN_PRIOR_ACCESS
ACCESS_HISTORY_INCOMPLETE
AGGREGATE_ONLY
EXECUTED_NOT_INSPECTED
TRAJECTORY_INSPECTED
USED_FOR_METHOD_DESIGN
SENT_TO_EXTERNAL_MODEL
```

### 8.1 `NO_KNOWN_PRIOR_ACCESS`

只表示：

> 已审计记录中没有发现 prior-access evidence。

不表示：

> 绝对从未发生过访问。

该标签出现时必须是唯一标签。

### 8.2 `ACCESS_HISTORY_INCOMPLETE`

当现有记录不足以对历史访问作完整判断时必须使用。

带有该标签的 task：

- 不得进入 `CONFIRMATORY_SEALED`；
- 可以在当前 reduced pilot 中参加 DEV/SELECT 拆分，
  但结果只支持 developmental claim。

### 8.3 `SENT_TO_EXTERNAL_MODEL`

表示 task/gamefile 的身份已通过第 7 节的对照规则确认，
并且历史上被发送给外部模型。

它单独出现时：

- 不自动强制进入 DEV；
- 不得进入 `CONFIRMATORY_SEALED`；
- 仍可参加当前 DEV/SELECT 的冻结拆分；
- 旧外部模型输出不得进入当前数据血缘。

## 9. 明确详细检查或方法设计的 task 强制进入 DEV

硬规则：

```text
只要历史审计中存在：

TRAJECTORY_INSPECTED

或

USED_FOR_METHOD_DESIGN

→ 强制 DEV_VISIBLE
→ 不参加哈希拆分
→ 不得进入 SELECT
→ 不得进入 CONFIRMATORY
```

### 9.1 “明确”的证据标准

至少需要一个逐 task 可追溯证据：

- task ID 出现在人工分析报告；
- 对应 trajectory Markdown / JSON 被明确引用；
- 历史 commit 或脚本针对该 task 做过修复；
- 会议或研究记录明确点名该 task；
- 方法设计文档把该 task 作为案例；
- 旧实验的 per-task analysis 明确被人工使用。

不能因为：

```text
“可能看过”
“all134 都跑过”
“仓库里有文件”
```

就把全部 task 批量标成：

`TRAJECTORY_INSPECTED`

如果无法确认，使用：

`ACCESS_HISTORY_INCOMPLETE`

## 10. split 公式与 salt 一次性冻结

### 10.1 固定 salt

完整字符串冻结为：

```text
P1_B_ACCESS_SPLIT_V1|effb7c0b25002321a7c123376c53890731ee19a9
```

不得替换、重抽或试多个 salt。

### 10.2 规范化 split key

对每个非强制 DEV task 构造：

```json
{
  "schema_id": "P1_B_TASK_SPLIT_KEY_V1",
  "salt": "P1_B_ACCESS_SPLIT_V1|effb7c0b25002321a7c123376c53890731ee19a9",
  "task_type": "<task_type>",
  "task_id": "<current task_id>",
  "gamefile_sha1": "<current gamefile_sha1>"
}
```

然后：

```text
split_key_sha256
=
SHA-256(canonical_json_bytes(split_key_payload))
```

canonical JSON 必须复用仓库现有 canonicalization，
不得另写一套不同的序列化规则。

### 10.3 禁止进入 split 的信息

拆分不得读取：

- 旧 GPT 成功/失败；
- 旧 Claude 成功/失败；
- 旧 Gemini 成功/失败；
- 旧 failure taxonomy；
- 当前 π0 结果；
- 当前轨迹长度；
- 当前 teacher 输出；
- 人工难度判断；
- task 的历史成功率；
- 强模型候选数量；
- Q2 通过率；
- SFT 结果。

## 11. 六类任务分别拆分

每个 task family 独立执行。

对 family `f`：

```text
N_f
=
该 family 在当前候选池中的总 task 数
```

固定选择验收目标：

```text
SELECT_TARGET_f
=
max(1, floor(N_f / 3))
```

执行顺序：

```text
1. 取出所有 forced DEV task
2. 剩余 task 按 split_key_sha256 升序排序
3. 前 SELECT_TARGET_f 个进入 SELECT_SUMMARY_ONLY
4. 其余进入 DEV_VISIBLE
5. split_key 相同则按原 manifest_index 升序
```

### 11.1 fail-closed 条件

如果 forced DEV 后剩余 task 数小于 `SELECT_TARGET_f`：

```text
P1_B_SPLIT_INFEASIBLE
```

不得：

- 换 salt；
- 换公式；
- 重新随机；
- 手动搬 task；
- 根据当前结果缩小 SELECT；
- 偷偷从其他 family 借 quota。

此时必须单独修订 task-pool 设计。

### 11.2 拆分后禁止移动 task

一旦以下内容冻结：

- `TaskAccessManifestV1`;
- split contract；
- split proof；
- condition schedules；

任何 task 都不能因为以下原因在 DEV/SELECT 之间移动：

- π0 成功或失败；
- teacher 候选太少；
- Q2 通过率太低；
- SFT 数据不足；
- 某个 family 表现不好；
- SELECT 结果不理想；
- 置信区间不好看；
- 成本过高。

## 12. 当前 strict-134 不设置自动 confirmatory

本轮 reduced pilot 中，strict-134 的当前用途为：

```text
forced DEV
+
hash-split DEV
+
hash-split SELECT
```

当前不从 strict-134 自动生成：

`CONFIRMATORY_SEALED`

最终 confirmatory 任务必须在方法冻结后另行设计，
可以来自：

- 新的未接触 task pool；
- 第二环境；
- 新 benchmark；
- 其他预注册且与当前训练链隔离的数据。

## 13. P1 DEV 的 seed 17 固定且不自适应扩展

本节只约束 P1 DEV collection。

它不把 P4 SELECT evaluation 限定为 seed 17；
SELECT 使用第 6.2.2 节规定的独立预注册、非自适应 evaluation seed schedule。

第一批正式 P1 开发轨迹 schedule 固定为：

```text
policy_condition_id:
P4-R0-PI0

target_access_class:
DEV_VISIBLE

replicate_seeds:
[17]

run_purpose:
P1_PI0_DEV_ROLLOUT
```

### 13.1 禁止自适应增加 seed

不得因为以下结果增加 `31 / 47 / 73 / 101`：

- 失败 task 太少；
- 成功 task 太多；
- teacher 候选太少；
- Q2 通过率太低；
- BAD 数据不足；
- MIX 数据不足；
- 某个 family 样本不足；
- 初步 SFT 提升不明显；
- 置信区间不好看；
- 成本或时延不理想。

seed-17 collection 完成后只能给出：

```text
P1_DEV_COLLECTION_SUFFICIENT
```

或：

```text
P1_DEV_COLLECTION_INSUFFICIENT
```

如果不足，必须另行提出设计修订，
并在新增 schedule 执行前冻结规则。

### 13.2 基础设施重试不属于新增 seed

以下基础设施故障允许重试：

- Slurm 节点故障；
- vLLM 未启动；
- Ceph 发布失败；
- ALFWorld worker 崩溃；
- IPC 超时；
- 明确的 infrastructure error。

重试必须保持：

- 同一 task；
- 同一 seed 17；
- 同一 policy condition；
- 同一 condition cell；
- 增加 attempt ordinal；
- 保留失败 terminal receipt；
- 不挑选多个 attempt 中的最佳结果。

### 13.3 SELECT evaluation seed 单独冻结

后续 P4 Harness-OFF SELECT 的 evaluation seed schedule：

- 不由本节的 seed `17` 限定；
- 必须在 SELECT 执行前单独预注册；
- 必须对 π0 / π1 使用相同的 paired evaluation seed schedule；
- 不得根据中期 SELECT 指标自适应增加、删除或替换 seed；
- 不得因为某个训练条件表现不理想而补跑有利 seed；
- 任何后续 seed-schedule 修订都必须发生在新的 SELECT 执行之前，
  并使用独立设计修订与冻结证据。

## 14. 完整轨迹证据目标

正式 P1 收集的对象不是最小的：

```text
observation → action → reward
```

而是：

`P1_PI0_COMPLETE_TRAJECTORY_EVIDENCE_V1`

它必须能够回答：

- 模型每一步到底看到了什么；
- 发给模型的精确请求是什么；
- 模型原始返回是什么；
- parser 如何处理；
- 为什么调用或没有调用环境；
- 环境实际执行了什么；
- 动作前后公开状态如何变化；
- menu / memory / feedback / budget 如何变化；
- episode 为什么终止；
- 所有记录属于哪个 task、seed、model、commit 和协议。

## 15. 三层数据视图

### 15.1 完整不可变审计视图

服务器保存最完整的协议事实和 provenance，
用于：

- 审计；
- 复算；
- exact-state replay；
- teacher exporter；
- 数据泄漏检查。

### 15.2 DEV 强模型离线分析视图

只允许 `DEV_VISIBLE`。

可以包含完整已结束轨迹，包括：

- 当步 observation/menu；
- 原始模型回复；
- parser/off-list 结果；
- 后续公开状态；
- 最终 success/failure；
- 终止原因。

强模型的结论必须使用：

```text
teacher_proposed_*
```

不能被当作 environment truth。

### 15.3 Student 当步输入视图

第 `t` 步只能包含行动前可见信息：

- public task goal；
- current observation；
- current complete menu；
- M0 最近 8 个真实 executed transitions；
- current interface feedback。

禁止：

- 第 `t` 步之后的 observation；
- 未来 menu；
- 最终 success/failure；
- teacher rationale；
- teacher confidence；
- Q2 replay 后才知道的结果；
- hidden simulator state；
- expert/answer path。

## 16. 每次 policy call 的必要证据

每次模型调用，无论动作是否进入环境，都必须保存：

### 16.1 行动前可见状态

- `model_call_index`;
- `environment_step_index`;
- public task goal + hash；
- current observation + hash；
- complete admissible menu；
- menu 原顺序；
- menu 原数量；
- menu sequence hash；
- M0 完整 0–8 条 executed transitions；
- M0 hash；
- current interface feedback；
- complete `BudgetState` before call；
- policy attempt count；
- environment step count；
- consecutive non-executed count。

### 16.2 精确模型请求

- raw prompt text；
- prompt bytes / hash；
- rendered chat-template prompt；
- rendered bytes / hash；
- request wire payload；
- request bytes / hash；
- model repo / revision；
- served model name；
- seed；
- temperature；
- top_p；
- max tokens；
- stop parameters；
- tokenizer identity；
- chat-template identity；
- client request ID。

### 16.3 原始模型返回

- HTTP status；
- allowlisted response headers；
- provider request ID；
- client request ID；
- raw response body；
- raw response body hash；
- raw assistant content；
- raw assistant content hash；
- finish reason；
- prompt/completion token counts；
- prompt/completion token IDs；
- latency。

禁止保存：

- API key；
- Authorization header；
- secret；
- 非 allowlist 的敏感 header。

### 16.4 Runtime Core 处理结果

- parser input；
- parser status；
- failure stage/code；
- normalized action；
- exact menu membership；
- should_call_env；
- submitted action candidate；
- feedback code；
- attempt outcome；
- termination reason；
- BudgetState before/after。

所有格式错误、duplicate key、off-list 等未执行尝试必须保留，
但不得进入 executed history。

## 17. 每次环境调用的必要证据

对每个真实 `environment.step()` 保存：

- environment call index；
- environment step index；
- submitted action；
- pre observation + hash；
- pre menu + sequence hash；
- resulting observation + hash；
- resulting menu + sequence hash；
- score；
- done；
- won；
- gamefile identity；
- worker identity；
- IPC request/response identity；
- timeout/error；
- worker lifecycle status。

必须满足：

```text
每个成功 env.step
↔ 恰好一个 public transition
```

```text
每个 environment error
↔ 不伪造 public transition
```

```text
每个 executed action
↔ 是对应 pre-menu 的 exact member
```

## 18. Episode 级必要证据

每个 episode 至少绑定：

- task ID / task type；
- gamefile path / SHA-1 / SHA-256；
- original dataset split；
- access class；
- seed；
- condition cell ID；
- execution attempt ID；
- attempt ordinal；
- TaskAccessManifest hash；
- PolicyConditionManifest hash；
- ConditionRunSchedule hash；
- model / tokenizer / template identity；
- Runtime Core commit；
- evaluator commit；
- initial observation；
- all policy-call records；
- all environment transitions；
- final observation；
- success；
- termination reason；
- score / done / won；
- final BudgetState；
- scientific outcome status；
- publication status；
- episode semantic SHA-256；
- attempt bundle SHA-256；
- scientific cell lock；
- terminal receipt。

## 19. 可见性与泄漏标签

证据字段或记录必须能被机器分类为：

```text
POLICY_VISIBLE_AT_DECISION
POST_ACTION_PUBLIC_AUDIT
EPISODE_TERMINAL_OUTCOME
OFFLINE_TEACHER_VISIBLE_DEV_ONLY
OPERATIONAL_PROVENANCE_ONLY
SEALED_ORACLE_AUDIT_ONLY
```

并明确：

- `student_input_eligible`;
- `teacher_input_eligible`;
- `q2_replay_required`;
- `select_export_permitted`.

如果未来保存 hidden simulator state，
它必须是：

```text
SEALED_ORACLE_AUDIT_ONLY
teacher_input_eligible = false
student_input_eligible = false
training_eligible = false
```

## 20. 完整轨迹 evidence gap audit

P1-B 必须对当前 evaluator 做字段级审计，
至少回答：

1. exact request wire bytes 是否发布；
2. rendered prompt bytes/hash 是否发布；
3. raw HTTP response body 是否发布；
4. prompt/completion token IDs 是否发布；
5. usage / finish_reason / latency 是否发布；
6. resulting menu 是否可与 ActionTrace/PublicTransition 对齐；
7. M0 的具体 0–8 条内容是否发布；
8. interface feedback 前后状态是否完整；
9. 每个非执行 attempt 是否完整存在；
10. visibility/training-eligibility 是否可机器验证；
11. BudgetState 是否逐 attempt 连续；
12. public observation/menu hash 链是否连续。

每项输出：

```text
PRESENT_AND_VALIDATED
PRESENT_BUT_UNVALIDATED
PARTIAL
MISSING
NOT_APPLICABLE_WITH_JUSTIFICATION
```

## 21. Evidence completeness gate

一个 episode 只有在以下条件全部满足时，
才允许进入 teacher distillation：

- bundle 已发布；
- scientific hashes 通过；
- 每个 model call 有一个 pre-decision snapshot；
- 每个 model call 有一个 exact request；
- 每个 model call 有一个 raw response；
- 每个 model call 有一个 parser/runtime result；
- 每个 executed action 有一个 public transition；
- action/menu membership 可复算；
- BudgetState 连续；
- M0 可重建；
- observation/menu hash 链连续；
- visibility labels 完整；
- TaskAccess=`DEV_VISIBLE`。

缺失任一关键项：

```text
INELIGIBLE_DISTILLATION_EVIDENCE_INCOMPLETE
```

不得用空值或人工补写静默修复。

## 22. P1-B 输出

P1-B 最终应生成：

1. `LegacyCurrentTaskCrosswalkV1`;
2. `HistoricalAccessAuditV1`;
3. `forced_dev_tasks.json`;
4. `split_contract.json`;
5. `split_proof.json`;
6. `TaskAccessManifestV1`;
7. `CURRENT_PILOT_DATA_LINEAGE_V1`;
8. `P4-R0-PI0 PolicyConditionManifestV1`;
9. seed-17 `ConditionRunScheduleV1`;
10. governance freeze bundle；
11. complete trajectory evidence gap report；
12. field-level visibility matrix；
13. P1 DEV execution-readiness report。

## 23. Fail-closed 条件

出现以下任一情况，P1-B 不得批准正式 collection：

- legacy/current task identity 无法可靠对照；
- forced DEV 证据不能逐 task 追溯；
- split formula/salt 未按本文冻结；
- split 读取了 success/failure；
- family quota infeasible；
- task 在 freeze 后被移动；
- schedule 含 seed 17 以外的 seed；
- current/legacy data lineage 混用；
- evidence gap 存在关键 `MISSING`；
- teacher exporter 可读取 SELECT；
- student projection 包含 future outcome；
- hidden state 可进入 teacher/training；
- governance bundle hash 不匹配；
- π0 identity 不是 `P4-R0-PI0`；
- worktree/commit/task manifest identity 不匹配。

## 24. 明确禁止

P1-B 阶段禁止：

- 运行 π0；
- 调用强模型；
- 查看当前 SELECT 的详细 trajectory；
- 根据当前结果调整 split；
- 根据旧 success/failure 调整 split；
- 尝试多个 salt；
- 自动追加 seed；
- 把基础设施重试当成新 replicate；
- 使用旧轨迹构造当前训练数据；
- 把 strict-134 自动称为 confirmatory；
- 用人工猜测代替 task-level evidence；
- 放宽 schema inventory；
- 修改 Runtime Core 的冻结语义；
- 修改 Harness-OFF 主问题。

## 25. P1-B 之后的审批门

本文写入并审核后：

1. 编写 file-level implementation plan；
2. 实现历史对照、split proof 和 evidence gap audit 工具；
3. 独立代码审核；
4. 生成真实 P1-B artifacts；
5. 人工审核 forced DEV 与 split proof；
6. 审核完整轨迹 evidence gap；
7. 必要时修复 evidence layer；
8. 运行 1–3 task completeness smoke；
9. 审核 smoke；
10. 单独授予：

`EXECUTION_APPROVED_P1_PI0_DEV_COLLECTION`

之后才允许正式收集 frozen `DEV_VISIBLE` 的 seed-17 π0 轨迹。
