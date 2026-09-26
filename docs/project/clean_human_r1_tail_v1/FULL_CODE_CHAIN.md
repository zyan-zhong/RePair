# Clean Human Reference Round: complete code and data handoff map

Fixed source: `ede426ffb069bd887bd3caf847add8193c801d60` / tree `4460d1dd9b653258906ef0e625e5af7d7edbc338`.
Round: `CLEAN-HUMAN-REFERENCE-R1-PI0`. Parent: `PI0_CLEAN`. Candidate remains diagnostic-only.

## Scope and authority

- This index preserves existing modules, historical snapshots and exact external execution drivers.
- Native module existence, live execution, result approval and autonomous takeover are distinct states.
- The older project baseline JSON contains historical pilot `current_round` metadata. Current execution authority is the frozen clean-round protocol/binding, not that historical label.
- No current SELECT task-level observations, actions or outcomes may be fed to Analyzer/Planner; only the audited aggregate projection may be consumed.
- The companion JSON lists every file hash, Python class/function signature, source lines, imports and syntactic call sites. Dynamic targets are not claimed to be fully resolved.

## Primary end-to-end route

### 1. Round registration, component ports and execution plan

Input: Role-neutral parent/model and frozen data-plane bindings
Output: GenericRoundManifest / BindingRegistry / ExecutionPlan
Authority / boundary: Existing control contracts are reused; no model/environment execution is inferred from contract existence.

- [`src/pchsi/round_control/round_manifest.py`](../../../src/pchsi/round_control/round_manifest.py) — SHA-256 `95e90802447a95878e2fe6a9449926e12943d4ad532a08d09e4142e1036a3712`
  Symbols: `CleanRoundDataPlaneV1` L10–L36, `CleanRoundDataPlaneV1.__post_init__` L15–L29, `CleanRoundDataPlaneV1.to_dict` L31–L36, `GenericRoundManifestV1` L40–L70, `GenericRoundManifestV1.to_dict` L53–L70, `freeze_generic_round_manifest` L73–L125.
- [`src/pchsi/round_control/bindings.py`](../../../src/pchsi/round_control/bindings.py) — SHA-256 `cecc09b39bfd7a4bcd601869b21b0fb7ebe0005df7844462d69765e5cdb61115`
  Symbols: `validate_repo_component_bindings` L63–L106.
- [`src/pchsi/round_control/concrete_bindings.py`](../../../src/pchsi/round_control/concrete_bindings.py) — SHA-256 `874943475ed9874afb058f32aea7ea77cc0d369ba2d3c650a1b58e8c76464b16`
  Symbols: `BindingKindV1` L16–L19, `ConcreteComponentBindingV1` L23–L45, `ConcreteComponentBindingV1.to_dict` L33–L45, `required_concrete_component_ids` L240–L246, `_source_identity` L249–L265, `build_concrete_component_bindings` L268–L307, `binding_map` L310–L321.
- [`src/pchsi/round_control/clean_execution_binding.py`](../../../src/pchsi/round_control/clean_execution_binding.py) — SHA-256 `1b602201ec3228dcbcc1e75c280aea49d15487e39a4955706cc5782006d7ad7a`
  Symbols: `_sha256_file` L13–L18, `_require_sha256` L21–L28, `_regular_file` L31–L35, `_bound_regular_file` L38–L52, `_load_jsonl` L55–L68, `load_clean_train_pool_records` L71–L152, `load_official_benchmark_records` L155–L198, `CleanScheduledEpisodeV1` L202–L207, `bind_stage2c_official_schedule` L210–L265, `build_clean_train_schedule` L268–L302.
- [`src/pchsi/round_control/execution_plan.py`](../../../src/pchsi/round_control/execution_plan.py) — SHA-256 `3fea15a04e737561f3e3d620169eff483ac51965adcd9ab0bdcfd423053bfcb3`
  Symbols: `ComponentExecutionPlanV1` L93–L101, `build_component_execution_plans` L104–L138.

### 2. Clean data / train partition access

Input: ALFWorld TRAIN_UPDATE, TRAIN_SELECT, TRAIN_AUDIT manifest identities
Output: Train-only stage access decisions; disjoint task universe
Authority / boundary: No valid_seen/valid_unseen or old pilot semantic data in the adaptive loop.

- [`src/pchsi/round_control/clean_data_gate.py`](../../../src/pchsi/round_control/clean_data_gate.py) — SHA-256 `01c4650efa0cf58564bfe5fc48281fd8a8c7d4b0a3fd111eb829a39c6d178231`
  Symbols: `CleanSplitV1` L9–L12, `TrainPoolV1` L15–L19, `CleanConsumerV1` L22–L32, `CleanAccessGrantV1` L36–L54, `CleanAccessGrantV1.to_dict` L44–L54, `authorize_clean_access` L77–L133.
- [`src/pchsi/round_control/retention.py`](../../../src/pchsi/round_control/retention.py) — SHA-256 `10851b0998e92692e99ffea54d98fe5a7374ee911635b85bbc642540d7867221`
  Symbols: `ArtifactKindV1` L9–L20, `RetentionDecisionV1` L24–L28, `decide_cross_round_retention` L40–L118.
- [`src/pchsi/evaluation/distillation_access.py`](../../../src/pchsi/evaluation/distillation_access.py) — SHA-256 `a10bdc77bbddc6ee0c49cedc71f62f67bceb7720666df0f64dd8a1e6e2a35901`
  Symbols: `_mapping` L22–L27, `_expect_keys` L30–L36, `_text` L39–L44, `_optional_date` L47–L57, `_sha1` L60–L63, `_tuple_strings` L66–L74, `_wire_string_tuple` L77–L80, `HistoricalAccessFlag` L83–L90, `DistillationAccessClass` L93–L97, `_flags` L100–L120, `_wire_flags` L123–L132, `HistoricalAccessAuditRecordV1` L136–L194, `HistoricalAccessAuditRecordV1.__post_init__` L153–L162, `HistoricalAccessAuditRecordV1.to_dict` L164–L172, `HistoricalAccessAuditRecordV1.from_dict` L175–L194, `HistoricalAccessAuditV1` L198–L287, `HistoricalAccessAuditV1.__post_init__` L220–L251, `HistoricalAccessAuditV1.to_dict` L253–L261, `HistoricalAccessAuditV1.to_json` L263–L264, `HistoricalAccessAuditV1.from_dict` L267–L283, `HistoricalAccessAuditV1.from_json` L286–L287, `TaskAccessRecordV1` L291–L452, `TaskAccessRecordV1.__post_init__` L324–L393, `TaskAccessRecordV1.to_dict` L395–L415, `TaskAccessRecordV1.from_dict` L418–L452, `TaskAccessManifestV1` L456–L560, `TaskAccessManifestV1.__post_init__` L480–L518, `TaskAccessManifestV1.to_dict` L520–L531, `TaskAccessManifestV1.to_json` L533–L534, `TaskAccessManifestV1.from_dict` L537–L556, `TaskAccessManifestV1.from_json` L559–L560.
- [`src/pchsi/evaluation/distillation_governance.py`](../../../src/pchsi/evaluation/distillation_governance.py) — SHA-256 `f9168176e186fee7830054b22f114994159db139672b153423b3c11fd9764209`
  Symbols: `DistillationGovernanceBundleV1` L23–L27, `canonical_model_sha256` L30–L37, `validate_distillation_governance_bundle` L40–L158, `GovernanceFreezeResultV1` L170–L176, `_write_exclusive` L179–L193, `freeze_governance_inputs` L196–L286.

### 3. Policy inference interface and task collection

Input: Frozen parent policy, complete menu, RAW prompt, I1 request schema, seeds and dual budgets
Output: Environment outcomes plus exact policy-call evidence
Authority / boundary: Strict parser and exact menu membership retained. I1 affects generation; it is not unconstrained RAW generation.

- [`src/pchsi/evaluation/episode_evaluator.py`](../../../src/pchsi/evaluation/episode_evaluator.py) — SHA-256 `33c5a7828329e6b7634e588230206cf4f1a71ffea2a461a60f4ae16f9f054a52`
  Symbols: `EpisodeExecutionConfig` L89–L383, `EpisodeExecutionConfig.__post_init__` L121–L383, `EpisodeDependencies` L388–L393, `EpisodeAttemptResult` L397–L405, `_utc_now` L408–L413, `_parse_public_task_goal` L416–L425, `_config_sha256` L428–L483, `_replicate_id` L486–L490, `_provenance` L493–L633, `_started_receipt` L636–L664, `_terminal_receipt` L667–L699, `_budget_snapshot` L702–L711, `_EnvironmentCloseEvidence` L715–L719, `_read_worker_reap_state` L722–L745, `_close_environment` L748–L798, `_write_terminal_best_effort` L801–L810, `_early_result` L813–L856, `run_single_episode` L859–L1441.
- [`src/pchsi/evaluation/raw_policy_prompt.py`](../../../src/pchsi/evaluation/raw_policy_prompt.py) — SHA-256 `076da310cceaf617fd2efdcf1750ddedec2439e2f009205c933e68c992393590`
  Symbols: `InterfaceFeedbackCode` L35–L39, `ExecutedTransition` L58–L62, `_canonical_json` L72–L85, `_validated_transition_tuple` L88–L119, `_memory_m0` L122–L131, `_transition_payload` L134–L151, `canonical_executed_transitions_json` L154–L164, `sha256_executed_transitions` L167–L180, `_feedback_text` L183–L214, `_validated_commands` L217–L237, `build_raw_policy_prompt` L240–L306.
- [`src/pchsi/evaluation/raw_policy_parser.py`](../../../src/pchsi/evaluation/raw_policy_parser.py) — SHA-256 `6d06ed0311a4bd8ea137d296f8d859312ef537ac1a9c1cb835b258143ece8c81`
  Symbols: `ParserStatus` L29–L33, `FailureStage` L36–L40, `ParserFailureCode` L43–L66, `RawPolicyParseResult` L70–L76, `_JsonObject` L80–L83, `_DuplicateMemberError` L86–L87, `_NonStandardConstantError` L90–L91, `_build_object` L98–L115, `_reject_nonstandard_constant` L118–L123, `_failure` L133–L145, `_success` L148–L158, `_contains_forbidden_control_character` L161–L175, `parse_raw_policy_response` L178–L299.
- [`src/pchsi/evaluation/budget.py`](../../../src/pchsi/evaluation/budget.py) — SHA-256 `3381e47beb1b568d7b88460d0a18e1b2aaa370f50d85a7503f1a1a9adc972453`
  Symbols: `BudgetAttemptOutcome` L33–L38, `EpisodeTerminationReason` L41–L57, `_require_nonnegative_integer` L60–L77, `BudgetLimits` L81–L106, `BudgetLimits.__post_init__` L88–L106, `BudgetState` L110–L130, `BudgetState.__post_init__` L119–L130, `_validate_limits` L133–L141, `_validate_state_against_limits` L144–L183, `can_start_policy_attempt` L186–L200, `apply_completed_attempt` L203–L327, `resolve_nonexecuted_termination` L330–L368, `resolve_after_environment` L371–L433.
- [`src/pchsi/evaluation/runtime_core.py`](../../../src/pchsi/evaluation/runtime_core.py) — SHA-256 `96fd04939d751f1e555bf33408fddb6a47f1ff23e05daa097cc14cfdc70db40f`
  Symbols: `AttemptOutcome` L64–L76, `AdmissibilityStatus` L79–L84, `AttemptFailureStage` L87–L93, `RuntimeFailureCode` L96–L104, `MenuFailureCode` L107–L137, `MenuValidationResult` L141–L146, `ProtocolPreconditionResult` L150–L158, `RuntimeDecision` L162–L181, `_require_action_limit` L184–L199, `_freeze_menu` L202–L223, `_contains_forbidden_control_character` L226–L240, `_command_shape_failure` L243–L292, `_invalid_menu` L295–L304, `validate_menu_contract` L307–L401, `validate_runtime_preconditions` L404–L520, `_require_process_precondition` L523–L584, `_validate_processing_menu` L587–L637, `_map_parser_failure_stage` L640–L660, `process_completed_generation` L663–L862, `finalize_environment_result` L865–L942.
- [`src/pchsi/evaluation/policy_execution_profile.py`](../../../src/pchsi/evaluation/policy_execution_profile.py) — SHA-256 `6bdf20389c86513ef084081772139f952610214e566856fd91f3c7fe6138d989`
  Symbols: `PolicyRequestProtocol` L39–L53, `PolicyRequestProtocol.to_wire_dict` L45–L48, `PolicyRequestProtocol.to_wire_bytes` L50–L53, `PolicyExecutionProfileV1` L60–L241, `PolicyExecutionProfileV1.__post_init__` L77–L151, `PolicyExecutionProfileV1.build_request` L153–L241.
- [`src/pchsi/evaluation/interface_isolation_request.py`](../../../src/pchsi/evaluation/interface_isolation_request.py) — SHA-256 `163d8c62e8359afa7efcc2e8032dd018d67e4b30f0facbe413c1fc697188d38b`
  Symbols: `_deep_thaw` L33–L42, `i1_structured_serialization_schema_dict` L65–L71, `I1StructuredPolicyRequestV1` L80–L112, `I1StructuredPolicyRequestV1.__post_init__` L87–L92, `I1StructuredPolicyRequestV1.to_wire_dict` L94–L109, `I1StructuredPolicyRequestV1.to_wire_bytes` L111–L112, `_freeze_i2_admissible_commands` L116–L154, `i2_admissible_action_schema_dict` L157–L175, `i2_admissible_action_schema_sha256` L178–L189, `I2AdmissiblePolicyRequestV1` L193–L236, `I2AdmissiblePolicyRequestV1.__post_init__` L201–L214, `I2AdmissiblePolicyRequestV1.to_wire_dict` L216–L233, `I2AdmissiblePolicyRequestV1.to_wire_bytes` L235–L236.

### 4. Environment worker and attempt publication

Input: Registered gamefile / environment runtime; policy output
Output: Public transitions; no-clobber attempt bundle, lock and attempt receipts
Authority / boundary: Environment failures and scientific task failures remain distinct.

- [`src/pchsi/evaluation/alfworld_adapter.py`](../../../src/pchsi/evaluation/alfworld_adapter.py) — SHA-256 `5d836fbcffbc774fd5a9bc7405aa84c08edd59a7074b4d020b0d6bb456c0c163`
  Symbols: `WorkerAdapterError` L13–L13, `WorkerTimeoutError` L14–L14, `WorkerExitedError` L15–L15, `WorkerProtocolError` L16–L16, `_get_spawn_context` L17–L17, `_positive` L19–L21, `WorkerTimeouts` L23–L26, `WorkerTimeouts.__post_init__` L25–L26, `SpawnedAlfworldAdapter` L28–L123, `SpawnedAlfworldAdapter.__init__` L29–L30, `SpawnedAlfworldAdapter.start` L32–L50, `SpawnedAlfworldAdapter.exact_gamefile` L52–L52, `SpawnedAlfworldAdapter.process_start_method` L54–L54, `SpawnedAlfworldAdapter.worker_pid` L56–L56, `SpawnedAlfworldAdapter.worker_alive` L58–L58, `SpawnedAlfworldAdapter.process_exitcode` L60–L60, `SpawnedAlfworldAdapter.close_request_sent` L62–L62, `SpawnedAlfworldAdapter._receive` L63–L73, `SpawnedAlfworldAdapter._join_if_exited` L74–L76, `SpawnedAlfworldAdapter._wait_join` L77–L77, `SpawnedAlfworldAdapter._abort_worker` L78–L84, `SpawnedAlfworldAdapter._send` L85–L90, `SpawnedAlfworldAdapter.reset` L91–L96, `SpawnedAlfworldAdapter.step` L97–L106, `SpawnedAlfworldAdapter.close` L107–L123.
