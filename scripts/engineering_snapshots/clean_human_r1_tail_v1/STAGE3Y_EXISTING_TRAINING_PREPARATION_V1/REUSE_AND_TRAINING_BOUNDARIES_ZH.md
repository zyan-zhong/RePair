# 本轮 pi1 训练准备：已完成与未完成

## 已完成的具体工作

从已上传的 corrected F0/F1 完整包中，使用当前固定头的原类型、原候选校验器和原 prompt builder，复核 65 次重复的首个 F0 决策上下文并得到 13 个唯一 source-state/action。调用原 v1.7.2 renderer 的 `build_t2_source_adapter_row` 生成 13 条兼容输入。

这些是新的 clean 本轮数据预览，不是旧 pilot 的 12 条样本。它们全部标为诊断用途、非 verified positive、不可直接 promotion。没有将 F1 修复后的状态配上前一状态的动作，也没有将五个重复当作五条独立训练数据。

## 当前不能跳过的事实

已冻结 Human POST 不建议从当前证据包直接调用 Trainer，并明确要求 T1/T2/T3 或混合方案另有冻结计划。本批 T4/T5 合格数据为零。用户希望训练 pi1 可以通过提出单独的诊断控制臂来研究，但不是既有 POST 自动批准了这种训练，更不是可以把 Neutral 重标为 Benefit。

当前建议的审阅方案为 T0 + 所选 portfolio 的 T2 诊断候选；不称为全 Analyzer 候选库的完整 T2 对照。配方只是草案：一个 pass、seed 17、micro batch 1、gradient accumulation 1，13 个 optimizer steps 由 13 条实际行数推导。训练前必须独立批准；不会直接套用旧 12 行、accumulation 4、3 steps 的预算。

## 已有代码保留

Generic Training Stage V2.1、原 v1.7.2 renderer 函数、原 POST finalizer/comparison、原 F0/F1 验证类型和 artifact index 均复用。不创建第二个 Trainer。旧 materialize-current-t2 wrapper 带有固定 12 行和长度常量，不能直接用于新数据；本准备适配器只复用其下层通用函数。

原 runtime adapter 从已训练的 parent PEFT adapter 加载权重，不能拿 pilot adapter 当 clean pi0。下一处必要实施工作限定为 clean-model initialization/profile 的绑定，并应保留原参数身份和训练回执校验。

## 训练和权威不冒进

脚本会直接读取服务器已生成的 Strong POST 回执，不再次调用 API。自动字段比较不等于科学字段裁决；返回 ACCEPTED 也不等于与 Human 意见一致。最终 Strong 审核包在本响应的本地附件中尚不存在，因此这里没有编造其观点或提前批准训练。

训练准备程序可以正常返回 0，同时保留显式训练阻塞项。它没有生成 optimizer authorization，因此原 Generic Training Stage 无法将这些 preview 误作已授权输入。

尚未完成：正式 POST adjudication、单独 T2 计划批准、train-update/selection 访问身份、clean LoRA 初始化绑定、训练及评测。准备文件不应被宣布为新的 pi1 checkpoint。
