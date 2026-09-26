# Strong-Model Shared-Protocol Live Executor Implementation Plan V1

**Goal:** 将 OpenAI Responses provider 通过窄 adapter 接入现有 `run_single_episode()`，不复制 ALFWorld evaluator、prompt、parser、budget、trace、publisher 或 P2 transport。

## Task 1 — Provider-aware execution identity

- 扩展 `PolicyExecutionProfileV1`：provider、requested model、transport kind；保留现有本地默认值。
- `_provenance()` 不再硬编码 `vllm`。
- RED：本地 profile 现有序列化不变；OpenAI profile 写入 OpenAI identity。

## Task 2 — OpenAI request factory

- R0 强模型 profile 构建 `OpenAIResponsesPolicyRequestV1`。
- 不启用 structured output、tools、conversation 或 previous_response_id。
- HIGH 与 DIRECT arm 分开注册，不能临时改 reasoning 设置。

## Task 3 — 复用 P2 transport primitive

- 不实现新的 HTTP client。
- compatibility wrapper 固定 P2 root、文件 SHA、函数签名、返回 tuple 与 exception taxonomy。
- 一个 scientific call 只允许一个 transport attempt；reservation 在发送前写入。

## Task 4 — Provider-specific raw evidence binding

- 保留 STARTED、TERMINAL 或 TRANSPORT_EXCEPTION no-clobber evidence。
- 不伪造 Qwen tokenizer IDs；provider usage 与 raw bytes 单独保存。
- episode artifact 与 provider sidecar 建立 SHA binding。

## Task 5 — Existing evaluator integration

- 复用 `run_single_episode()`、`SpawnedAlfworldAdapter`、Runtime Core、strict parser 和 ArtifactPublisher。
- 不创建第二套 episode loop。
- fake environment + injected P2 transport 做 TDD integration。

## Task 6 — Single-cell live smoke

- 一条 DEV-visible、非论文 cell；一次完整 episode；无自动重试。
- 审核 raw request/response、menu equality、budget、trace、publication 和 worker close。

## Task 7 — Frozen shared-protocol schedule

- 与最终本地 benchmark 绑定同一 task manifest、task order、success definition 和 registered seed schedule。
- 强模型无可控 seed 时明确记录，不伪造；统计仍按 task-level paired panel。
- benchmark output 写入 sealed root，Human PRE/Planner 无逐任务读取权限。

## Task 8 — Parallel collection

- 单独 execution approval 后逐任务运行 sequential API calls。
- 运行中只公开 operational census 和 aggregate cost。
- 完成后先做完整性审计，不用于方法开发。

## Task 9 — Unseal and primary comparison

- 本地 π2 protocol 冻结后解封。
- 报告 task-level paired difference、task-family breakdown、tokens、latency、费用和 failure census。
- 任一 shared-protocol mismatch 自动降级为 context-only。