- [`src/pchsi/evaluation/artifact_publisher.py`](../../../src/pchsi/evaluation/artifact_publisher.py) — SHA-256 `cd329e5b619b66963f413ad3bc81626d8abb03ec0677f31b3677d76b3cf53f93`
  Symbols: `PublicationFaultPoint` L19–L31, `InjectedPublicationFault` L34–L35, `PublicationRecoveryStatus` L38–L43, `PublicationRecoveryResult` L47–L49, `_ensure_directory` L56–L64, `_write_all` L67–L73, `_write_file_no_clobber` L76–L91, `_fsync_file` L94–L102, `_fsync_directory` L105–L115, `_rename_directory_native_noreplace` L127–L165, `_rename_directory_guarded_posix` L168–L193, `_rename_directory_no_clobber` L196–L225, `_receipt_filename` L228–L234, `ArtifactPublisher` L237–L622, `ArtifactPublisher.__init__` L238–L266, `ArtifactPublisher._fault` L268–L270, `ArtifactPublisher.write_started_receipt` L272–L290, `ArtifactPublisher.stage_bundle` L292–L336, `ArtifactPublisher.write_scientific_cell_lock` L338–L359, `ArtifactPublisher.publish_staged_directory` L361–L417, `ArtifactPublisher.write_terminal_receipt` L419–L436, `ArtifactPublisher._validate_bundle_directory` L438–L465, `ArtifactPublisher._validate_disk_lock` L467–L486, `ArtifactPublisher.recover_publication` L488–L547, `ArtifactPublisher._validate_inputs` L549–L591, `ArtifactPublisher.publish_scientific_attempt` L593–L622.
- [`src/pchsi/evaluation/episode_artifact.py`](../../../src/pchsi/evaluation/episode_artifact.py) — SHA-256 `9ec17c00505e220b13ff73c52ba5650234b0c8a311204083b8f642594e7669ad`
  Symbols: `AttemptBundleBytes` L14–L25, `AttemptBundleBytes.file_bytes` L22–L25, `_freeze_traces` L27–L32, `_freeze_policy_calls` L34–L40, `_freeze_transitions` L42–L48, `_semantic_trace` L50–L53, `_semantic_episode` L55–L58, `_semantic_transition` L60–L63, `_semantic_projection` L65–L73, `_validate_counts` L75–L80, `_jsonl_action_traces` L82–L82, `_jsonl_schema_models` L83–L84, `_checksum_text` L85–L85, `_bundle_identity` L86–L86, `build_attempt_bundle_bytes` L88–L100.
- [`src/pchsi/evaluation/schema_models.py`](../../../src/pchsi/evaluation/schema_models.py) — SHA-256 `004d4b42ef3dd9dec59c28111e3cc32b837c0e22cd4487f32a8925ed0eea6b27`
  Symbols: `_require_mapping` L17–L22, `_expect_keys` L25–L39, `_tuple_of_strings` L42–L47, `_tuple_of_ints` L50–L55, `_SchemaModel` L58–L80, `_SchemaModel.to_dict` L62–L63, `_SchemaModel.to_json` L65–L66, `_SchemaModel.from_json` L69–L70, `_SchemaModel.from_dict` L73–L74, `_SchemaModel._validate` L76–L80, `BudgetSnapshotV1` L84–L130, `BudgetSnapshotV1.__post_init__` L99–L105, `BudgetSnapshotV1.to_dict` L107–L116, `BudgetSnapshotV1.from_dict` L119–L130, `RunScheduleCellV1` L134–L176, `RunScheduleCellV1.__post_init__` L147–L157, `RunScheduleCellV1.to_dict` L159–L165, `RunScheduleCellV1.from_dict` L168–L176, `PublicTransitionRecordV1` L180–L305, `PublicTransitionRecordV1.__post_init__` L227–L228, `PublicTransitionRecordV1.to_dict` L230–L264, `PublicTransitionRecordV1.from_dict` L267–L305, `AttemptReceiptV1` L309–L384, `AttemptReceiptV1.__post_init__` L352–L353, `AttemptReceiptV1.to_dict` L355–L378, `AttemptReceiptV1.from_dict` L381–L384, `ScientificCellLockV1` L388–L439, `ScientificCellLockV1.__post_init__` L415–L416, `ScientificCellLockV1.to_dict` L418–L433, `ScientificCellLockV1.from_dict` L436–L439, `EpisodeArtifactV1` L443–L760, `EpisodeArtifactV1.__post_init__` L552–L702, `EpisodeArtifactV1.to_dict` L704–L721, `EpisodeArtifactV1.from_dict` L724–L760, `RunScheduleV1` L764–L858, `RunScheduleV1.__post_init__` L793–L801, `RunScheduleV1.to_dict` L803–L825, `RunScheduleV1.from_dict` L828–L858.
- [`src/pchsi/evaluation/policy_call_evidence.py`](../../../src/pchsi/evaluation/policy_call_evidence.py) — SHA-256 `96ec73c9a7bbcb8419b35a052a09f47ce731b8dbff89b85cfed6569ceaeeb867`
  Symbols: `allowlisted_response_headers` L12–L15, `PolicyCallTransportEvidenceV1` L18–L33, `PolicyCallTransportEvidenceV1.__post_init__` L24–L32, `PolicyCallTransportEvidenceV1.headers_dict` L33–L33, `PolicyCallResultV1` L36–L38, `PolicyCallEvidenceV1` L41–L134, `PolicyCallEvidenceV1.__post_init__` L50–L101, `PolicyCallEvidenceV1.request_wire_bytes` L103–L103, `PolicyCallEvidenceV1.raw_response_body` L105–L105, `PolicyCallEvidenceV1.to_dict` L106–L114, `PolicyCallEvidenceV1.to_json` L115–L115, `PolicyCallEvidenceV1.from_dict` L117–L131, `PolicyCallEvidenceV1.from_json` L133–L134, `exact_policy_call_payload` L136–L136, `semantic_policy_call_payload` L138–L142, `build_policy_call_evidence` L145–L166.

### 5. Mechanical and clean Analyzer evidence

Input: Frozen train-side episode and full traces
Output: Evidence Pack / mechanical event facts / current clean policy binding
Authority / boundary: Facts reconstructed by code; hypotheses do not overwrite environmental evidence.

- [`src/pchsi/reference_loop/bundle_reader.py`](../../../src/pchsi/reference_loop/bundle_reader.py) — SHA-256 `043b59c956eb8c46b03dbfdc1ba9113eb605956f9b55aa2c61abeb73c58d1180`
  Symbols: `_parse_checksum_manifest` L31–L60, `_jsonl_lines` L63–L71, `_load_action_trace` L74–L172, `_normalize_policy_call` L175–L191, `_normalize_trace` L194–L244, `_normalize_transition` L247–L261, `_validate_alignment` L264–L401, `validate_attempt_bundle` L404–L523.
- [`src/pchsi/reference_loop/clean_analyzer_evidence.py`](../../../src/pchsi/reference_loop/clean_analyzer_evidence.py) — SHA-256 `7b5bf22b7ea9984c4a0a994635a6558042274d7631a4d3b05f04947d55d26dcd`
  Symbols: `_require_sha256` L12–L19, `_require_schema` L22–L24, `build_pi0_i1_analyzer_policy_identity` L27–L109, `build_clean_current_trajectory_binding` L112–L222, `build_clean_analyzer_evidence_pack` L225–L347, `write_clean_analyzer_evidence_pack` L350–L365.
- [`src/pchsi/reference_loop/analyzer_evidence_pack.py`](../../../src/pchsi/reference_loop/analyzer_evidence_pack.py) — SHA-256 `ab77511f6a79898a9d7a393710b174f293e2deff44f0fde5ba54ff21f2425930`
  Symbols: `_transition_by_model_call` L10–L18, `build_analyzer_evidence_pack` L21–L188, `write_analyzer_evidence_pack` L191–L208.
- [`src/pchsi/reference_loop/mechanical.py`](../../../src/pchsi/reference_loop/mechanical.py) — SHA-256 `2f63163b41159038c9512acd56d2bd51be06fe70494f6205f20ce5c598a4d0bb`
  Symbols: `_max_run` L20–L31, `_first_and_last_true` L34–L38, `extract_mechanical_episode_evidence` L41–L188, `extract_mechanical_episode_evidence_file` L191–L198.
- [`src/pchsi/reference_loop/alfworld_events.py`](../../../src/pchsi/reference_loop/alfworld_events.py) — SHA-256 `5d3cc272965da17adaeb58714e115529686241153d0e652983b8233c9cf4e695`
  Symbols: `_source_family` L27–L28, `_effective` L31–L44, `_goal_object` L47–L68, `_object_matches` L71–L79, `extract_alfworld_event_facts` L82–L222, `extract_alfworld_event_facts.revisit_count` L160–L168.

### 6. Adaptive analysis budget and source input materialization

Input: Round resource cap + eligible complete failure universe
Output: Deterministic local input registry and count
Authority / boundary: Counts derived from frozen budget and evidence; no Analyzer-controlled denominator.

- [`src/pchsi/round_control/clean_analyzer_input_materialization.py`](../../../src/pchsi/round_control/clean_analyzer_input_materialization.py) — SHA-256 `225a1548e6b03cbcdac11a6152863f9c6683b545b8886d176107c8792ac07758`
  Symbols: `_nonempty_text` L33–L36, `_sha256` L39–L46, `_positive_int` L49–L52, `_validate_hash` L55–L66, `build_round_analyzer_resource_budget` L69–L164, `validate_round_analyzer_resource_budget` L167–L245, `_failure_order_score` L248–L262, `select_failure_only_u_reg` L265–L345, `build_local_u_reg_manifest` L348–L446, `build_clean_analyzer_task_access_record` L449–L487, `build_actor_input_binding` L490–L524.
- [`src/pchsi/round_control/clean_role_actor_binding.py`](../../../src/pchsi/round_control/clean_role_actor_binding.py) — SHA-256 `5cacb0ad65cd82e371f6efddf762ffaa05b194a0f8591368df80bb0857b39154`
  Symbols: `CleanRoleActorBindingV1` L8–L15, `human_primary_strong_shadow_bindings` L18–L106.
- [`src/pchsi/round_control/analyzer_substage.py`](../../../src/pchsi/round_control/analyzer_substage.py) — SHA-256 `32f79122a13d757948d3a47fb3741f74f233cc160a06a0976a51398b6be9fc64`
  Symbols: `AnalyzerSubstageV1` L21–L28, `AnalyzerPipelineStateV1` L61–L137, `AnalyzerPipelineStateV1.from_frozen_receipt` L70–L104, `AnalyzerPipelineStateV1.advance` L106–L125, `AnalyzerPipelineStateV1.to_dict` L127–L137, `AnalyzerSubstageActionV1` L141–L149, `next_analyzer_substage_action` L152–L197, `future_nonhuman_phases_are_automatic` L200–L232.
- [`src/pchsi/analyzer/analysis_budget.py`](../../../src/pchsi/analyzer/analysis_budget.py) — SHA-256 `9839d6049cdf329bf371be4e08b30447d65a9d8966441a0be2b4a43e6487d1d0`
- [`src/pchsi/analyzer/analysis_sampling.py`](../../../src/pchsi/analyzer/analysis_sampling.py) — SHA-256 `e9103859629b865c27bc29658ddbcbe165974fc9eaf9f55bb203081caa9e251b`
  Symbols: `AnalysisUnit` L23–L34, `MechanicalPolicySignals` L38–L46, `MechanicalPolicySignals.validate` L43–L46, `default_manifest_path` L49–L53, `load_sampling_approval` L56–L84, `_family_rates` L87–L93, `select_analysis_regime` L96–L126, `_largest_remainder` L129–L144, `_family_order_key` L147–L152, `allocate_analysis_sampling` L155–L285, `validate_sampling_allocation` L288–L313.
- [`src/pchsi/analyzer/outcome_router.py`](../../../src/pchsi/analyzer/outcome_router.py) — SHA-256 `c90e2c258e82aeb8a67c2934727381fe4b7b35ca9740bfb1427be146359ad772`
  Symbols: `_require_mapping` L20–L23, `_pack_incidents` L26–L88, `validate_route_semantics` L91–L120, `route_episode` L123–L199, `build_mechanical_census` L202–L287, `validate_census_semantics` L290–L311.

### 7. Local error lifecycle / A0-A1

Input: Same authorized train episode; Memory OFF
Output: Local error instances / principal proposal or abstention
Authority / boundary: No causal Benefit authority; complete trace boundaries preserved.

- [`src/pchsi/analyzer/local_results.py`](../../../src/pchsi/analyzer/local_results.py) — SHA-256 `855e4f17c25f074271d8916e51ff36431b95b571b356036b687ad9bab5af7e57`
  Symbols: `EvidenceReferenceResolver` L26–L27, `EvidenceReferenceResolver.resolve` L27–L27, `EvidencePackReferenceResolver` L31–L97, `EvidencePackReferenceResolver.from_pack` L38–L70, `EvidencePackReferenceResolver.from_pack.walk` L53–L61, `EvidencePackReferenceResolver.resolve` L72–L97, `_keys` L100–L107, `_refs` L110–L116, `_trajectory` L119–L128, `_hash_without` L131–L134, `finalize_local_result` L137–L146, `validate_local_result` L149–L351.
- [`src/pchsi/analyzer/authorities.py`](../../../src/pchsi/analyzer/authorities.py) — SHA-256 `2e4d50f7cf9608da4f1dec372f7c7d60726933a4cff780e1e55cdf146d33c8c4`
  Symbols: `AnalyzerAuthority` L10–L18, `AnalyzerCondition` L28–L32, `TrajectoryOutcome` L41–L43, `OutcomeRouteStatus` L46–L50, `AnalysisObjective` L53–L55, `AnalysisRegime` L58–L61, `AnalysisSchedulerRole` L64–L66, `ScientificUse` L69–L75, `AnalysisTimeInformationBoundary` L78–L79, `RepairKind` L82–L85, `CandidateStatus` L88–L95, `ErrorLifecycleStatus` L98–L102, `TerminalFootprint` L105–L109, `CrosscheckDisposition` L112–L116, `canonical_analyzer_identity` L119–L130.
- [`scripts/analyzer/freeze_human_analyzer_primary_v1.py`](../../../scripts/analyzer/freeze_human_analyzer_primary_v1.py) — SHA-256 `8a5e099c466f4d961c7ca10d9b68a3baf883a11fc35cbc5e72d5d84811838513`
  Symbols: `_require_sha256` L18–L25, `freeze_human_analyzer_primary` L28–L96, `main` L99–L124.
- [`src/pchsi/cognitive_runtime/projections.py`](../../../src/pchsi/cognitive_runtime/projections.py) — SHA-256 `1dcd5ac80e7a9456b9967491508d66b1a7478a02f4d061251114685ca85cd6ae`
  Symbols: `load_object` L8–L11, `_artifact_sha` L14–L18, `_catalog_ref` L21–L28, `evidence_reference_catalog` L31–L75, `local_repair_contract` L78–L100, `local_projection` L103–L111, `group_projection` L114–L122, `group_projection_v2` L125–L179, `component_projection` L182–L185, `crosscheck_projection` L188–L194, `_x_manifest_sha` L198–L206, `crosscheck_projection_v2` L209–L335, `_valid_sha256_text` L337–L342, `_typed_evidence_artifact_sha256s` L345–L392, `_typed_evidence_artifact_sha256s.add_refs` L353–L370, `canonical_group_current_evidence_sha256s` L395–L441, `group_projection_v3` L444–L472.
