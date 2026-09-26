# Formal Max-10 POST 原生配方契约修复

R2 的60个因果分支完整，独立verifier为 BENEFIT=1 / NEUTRAL=5。原POST建议TRAIN，但返回两个不同种子。旧schema允许，而已有原生trainer要求相同，导致NATIVE_FORMAL_MATCHED_SEEDS_REQUIRED。此包只将既有原生约束完整公开给同一个强POST：共享种子、当前行数可整除的梯度累积、实际步数及warmup界限。所有自由值仍由强模型选择，运行时保留严格校验，不替模型改种子，不放宽训练有效性。

原SEMANTIC_INVALID逻辑调用、原始响应及方法失败分母保留。使用修正契约登记一个新的内容绑定调用，不重发原logical call，无循环语义重试。REGISTERED_POST_CONTRACT_EXECUTION_INDEX.json指向新增POST恢复目录。仅按已冻结计划的60个branch key复制精确终端、按capture index复用原input，保留原计划与独立verifier SHA；Dual-View两行数据原SHA直接复用。原controller看到已存在GPU terminal后只回放验证并执行POST，完全不再提交F0/F1。

修复也应用于后续轮原POST。resident结果读取、Memory、TRAIN读取同一注册执行索引；既有native训练、TRAIN_SELECT OFF/OFF、晋升、记忆和下一轮owner不替换。TRAIN_SELECT严格成功数提升晋升，最终134unseen/140seen保持隔离。Max10及patience/infra预算不变。

VERIFY.py含实际错误回归、当前原生schema/prompt测试和服务器真实POST请求渲染无发送验证。RUN.sh验证后续接已有campaign，使用已加载项目Python；不得启用set -e/-u/pipefail，外接tee后显式读取PIPESTATUS[0]。重复启动由原锁和launch claim拒绝。Git只staging cache，无Git mutation。
