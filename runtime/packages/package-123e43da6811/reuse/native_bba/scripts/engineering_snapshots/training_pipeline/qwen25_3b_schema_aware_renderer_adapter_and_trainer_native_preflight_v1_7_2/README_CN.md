# Qwen2.5-3B V1.7：精确 Schema-aware Renderer Adapter + Trainer 原生数据预检

## 中文科研主线

```text
真实 π1 失败
→ Human Research Planner PRE
→ Strong PRE shadow
→ PRE adjudication
→ 同状态 F0/F1
→ Benefit / Harm / Neutral / Uncertain
→ Human POST
→ Strong POST shadow
→ POST adjudication
→ Strong Research Planner 生成训练计划
→ Deterministic Data Builder 物化 semantic datasets
→【当前】把 12 条 Policy T2 转成 Qwen Trainer 原生 input_ids/labels
→ 审核 Train17 LoRA 继续训练 Runner
→ π2-human diagnostic
→ Memory OFF + Harness OFF
→ Human Reference Round 收尾
→ Strong 主导 fresh round
→ Local Qwen autonomous fresh round
```

## 人工参考轮和 Strong 接管不是相互脱离

正确关系：

```text
Authority 分开
+
规范 / schema / teacher curriculum 连续
```

人工参考轮负责搭建：
- 分析思路与分析规范；
- PRE / POST 科研规范；
- F0/F1 验证规范；
- B/H/N/U 解释与训练路由规范；
- Failure Experience / applicability / counterexample；
- T0–T6 训练层级；
- Data Builder / Trainer / Promotion 权限边界；
- mixture / budget / stop / rollback；
- 完整 teacher traces。

Strong takeover 必须继承上面这些“科研方法和规范”，但在 fresh round
重新决定当前 policy、fresh failures、bottleneck、repair、F0/F1、
training routes、mixture、recipe 和 promotion。

一句话：

```text
继承规范与 Teacher Traces；
重置 Fresh-Round 答案。
```

## V1.6 已确认的旧 Renderer Schema

历史 84 条源样本不是 `messages`，而是：

```text
input.prompt_text
input.prompt_sha256

target.exact_action
target.action_json
target.target_sha256
```

所以 V1.7 不再假设 top-level `messages`。

## V1.7 执行逻辑

1. 校验 V1.6 census / normative bridge / V1.3 semantic datasets / Strong plan / Train17。
2. 使用真实历史 schema 构造：
   - user = `input.prompt_text`
   - assistant = `target.action_json`
3. 使用冻结 Qwen2.5-3B-Instruct tokenizer + `chat_template.jinja`。
4. 对 84 条历史样本重新计算 `input_ids + labels`。
5. 必须达到：
   - input_ids 84/84 exact match
   - labels 84/84 exact match
6. 只有 84/84 通过，才处理当前 12 条 T2。
7. 当前 T2：
   - Policy input = exact frozen source prompt
   - Policy target = canonical exact repair action JSON
   - Neutral/F0F1/mechanism/Strong route 全部只留 provenance，不进入 Policy 输入/target。
8. 输出 Trainer 原生数据 manifest 和 Trainer preflight。
9. STOP：不执行 Trainer。

## 下一关

```text
审核并构建 Train17 LoRA 继续训练 Runner
→ 显式 GPU 批准
→ π2-human diagnostic
```