- [`src/pchsi/cognitive_runtime/request_renderer.py`](../../../src/pchsi/cognitive_runtime/request_renderer.py) — SHA-256 `27eb63847ab827b98290ce102d02850650cefc0dc2b3ae74681a5d51645125b9`
  Symbols: `_repo_root` L27–L28, `_assert_projection` L31–L96, `_assert_projection.valid_sha` L41–L49, `_local_selector_allowlist` L99–L137, `_specialize_local_selector_enums` L140–L200, `_specialize_local_selector_enums.walk` L146–L188, `_specialize_component_taxonomy_enums` L203–L248, `_specialize_component_taxonomy_enums.copy_json` L210–L218, `render_stage_request` L251–L303.
- [`src/pchsi/cognitive_runtime/output_validation.py`](../../../src/pchsi/cognitive_runtime/output_validation.py) — SHA-256 `50a279c0507d0b0e1d4c0599dbe0fc48e49df3ba50dbc25b82affefc70bf074f`
  Symbols: `_object` L9–L12, `_finalize_group_v2` L15–L132, `_finalize_crosscheck_v2` L135–L258, `_finalize_crosscheck_v2.sha_set` L210–L220, `validate_stage_output` L260–L286.

### 8. Deterministic cross-trajectory groups / A2-A3

Input: Exact accepted A1 bytes + mechanical grouping; optional historical Memory pack
Output: Source-conditioned grouped hypotheses and candidate repairs
Authority / boundary: A2 and A3 differ only by registered Memory exposure; K and member lineage retained.

- [`src/pchsi/analyzer/grouping.py`](../../../src/pchsi/analyzer/grouping.py) — SHA-256 `6a06553020931bc9bf4eccaa7ec22a4e2deb64dfa387ddd7159cf3277bf1dabd`
  Symbols: `_hash` L9–L10, `build_group_manifests` L13–L79, `build_group_synthesis_inputs` L82–L129, `finalize_source_conditioned_proposal` L132–L153.
- [`src/pchsi/analyzer/state_candidate_budget.py`](../../../src/pchsi/analyzer/state_candidate_budget.py) — SHA-256 `dfe92fad48721eab6a53bea5f17eebe593b727af6a95e27c47528167c55a66c0`
  Symbols: `_sha64` L23–L30, `execution_semantics_payload` L33–L77, `execution_identity_sha256` L80–L84, `deduplicate_execution_equivalent` L87–L96, `_candidate_sha` L99–L101, `materialize_state_condition_k1` L104–L196.
- [`src/pchsi/analyzer/act3_registration.py`](../../../src/pchsi/analyzer/act3_registration.py) — SHA-256 `81b69613e3666be06820570a739effc8e422462ffa0d7d92b14b0b2b793f9046`
  Symbols: `_domain_sha` L16–L17, `_error_hypothesis_ids` L20–L28, `linked_repairs` L31–L49, `select_dev_source_call` L52–L78, `_first_seen_pattern` L81–L88, `build_group_signature_binding` L91–L228, `build_group_signature_binding.delta` L116–L121, `build_exact_source_registration` L231–L308.
- [`src/pchsi/round_control/clean_group_analyzer_binding.py`](../../../src/pchsi/round_control/clean_group_analyzer_binding.py) — SHA-256 `fb60c48bb4af04938aa7bad3aee5182b254e26eae9bab27ca05f6f11add04a89`
  Symbols: `_text` L36–L43, `_sha` L46–L53, `_positive_int` L56–L59, `_verify_single_source_access` L62–L84, `build_clean_group_task_access_record` L87–L228, `build_group_universe` L231–L261, `build_round_group_analyzer_resource_authority` L264–L373, `validate_round_group_analyzer_resource_authority` L376–L483.

### 9. Component, policy profile and independent cross-check / C-P-X

Input: Group hypotheses / current evidence / admissible historical evidence
Output: Component attribution; deterministic policy profile; challenge results
Authority / boundary: Challenge may reject/downgrade; cannot rewrite environment truth or secretly replace repairs.

- [`src/pchsi/analyzer/component_attribution.py`](../../../src/pchsi/analyzer/component_attribution.py) — SHA-256 `d969519f3add50a75bb7a21ac95e8e1197a1c8a7ea756f3c1b1072cd40a26540`
  Symbols: `load_taxonomy` L11–L14, `_validate_group_result` L17–L24, `finalize_component_attribution` L27–L57, `aggregate_capability_profile` L60–L105, `build_policy_behavior_profile` L108–L135.
- [`src/pchsi/analyzer/capability_profile.py`](../../../src/pchsi/analyzer/capability_profile.py) — SHA-256 `36ada6b6066ae54e2049d16e2203bbc22ffd7dedda2a47014da4c0fa5ad3cb2a`
- [`src/pchsi/analyzer/crosscheck.py`](../../../src/pchsi/analyzer/crosscheck.py) — SHA-256 `ffc1b75f30152bfc5653fbe28a7a3f1ffe92539ccbfb1e12551a4aa00041c892`
  Symbols: `_validate_source_balance` L11–L15, `finalize_crosscheck` L18–L29, `validate_crosscheck` L32–L41, `apply_crosscheck_disposition` L44–L59.
- [`src/pchsi/analyzer/candidate_projector.py`](../../../src/pchsi/analyzer/candidate_projector.py) — SHA-256 `a0a4419fda674bb9b3fa40ea70518502afae3d4d6d765cc6c99ceea82d9bb1eb`
  Symbols: `_validate_proposal` L17–L35, `project_candidate` L38–L96.

### 10. Strong cognitive runtime

Input: Typed actor manifest + stage projection + fixed output schema
Output: Exact requests/responses / validated result / censored attempt ledger
Authority / boundary: Original P2 transport adapter reused. No hidden conversation state or retry after ambiguous send.

- [`src/pchsi/cognitive_runtime/manifest.py`](../../../src/pchsi/cognitive_runtime/manifest.py) — SHA-256 `a3e0719cee006d6a8a3b776fe8fca276f75eabddd45c8ce7545482b8f1a7ea17`
  Symbols: `manifest_path` L6–L7, `load_runtime_manifest` L10–L28, `stage_spec` L31–L36.
- [`src/pchsi/cognitive_runtime/p2_assets.py`](../../../src/pchsi/cognitive_runtime/p2_assets.py) — SHA-256 `fb6da4c25a74695d3473d07abb69754917d738bb14c2805a37048a828ab4ec91`
  Symbols: `config_path` L28–L32, `binding_config` L35–L50, `_matches_exact_binding` L53–L72, `locate_p2_root` L75–L93, `verify_httpx_runtime` L96–L104, `audit_p2_assets` L107–L146.
- [`src/pchsi/cognitive_runtime/p2_bridge.py`](../../../src/pchsi/cognitive_runtime/p2_bridge.py) — SHA-256 `d8f768569ea02083594c31460ca92b5c64b2fac82b5aa2f4f87b5a058b969e5f`
  Symbols: `P2TransportResult` L22–L26, `P2TransportError` L29–L60, `P2TransportError.__init__` L30–L60, `_load_source_module` L63–L93, `_load_transport_module` L97–L116, `_validated_transport_callable` L119–L137, `inspect_bridge` L140–L161, `_error` L164–L192, `_configuration_error` L195–L206, `execute_via_existing_p2` L209–L445.
- [`src/pchsi/cognitive_runtime/orchestrator.py`](../../../src/pchsi/cognitive_runtime/orchestrator.py) — SHA-256 `ed44d301bb32fb6ff7fd60da1629f2569d3d9d10bdf703a3da491bb40ee692bd`
  Symbols: `_write_logical_call` L32–L64, `_transport_meta` L67–L85, `execute_one` L88–L380.
- [`src/pchsi/cognitive_runtime/ledger.py`](../../../src/pchsi/cognitive_runtime/ledger.py) — SHA-256 `4e24f4b22b641dacd67116a2417ad9a085124ce571b49df1e735edd1855ddb38`
  Symbols: `create_call_directory` L8–L11, `record_rendered_request` L14–L15, `record_raw_request` L18–L22, `record_raw_response` L25–L29, `monotonic_ms` L32–L33.
- [`src/pchsi/cognitive_runtime/formal_registry_v2.py`](../../../src/pchsi/cognitive_runtime/formal_registry_v2.py) — SHA-256 `6091e95827bdeb19d02eda872b7d1b79c5170fdb857f82390363da42d377a403`
  Symbols: `validate_formal_dag_v2` L12–L162.
- [`src/pchsi/cognitive_runtime/response.py`](../../../src/pchsi/cognitive_runtime/response.py) — SHA-256 `2e8b1effabbeac262402ee004ed6792ef5355e657654b42eadb0aa3976d76694`
  Symbols: `ProviderResponseError` L8–L20, `ProviderResponseError.__init__` L9–L20, `parse_provider_response` L23–L32, `_extract_payload` L35–L75, `extract_output_text` L78–L118, `usage_summary` L121–L137.

### 11. Procedural Failure Experience and role-specific retrieval

Input: Clean train experience, Analyzer hypotheses, frozen effect status
Output: Governed Memory records; Policy/Analyzer/Researcher projections
Authority / boundary: Memory is evidence storage and retrieval, not a separate semantic reasoning model.

- [`src/pchsi/memory/sequence_failure_experience.py`](../../../src/pchsi/memory/sequence_failure_experience.py) — SHA-256 `b949b83c10ecbb0bf521431fec5d32b363c46847c9bb487fb47514097f3dad58`
  Symbols: `_require_text` L53–L79, `_require_lower_sha256` L82–L104, `_require_nonnegative_int` L107–L121, `_expect_exact_keys` L124–L148, `SequenceSourceTaskAccessBindingV1` L155–L432, `SequenceSourceTaskAccessBindingV1.__post_init__` L207–L319, `SequenceSourceTaskAccessBindingV1.to_dict` L321–L361, `SequenceSourceTaskAccessBindingV1.from_dict` L364–L432, `SourceRecordPointerV1` L439–L552, `SourceRecordPointerV1.__post_init__` L458–L488, `SourceRecordPointerV1.to_dict` L490–L505, `SourceRecordPointerV1.from_dict` L508–L552, `RegisteredFailureSequenceWindowV1` L559–L981, `RegisteredFailureSequenceWindowV1.__post_init__` L646–L820, `RegisteredFailureSequenceWindowV1.to_dict` L822–L888, `RegisteredFailureSequenceWindowV1.from_dict` L891–L981, `_task2_require_optional_text` L1023–L1026, `_task2_require_bool_or_none` L1029–L1034, `_task2_require_finite_or_none` L1037–L1044, `_task2_require_string_tuple` L1047–L1050, `_task2_require_int_tuple` L1053–L1059, `_task2_budget_to_dict` L1062–L1075, `_task2_budget_from_dict` L1078–L1099, `_task2_optional_budget_from_dict` L1102–L1105, `_task2_pointer_from_wire` L1108–L1109, `_task2_pointer_to_wire` L1112–L1117, `SequenceFailureEventV1` L1121–L1417, `SequenceFailureEventV1.__post_init__` L1204–L1302, `SequenceFailureEventV1.to_dict` L1304–L1356, `SequenceFailureEventV1.from_dict` L1359–L1417, `SequenceFailureRelevantStartV1` L1421–L1537, `SequenceFailureRelevantStartV1.__post_init__` L1452–L1484, `SequenceFailureRelevantStartV1.to_dict` L1486–L1506, `SequenceFailureRelevantStartV1.from_dict` L1509–L1537, `SequenceFailureObservedEndV1` L1541–L1616, `SequenceFailureObservedEndV1.__post_init__` L1564–L1588, `SequenceFailureObservedEndV1.to_dict` L1590–L1600, `SequenceFailureObservedEndV1.from_dict` L1603–L1616, `SequenceFailureExperienceV1` L1620–L1820, `SequenceFailureExperienceV1.__post_init__` L1659–L1726, `SequenceFailureExperienceV1._payload_without_experience_id` L1728–L1731, `SequenceFailureExperienceV1._computed_experience_id` L1733–L1738, `SequenceFailureExperienceV1.to_dict` L1740–L1761, `SequenceFailureExperienceV1.canonical_bytes` L1763–L1764, `SequenceFailureExperienceV1.to_json` L1766–L1767, `SequenceFailureExperienceV1.from_dict` L1770–L1816, `SequenceFailureExperienceV1.from_json` L1819–L1820, `SequenceSourceEvidenceV1` L1850–L1888, `SequenceSourceEvidenceV1.__post_init__` L1861–L1888, `_task3_budget_from_trace_before` L1891–L1907, `_task3_episode_final_budget` L1910–L1920, `_task3_bundle_member_bytes` L1923–L1930, `source_record_pointer_from_bundle_v1` L1933–L1959, `_task3_validate_policy_trace_pair` L1962–L1994, `_task3_validate_task_access_record` L1997–L2019, `validate_sequence_source_evidence_v1` L2022–L2109, `_task4_trace_budget_after` L2116–L2132, `_task4_transition_for_trace` L2135–L2152, `_task4_visible_change` L2155–L2177, `_task4_event` L2180–L2265, `build_sequence_failure_experience_v1` L2268–L2369.
- [`src/pchsi/memory/procedural_record.py`](../../../src/pchsi/memory/procedural_record.py) — SHA-256 `92102adbf41569553b9190d953cbe93ce7154725d36e79735ff22513d446e6d0`
  Symbols: `_expect_exact_keys` L29–L45, `_require_text` L48–L53, `_require_sha256` L56–L59, `_require_positive_version` L62–L65, `MemoryAuthorityTypeV1` L68–L74, `MemoryEvidenceRefV1` L78–L111, `MemoryEvidenceRefV1.__post_init__` L87–L91, `MemoryEvidenceRefV1.to_dict` L93–L98, `MemoryEvidenceRefV1.from_dict` L101–L111, `FactualSequenceBindingV1` L115–L198, `FactualSequenceBindingV1.__post_init__` L134–L144, `FactualSequenceBindingV1.from_experience` L147–L162, `FactualSequenceBindingV1.validate_against` L164–L170, `FactualSequenceBindingV1.to_dict` L172–L180, `FactualSequenceBindingV1.from_dict` L183–L198, `AssemblyRegistrationBindingV1` L202–L264, `AssemblyRegistrationBindingV1.__post_init__` L217–L238, `AssemblyRegistrationBindingV1.to_dict` L240–L246, `AssemblyRegistrationBindingV1.from_dict` L249–L264, `PreviousProceduralRecordBindingV1` L268–L307, `PreviousProceduralRecordBindingV1.__post_init__` L281–L287, `PreviousProceduralRecordBindingV1.to_dict` L289–L294, `PreviousProceduralRecordBindingV1.from_dict` L297–L307, `ProceduralMemoryLineageV1` L311–L370, `ProceduralMemoryLineageV1.__post_init__` L324–L339, `ProceduralMemoryLineageV1.to_dict` L341–L350, `ProceduralMemoryLineageV1.from_dict` L353–L370, `ProceduralMemoryProvenanceV1` L374–L457, `ProceduralMemoryProvenanceV1.__post_init__` L391–L417, `ProceduralMemoryProvenanceV1.to_dict` L419–L430, `ProceduralMemoryProvenanceV1.from_dict` L433–L457, `record_id_for_lineage_version_v1` L460–L473, `canonical_payload_sha256_v1` L476–L477.
