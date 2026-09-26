"""Execute the existing Dynamic PRE V2 once, or adopt its exact terminal."""
from contextlib import ExitStack
from pathlib import Path
import re
import subprocess
from unittest.mock import patch

from exact_bindings import (BindingError, accept_pre, canonical, digest, read_json,
                            immutable_json, immutable_bytes, file_ref, read_ref)
from local_stage import sealed

LABELS_REL = Path('scripts/engineering_snapshots/training_pipeline/qwen25_3b_schema_aware_renderer_adapter_and_trainer_native_preflight_v1_7_2/tools')


def load_native_labels(repo, out, source_registration):
    from training_binding.native_labels import NativeLabels
    root = Path(repo).absolute() / LABELS_REL
    names = ('common.py', 'renderer_adapter_core.py', 'strategy_dual_view_adapter.py')
    refs = {name: file_ref(root / name) for name in names}
    schema_ref = file_ref(Path(repo).absolute() / 'configs/analyzer/schemas/analyzer_repair_candidate_v1.json')
    head = source_registration.get('scientific_repo_head')
    if not isinstance(head, str) or re.fullmatch('[0-9a-f]{40}', head) is None:
        raise BindingError('NATIVE_LABELS_REGISTERED_GIT_HEAD_REQUIRED')
    object_root = Path(source_registration.get('scientific_git_object_root', repo)).absolute()
    for path in [root / name for name in names] + [Path(schema_ref['path'])]:
        relative = path.relative_to(Path(repo).absolute()).as_posix()
        check = subprocess.run(['git', '-C', str(object_root), 'cat-file', 'blob', head + ':' + relative],
                               capture_output=True, check=False, shell=False)
        if check.returncode or check.stdout != path.read_bytes():
            raise BindingError('NATIVE_LABELS_REGISTERED_GIT_BYTES_MISMATCH:' + relative)
    seal = {'schema_id': 'CURRENT_NATIVE_LABELS_SOURCE_SEAL_V1', 'scientific_repo_root': str(Path(repo).absolute()),
        'tools_relative_path': LABELS_REL.as_posix(), 'files': refs, 'candidate_schema_ref': schema_ref,
        'registered_git_head': head, 'registered_git_bytes_verified': True}
    immutable_json(Path(out) / 'NATIVE_LABELS_SOURCE_SEAL.json', seal)
    return NativeLabels.load(root, {name: ref['file_sha256'] for name, ref in refs.items()})


def selected_candidates(artifact, pair_view):
    selected = []
    for review in artifact['state_reviews']:
        if review['selected_for_verification'] is not True:
            continue
        row = pair_view['pair_table'][review['state_index']]
        candidate = row[review['preferred_condition']]['candidate']
        if row['source_state_sha256'] != review['source_state_sha256'] or candidate['candidate_sha256'] != review['preferred_candidate_sha256']:
            raise BindingError('PRE_STRATEGY_SELECTED_CANDIDATE_BINDING')
        selected.append(candidate)
    if len(selected) != artifact['selected_state_count'] or {x['candidate_sha256'] for x in selected} != set(artifact['selected_candidate_sha256s']):
        raise BindingError('PRE_STRATEGY_SELECTED_CANDIDATE_SET')
    return selected


