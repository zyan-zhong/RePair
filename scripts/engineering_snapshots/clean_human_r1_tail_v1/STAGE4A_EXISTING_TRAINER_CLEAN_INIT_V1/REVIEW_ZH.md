# 本次已冻结计划核查及推进边界

上传 PLAN_HANDOFF_REVIEW(1).zip 的 SHA-256：
`ec4b2396208f71dad21bc3b2bdb4b29d05a3c2d3ecdf17ab14695a6ac99d8596`。

原始记录：POST adjudication 已冻结，8 ACCEPTED / 2 REVISED / 1 REJECTED；
Training Plan 已冻结，计划 SHA 为
`ac04690c3cf665058b24b2c53af8ed9e35d2fdbb4a5771f771625772edfebb9e`。
TRAIN_UPDATE/SELECT/AUDIT 元数据归属检查通过。当前计划为 T0 加本轮 selected-portfolio
T2 诊断候选，不是完整 Analyzer T2 宇宙，也不是 verified Benefit。

预算原样保留：13 行、13 个唯一 task、176 个监督 loss tokens、1 epoch、seed/data_seed 17、
microbatch=1、accumulation=1、13 optimizer steps，AdamW lr=1e-4、线性调度、warmup=0，
LoRA r16/alpha32/dropout0.05 和原 target modules。I1/RAW 与 Neutral 标签保持不变。

此次唯一实质工作是关闭模型初始化与训练执行绑定：

- 原 base checkpoint 文件哈希清单作为模型字节身份依据；在 clean snapshot 目录核实真实文件。
- 调用原 build_seeded_formal_lora_model，验证两次 seed 初始化一致、B=0、base冻结。
- 在 eval 模式比较一个短数值探针的 adapter-enabled/disabled logits，非任务评测。
- 保存零优化步数的初始化 adapter，再用原 PEFT adapter reload 路径验证其参数哈希。
- 为原 Generic Stage 生成合同和绑定，不覆盖上游合同；新增字段只有初始化证据与运行接线。
- smoke 不创建 optimizer、不执行 optimizer step。原先的计划批准并不授权训练。
- 同一包支持之后的独立训练授权，无需再写 Trainer；没有在此环境运行真实 Qwen/GPU。

发现并处理的旧配置边界：formal_train.verify_formal_schedule 对 pilot effective_batch=4
作了字面断言。运行时仅将该函数接到已经存在的通用预算/样本顺序验证器，并检查实际绑定值一致。
不是删除预算检查，不填充、不丢弃13条数据，不更改原优化循环。

本次保存的初始化 adapter 不是旧 pilot adapter，也不是新 pi1。它只是 clean π0 加上零更新的
seeded LoRA。训练时使用它可以直接复用原有 PeftModel.from_pretrained(is_trainable=True)
及初始参数哈希检查，而不用重新写训练循环。

归档 provenance 仍为 incomplete，诊断候选 promotion_eligible=false；训练后必须评估。
源码固定头与新人工轮已集成内容不修改、不提交、不推送。

交付前还测试了已清理 PYTHONPATH 的独立 worker：先引导固定仓库，再使用原严格 JSON 和
合同校验器，避免登录节点可运行但 Slurm 计算节点导入失败。21项本包测试、40项原训练测试通过。
本地没有加载真实Qwen/PEFT、没有使用GPU/提交Slurm；相关真实检查由 --submit-smoke 完成。