- [`src/pchsi/memory/procedural_builder.py`](../../../src/pchsi/memory/procedural_builder.py) — SHA-256 `845f6dc391fc019aeb00f26d7b7a5cb78d1e93b024312bb2bffe32068da09f3b`
  Symbols: `_expect_exact_keys` L40–L54, `_require_text` L57–L62, `_sha` L65–L66, `ProceduralMemoryAssemblyInputV1` L70–L245, `ProceduralMemoryAssemblyInputV1.__post_init__` L103–L161, `ProceduralMemoryAssemblyInputV1.__post_init__.require_unique` L138–L140, `ProceduralMemoryAssemblyInputV1.to_dict` L163–L186, `ProceduralMemoryAssemblyInputV1.canonical_bytes` L188–L189, `ProceduralMemoryAssemblyInputV1.from_dict` L192–L238, `ProceduralMemoryAssemblyInputV1.from_dict.parse_list` L199–L203, `ProceduralMemoryAssemblyInputV1.from_json` L241–L245, `ProceduralFailureMemoryRecordV1` L249–L514, `ProceduralFailureMemoryRecordV1.__post_init__` L286–L375, `ProceduralFailureMemoryRecordV1._content_payload` L377–L393, `ProceduralFailureMemoryRecordV1._computed_content_sha256` L395–L400, `ProceduralFailureMemoryRecordV1._payload_without_canonical_record_sha256` L402–L428, `ProceduralFailureMemoryRecordV1._computed_canonical_record_sha256` L430–L437, `ProceduralFailureMemoryRecordV1.to_dict` L439–L442, `ProceduralFailureMemoryRecordV1.canonical_bytes` L444–L445, `ProceduralFailureMemoryRecordV1.to_json` L447–L448, `ProceduralFailureMemoryRecordV1.from_dict` L451–L507, `ProceduralFailureMemoryRecordV1.from_dict.parse_list` L458–L462, `ProceduralFailureMemoryRecordV1.from_json` L510–L514, `_validate_source_experiences` L517–L536, `_validate_previous_record` L539–L565, `_validate_recovery_bindings` L568–L587, `build_procedural_failure_memory_record_v1` L590–L664.
- [`src/pchsi/memory/consumer_views.py`](../../../src/pchsi/memory/consumer_views.py) — SHA-256 `78bc0275984fa369d22934d829bc74c47b9bfca2bfb765e23680f8652000777a`
  Symbols: `_sha_domain` L52–L57, `_require_sha` L60–L67, `_require_text` L70–L82, `MemoryConsumerRoleV1` L85–L88, `ResearcherPurposeV1` L91–L94, `MemorySourcePartitionV1` L97–L102, `MemoryPartitionAuthorityScopeV1` L105–L107, `MemorySourcePartitionBindingV1` L111–L199, `MemorySourcePartitionBindingV1.__post_init__` L122–L160, `MemorySourcePartitionBindingV1.full_train_source_provenance` L163–L188, `MemorySourcePartitionBindingV1.to_dict` L190–L199, `PolicyMemoryDecisionReasonV1` L202–L210, `MemoryConsumerQueryV1` L214–L286, `MemoryConsumerQueryV1.__post_init__` L221–L248, `MemoryConsumerQueryV1.scoring_text` L250–L265, `MemoryConsumerQueryV1.to_dict` L267–L286, `PolicyMemoryViewV1` L290–L395, `PolicyMemoryViewV1.__post_init__` L302–L360, `PolicyMemoryViewV1._without_sha` L362–L383, `PolicyMemoryViewV1.to_dict` L385–L391, `PolicyMemoryViewV1.policy_prompt_fragment` L393–L395, `AnalyzerMemoryCandidateV1` L399–L479, `AnalyzerMemoryCandidateV1.__post_init__` L417–L437, `AnalyzerMemoryCandidateV1.to_dict` L439–L479, `AnalyzerMemoryViewV1` L483–L532, `AnalyzerMemoryViewV1.__post_init__` L489–L510, `AnalyzerMemoryViewV1._without_sha` L512–L524, `AnalyzerMemoryViewV1.to_dict` L526–L532, `ResearcherMemoryViewV1` L536–L589, `ResearcherMemoryViewV1.__post_init__` L544–L565, `ResearcherMemoryViewV1._without_sha` L567–L581, `ResearcherMemoryViewV1.to_dict` L583–L589, `_walk_keys` L644–L651, `audit_policy_prompt_payload_v1` L654–L676, `audit_analyzer_view_payload_v1` L679–L689, `_audit_heldout_aggregate_only` L692–L702, `audit_researcher_view_payload_v1` L705–L720, `_eligible_analyzer_member` L723–L742, `_collect_evidence_reference_digests` L745–L777, `_collect_evidence_reference_digests.walk` L750–L768, `_score_members` L780–L797, `build_policy_memory_view_v1` L800–L953, `build_analyzer_memory_view_v1` L956–L1032, `build_researcher_memory_view_v1` L1035–L1121.
- [`src/pchsi/memory/formal_b_retrieval.py`](../../../src/pchsi/memory/formal_b_retrieval.py) — SHA-256 `b815d1ad127393c98830831d94d45c233eb151de0f0178ee1fe231da04f4b3a6`
  Symbols: `_canonical_json_bytes` L48–L58, `_domain_sha` L61–L66, `_require_text` L69–L76, `_require_sha` L79–L82, `FormalBPoolV1` L85–L88, `FormalBGoldDispositionV1` L91–L93, `FormalBDecisionReasonV1` L96–L103, `FormalBGoldTargetV1` L107–L137, `FormalBGoldTargetV1.__post_init__` L111–L120, `FormalBGoldTargetV1.to_dict` L122–L126, `FormalBGoldTargetV1.from_dict` L129–L137, `FormalBQueryV1` L141–L297, `FormalBQueryV1.__post_init__` L153–L195, `FormalBQueryV1.identity_payload` L197–L218, `FormalBQueryV1.to_dict` L220–L228, `FormalBQueryV1.from_dict` L231–L297, `FormalBIndependentGoldRowV1` L301–L345, `FormalBIndependentGoldRowV1.__post_init__` L306–L313, `FormalBIndependentGoldRowV1.to_dict` L315–L322, `FormalBIndependentGoldRowV1.from_dict` L325–L345, `FormalBIndependentGoldAuthorityV1` L349–L442, `FormalBIndependentGoldAuthorityV1.__post_init__` L357–L383, `FormalBIndependentGoldAuthorityV1._payload_without_sha` L385–L392, `FormalBIndependentGoldAuthorityV1.to_dict` L394–L398, `FormalBIndependentGoldAuthorityV1.canonical_bytes` L400–L401, `FormalBIndependentGoldAuthorityV1.from_dict` L404–L435, `FormalBIndependentGoldAuthorityV1.from_json` L438–L442, `FormalBGoldPanelV1` L445–L538, `FormalBGoldPanelV1.__post_init__` L454–L478, `FormalBGoldPanelV1._payload_without_sha` L480–L490, `FormalBGoldPanelV1.to_dict` L492–L496, `FormalBGoldPanelV1.canonical_bytes` L498–L499, `FormalBGoldPanelV1.from_dict` L502–L531, `FormalBGoldPanelV1.from_json` L534–L538, `validate_panel_against_independent_gold_authority_v1` L541–L574, `FormalBCandidateV1` L577–L603, `FormalBCandidateV1.__post_init__` L581–L603, `FormalBRetrieverConfigV1` L607–L647, `FormalBRetrieverConfigV1.__post_init__` L613–L626, `FormalBRetrieverConfigV1.threshold` L629–L630, `FormalBRetrieverConfigV1.to_dict` L632–L640, `FormalBRetrieverConfigV1.config_sha256` L643–L647, `FormalBMetricFractionV1` L651–L673, `FormalBMetricFractionV1.__post_init__` L655–L661, `FormalBMetricFractionV1.fraction` L664–L667, `FormalBMetricFractionV1.to_dict` L669–L673, `FormalBDecisionV1` L677–L699, `FormalBDecisionV1.to_dict` L687–L699, `FormalBPanelMetricsV1` L703–L834, `FormalBPanelMetricsV1.__post_init__` L715–L733, `FormalBPanelMetricsV1.unsafe_exposure_count` L736–L740, `FormalBPanelMetricsV1.unsafe_memory_exposure_rate` L743–L747, `FormalBPanelMetricsV1.wrong_memory_exposure_rate` L750–L754, `FormalBPanelMetricsV1.non_applicable_memory_exposure_rate` L757–L761, `FormalBPanelMetricsV1.correct_memory_exposure_rate` L764–L768, `FormalBPanelMetricsV1.abstention_rate` L771–L775, `FormalBPanelMetricsV1.coverage` L778–L782, `FormalBPanelMetricsV1.selective_accuracy` L785–L789, `FormalBPanelMetricsV1.pre_gate_top1_hit_rate` L792–L796, `FormalBPanelMetricsV1.to_dict` L798–L834, `FormalBThresholdReportV1` L838–L851, `FormalBThresholdReportV1.to_dict` L843–L851, `FormalBProtocolResultV1` L855–L890, `FormalBProtocolResultV1.to_summary_dict` L862–L890, `validate_formal_b_pool_isolation_v1` L893–L914, `_feedback_text` L917–L926, `build_formal_b_query_scoring_text_v1` L929–L941, `casefold_word_tokens_v1` L944–L946, `jaccard_score_v1` L949–L958, `_record_applicability_cues` L961–L969, `evaluate_formal_b_query_v1` L972–L1081, `evaluate_formal_b_panel_v1` L1084–L1157, `_selection_key` L1160–L1180, `select_calibration_candidates_v1` L1183–L1191, `select_validation_config_v1` L1194–L1206, `run_formal_b_three_stage_protocol_v1` L1209–L1295.
- [`src/pchsi/memory/policy_projection.py`](../../../src/pchsi/memory/policy_projection.py) — SHA-256 `ab8587be3e082be5c357bf9f4a0fc7b4f1352f91246e5102939d2121f3bb6281`
  Symbols: `_expect_exact_keys` L46–L60, `_require_string_tuple` L63–L71, `PolicyVisibleFailurePatternItemV1` L75–L119, `PolicyVisibleFailurePatternItemV1.__post_init__` L84–L96, `PolicyVisibleFailurePatternItemV1.to_dict` L98–L103, `PolicyVisibleFailurePatternItemV1.from_dict` L106–L119, `FailureMemoryPolicyVisiblePayloadV1` L123–L205, `FailureMemoryPolicyVisiblePayloadV1.__post_init__` L142–L157, `FailureMemoryPolicyVisiblePayloadV1.to_dict` L159–L171, `FailureMemoryPolicyVisiblePayloadV1.from_dict` L174–L205, `FailureMemoryPolicyVisiblePayloadV1.from_dict.items` L184–L188, `FailureMemoryPolicyProjectionV1` L209–L595, `FailureMemoryPolicyProjectionV1.__post_init__` L236–L498, `FailureMemoryPolicyProjectionV1.to_dict` L500–L530, `FailureMemoryPolicyProjectionV1.from_dict` L533–L585, `FailureMemoryPolicyProjectionV1.from_json` L588–L592, `FailureMemoryPolicyProjectionV1.canonical_bytes` L594–L595, `descriptive_policy_payload_v1` L598–L613, `_record_binding` L616–L625, `_failure_pattern` L628–L646, `_descriptive` L649–L683, `_prescriptive_gate` L686–L716, `_append_exact_identity_v1` L719–L724, `_append_evidence_ref_identities_v1` L727–L732, `_unit3_forbidden_exact_identities_v1` L735–L854, `_source_identity_augmented_report` L857–L890, `_invalid` L893–L910, `build_failure_memory_policy_projection_v1` L913–L1050.
- [`src/pchsi/memory/policy_view_safety.py`](../../../src/pchsi/memory/policy_view_safety.py) — SHA-256 `4aa650ad4acac03910a19b5bf8b79ed108bd8dff9dc068c472269533ffe0ac6c`
  Symbols: `PolicyViewStaticFailureCodeV1` L18–L31, `_expect_exact_keys` L34–L48, `_require_sha` L51–L58, `PolicyViewSafetyReportV1` L62–L171, `PolicyViewSafetyReportV1.__post_init__` L85–L118, `PolicyViewSafetyReportV1.to_dict` L120–L134, `PolicyViewSafetyReportV1.from_dict` L137–L164, `PolicyViewSafetyReportV1.from_json` L167–L168, `PolicyViewSafetyReportV1.canonical_bytes` L170–L171, `_iter_leaves` L240–L257, `policy_visible_contains_bound_identity_v1` L260–L291, `_is_strict_action_json` L294–L306, `audit_policy_visible_payload_v1` L309–L416, `validate_contextual_menu_oracle_v1` L419–L436.

### 12. Memory round maintenance / persistence

Input: Prior immutable snapshot + current round shadow events and verified effects
Output: Next-round promotion/quarantine decisions and immutable snapshot
Authority / boundary: No same-round readback. Current T2 diagnostic result alone does not promote Memory content.

- [`src/pchsi/memory/round_maintenance.py`](../../../src/pchsi/memory/round_maintenance.py) — SHA-256 `65c860667587869533f0a570b694c5b14bb28eb4dc33bb03f9ab99fcf61ecd6e`
  Symbols: `_require_sha` L28–L35, `_require_text` L38–L43, `_domain_sha` L46–L51, `MemoryRoundPhaseV1` L54–L56, `MemorySourcePartitionV1` L59–L64, `VerifierEffectV1` L67–L72, `ShadowDispositionV1` L75–L88, `MemoryRecordBindingV1` L92–L129, `MemoryRecordBindingV1.__post_init__` L97–L107, `MemoryRecordBindingV1.to_dict` L109–L116, `MemoryRecordBindingV1.from_dict` L119–L129, `MemoryRoundStateV1` L133–L261, `MemoryRoundStateV1.__post_init__` L144–L180, `MemoryRoundStateV1._without_sha` L182–L197, `MemoryRoundStateV1.to_dict` L199–L205, `MemoryRoundStateV1.from_dict` L208–L252, `MemoryRoundStateV1.from_json` L255–L261, `MemoryShadowEventV1` L265–L418, `MemoryShadowEventV1.__post_init__` L278–L335, `MemoryShadowEventV1._without_id` L337–L355, `MemoryShadowEventV1.to_dict` L357–L363, `MemoryShadowEventV1.from_dict` L366–L418, `MemoryRoundDispositionV1` L422–L448, `MemoryRoundDispositionV1.__post_init__` L428–L440, `MemoryRoundDispositionV1.to_dict` L442–L448, `MemoryRoundClosureV1` L452–L526, `MemoryRoundClosureV1.__post_init__` L464–L502, `MemoryRoundClosureV1._without_sha` L504–L518, `MemoryRoundClosureV1.to_dict` L520–L526, `classify_shadow_event_v1` L529–L633, `active_bindings_for_current_round_v1` L636–L641, `_next_bindings` L644–L669, `close_memory_round_v1` L672–L723, `next_round_state_v1` L726–L749, `_write_new` L752–L771, `initialize_round_store_v1` L774–L789, `append_shadow_event_v1` L792–L829, `finalize_round_store_v1` L832–L853.
- [`src/pchsi/memory/effect_ledger.py`](../../../src/pchsi/memory/effect_ledger.py) — SHA-256 `4d1931f5bde06bb7125dbb795672adbc95771fe56ade2285e5f5529868dc84bd`
  Symbols: `make_memory_effect_entry_v1` L3–L23.
- [`src/pchsi/memory/event_ledger.py`](../../../src/pchsi/memory/event_ledger.py) — SHA-256 `69f19fa596e3a9105fb332b4753c08171180d2a0f452bde44fb935975481f158`
  Symbols: `make_memory_event_entry_v1` L3–L9.