def run_pre(binding, values, core, tail, universe, out):
    import jsonschema
    from training_binding.strategy_source import (extend_pre_schema, extend_pre_prompt,
        validate_pre_strategies, adopt_pre_strategies)
    out = Path(out); x = core.x; rid = binding['round_id']; pid = binding['parent_policy_id']
    native_labels = load_native_labels(core.repo, out, binding['source_registration'])
    view = x.translate_pair_universe(universe, core.domain_hash)
    protocol = values['f0f1_protocol']
    contract = x.build_dynamic_pre_contract_v2(pair_rows=view['pair_table'], f0f1_protocol=protocol,
        dynamic_pair_universe_sha256=universe['pair_universe_sha256'])
    evidence = x.build_current_round_evidence(round_id=rid, parent_policy_id=pid,
        analyzer_terminal_sha256=tail['terminal_sha256'], dynamic_pair_universe_sha256=universe['pair_universe_sha256'],
        dynamic_pair_count=len(view['pair_table']),
        round_start_memory_snapshot_sha256=values['request']['round_start_memory_snapshot_sha256'])
    # Finite typed input; no filesystem candidate census.
    memory_refs = binding['refs'].get('researcher_views')
    inputs = [read_ref(r) for r in memory_refs] if memory_refs is not None else [values['researcher_view']]
    aggregate_context = {}
    if 'previous_select_context' in binding['refs']:
        from analyzer_binding.aggregate_context import validate_previous_select_context
        aggregate_context = validate_previous_select_context(
            read_ref(binding['refs']['previous_select_context']), current_request=values['request'])
    if any(value.get('heldout_aggregate_metrics') != aggregate_context for value in inputs):
        raise BindingError('PRE_RESEARCHER_SELECT_CONTEXT_IDENTITY')
    predecessors, _ = x.partition_predecessor_memory_candidates(inputs, current_round_evidence=evidence)
    stable = x.resolve_stable_memory_authority(predecessors,
        snapshot_sha256=values['request']['round_start_memory_snapshot_sha256'])
    memory = core.researcher_view(snapshot_sha256=values['request']['round_start_memory_snapshot_sha256'],
        purpose=core.researcher_purpose.ROUND_RESEARCH_PLANNING,
        train_side_records=tuple(stable['train_side_records']), round_evidence=evidence,
        heldout_aggregate_metrics=aggregate_context).to_dict()
    blind = sealed(core, 'STRONG_RESEARCHER_BLIND_PRE_INPUT_V3', {
        'schema_version': 3, 'round_id': rid, 'parent_policy_id': pid, 'pre_outcome_only': True,
        'human_pre_visible': False, 'human_selection_visible': False, 'human_rationale_visible': False,
        'sealed_benchmark_per_task_results_visible': False, 'current_or_future_f0f1_outcomes_visible': False,
        'analyzer_terminal_sha256': tail['terminal_sha256'], 'registered_candidate_universe': view,
        'dynamic_contract': contract, 'researcher_memory_view': memory,
        'f0f1_replication_protocol': protocol}, 'blind_input_sha256')
    projection = {'round_id': rid, 'blind_input_sha256': blind['blind_input_sha256'],
        'dynamic_contract_sha256': contract['contract_sha256'], 'dynamic_pair_universe_sha256': universe['pair_universe_sha256'],
        'researcher_memory_view_sha256': memory['view_sha256'], 'dynamic_contract': contract, 'blind_input': blind}
    prompt_path = out / 'PRE_STRATEGY_PROMPT.txt'
    immutable_bytes(prompt_path, extend_pre_prompt(x.PROMPT_PATH.read_text(encoding='utf-8')).encode('utf-8'))
    prompt_sha = digest(prompt_path.read_bytes()); schema_raw = x.SCHEMA_PATH.read_bytes()
    schema = extend_pre_schema(read_json(x.SCHEMA_PATH)); jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    provider_schema, normalization_count = core.schema_compatibility.normalize_const_types(schema)
    provider_schema_path = out / 'PRE_PROVIDER_SCHEMA.json'
    immutable_json(provider_schema_path, provider_schema)
    manifest = x.build_overlay_manifest(values['runtime_manifest'], prompt_sha, digest(canonical(provider_schema)), core.domain_hash)
    manifest['stage_rows'][-1]['output_schema_relative_path'] = str(provider_schema_path.absolute())
    manifest['stage_rows'][-1]['prompt_relative_path'] = str(prompt_path.absolute())
    manifest['runtime_manifest_sha256'] = core.domain_hash('UNIFIED_COGNITIVE_RUNTIME_MANIFEST_V1', manifest,
                                                        excluded_field='runtime_manifest_sha256')
    immutable_json(out / 'PRE_SCHEMA_COMPATIBILITY.json', {'original_schema_sha256': digest(schema_raw),
        'provider_schema_file_sha256': digest(canonical(provider_schema)),
        'const_type_annotations_added': normalization_count, 'scientific_constraints_changed': False,
        'same_call_strategy_representation_added': True, 'original_prompt_sha256': digest(x.PROMPT_PATH.read_bytes()),
        'adapted_prompt_file_sha256': prompt_sha})
    unit_id = core.domain_hash('V1232V_PRE_SCIENTIFIC_UNIT_ID_V1', {'round_id': rid,
        'dynamic_pair_universe_sha256': universe['pair_universe_sha256'],
        'blind_input_sha256': blind['blind_input_sha256'], 'researcher_memory_view_sha256': memory['view_sha256']})
    unit = core.identity(scientific_unit_type='ROUND', scientific_unit_id=unit_id,
        source_unit_manifest_sha256=blind['blind_input_sha256'], task_set_manifest_sha256=universe['pair_universe_sha256'],
        task_id=None, gamefile_sha256=None, group_manifest_sha256=None, round_evidence_package_sha256=tail['terminal_sha256'])
    access = {'schema_id': 'V1232V_RESEARCH_PLANNER_PRE_TASK_ACCESS_V1', 'schema_version': 1,
        'task_id': rid, 'gamefile_sha256': universe['pair_universe_sha256'],
        'access_class': 'TRAIN_UPDATE_RESEARCH_PLANNER_VISIBLE', 'dataset_split': 'train',
        'teacher_call_permitted': True, 'training_permitted': False, 'select_evaluation_permitted': False,
        'confirmatory_permitted': False, 'benchmark_result_values_visible': False, 'policy_action_authority': False}
    for filename, value in [('V1232V_DYNAMIC_PRE_PAIR_UNIVERSE_VIEW_V1.json', view),
        ('STRONG_RESEARCHER_PRE_PRIMARY_DYNAMIC_CONTRACT_V2.json', contract),
        ('RESEARCHER_MEMORY_VIEW_V1.json', memory), ('STRONG_RESEARCHER_BLIND_PRE_INPUT_V3.json', blind),
        ('V1232V_PRE_PROJECTION_V1.json', projection), ('V1232V_PRE_SCIENTIFIC_UNIT_IDENTITY_V1.json', unit),
        ('V1232V_PRE_TASK_ACCESS_V1.json', access), ('EXACT_RUNTIME_MANIFEST.json', manifest)]:
        immutable_json(out / filename, value)

    def finalize(value):
        return x.finalize_dynamic_primary_pre_v2(value=value, pair_rows=view['pair_table'], contract=contract,
            blind_input_sha256=blind['blind_input_sha256'], round_id=rid)

    def finalize_original_output(value, raw_response_sha256=None):
        try:
            return finalize(value)
        except ValueError as original:
            normalized = x.try_semantic_normalization(original_output=value, contract=contract,
                original_validation_error=str(original), validator=finalize)
            if normalized['status'] != 'ACCEPTED_AFTER_DETERMINISTIC_NORMALIZATION':
                raise
            if raw_response_sha256 is not None:
                immutable_json(out / 'PRE_NORMALIZATION_RECEIPT.json', {'raw_response_sha256': raw_response_sha256,
                    'scientific_choices_changed': False, 'changed_paths': normalized['changed_paths'], 'provider_call_count': 0})
            return normalized['validated_artifact']

    def validate_output(*, stage_id, text, raw_response_sha256, projection):
        from exact_bindings import loads
        if stage_id != 'R-PRE-PRIMARY-V2':
            raise BindingError('PRE_OVERLAY_STAGE_MISMATCH')
        value = loads(text); validator.validate(value)
        strategies = value.pop('training_strategies')
        artifact = finalize_original_output(value, raw_response_sha256)
        validate_pre_strategies(strategies, accepted_pre=artifact,
            selected_candidates=selected_candidates(artifact, view), native_labels=native_labels)
        return artifact

    def artifact_identity(*, stage_id, artifact):
        if stage_id != 'R-PRE-PRIMARY-V2':
            raise BindingError('PRE_OVERLAY_IDENTITY_STAGE_MISMATCH')
        result = finalize(artifact)
        if result != artifact:
            raise BindingError('PRE_SELF_HASH_MISMATCH')
        return result['primary_record_sha256']

    runtime = out / 'strong_pre_runtime'
    with ExitStack() as stack:
        stack.enter_context(patch.object(core.rr, 'load_runtime_manifest', lambda *a, **k: manifest))
        stack.enter_context(patch.object(core.orch, 'load_runtime_manifest', lambda *a, **k: manifest))
        stack.enter_context(patch.object(core.orch, 'validate_stage_output', validate_output))
        stack.enter_context(patch.object(core.orch, 'validated_artifact_identity', artifact_identity))
        rendered = core.rr.render_stage_request(stage_id='R-PRE-PRIMARY-V2', projection=projection)
        logical_id = x.expected_logical_call_id(unit_identity=unit, round_id=rid, policy_version=pid,
            request_body_sha256=rendered['request_body_sha256'], domain_hash=core.domain_hash)

        def expected(identity, call_id):
            return {'logical_call_id': call_id, 'scientific_unit_identity_sha256': identity['identity_sha256'],
                'stage_id': 'R-PRE-PRIMARY-V2', 'condition_id': None, 'round_id': rid,
                'policy_version': pid, 'request_body_sha256': rendered['request_body_sha256'],
                'runtime_manifest_sha256': rendered['runtime_manifest_sha256']}

        call = runtime / logical_id
        if not (call.exists() or call.is_symlink()):
            core.orch.execute_one(output_root=runtime, unit_identity=unit, stage_id='R-PRE-PRIMARY-V2',
                condition_id=None, round_id=rid, policy_version=pid, projection=projection, task_access=access)
        # Exact logical binding is checked before inspecting a recovery disposition.
        if not (call / 'logical_call.json').is_file():
            raise BindingError('PARTIAL_PRE_NO_RESEND:' + str(call))
        logical = read_json(call / 'logical_call.json')
        for key, value in expected(unit, logical_id).items():
            if logical.get(key) != value:
                raise BindingError('PRE_LOGICAL_IDENTITY:' + key)
        accepted_id = logical_id
        accepted_unit = unit
        if logical['terminal_method_status'] != 'ACCEPTED':
            classification = x.classify_infrastructure_recovery(method=read_json(call / 'method_result.json'),
                attempt=read_json(call / 'attempt_000.json'), transport_meta=read_json(call / 'transport_http_meta.json'))
            authority = binding.get('bounded_pre_recovery_authority')
            if not classification['eligible'] or not isinstance(authority, dict):
                raise BindingError('PRE_RECOVERY_NOT_AUTHORIZED_OR_NOT_ELIGIBLE_NO_RESEND')
            auth = read_ref(authority)
            if auth.get('maximum_provider_recovery_calls') != 1 or auth.get('same_logical_call_resend_authorized') is not False:
                raise BindingError('PRE_RECOVERY_AUTHORITY_INVALID')
            remediation_id = core.domain_hash('V1232X_PRE_INFRASTRUCTURE_REMEDIATION_UNIT_V1', {
                'original_logical_call_id': logical_id, 'original_scientific_unit_identity_sha256': unit['identity_sha256'],
                'request_body_sha256': rendered['request_body_sha256'], 'recovery_class': classification['recovery_class'],
                'original_failure_class': read_json(call / 'method_result.json')['failure_class'],
                'recovery_authority_sha256': authority['file_sha256']})
            remedial = core.identity(scientific_unit_type='ROUND', scientific_unit_id=remediation_id,
                source_unit_manifest_sha256=blind['blind_input_sha256'], task_set_manifest_sha256=universe['pair_universe_sha256'],
                task_id=None, gamefile_sha256=None, group_manifest_sha256=None,
                round_evidence_package_sha256=tail['terminal_sha256'])
            accepted_id = x.expected_logical_call_id(unit_identity=remedial, round_id=rid, policy_version=pid,
                request_body_sha256=rendered['request_body_sha256'], domain_hash=core.domain_hash)
            accepted_unit = remedial
            call = runtime / accepted_id
            if not (call.exists() or call.is_symlink()):
                core.orch.execute_one(output_root=runtime, unit_identity=remedial, stage_id='R-PRE-PRIMARY-V2',
                    condition_id=None, round_id=rid, policy_version=pid, projection=projection, task_access=access)
            artifact = accept_pre(call, expected=expected(remedial, accepted_id), finalizer=finalize)
        else:
            artifact = accept_pre(call, expected=expected(unit, logical_id), finalizer=finalize)
        strategy_receipt = adopt_pre_strategies(call_dir=call, expected=expected(accepted_unit, accepted_id),
            selected_candidates=selected_candidates(artifact, view), native_finalize=finalize_original_output,
            native_labels=native_labels)
        immutable_json(out / 'PRE_STRATEGY_RECEIPT.json', strategy_receipt)
    handoff = x.freeze_f0f1_handoff(artifact=artifact, pair_view=view, protocol=protocol,
        u_pair_sha=universe['pair_universe_sha256'], pre_artifact_sha=artifact['primary_record_sha256'],
        domain_hash=core.domain_hash)
    immutable_json(out / 'V1232V_PLANNER_BOUND_F0F1_LAUNCH_HANDOFF_V1.json', handoff)
    result = {'schema_id': 'EXACT_CURRENT_ACCEPTED_PRE_REF_V1_6', 'round_id': rid, 'parent_policy_id': pid,
        'accepted_pre_logical_call_id': accepted_id, 'original_pre_logical_call_id': logical_id,
        'artifact': file_ref(call / 'validated_artifact.json'), 'logical_call': file_ref(call / 'logical_call.json'),
        'handoff': file_ref(out / 'V1232V_PLANNER_BOUND_F0F1_LAUNCH_HANDOFF_V1.json'),
        'runtime_manifest': file_ref(out / 'EXACT_RUNTIME_MANIFEST.json'),
        'pre_strategy_receipt': file_ref(out / 'PRE_STRATEGY_RECEIPT.json'),
        'native_labels_source_seal': file_ref(out / 'NATIVE_LABELS_SOURCE_SEAL.json'),
        'selected_state_count': artifact['selected_state_count'],
        'pre_primary_record_sha256': artifact['primary_record_sha256']}
    immutable_json(out / 'ACCEPTED_PRE_REF.json', result)
    return result, handoff
