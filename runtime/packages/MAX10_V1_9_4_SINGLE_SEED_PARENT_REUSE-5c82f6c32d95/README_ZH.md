# Formal Max-10：一个固定配对seed，自动继承父模型评估

使用既定355个TRAIN_SELECT任务与原登记序列第一个seed。逻辑上仍是355对、710条比较结果；父模型355条继承已审计原始证据，候选新增355个模型episode。F0/F1、训练、最终134 unseen/140 seen benchmark不改。旧5seed配置不是丢失科研数据的理由：所有原始回执保留。

本轮R2特别切换：用户询问是否停止4个旧SELECT作业以节约时间，已发现固定seed双方355个任务全部发布。对这710条做原生完整审计后即可复用，无需重新推理。本次coverage amendment明确记录为episode已发布后的覆盖范围变更，不冒称事前冻结；R2保留原严格成功数晋升判据。新终局由原生审计/数值聚合/自动判决产生，其他seed的部分结果保存但不参与此次选择。停止注册旧作业和resident交接有独立记录。

后续父模型缓存由resident在原生round closure验证后自动登记。晋升继承本轮候选评估；回退或NO_TRAINING_UPDATE继续保留同一父模型的物理来源。typed index按请求SHA定位，直接指向terminal/binding/summary，不递归追receipt。权重、任务顺序、固定seed、环境、tokenizer、模板、解码服务、请求契约、episode预算、OFF/OFF必须一致。TRAIN_UPDATE不能替代TRAIN_SELECT。

旧episode按原始condition/runtime/schedule、attempt bundle和publication lock重新审计；不复制或重标为新episode。当前轮写独立REUSE.json，原生数值聚合器比较旧父结果与新候选结果。恢复时验证同一复用记录和源证据，不重发父模型请求。汇总记录parent_reused_cell_count与fresh_model_episode_count。

后续新晋升规则：成功数增加晋升，减少回退；持平时，候选平均终局动态目标条件完成比例严格更高才晋升，否则保留父模型。指标从原始PDDL目标与真实终局计算；静态约束限制合法对象见证而不计分，同一量词保持一致绑定。旧结果无此指标时，自动重放封存动作，逐步核对公开观察、菜单、score/done/won和终局；无策略调用、不改旧结果、不计新科研episode。隐藏目标、事实和逐任务指标不进入模型、训练标签或活跃跨轮记忆。

并行复用登记campaign资源上限（当前8），使用原生单GPU独立SELECT作业；355对分8片，每片44或45对。独立获配，不等待8卡同时到齐。保持原生预算、成对停止边界和有限partial resumption。

VERIFY：包SHA、晋升规则、355目标语义、spawn环境、真实历史cell审计/重放/恢复/篡改拦截、原生finalizer和355对8分片材料化。没有模型请求、Slurm提交或Git操作。当前R2切换的全部710条审计另有证据。

RUN.sh先VERIFY再启动登记resident；不得与旧owner并行。当前部署由受控handoff接管，用户无需重复上传/启动。统一观察入口沿用登记的FORMAL_MAX10_STAGE_STATUS.sh --watch。

operator shell不启用set -e/-u/pipefail；接tee后立即读取rc=${PIPESTATUS[0]}。总账append-only；Git staging cache/delta，没有git add/commit/push。论文补充见PAPER_PROTOCOL_AMENDMENT.md。