- [`src/pchsi/memory/promotion_ledger.py`](../../../src/pchsi/memory/promotion_ledger.py) — SHA-256 `3c196b0c3c58e740e8c0d92c82ec0bd30a8f409ae480b0c0f44af240c296987a`
  Symbols: `make_memory_promotion_entry_v1` L3–L23.
- [`src/pchsi/memory/dev_snapshot_loader.py`](../../../src/pchsi/memory/dev_snapshot_loader.py) — SHA-256 `b73b46ce328c1b4ed9676cb142c6e457ff6e693e8190cf6b8f4216e1e264854f`
  Symbols: `FM1AvailabilityV1` L33–L38, `FM2AvailabilityV1` L41–L43, `LoadedDevSnapshotMemberV2` L47–L54, `LoadedDevSnapshotV2` L58–L62, `_fm1_availability` L65–L82, `_fm2_availability` L85–L93, `load_calibrated_dev_snapshot_v2` L96–L183.
- [`src/pchsi/memory/component_ports.py`](../../../src/pchsi/memory/component_ports.py) — SHA-256 `fef4f74e4098dc2847e59617cabe84595af37118db23bf8099b758d906bdfa57`
  Symbols: `_require_text` L26–L33, `_domain_sha` L36–L41, `MemoryPortAuthorityV1` L44–L51, `MemorySourcePartitionV1` L54–L59, `VerifierEffectV1` L62–L67, `MemoryEvidenceRefV1` L71–L101, `MemoryEvidenceRefV1.__post_init__` L76–L80, `MemoryEvidenceRefV1.to_dict` L82–L87, `MemoryEvidenceRefV1.from_dict` L90–L101, `AnalyzerRepairProposalV1` L105–L141, `AnalyzerRepairProposalV1.__post_init__` L111–L122, `AnalyzerRepairProposalV1.to_dict` L124–L130, `AnalyzerRepairProposalV1.from_dict` L133–L141, `AnalyzerProposalIngressV1` L145–L254, `AnalyzerProposalIngressV1.__post_init__` L166–L218, `AnalyzerProposalIngressV1._without_sha` L220–L246, `AnalyzerProposalIngressV1.to_dict` L248–L254, `SameStateVerifierIngressV1` L258–L342, `SameStateVerifierIngressV1.__post_init__` L272–L318, `SameStateVerifierIngressV1._without_sha` L320–L334, `SameStateVerifierIngressV1.to_dict` L336–L342, `ResearcherMemoryEvidenceExportV1` L346–L447, `ResearcherMemoryEvidenceExportV1.__post_init__` L371–L415, `ResearcherMemoryEvidenceExportV1.__post_init__.walk` L392–L399, `ResearcherMemoryEvidenceExportV1._without_sha` L417–L439, `ResearcherMemoryEvidenceExportV1.to_dict` L441–L447, `VerifiedTrainingEvidencePortV1` L451–L520, `VerifiedTrainingEvidencePortV1.__post_init__` L464–L495, `VerifiedTrainingEvidencePortV1._without_sha` L497–L512, `VerifiedTrainingEvidencePortV1.to_dict` L514–L520, `build_verified_training_evidence_port_v1` L523–L552.

### 13. Research evidence hydration / role-neutral input

Input: Analyzer results, current scientific evidence, permitted Memory and cost views
Output: Round Evidence Package / Research Planner common input
Authority / boundary: SELECT reaches Planner only as aggregate; sealed benchmarks never reach adaptive decisions.

- [`src/pchsi/cognitive_runtime/round_evidence.py`](../../../src/pchsi/cognitive_runtime/round_evidence.py) — SHA-256 `2acf66adb9c124263ab8c4d819522518b21ffac6e18e6a22865ffdbe14463cb2`
  Symbols: `freeze_round_evidence_package` L11–L20.
- [`src/pchsi/cognitive_runtime/researcher.py`](../../../src/pchsi/cognitive_runtime/researcher.py) — SHA-256 `6677238a8cac88bc52b882f3be3ceb612b3b419725287ad2fe3d2d9e9d0b450d`
  Symbols: `finalize_human_pre` L7–L15, `finalize_api_pre_shadow` L18–L23, `finalize_field_adjudication` L26–L31, `finalize_api_post_shadow` L34–L39.
- [`src/pchsi/cognitive_runtime/researcher_hydrated.py`](../../../src/pchsi/cognitive_runtime/researcher_hydrated.py) — SHA-256 `7a12157c55203e2d0407488ae697fdb2848e435811dd34106c89750b7d8afdfd`
  Symbols: `_valid_sha` L14–L15, `_collect_sha_values` L18–L34, `_collect_sha_values.walk` L21–L31, `_require_mapping` L37–L40, `_require_list` L43–L46, `finalize_strong_researcher_pre_shadow_v2` L49–L359.
- [`src/pchsi/research_intelligence/round_research_inputs.py`](../../../src/pchsi/research_intelligence/round_research_inputs.py) — SHA-256 `9ea4c2207554c246261e5e58ea62742d542ea113c210ac6124fe14c1e05c084b`
  Symbols: `_require_sha` L42–L54, `_walk_keys` L57–L64, `sha256_file` L67–L70, `round_evidence_semantic_sha256` L73–L122, `researcher_memory_view_from_dict` L125–L231, `ResearcherRoundInputPackageV1` L235–L402, `ResearcherRoundInputPackageV1.__post_init__` L254–L342, `ResearcherRoundInputPackageV1._without_sha` L344–L392, `ResearcherRoundInputPackageV1.to_dict` L394–L402, `build_researcher_round_input_package_v1` L405–L666, `build_human_evidence_binding_candidate_v1` L669–L700, `researcher_round_input_package_from_dict` L704–L795, `build_shared_researcher_pre_projection_v1` L798–L903.
- [`src/pchsi/research_intelligence/visibility.py`](../../../src/pchsi/research_intelligence/visibility.py) — SHA-256 `3b6da85849a17bba9212275dbdc6bf5bd51072abcc3ae24d8344b3f48e2b9561`
  Symbols: `_assert_absent` L27–L30, `build_strong_pre_projection` L33–L50, `build_strong_post_projection` L53–L76.
- [`src/pchsi/research_intelligence/role_neutral.py`](../../../src/pchsi/research_intelligence/role_neutral.py) — SHA-256 `60056d7fdb8f0e8f7c4e3e52be5c5436e790a2a3c27b76fa8fb77746daaedf90`
  Symbols: `ResearcherRoleModeV1` L10–L15, `ResearcherArtifactStageV1` L18–L20, `_require_text` L23–L25, `_require_sha256` L28–L31, `_unique` L34–L40, `ResearcherPreDecisionV1` L44–L107, `ResearcherPreDecisionV1.validate` L61–L87, `ResearcherPreDecisionV1.to_dict` L89–L107, `ResearcherPostInterpretationV1` L111–L164, `ResearcherPostInterpretationV1.validate` L126–L146, `ResearcherPostInterpretationV1.to_dict` L148–L164, `UnifiedQwenRoleTargetV1` L168–L244, `UnifiedQwenRoleTargetV1.validate` L186–L223, `UnifiedQwenRoleTargetV1.to_dict` L225–L244, `AutonomyAttestationV1` L248–L283, `AutonomyAttestationV1.validate_for_autonomous_claim` L261–L283.

### 14. Planner PRE / high-value portfolio

Input: Shared blind evidence cutoff + candidate universe
Output: Single principal change; selected/rejected/deferred portfolio; verification budget
Authority / boundary: Human PRE is current reference, not future permanent controller. Strong shadow cannot retroactively alter it.

- [`src/pchsi/research_intelligence/repair_portfolio.py`](../../../src/pchsi/research_intelligence/repair_portfolio.py) — SHA-256 `36da258a86d0e00f06ed10fae835607c99f5fb25b8b0fc3285fff1afd0009953`
  Symbols: `RepairCandidateOriginV1` L19–L23, `RepairDispositionV1` L26–L29, `PortfolioDecisionV1` L32–L34, `RepairProgramKindV1` L37–L41, `_canonical_json_bytes` L53–L62, `_require_text` L65–L67, `_require_sha256` L70–L73, `_require_probability` L76–L78, `_unique_nonempty` L81–L89, `RepairLineageV1` L93–L174, `RepairLineageV1.validate` L101–L137, `RepairLineageV1.to_dict` L139–L148, `RepairLineageV1.from_dict` L151–L174, `ResearchRepairCandidateV1` L178–L286, `ResearchRepairCandidateV1.validate` L195–L222, `ResearchRepairCandidateV1.to_dict` L224–L242, `ResearchRepairCandidateV1.from_dict` L245–L286, `ResearchRepairProgramV1` L290–L371, `ResearchRepairProgramV1.validate` L303–L319, `ResearchRepairProgramV1.to_dict` L321–L335, `ResearchRepairProgramV1.from_dict` L338–L371, `ResearchRepairPortfolioV1` L375–L527, `ResearchRepairPortfolioV1.validate` L389–L443, `ResearchRepairPortfolioV1.to_dict` L445–L466, `ResearchRepairPortfolioV1.from_dict` L469–L527, `freeze_repair_portfolio` L530–L545, `load_repair_portfolio` L548–L552.
- [`src/pchsi/research_intelligence/planner_portfolio_selection.py`](../../../src/pchsi/research_intelligence/planner_portfolio_selection.py) — SHA-256 `084bee8cbd40f6ba082b8a036fe434559fde76c9b42682f1a1b904512bbd0962`
  Symbols: `_walk_strings` L33–L41, `_walk_sha` L44–L56, `_count_named_lists` L59–L69, `_crosscheck_dispositions` L72–L89, `_disposition_signal` L92–L102, `CandidateEvidenceProfileV1` L106–L142, `CandidateEvidenceProfileV1.to_dict` L124–L142, `profile_candidate_v1` L145–L208, `build_select12_decision_aid_v1` L211–L346.
- [`src/pchsi/research_intelligence/canonical_candidate_pool_v2.py`](../../../src/pchsi/research_intelligence/canonical_candidate_pool_v2.py) — SHA-256 `cf1ba98c0e5312d84a85e217491c2a21536244e649ce2c4461a751ed63843201`
  Symbols: `_require_sha` L22–L29, `_walk` L32–L39, `_index_unique` L42–L60, `_crosschecks` L63–L83, `_evidence_shas` L86–L106, `_evidence_shas.walk` L89–L103, `build_canonical_selected_pool_v2` L109–L304.
- [`src/pchsi/research_intelligence/selected_candidate_authority.py`](../../../src/pchsi/research_intelligence/selected_candidate_authority.py) — SHA-256 `280901f0b25b1553727f4691a8953bbd4d8a4c19af5a2149e1a55468abd39d36`
  Symbols: `_require_sha` L29–L36, `_normalize_condition` L39–L57, `_candidate_objects` L60–L84, `_candidate_objects.walk` L63–L81, `_candidate_sha_refs` L87–L116, `_candidate_sha_refs.walk` L94–L113, `_condition_from_row_or_path` L119–L137, `SelectionLedgerRowV1` L141–L151, `SelectionLedgerRowV1.to_dict` L146–L151, `SelectedCandidateAuthorityV1` L155–L228, `SelectedCandidateAuthorityV1.__post_init__` L163–L207, `SelectedCandidateAuthorityV1._without_sha` L209–L222, `SelectedCandidateAuthorityV1.to_dict` L224–L228, `_rows_from_list` L231–L283, `_rows_from_a2_a3_dict` L286–L347, `discover_selected_candidate_authority_v1` L350–L472, `discover_selected_candidate_authority_v1.walk` L368–L401.
- [`src/pchsi/research_intelligence/human_planner_freeze_lineage.py`](../../../src/pchsi/research_intelligence/human_planner_freeze_lineage.py) — SHA-256 `a16f0776e7513d874d296b437a07e513ce5dc9ca34379a38f0ab5551c3350bf9`
  Symbols: `_approval_status` L35–L42, `_without_approval` L45–L48, `validate_approval_only_transition_v1` L51–L63, `compile_preapproval_freeze_artifacts_v1` L66–L137.

### 15. Same-state F0/F1 verification

Input: Exact source state/prefix/menu/policy; frozen repair; paired seeds
Output: Branch evidence and terminal Benefit/Harm/Neutral/Uncertain labels
Authority / boundary: No Analyzer/Planner self-granted causal authority; all branch actions consume original budgets.

- [`src/pchsi/research_intelligence/clean_f0f1_manifest.py`](../../../src/pchsi/research_intelligence/clean_f0f1_manifest.py) — SHA-256 `3bc91c83ae2cc63ab204c7e68dc06cf10f21eeb1c0d9f8c4ea79ec7a43f501f6`
  Symbols: `_sha` L16–L23, `_text` L26–L29, `_state_row` L32–L64, `build_clean_f0f1_execution_manifest` L67–L167, `build_clean_f0f1_branch_bindings` L170–L203, `build_research_planner_f0f1_handoff_v2` L206–L261, `build_planner_bound_clean_f0f1_execution_manifest` L264–L337.
- [`src/pchsi/research_intelligence/human_f0f1_runtime.py`](../../../src/pchsi/research_intelligence/human_f0f1_runtime.py) — SHA-256 `6160b6da6658687130229bc006e23d377c74e1eddfaf56681ecf677d0d942791`
  Symbols: `_sha64` L40–L47, `reserve_registered_repair_environment_step_v1` L50–L75, `validate_candidate_content_hash_v1` L78–L86, `load_registered_replay_source_authority_v1` L88–L100, `validate_candidate_source_provenance_v1` L103–L141, `validate_executable_exact_candidate_v1` L143–L182, `classify_pair_effect_v1` L185–L203, `aggregate_five_pair_effects_v1` L206–L226, `validate_branch_binding_v1` L229–L281, `build_branch_evidence_hash_v1` L284–L289, `build_pair_result_hash_v1` L292–L297, `build_state_result_hash_v1` L300–L305, `continuation_request_contract_v1` L316–L327, `_continuation_profile_v1` L330–L341, `load_continuation_runtime_binding_v2` L344–L373, `_ServiceBoundContinuationRequestV1` L377–L399, `_ServiceBoundContinuationRequestV1.prompt_text` L382–L383, `_ServiceBoundContinuationRequestV1.seed` L386–L387, `_ServiceBoundContinuationRequestV1.request_id` L390–L391, `_ServiceBoundContinuationRequestV1.to_wire_dict` L393–L396, `_ServiceBoundContinuationRequestV1.to_wire_bytes` L398–L399, `build_bound_continuation_request_v1` L402–L405, `validate_continuation_wire_v1` L408–L417, `validate_continuation_record_v1` L420–L446.
- [`src/pchsi/memory/source_state_replay.py`](../../../src/pchsi/memory/source_state_replay.py) — SHA-256 `3c4f92e84c8c4cfef3ea5379a2ef628aca97d3c2dc8c43e137625721db4f1d4f`
  Symbols: `ReplayAdapterV1` L15–L20, `ReplayAdapterV1.exact_gamefile` L17–L17, `ReplayAdapterV1.reset` L18–L18, `ReplayAdapterV1.step` L19–L19, `ReplayAdapterV1.close` L20–L20, `SourceStateReplayError` L23–L24, `replay_source_decision_state_v1` L27–L105.
- [`src/pchsi/memory/source_state_contracts.py`](../../../src/pchsi/memory/source_state_contracts.py) — SHA-256 `359e42a965b0d6c07d04bc638ae9a29510f8357ac93e1ef66a82cfd683ab8ed5`
  Symbols: `_exact` L17–L26, `_text` L29–L32, `_budget_dict` L35–L44, `_budget_from` L47–L55, `_domain_sha` L58–L59, `ReplayTransitionExpectationV1` L63–L111, `ReplayTransitionExpectationV1.__post_init__` L74–L89, `ReplayTransitionExpectationV1.to_dict` L91–L102, `ReplayTransitionExpectationV1.from_dict` L105–L111, `SourceDecisionStateFingerprintV1` L115–L211, `SourceDecisionStateFingerprintV1.__post_init__` L140–L162, `SourceDecisionStateFingerprintV1._payload_without_sha` L164–L180, `SourceDecisionStateFingerprintV1.to_dict` L182–L183, `SourceDecisionStateFingerprintV1.canonical_bytes` L185–L186, `SourceDecisionStateFingerprintV1.from_dict` L189–L207, `SourceDecisionStateFingerprintV1.from_json` L210–L211, `build_source_decision_state_fingerprint_v1` L214–L220, `RegisteredReplaySourceV1` L224–L360, `RegisteredReplaySourceV1.__post_init__` L253–L302, `RegisteredReplaySourceV1.to_dict` L304–L324, `RegisteredReplaySourceV1.canonical_bytes` L326–L327, `RegisteredReplaySourceV1.from_dict` L330–L356, `RegisteredReplaySourceV1.from_json` L359–L360, `SourceStateReplayReportV1` L364–L405, `SourceStateReplayReportV1.__post_init__` L374–L388, `SourceStateReplayReportV1._payload` L390–L399, `SourceStateReplayReportV1.to_dict` L401–L402, `SourceStateReplayReportV1.canonical_bytes` L404–L405.
- [`scripts/research_intelligence/run_human_reference_f0f1_branch_v2.py`](../../../scripts/research_intelligence/run_human_reference_f0f1_branch_v2.py) — SHA-256 `5133fcc1613c116ee147e7b5f214bbcaee4981d14625d827fb5d1cf096f36568`
  Symbols: `_file_sha` L73–L78, `_write_once` L81–L96, `_canonical_object` L99–L108, `_budget_payload` L111–L118, `_budget_sha` L121–L122, `_load_runtime` L125–L131, `_task_goal` L134–L141, `_transition_record` L144–L170, `_bind_source_raw_m0_prompt_v1` L173–L199, `_failure_payload` L202–L229, `execute` L232–L560, `main` L563–L596.
- [`scripts/research_intelligence/aggregate_human_reference_f0f1_v2.py`](../../../scripts/research_intelligence/aggregate_human_reference_f0f1_v2.py) — SHA-256 `5382ed928360aee8b27a9ac33046761731c5196f2d100e117bd86b93ce67d1a6`
  Symbols: `_write_once` L27–L31, `_load_record` L34–L71, `_load_execution_manifest` L74–L90, `_validate_record_against_manifest` L92–L94, `_pair` L97–L153, `main` L156–L274.

### 16. Planner POST and training-data semantics

Input: Frozen F0/F1 results + original PRE decisions
Output: Selected training arm / dataset semantics / loss and resource plan
Authority / boundary: Current T2 remains unverified-repair diagnostic. Neutral does not become Benefit.

- [`src/pchsi/cognitive_runtime/researcher.py`](../../../src/pchsi/cognitive_runtime/researcher.py) — SHA-256 `6677238a8cac88bc52b882f3be3ceb612b3b419725287ad2fe3d2d9e9d0b450d`
  Symbols: `finalize_human_pre` L7–L15, `finalize_api_pre_shadow` L18–L23, `finalize_field_adjudication` L26–L31, `finalize_api_post_shadow` L34–L39.
- [`scripts/research_intelligence/freeze_human_researcher_post_v1.py`](../../../scripts/research_intelligence/freeze_human_researcher_post_v1.py) — SHA-256 `2ea508332a4e4974800c9e524770b84f8e1604eb7839f5a1ea30c31b2b548a12`
  Symbols: `main` L8–L9.
- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE3Y_EXISTING_TRAINING_PREPARATION_V1/prepare.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE3Y_EXISTING_TRAINING_PREPARATION_V1/prepare.py) — SHA-256 `bbb60518a2b245b756b322cc9f400704462d2cb1ad62f1607a6087c957126455`
  Symbols: `need` L19–L20, `sha` L22–L22, `cb` L24–L26, `obj` L28–L30, `regular` L32–L34, `load_zip` L36–L48, `module_from` L50–L54, `renderer_module` L56–L64, `verify_repository` L66–L75, `materialize_source_previews` L77–L158, `inspect_registered_post` L160–L178, `batch_proposal` L180–L187, `tokenize_preview` L189–L208, `collect_frozen_engineering_sources` L210–L217, `publish` L219–L238, `main` L240–L321.
- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE3Y_EXISTING_TRAINING_PREPARATION_V1/RUN_PREPARE.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE3Y_EXISTING_TRAINING_PREPARATION_V1/RUN_PREPARE.py) — SHA-256 `2e6a1525afc1fa278ec8adb8f771fbdc910fd2d43d6f744ca8251dbc979e9172`
  Symbols: `main` L7–L18.

### 17. Deterministic training materialization and renderer

Input: Approved training plan + exact source/action evidence
Output: Trainer-native input IDs, target labels and lineage checks
Authority / boundary: No silent truncation; no benchmark data; use existing renderer and training contracts.

- [`scripts/engineering_snapshots/training_pipeline/qwen25_3b_schema_aware_renderer_adapter_and_trainer_native_preflight_v1_7_2/tools/renderer_adapter_core.py`](../../../scripts/engineering_snapshots/training_pipeline/qwen25_3b_schema_aware_renderer_adapter_and_trainer_native_preflight_v1_7_2/tools/renderer_adapter_core.py) — SHA-256 `57c47de191f15860e3d1feb896421b4916cd79602ea489cd5ae5dedbe5d5af30`
  Symbols: `sha256_text` L10–L11, `canonical_action_json` L14–L22, `validate_historical_source_row` L25–L48, `make_messages` L51–L55, `mask_prompt_prefix` L58–L65, `find_unique_nested_key_path` L68–L84, `find_unique_nested_key_path.walk` L71–L77, `get_path` L87–L93, `build_t2_source_adapter_row` L96–L157, `build_native_row` L160–L202.
- [`scripts/engineering_snapshots/training_pipeline/round_generic_training_stage_v2_1_hardening_build/round_training/contracts.py`](../../../scripts/engineering_snapshots/training_pipeline/round_generic_training_stage_v2_1_hardening_build/round_training/contracts.py) — SHA-256 `6b4d29d999fbc113d8945baff30eef8308d66b61266592c48e8f410f72ce66d2`
  Symbols: `StageContext` L17–L24, `_load_file_ref` L27–L40, `validate_training_contract` L43–L292, `validate_training_contract.is_number` L130–L131, `load_stage_context` L295–L369, `load_execution_authorization` L372–L454.

### 18. Clean initialization, training execution and receipts

Input: Clean parent + fixed final-only training plan
Output: T2 adapter, formal training manifest, candidate handoff
Authority / boundary: Current final checkpoint only; no post-evaluation seed selection or retraining.

- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4A_EXISTING_TRAINER_CLEAN_INIT_V1/clean_adapter.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4A_EXISTING_TRAINER_CLEAN_INIT_V1/clean_adapter.py) — SHA-256 `329c749d39fef22b62d38ad5a212f6ce6c0443ad12b60a3a6733332d651edacc`
  Symbols: `need` L19–L20, `cb` L22–L23, `sha` L25–L26, `obj` L28–L30, `regular` L32–L35, `file_sha` L37–L41, `module` L43–L45, `checked_ref` L47–L48, `validate_packet` L50–L87, `verify_clean_base` L89–L113, `bind_formal_constants` L115–L128, `load_clean_formal` L130–L138, `verify_seed_zero_receipt` L140–L153, `_configured_legacy` L155–L196, `_configured_legacy.install_clean` L164–L193, `_configured_legacy.install_clean.check_current` L167–L170, `_configured_legacy.install_clean.check_data` L171–L174, `_configured_legacy.install_clean.check_schedule` L178–L182, `_configured_legacy.install_clean.run_manifest` L187–L192, `validate_profile_without_model_load` L198–L209, `input_artifact_refs` L211–L228, `execute_training_stage` L230–L232.
- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4A_EXISTING_TRAINER_CLEAN_INIT_V1/run_stage.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4A_EXISTING_TRAINER_CLEAN_INIT_V1/run_stage.py) — SHA-256 `4739616881e09f4d0d85be8bcff4fcff74f315b3cbcb3f611391e5e8430f794d`
  Symbols: `write_once` L14–L24, `put` L26–L26, `tagged` L28–L30, `read_zip` L32–L39, `setup` L41–L58, `package_identity` L60–L67, `load_source` L69–L83, `execution_sources` L85–L91, `prepare` L93–L126, `checked_request` L128–L139, `versions` L141–L143, `smoke` L145–L211, `compile_binding` L213–L260, `compile_binding.ref` L236–L236, `authorize_training` L262–L278, `train` L280–L299, `worker_environment` L301–L306, `job_script` L308–L310, `sbatch_args` L312–L314, `invoke_sbatch` L316–L319, `submit_once` L321–L332, `review_bundle` L334–L353, `show` L355–L369, `main` L371–L399.
- [`scripts/engineering_snapshots/training_pipeline/round_generic_training_stage_v2_1_hardening_build/round_training/stage_runner.py`](../../../scripts/engineering_snapshots/training_pipeline/round_generic_training_stage_v2_1_hardening_build/round_training/stage_runner.py) — SHA-256 `42f657bf9bc7b796bfe02612dd1a4d13d8896f0bcbdb69db9fa23cec71a961e1`
  Symbols: `reject_ambient_environment` L33–L47, `_load_runtime_adapter` L50–L70, `_input_refs` L73–L146, `run_training_stage` L149–L322, `build_argument_parser` L325–L342, `main` L345–L368.
- [`scripts/engineering_snapshots/training_pipeline/round_generic_training_stage_v2_1_hardening_build/round_training/receipts.py`](../../../scripts/engineering_snapshots/training_pipeline/round_generic_training_stage_v2_1_hardening_build/round_training/receipts.py) — SHA-256 `e09688d37cb9a5e8c4aeb8c4442f96f713c02143ae7f9ecd54db037479eec379`
  Symbols: `_artifact_ref` L14–L30, `build_input_artifact_index` L33–L53, `build_output_artifact_index` L56–L76, `build_stage_receipt` L79–L121, `create_attempt_root` L124–L129, `write_attempt_json` L132–L139, `artifact_ref_for_output` L142–L154.

### 19. SELECT preflight and frozen scientific protocol

Input: Candidate handoff + disjoint TRAIN_SELECT pool
Output: 355-task seed-major T0/T2 grid; fixed protocol and fixed head
Authority / boundary: No reselection, budget expansion, or changed I1 request semantics after results.

- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4B_EXISTING_SELECT_PREFLIGHT_V1/preflight.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4B_EXISTING_SELECT_PREFLIGHT_V1/preflight.py) — SHA-256 `f703ea94788b7b3048ab1d61fdd046c39281f2227aa24d8276f76be36450831a`
  Symbols: `need` L17–L18, `sha` L21–L21, `regular` L24–L27, `file_sha` L30–L34, `load_module` L37–L41, `load_helpers` L44–L46, `read_packet` L49–L50, `obj` L53–L55, `cb` L58–L60, `by_suffix` L63–L66, `verify_training_evidence` L69–L141, `load_pure_training_checks` L144–L159, `pool_references` L162–L171, `load_bound_pool_metadata` L174–L182, `draft_task_seed_grid` L185–L197, `verify_adapter_files` L200–L208, `write_once` L211–L215.
- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4B_EXISTING_SELECT_PREFLIGHT_V1/run_preflight.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4B_EXISTING_SELECT_PREFLIGHT_V1/run_preflight.py) — SHA-256 `14d046b49ea6b855e48be64dd063f1c6c9f5fe9b4b14c056754f57c74b6324c1`
  Symbols: `cmd` L21–L24, `verify_delivery` L27–L30, `isolated_code` L33–L59, `main` L62–L161.
- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4C_EXISTING_SELECT_FREEZE_V1/freeze_select.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4C_EXISTING_SELECT_FREEZE_V1/freeze_select.py) — SHA-256 `8ba7c97c13f387daa68019c3836f4c6db5c50d46730defaa1e63654cf8badf1d`
  Symbols: `need` L19–L20, `sha` L23–L24, `cb` L27–L29, `domain_hash` L32–L34, `obj` L37–L40, `regular` L43–L46, `file_sha` L49–L53, `write_once` L56–L67, `command` L70–L73, `git` L76–L77, `read_review` L80–L94, `validate_grid` L97–L111, `validate_review` L114–L134, `approve_decision` L137–L143, `make_protocol` L146–L168, `tree_entries` L171–L178, `expected_tree` L181–L193, `check_tree` L196–L205, `freeze_ref` L208–L209, `freeze_code` L212–L245, `publish_review` L248–L263.
- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4C_EXISTING_SELECT_FREEZE_V1/run_freeze.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4C_EXISTING_SELECT_FREEZE_V1/run_freeze.py) — SHA-256 `556aa35b71572d7b397e25371574b433a7809ea4b7bb87e758f417530d9f9a73`
  Symbols: `load_module` L21–L24, `verify_delivery` L27–L31, `dependencies` L34–L55, `authorize` L58–L63, `verify_server_inputs` L66–L92, `regression_dependencies` L95–L109, `run_regression` L112–L143, `main` L146–L240.

### 20. Typed SELECT binding and server readiness

Input: Frozen protocol + exact model/adapter/runtime
Output: Typed policy/server/condition/schedule manifests; two route probes
Authority / boundary: Readiness is non-scientific; static base + single LoRA, no dynamic updates.

- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4D_EXISTING_SELECT_LIVE_BINDING_AND_READINESS_V1_1_PROTOCOL_FIELD_FIX/stage4d_pkg/prepare.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4D_EXISTING_SELECT_LIVE_BINDING_AND_READINESS_V1_1_PROTOCOL_FIELD_FIX/stage4d_pkg/prepare.py) — SHA-256 `bd7f32adbd4820ad1df96fe8c85d9b171e8eb48632e44123ee68cb96b5d25735`
  Symbols: `git` L58–L66, `verify_frozen_protocol_grid` L69–L104, `discover_stage4c` L107–L118, `discover_candidate_handoff` L122–L141, `verify_existing_output_inventory` L144–L161, `stage2_dataset_roots` L164–L181, `load_repo_types` L184–L227, `tokenizer_identity` L230–L257, `build_environment` L260–L332, `main` L335–L862.
- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4D_EXISTING_SELECT_LIVE_BINDING_AND_READINESS_V1_1_PROTOCOL_FIELD_FIX/stage4d_pkg/readiness.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4D_EXISTING_SELECT_LIVE_BINDING_AND_READINESS_V1_1_PROTOCOL_FIELD_FIX/stage4d_pkg/readiness.py) — SHA-256 `bab901718dd66d9708808e41ba2a160ca81bd4eb7d42f81f918d92273f7d7fd8`
  Symbols: `_urlopen` L30–L34, `get_json` L37–L42, `post_json` L45–L56, `wait_ready` L59–L82, `find_port` L85–L88, `main` L91–L226.
- [`src/pchsi/evaluation/select_policy_runtime.py`](../../../src/pchsi/evaluation/select_policy_runtime.py) — SHA-256 `64dbfc73957d58d058b8b13a6bcd6627f835ac57da6a3d74f78878c741487486`
  Symbols: `_mapping` L32–L54, `_expect_keys` L57–L83, `_text` L86–L113, `_optional_text` L116–L126, `_optional_sha256` L129–L141, `SelectStaticLoRARegistrationV1` L148–L298, `SelectStaticLoRARegistrationV1.__post_init__` L167–L226, `SelectStaticLoRARegistrationV1.to_dict` L228–L246, `SelectStaticLoRARegistrationV1.from_dict` L249–L298, `SelectServerRuntimeManifestV1` L305–L793, `SelectServerRuntimeManifestV1.__post_init__` L363–L601, `SelectServerRuntimeManifestV1.to_dict` L603–L648, `SelectServerRuntimeManifestV1.to_json` L650–L655, `SelectServerRuntimeManifestV1.from_dict` L658–L782, `SelectServerRuntimeManifestV1.from_json` L785–L793, `SelectPolicyRuntimeManifestV1` L800–L1116, `SelectPolicyRuntimeManifestV1.__post_init__` L840–L986, `SelectPolicyRuntimeManifestV1.to_dict` L988–L1016, `SelectPolicyRuntimeManifestV1.to_json` L1018–L1023, `SelectPolicyRuntimeManifestV1.from_dict` L1026–L1105, `SelectPolicyRuntimeManifestV1.from_json` L1108–L1116.
- [`src/pchsi/evaluation/policy_condition.py`](../../../src/pchsi/evaluation/policy_condition.py) — SHA-256 `20ed04159621451363c87c32134fc0ce4b38bd7caa2279727203c7f3cd6066c7`
  Symbols: `_mapping` L26–L29, `_expect_keys` L32–L38, `_text` L41–L46, `_optional_text` L49–L50, `_commit` L53–L58, `CheckpointKind` L61–L64, `TrainingMethod` L67–L69, `PolicyConditionManifestV1` L73–L295, `PolicyConditionManifestV1.__post_init__` L110–L218, `PolicyConditionManifestV1.to_dict` L220–L246, `PolicyConditionManifestV1.to_json` L248–L249, `PolicyConditionManifestV1.from_dict` L252–L291, `PolicyConditionManifestV1.from_json` L294–L295.
- [`src/pchsi/evaluation/condition_run_schedule.py`](../../../src/pchsi/evaluation/condition_run_schedule.py) — SHA-256 `1eac1306540417d4794fa98ca338198206826590f50236187c6563ec6dbaf2a6`
  Symbols: `_mapping` L32–L35, `_expect_keys` L38–L44, `_text` L47–L52, `ConditionRunPurpose` L55–L57, `condition_cell_id` L60–L83, `ConditionRunScheduleCellV1` L87–L132, `ConditionRunScheduleCellV1.__post_init__` L100–L110, `ConditionRunScheduleCellV1.to_dict` L112–L118, `ConditionRunScheduleCellV1.from_dict` L121–L132, `ConditionRunScheduleV1` L136–L325, `ConditionRunScheduleV1.__post_init__` L170–L253, `ConditionRunScheduleV1.to_dict` L255–L276, `ConditionRunScheduleV1.to_json` L278–L279, `ConditionRunScheduleV1.from_dict` L282–L321, `ConditionRunScheduleV1.from_json` L324–L325, `build_condition_run_schedule` L328–L445.
- [`src/pchsi/evaluation/select_execution_identity.py`](../../../src/pchsi/evaluation/select_execution_identity.py) — SHA-256 `d63e7e7d5d5c10c4964f3c2a166effc83f1b3c6d43b5d4b7b44761dba449dc89`
  Symbols: `_runtime_sha256` L42–L50, `SelectExecutionIdentityV1` L57–L175, `SelectExecutionIdentityV1.__post_init__` L79–L175, `SelectBoundEpisodeCellV1` L183–L246, `SelectBoundEpisodeCellV1.__post_init__` L196–L246, `bind_select_condition_cell` L249–L544, `validate_select_execution_profile_binding` L547–L588, `build_select_execution_profile` L591–L626, `validate_select_model_identity_chain` L629–L674, `select_i1_request_contract_sha256` L679–L685, `SelectI1ExecutionProfileV1` L689–L743, `SelectI1ExecutionProfileV1.__post_init__` L693–L697, `SelectI1ExecutionProfileV1.profile_id` L700–L701, `SelectI1ExecutionProfileV1.arm_id` L704–L705, `SelectI1ExecutionProfileV1.policy_version` L708–L709, `SelectI1ExecutionProfileV1.request_kind` L712–L713, `SelectI1ExecutionProfileV1.requires_diagnostic_policy_call_evidence` L716–L717, `SelectI1ExecutionProfileV1.requires_current_admissible_commands` L720–L721, `SelectI1ExecutionProfileV1.served_model_name` L724–L725, `SelectI1ExecutionProfileV1.build_request` L727–L743, `build_select_i1_execution_profile` L746–L749, `validate_select_i1_wire_v1` L752–L772.

### 21. Four-GPU paired SELECT execution

Input: Original authorization + completed canonical prefix + exact schedules
Output: Shard-local attempt/receipt chains and deterministic canonical consolidation
Authority / boundary: One GPU per shard; each pair remains T0 then T2; no duplicate scientific cells. This source is immutable while job 156834 runs.

- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_AND_RESUMABLE_LIVE_V1_3_4GPU_PARALLEL_SHARDING/stage4d_full/authorize.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_AND_RESUMABLE_LIVE_V1_3_4GPU_PARALLEL_SHARDING/stage4d_full/authorize.py) — SHA-256 `0e29fa28d962a83b5970bf4777580740f5dc6611458efb808d7a232abcc2b64d`
  Symbols: `main` L28–L74.
- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_AND_RESUMABLE_LIVE_V1_3_4GPU_PARALLEL_SHARDING/stage4d_full/contract.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_AND_RESUMABLE_LIVE_V1_3_4GPU_PARALLEL_SHARDING/stage4d_full/contract.py) — SHA-256 `c97e02310bfcc8d04b24ece35ad0e5dde676e911386329c8945e36ab953a40d3`
  Symbols: `Stage4DFullError` L81–L82, `canonical_json_bytes` L85–L92, `sha256_bytes` L95–L96, `sha256_file` L99–L104, `semantic_json_file_sha256` L107–L114, `load_json` L117–L123, `require_sha` L126–L133, `write_new_json` L136–L149, `write_or_reuse_exact` L152–L158, `git` L161–L170, `validate_readiness_receipt` L173–L195, `verify_binding_inventory` L198–L229, `schedule_grid` L232–L242, `verify_scientific_grid` L245–L266, `verify_code_authority` L269–L287, `authorization_payload` L290–L318, `authorization_sha` L321–L322, `execution_root` L325–L326.
- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_AND_RESUMABLE_LIVE_V1_3_4GPU_PARALLEL_SHARDING/stage4d_full/live.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_AND_RESUMABLE_LIVE_V1_3_4GPU_PARALLEL_SHARDING/stage4d_full/live.py) — SHA-256 `1419854de8945b28840ff86d3282a53600af4b11b56aa373396966b9943bf8db`
  Symbols: `_load_adapted_legacy_live_runner` L32–L54, `_load_repo_types` L57–L70, `_prepare_live_context` L73–L148, `_prepare_live_context.build_i1` L85–L89, `_prepare_live_context.validate_i1` L91–L96, `_validate_canonical_row` L151–L157, `_canonical_prefix` L160–L180, `canonical_completed_prefix` L183–L187, `_shard_root` L190–L191, `execute_shard` L194–L294, `_tree_inventory` L297–L308, `_copy_tree_no_clobber_exact` L311–L330, `_copy_file_no_clobber_exact` L333–L358, `_copy_publication_metadata` L361–L378, `_validate_shard_receipt` L381–L398, `consolidate_shards` L401–L519.
- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_AND_RESUMABLE_LIVE_V1_3_4GPU_PARALLEL_SHARDING/stage4d_full/parallel.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_AND_RESUMABLE_LIVE_V1_3_4GPU_PARALLEL_SHARDING/stage4d_full/parallel.py) — SHA-256 `92d26d6183e191ed35ca944d2038179826a1f44671f27c4953f5ff671b6f4bd4`
  Symbols: `shard_for_ordinal` L11–L16, `remaining_ordinals` L19–L24, `partition_ordinals` L27–L43, `split_visible_devices` L46–L52, `require_single_visible_device` L56–L62, `allocate_free_ports` L64–L82.
- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_AND_RESUMABLE_LIVE_V1_3_4GPU_PARALLEL_SHARDING/stage4d_full/shard_worker.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_AND_RESUMABLE_LIVE_V1_3_4GPU_PARALLEL_SHARDING/stage4d_full/shard_worker.py) — SHA-256 `328e29d1e93c28bb7cb1721ff4a025297511095c9fe8b7fdd0c5017c378b0d13`
  Symbols: `main` L17–L114.
- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_AND_RESUMABLE_LIVE_V1_3_4GPU_PARALLEL_SHARDING/stage4d_full/slurm_entry.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_AND_RESUMABLE_LIVE_V1_3_4GPU_PARALLEL_SHARDING/stage4d_full/slurm_entry.py) — SHA-256 `ec06301334fa6f3bd41280617813e41544ab2574b96f9147e22864df55bbd564`
  Symbols: `_completion_payload` L16–L31, `main` L34–L186.
- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_AND_RESUMABLE_LIVE_V1_3_4GPU_PARALLEL_SHARDING/slurm_template.sh`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_AND_RESUMABLE_LIVE_V1_3_4GPU_PARALLEL_SHARDING/slurm_template.sh) — SHA-256 `7ea7524feb136376b5279fe01ae28b7f823682398cc5d552db69b287329c3ac8`

### 22. Independent one-GPU array migration and outcome-blind completion follow

Input: Original authorization + verified canonical prefix + never-started pending job
Output: Four registered shard jobs, original canonical completion and original Stage4E closeout
Authority / boundary: No new evaluator; cancel only an owned PENDING job; all array elements and native status hashes required; no failed-job rerun

- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4E_AUTOMATIC_AUDIT_CLOSEOUT_AND_SOURCE_PUBLICATION_V1_1_ORIGIN_AND_ARRAY_FIX/stage4e/array_jobs.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4E_AUTOMATIC_AUDIT_CLOSEOUT_AND_SOURCE_PUBLICATION_V1_1_ORIGIN_AND_ARRAY_FIX/stage4e/array_jobs.py) — SHA-256 `e0851d7e2f6e9a2b3ec3e7218035cc91a0eb200f8e525e99100082f6da74c05e`
  Symbols: `partition_from_prefix` L13–L16, `parse_accounting` L19–L37, `classify_accounting` L40–L47, `validate_pending_job` L50–L57, `parse_parsable_job` L60–L64, `submission_command` L67–L74, `incomplete_shards` L77–L87, `scheduler` L90–L94, `query_array` L97–L104, `cancel_pending_once` L107–L143.
- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4E_AUTOMATIC_AUDIT_CLOSEOUT_AND_SOURCE_PUBLICATION_V1_1_ORIGIN_AND_ARRAY_FIX/stage4e/array_driver.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4E_AUTOMATIC_AUDIT_CLOSEOUT_AND_SOURCE_PUBLICATION_V1_1_ORIGIN_AND_ARRAY_FIX/stage4e/array_driver.py) — SHA-256 `8cf7275d63c3ddae705e099ff320e3a23c2724b9d21b0aa75bf7e6a31ad4065d`
  Symbols: `existing_modules` L27–L37, `ledger_shas` L40–L41, `freeze_plan` L44–L81, `write_pointer` L84–L87, `submit_generation` L90–L120, `validate_native_status` L123–L135, `marker_path` L138–L139, `load_worker_status` L142–L152, `worker` L155–L198, `follow_arrays` L201–L220, `consolidate` L223–L248, `main` L251–L281.
- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4E_AUTOMATIC_AUDIT_CLOSEOUT_AND_SOURCE_PUBLICATION_V1_1_ORIGIN_AND_ARRAY_FIX/array_shard.sh`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4E_AUTOMATIC_AUDIT_CLOSEOUT_AND_SOURCE_PUBLICATION_V1_1_ORIGIN_AND_ARRAY_FIX/array_shard.sh) — SHA-256 `91401eba80297e140067e0e1fb1ebff59b7db085224906cb87c95c7b3babe4c4`

### 23. Completion-gated audit of full results

Input: Parent job completed 0:0 plus full 3550 completion artifact
Output: Reloaded attempts / native I1 identity-chain audit / complete denominator
Authority / boundary: Never read partial success while waiting; missing scientific outcome is not a failure.

- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4E_AUTOMATIC_AUDIT_CLOSEOUT_AND_SOURCE_PUBLICATION_V1_1_ORIGIN_AND_ARRAY_FIX/stage4e/driver.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4E_AUTOMATIC_AUDIT_CLOSEOUT_AND_SOURCE_PUBLICATION_V1_1_ORIGIN_AND_ARRAY_FIX/stage4e/driver.py) — SHA-256 `32ec70c9fd5e0c750b301cf48f713426f483e6f99647bcb312666bfa11e2bcaf`
  Symbols: `parse_accounting` L29–L36, `decide` L38–L41, `parse_submitted_job` L43–L47, `status` L49–L60, `check_authorization` L62–L66, `base_gate` L68–L87, `test_command` L89–L97, `regression_prerequisites` L99–L109, `prepare` L111–L174, `follow` L176–L221, `finalize` L223–L257, `main` L259–L283.
- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4E_AUTOMATIC_AUDIT_CLOSEOUT_AND_SOURCE_PUBLICATION_V1_1_ORIGIN_AND_ARRAY_FIX/stage4e/audit.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4E_AUTOMATIC_AUDIT_CLOSEOUT_AND_SOURCE_PUBLICATION_V1_1_ORIGIN_AND_ARRAY_FIX/stage4e/audit.py) — SHA-256 `a589f616e66c68e9b97ede40ad1c3b766f39f46151891a9948624293d472cd28`
  Symbols: `completion_gate` L23–L30, `validate_train_reference` L32–L35, `load_native` L37–L64, `check_receipt_grid` L66–L78, `audit_loaded_cell` L80–L95, `audit_publication_metadata` L97–L136, `takeover_pending` L138–L154, `execute_audit` L156–L165, `_audit_locked` L167–L283.
- [`scripts/memory/materialize_sequence_failure_experience_v1.py`](../../../scripts/memory/materialize_sequence_failure_experience_v1.py) — SHA-256 `b04d3976da429490cf03184245bc447e33b2877d8d6753a52a7b048408307055`
  Symbols: `_require_regular_file` L59–L65, `_require_regular_directory` L68–L74, `require_protected_task_access_manifest_v1` L77–L82, `_trace_from_dict` L85–L159, `_load_jsonl` L162–L169, `load_attempt_directory_v1` L172–L223, `_binding_from_manifest_line` L226–L257, `materialize_prevalidated_v1` L260–L285, `_load_registration` L288–L290, `main` L293–L332.
- [`src/pchsi/evaluation/select_result_audit.py`](../../../src/pchsi/evaluation/select_result_audit.py) — SHA-256 `b8b1e7452a2dc57b6e85036b4958ab7718c34d5438f68e238e513d7f2c51ddc3`
  Symbols: `ExpectedSelectCellV1` L54–L61, `validate_master_schedule_set` L64–L186, `derive_expected_select_cells_from_master_schedules` L189–L257, `_exact_model_names_from_policy_call` L260–L334, `audit_select_cell_identity_chain` L337–L748, `audit_select_i1_policy_calls_v1` L751–L779.

### 24. Paired descriptive statistics

Input: Fully audited canonical T0/T2 receipt sets
Output: Per-task mean-over-seeds difference, equal task weighting; registered secondary metrics
Authority / boundary: Reuse legacy numeric aggregator only, never old 17-task polluted pilot closeout. No post-hoc significance/equivalence threshold.

- [`scripts/engineering_snapshots/stage0/human_pilot_stage0_offoff_execution_and_closeout_v1_9/stage0/result_audit.py`](../../../scripts/engineering_snapshots/stage0/human_pilot_stage0_offoff_execution_and_closeout_v1_9/stage0/result_audit.py) — SHA-256 `96451ec9d6841510455ddf54a00c74635ff16b2e94d9463cab1cfcacbbb08bc0`
  Symbols: `audit_receipt_attempts` L37–L90, `aggregate_paired_results` L93–L187, `aggregate_paired_results.index` L100–L107, `_publish_recovered_review_root` L190–L240, `finalize_stage0` L243–L476.
- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4E_AUTOMATIC_AUDIT_CLOSEOUT_AND_SOURCE_PUBLICATION_V1_1_ORIGIN_AND_ARRAY_FIX/stage4e/__init__.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4E_AUTOMATIC_AUDIT_CLOSEOUT_AND_SOURCE_PUBLICATION_V1_1_ORIGIN_AND_ARRAY_FIX/stage4e/__init__.py) — SHA-256 `2188e65a6d09630eeaa290d019e102926d4dd83f3e323ea36f4b703a6e7108f2`
  Symbols: `GateError` L9–L10, `strict_loads` L12–L22, `strict_loads.pairs` L13–L19, `strict_loads.nonfinite` L20–L21, `canonical` L24–L25, `sha` L27–L28, `semantic_sha` L30–L31, `regular` L33–L37, `read_json` L39–L43, `file_sha` L45–L50, `require_file_sha` L52–L55, `write_bytes_exact` L57–L81, `write_exact` L83–L84, `safe_child` L86–L95, `verify_inventory` L97–L111, `validate_completion` L113–L131, `project_paired_summary` L133–L152, `diagnostic_disposition` L154–L166, `next_operation` L168–L177.

### 25. Disposition and next-parent handoff

Input: Audited aggregate + frozen diagnostic non-promotion rule
Output: Native PromotionDecision ROLLBACK/retain-parent; NextRoundCreation record
Authority / boundary: Positive measured delta does not override promotion_eligible=false. Next-round creation is not scientific execution authorization.

- [`src/pchsi/round_control/promotion.py`](../../../src/pchsi/round_control/promotion.py) — SHA-256 `0b563091a03a0257bce23eb9bf00fa38c8ce1091ac38f6aa54b1a12c8138a765`
  Symbols: `PromotionDecisionV1` L9–L33, `PromotionDecisionV1.to_dict` L20–L33, `freeze_promotion_decision` L36–L89.
- [`src/pchsi/round_control/next_round.py`](../../../src/pchsi/round_control/next_round.py) — SHA-256 `4a886b8342e031d326a805e623dde673f8570b00733b4e94dc486075cef1ad2f`
  Symbols: `NextRoundCreationV1` L10–L30, `NextRoundCreationV1.to_dict` L19–L30, `freeze_next_round_creation` L33–L75.
- [`src/pchsi/round_control/attempt_receipts.py`](../../../src/pchsi/round_control/attempt_receipts.py) — SHA-256 `c01266611ca35753076651397d772cd2c00783ffdd812fb487270e0e0980e004`
  Symbols: `StageAttemptReceiptV1` L19–L41, `StageAttemptReceiptV1.to_dict` L29–L41, `freeze_stage_attempt_receipt` L44–L101, `publish_receipt_no_clobber` L104–L122, `load_receipt` L125–L142.
- [`src/pchsi/round_control/lifecycle.py`](../../../src/pchsi/round_control/lifecycle.py) — SHA-256 `326e802a6abc1e33ad6d2ea04709e195ad711d765ab68700507e028a5c64ced9`
  Symbols: `RoundStageV1` L9–L21, `RoundLifecycleV1` L45–L134, `RoundLifecycleV1.new` L54–L83, `RoundLifecycleV1.advance` L85–L122, `RoundLifecycleV1.to_dict` L124–L134.

### 26. Human / Strong / Local role traces and localization data

Input: Frozen clean role traces with accepted/revised/rejected lineage
Output: RoleTraceRecord / reference demonstrations / eligible local supervision
Authority / boundary: No current round answer leak or old contaminated pilot reuse. Runtime role equivalence must be verified, not asserted.

- [`src/pchsi/round_control/trace_handoff.py`](../../../src/pchsi/round_control/trace_handoff.py) — SHA-256 `a93905ef47b752c81db333a5079aa173f675be4f8a8505f649240c5d9060c0f1`
  Symbols: `ActorV1` L10–L13, `AuthorityModeV1` L16–L19, `RoleTraceRecordV1` L23–L71, `RoleTraceRecordV1.validate` L34–L48, `RoleTraceRecordV1.to_dict` L50–L71, `RoundTraceLedgerV1` L75–L138, `RoundTraceLedgerV1.validate` L79–L110, `RoundTraceLedgerV1.localization_teacher_records` L112–L123, `RoundTraceLedgerV1.to_dict` L125–L138.
- [`src/pchsi/round_control/retention.py`](../../../src/pchsi/round_control/retention.py) — SHA-256 `10851b0998e92692e99ffea54d98fe5a7374ee911635b85bbc642540d7867221`
  Symbols: `ArtifactKindV1` L9–L20, `RetentionDecisionV1` L24–L28, `decide_cross_round_retention` L40–L118.
- [`src/pchsi/research_intelligence/research_planner_reference_trace.py`](../../../src/pchsi/research_intelligence/research_planner_reference_trace.py) — SHA-256 `b729b84f810b426bb953e68ae30f1bf2ef439e58a1bdb209946fe8eec10ad5c8`
  Symbols: `_require_sha` L18–L25, `VerificationBudgetPlanV1` L29–L126, `VerificationBudgetPlanV1.__post_init__` L37–L87, `VerificationBudgetPlanV1.branch_runs_per_state` L90–L94, `VerificationBudgetPlanV1._without_sha` L96–L120, `VerificationBudgetPlanV1.to_dict` L122–L126, `current_reference_budget_plan_v1` L129–L135, `verified_training_data_policy_v1` L138–L266, `research_planner_reference_trace_template_v1` L269–L348, `validate_research_planner_verification_plan_v2` L351–L419, `build_research_planner_verification_plan_v2` L422–L485.
- [`src/pchsi/research_intelligence/demonstrations.py`](../../../src/pchsi/research_intelligence/demonstrations.py) — SHA-256 `692f11740536d723f1b8757568996834045f24b5721057b06c6111f905dde3da`
  Symbols: `build_demonstration_pack` L9–L88.
- [`src/pchsi/research_intelligence/distillation.py`](../../../src/pchsi/research_intelligence/distillation.py) — SHA-256 `3bc7067bcd77e33546fba63df86d39bb7c28aab5d71864a62a02708bd4ed3547`
  Symbols: `_example_from_round` L16–L60, `build_local_role_supervision_dataset` L63–L109.
- [`src/pchsi/research_intelligence/reference_round.py`](../../../src/pchsi/research_intelligence/reference_round.py) — SHA-256 `f9dc23489fb6e2e9ca04f60cad98d2c4b635c9e21363769da54f054aa8e011b7`
  Symbols: `freeze_reference_round_manifest` L9–L54.

### 27. Strong-primary and later Local-primary takeover

Input: Measured takeover evidence, fresh round budget and actor/model bindings
Output: Existing deterministic eligibility and role authority plan
Authority / boundary: No invented missing metrics, no routine human decision fallback. Insufficient evidence yields machine HOLD; full autonomous execution not yet claimed.

- [`src/pchsi/research_intelligence/takeover.py`](../../../src/pchsi/research_intelligence/takeover.py) — SHA-256 `cedba560342ef976f30b54479a38601b8fe1a1a37f69ea4c85c8ac11898fdf82`
  Symbols: `evaluate_takeover_gate` L9–L88.
- [`src/pchsi/round_control/role_authority.py`](../../../src/pchsi/round_control/role_authority.py) — SHA-256 `5b2eded4c29aa29b0fac0b4257c5c0ebc3212dfc3b14d408d3f346e36b4b97ac`
  Symbols: `AuthorityPhaseV1` L9–L12, `ResearchRoleV1` L15–L18, `AuthorityPlanV1` L22–L35, `AuthorityPlanV1.primary_actor` L31–L32, `AuthorityPlanV1.shadow_actors` L34–L35, `_all_roles` L38–L39, `resolve_authority_plan` L42–L109.
- [`src/pchsi/round_control/orchestrator.py`](../../../src/pchsi/round_control/orchestrator.py) — SHA-256 `beb0736d38a6cc891aed66b042b9b18c4a9e18c6c4b7b2dda6c20b84609a280b`
  Symbols: `NextActionV1` L9–L15, `next_action_for` L67–L78.
- [`src/pchsi/round_control/clean_role_actor_binding.py`](../../../src/pchsi/round_control/clean_role_actor_binding.py) — SHA-256 `5cacb0ad65cd82e371f6efddf762ffaa05b194a0f8591368df80bb0857b39154`
  Symbols: `CleanRoleActorBindingV1` L8–L15, `human_primary_strong_shadow_bindings` L18–L106.

### 28. Independent benchmark sealing

Input: Fixed compared policies and shared benchmark protocol
Output: Sealed standard benchmark product / controlled final unsealing
Authority / boundary: Not an adaptive-loop data source; benchmark result values remain unread by this delivery.

- [`src/pchsi/round_control/benchmark_sealing.py`](../../../src/pchsi/round_control/benchmark_sealing.py) — SHA-256 `0ce0a3d76d8f40c964a3a49c66c6d71a33156ee5cc65c048016a61fd11fc9aff`
  Symbols: `BenchmarkSplitV1` L9–L11, `BenchmarkResultSealV1` L15–L88, `BenchmarkResultSealV1.create` L25–L59, `BenchmarkResultSealV1.reveal` L61–L88.
- [`src/pchsi/research_intelligence/benchmark_registry.py`](../../../src/pchsi/research_intelligence/benchmark_registry.py) — SHA-256 `9b5400cf45a6d5fe0a27297e67a01d741084e32af1b0af646dc80aaf52c54f4a`
  Symbols: `BenchmarkModelStageV1` L13–L19, `ComparabilityClassV1` L22–L26, `ResultStatusV1` L29–L35, `_canonical` L38–L47, `_require_text` L50–L52, `_require_sha256` L55–L61, `_optional_sha256` L64–L66, `SharedEvaluationProtocolV1` L70–L147, `SharedEvaluationProtocolV1.validate` L88–L107, `SharedEvaluationProtocolV1.to_dict` L109–L134, `SharedEvaluationProtocolV1.digest` L136–L137, `SharedEvaluationProtocolV1.differences` L139–L147, `ModelExecutionProfileV1` L156–L221, `ModelExecutionProfileV1.validate` L173–L196, `ModelExecutionProfileV1.to_dict` L198–L218, `ModelExecutionProfileV1.digest` L220–L221, `BenchmarkEntryV1` L225–L315, `BenchmarkEntryV1.protocol_fingerprint` L239–L242, `BenchmarkEntryV1.validate` L244–L291, `BenchmarkEntryV1.to_dict` L293–L315, `BenchmarkLineageRegistryV1` L364–L424, `BenchmarkLineageRegistryV1.validate` L370–L415, `BenchmarkLineageRegistryV1.to_dict` L417–L424, `required_metric_ids` L427–L428, `freeze_benchmark_registry` L431–L449.
- [`src/pchsi/research_intelligence/product_isolation.py`](../../../src/pchsi/research_intelligence/product_isolation.py) — SHA-256 `f1adc05946406272ca04ffcd7c2e647eab133d0308d67983e84003bfcf4d7416`
  Symbols: `_walk` L24–L33, `assert_separate_roots` L36–L40, `assert_artifact_domain` L43–L49, `load_object` L52–L58.

### 29. Isolated source consolidation and verified Git publication

Input: Fixed native Git history + explicit latest execution wrappers + audit-only adapters
Output: Complete code-chain docs/AST index + FF-only atomic branch/main update
Authority / boundary: No force push, no active worktree changes, no raw SELECT/benchmark trajectories or weights uploaded.

- [`scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4E_AUTOMATIC_AUDIT_CLOSEOUT_AND_SOURCE_PUBLICATION_V1_1_ORIGIN_AND_ARRAY_FIX/stage4e/source.py`](../../../scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4E_AUTOMATIC_AUDIT_CLOSEOUT_AND_SOURCE_PUBLICATION_V1_1_ORIGIN_AND_ARRAY_FIX/stage4e/source.py) — SHA-256 `12bf3c42282b1adfd9a095a7f5e2c9dec79a5074da537f76d0efb5aadcf020f9`
  Symbols: `run` L14–L20, `git` L22–L24, `require_ancestor` L26–L28, `is_snapshot_source` L30–L35, `reject_secret` L37–L42, `inspect_python` L44–L65, `inspect_python.visit` L47–L55, `source_inventory` L67–L68, `verify_active_repo` L70–L74, `approved_origin_pair` L76–L85, `optional_git_config` L88–L95, `ensure_isolated_repo` L98–L144, `stage_explicit` L146–L154, `commit_staged` L156–L159, `publish_atomic` L161–L180, `build_source_map` L182–L231.

## Machine-stopped future dependencies

- Formal Strong takeover metrics must be produced by the existing registered evaluation, including handling undefined ratios; values must not be invented.
- Next-round resource budget, blind evidence cutoff and Strong-primary actor binding must be frozen before calls or training.
- Local-shadow model/training artifact identity must exist before a local shadow is claimed.
- Historical archive-provenance completeness remains false until the existing missing upstream lineage is independently closed.
- This static source map does not prove a fresh Strong/Local autonomous round has executed.

## Exact runtime locations

- `round_root`: `/data/run01/scwb204/sdar_repro/badcase/new_human_pi1`
- `binding_root`: `/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/control/stage4d_existing_select_live_binding_v1/4ab7942b2c66238cb3833bdb04eb7f7ca23b52d10c388575aaf1bd272dfc100d`
- `execution_root`: `/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/control/stage4d_existing_select_live_execution_v1/978ab39389d447b74b1a1acf653619ff437c0d341c9fe76b72236dd8f5fd865b`
- `protocol`: `/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/control/stage4c_existing_select_freeze_v1/65c7aa120baae98471deb20796927f4adfa5be5c2920d4ed31749308908bad5b/SELECT_EVALUATION_PROTOCOL_V1.json`
- `candidate`: `/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/control/stage4a_clean_existing_trainer_v1/1711c5fbc6431f3bd59bda066011ab265837aecfcaf827b073f6a4754ec2f692/CANDIDATE_HANDOFF.json`
- `full_package`: `/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_AND_RESUMABLE_LIVE_V1_3_4GPU_PARALLEL_SHARDING`
- `readiness_package`: `/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/STAGE4D_EXISTING_SELECT_LIVE_BINDING_AND_READINESS_V1_1_PROTOCOL_FIELD_FIX`

## Status

This is an engineering source map, not evidence that the active four-GPU run has finished. Final disposition is emitted only after every registered cell passes the existing attempt and SELECT audits.
The current diagnostic candidate cannot be promoted by a positive observed SELECT delta. The automatic disposition retains the parent, while preserving the measured delta.
