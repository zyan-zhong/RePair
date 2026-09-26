"""Current-round Q materialization and existing ACT3 grouping, with exact refs."""
from pathlib import Path

from exact_bindings import (BindingError, canonical, digest, read_json, immutable_bytes,
                            immutable_json, file_ref)


def sealed(core, schema, fields, field):
    value = {'schema_id': schema, 'schema_version': 1, **fields, field: '0' * 64}
    value[field] = core.domain_hash(schema, value, excluded_field=field)
    return value


def materialize_local(binding, values, core, out):
    out = Path(out).absolute()
    req, handoff = values['request'], values['handoff']
    rid, pid = binding['round_id'], binding['parent_policy_id']
    hsha = binding['refs']['handoff']['file_sha256']
    if handoff.get('scientific_rollout_valid') is not True:
        raise BindingError('ROLLOUT_NOT_SCIENTIFICALLY_VALID')
    for name in ('infrastructure_invalid_count', 'protocol_invalid_count'):
        if handoff.get(name) != 0:
            raise BindingError('ROLLOUT_INVALID:' + name)
    for name in ('human_selection_performed', 'benchmark_feedback_used',
                 'memory_writeback_performed', 'training_execution_performed'):
        if handoff.get(name) is not False:
            raise BindingError('ROLLOUT_GOVERNANCE:' + name)
    if values['global_terminal'].get('scientific_rollout_valid') is not True:
        raise BindingError('GLOBAL_TERMINAL_NOT_VALID')
    if values['cohort'].get('human_selection_performed') is not False:
        raise BindingError('COHORT_SELECTION_NOT_FROZEN')
    stages = [dict(x) for x in values['runtime_manifest']['stage_rows'] if x['stage_id'] in ('L-A0', 'L-A1')]
    if {x['stage_id'] for x in stages} != {'L-A0', 'L-A1'} or len(stages) != 2:
        raise BindingError('LOCAL_RUNTIME_STAGES_INVALID')
    target = values['experiment_contract']['main_unique_states_target']
    if type(target) is not int or target <= 0:
        raise BindingError('EXPERIMENT_TARGET_INVALID')
    cap = target * sum(int(x['logical_call_budget_per_unit']) for x in stages)
    budget = core.clean.build_round_analyzer_resource_budget(round_id=rid, policy_version=pid,
        producer_role='REFERENCE_EXPERIMENT_CONTRACT', source_authority_sha256=hsha,
        local_stage_rows=stages, local_logical_call_cap=cap)
    failure_ids = values['cohort']['failure_scientific_cell_ids']
    if not failure_ids:
        raise BindingError('EMPTY_FAILURE_COHORT_REQUIRES_EXISTING_CAMPAIGN_GOVERNANCE')
    resolved, reconciliation = core.q.recover_bundle_authorities(state_root=Path(binding['state_root']),
        handoff=handoff, index=values['bundle_index'], failure_ids=failure_ids,
        attempt_receipt_type=core.api['AttemptReceiptV1'], episode_artifact_type=core.api['EpisodeArtifactV1'])
    source_sha = handoff['rollout_request_sha256']
    failure_rows = []
    for cid in failure_ids:
        row = resolved[cid]
        failure_rows.append({'classification': 'TASK_FAILURE', 'source_campaign_sha256': source_sha,
            'policy_interface_profile_id': 'I1_EXECUTION_PROFILE_V1', 'scientific_cell_id': cid,
            **{k: row[k] for k in ('execution_attempt_id', 'task_id', 'task_type', 'gamefile_sha256',
                                   'attempt_bundle_sha256', 'episode_semantic_sha256')}})
    universe = core.q.canonical_jsonl_bytes(failure_rows)
    selected = core.clean.select_failure_only_u_reg(failure_rows=failure_rows,
        resource_budget=budget, source_campaign_sha256=source_sha)
    bundles = {}
    for row in selected:
        authority = resolved[row['scientific_cell_id']]
        bundle = core.validate_bundle(Path(authority['bundle_path']))
        if (bundle.attempt_bundle_sha256, bundle.episode_semantic_sha256, bundle.task_id) != (
                authority['attempt_bundle_sha256'], authority['episode_semantic_sha256'], authority['task_id']):
            raise BindingError('SOURCE_BUNDLE_AUTHORITY_MISMATCH')
        sid = core.domain_hash('V1232Q_ANALYZER_SOURCE_UNIT_ID_V1', {'round_id': rid,
            'scientific_cell_id': row['scientific_cell_id'], 'attempt_bundle_sha256': bundle.attempt_bundle_sha256,
            'handoff_sha256': hsha})
        row.update(source_unit_id=sid, gamefile_sha256=bundle.gamefile_sha256)
        bundles[sid] = bundle
    ureg = core.clean.build_local_u_reg_manifest(round_id=rid, policy_version=pid,
        evidence_cutoff_sha256=hsha, failure_universe_file_sha256=digest(universe),
        source_campaign_sha256=source_sha, resource_budget=budget, selected_units=selected)
    immutable_bytes(out / 'CURRENT_ROUND_TRAIN_UPDATE_FAILURE_UNIVERSE_V1.jsonl', universe)
    immutable_json(out / 'ROUND_ANALYZER_RESOURCE_BUDGET_V1.json', budget)
    immutable_json(out / 'CLEAN_ANALYZER_LOCAL_U_REG_V1.json', ureg)
    immutable_json(out / 'V1232Q_SOURCE_ROLLOUT_HANDOFF_COPY.json', handoff)
    units, access_rows, source_rows = [], [], []
    for rank, row in enumerate(selected):
        sid = row['source_unit_id']; bundle = bundles[sid]; root = out / 'units' / sid
        pack = core.q.evidence_pack(bundle, round_id=rid, parent_policy_id=pid, handoff_sha=hsha,
            memory_snapshot_sha=req['round_start_memory_snapshot_sha256'],
            mechanical=core.mechanical(bundle), domain_hash=core.domain_hash)
        if core.route(pack).get('trajectory_outcome') != 'FAILURE':
            raise BindingError('SELECTED_PACK_NOT_FAILURE')
        immutable_json(root / 'analyzer_evidence_pack.json', pack)
        projection = core.projections.local_projection(root / 'analyzer_evidence_pack.json')
        immutable_json(root / 'local_projection.json', projection)
        access = core.clean.build_clean_analyzer_task_access_record(round_id=rid, source_unit_id=sid,
            task_id=bundle.task_id, gamefile_sha256=bundle.gamefile_sha256,
            source_campaign_sha256=source_sha, evidence_cutoff_sha256=hsha)
        immutable_json(root / 'task_access_record.json', access)
        manifest = sealed(core, 'V1232Q_ANALYZER_SOURCE_UNIT_MANIFEST_V1', {
            'round_id': rid, 'source_unit_id': sid, 'selection_rank': rank,
            'scientific_cell_id': row['scientific_cell_id'], 'execution_attempt_id': bundle.episode['execution_attempt_id'],
            'task_id': bundle.task_id, 'task_type': bundle.episode.get('task_type'),
            'gamefile_sha256': bundle.gamefile_sha256, 'attempt_bundle_path': str(bundle.bundle_root),
            'attempt_bundle_sha256': bundle.attempt_bundle_sha256, 'episode_semantic_sha256': bundle.episode_semantic_sha256,
            'evidence_pack_sha256': pack['evidence_pack_sha256'], 'rollout_handoff_sha256': hsha}, 'source_unit_manifest_sha256')
        immutable_json(root / 'source_unit_manifest.json', manifest)
        identity = core.identity(scientific_unit_type='EPISODE', scientific_unit_id=sid,
            source_unit_manifest_sha256=manifest['source_unit_manifest_sha256'], task_set_manifest_sha256=ureg['u_reg_sha256'],
            task_id=bundle.task_id, gamefile_sha256=bundle.gamefile_sha256,
            group_manifest_sha256=None, round_evidence_package_sha256=hsha)
        immutable_json(root / 'scientific_unit_identity.json', identity)
        access_rows.append({'source_unit_id': sid, 'task_access_record_path': str((root / 'task_access_record.json').relative_to(out)),
                            'task_access_record_sha256': access['task_access_sha256']})
        for stage, condition in (('L-A0', 'A0'), ('L-A1', 'A1')):
            units.append({'source_unit_id': sid, 'stage_id': stage, 'condition_id': condition,
                **{key: str((root / filename).relative_to(out)) for key, filename in (
                    ('scientific_unit_identity_path', 'scientific_unit_identity.json'),
                    ('input_projection_path', 'local_projection.json'), ('task_access_record_path', 'task_access_record.json'))},
                'expected_common_evidence_sha256': pack['evidence_pack_sha256'],
                'expected_a1_local_result_sha256': None, 'expected_memory_pack_sha256': None})
        source_rows.append({'source_unit_id': sid, 'source_manifest': file_ref(root / 'source_unit_manifest.json')})
    access_manifest = sealed(core, 'CLEAN_ANALYZER_TASK_ACCESS_MANIFEST_V1', {'round_id': rid,
        'source_campaign_sha256': source_sha, 'evidence_cutoff_sha256': hsha,
        'row_count': len(access_rows), 'rows': access_rows}, 'manifest_sha256')
    access_path = out / 'CLEAN_ANALYZER_TASK_ACCESS_MANIFEST_V1.json'
    immutable_json(access_path, access_manifest)
    registry = sealed(core, 'RUNTIME_INPUT_REGISTRY_V1', {'registry_role': 'FORMAL_A0_A3',
        'round_id': rid, 'policy_version': pid, 'task_access_manifest_sha256': digest(access_path.read_bytes()),
        'units': units}, 'registry_sha256')
    core.validate_artifact('RUNTIME_INPUT_REGISTRY_V1', registry)
    registry_path = out / 'CLEAN_ANALYZER_LOCAL_RUNTIME_INPUT_REGISTRY_V1.json'
    immutable_json(registry_path, registry)
    immutable_json(out / 'SOURCE_UNITS.json', {'rows': source_rows})
    return registry_path


def prepare_groups(binding, core, local_root, execution):
    root = Path(local_root); rid = binding['round_id']; pid = binding['parent_policy_id']
    if execution.get('terminal_route') is not None:
        raise BindingError('LOCAL_GLOBAL_FAIL_CLOSED:' + str(execution['terminal_route']))
    registry = read_json(root / 'CLEAN_ANALYZER_LOCAL_RUNTIME_INPUT_REGISTRY_V1.json')
    if execution.get('registry_sha256') != registry['registry_sha256']:
        raise BindingError('LOCAL_EXECUTION_REGISTRY_MISMATCH')
    if len(execution['rows']) != len(registry['units']):
        raise BindingError('LOCAL_EXECUTION_NOT_FULL_FROZEN_REGISTRY')
    by_source = {}
    for row, unit in zip(execution['rows'], registry['units'], strict=True):
        for field in ('source_unit_id', 'stage_id', 'condition_id'):
            if row.get(field) != unit.get(field):
                raise BindingError('LOCAL_ROW_UNIT_MISMATCH:' + field)
        by_source.setdefault(row['source_unit_id'], {})[row['stage_id']] = row
    locals_, signatures, contexts, a1_paths, accesses, source_lookup, censored = [], [], {}, {}, {}, {}, []
    for sid, rows in by_source.items():
        if not all(rows.get(stage, {}).get('status') == 'ACCEPTED' for stage in ('L-A0', 'L-A1')):
            censored.append(sid); continue
        unit = root / 'units' / sid
        sm = read_json(unit / 'source_unit_manifest.json')
        bundle = core.api['load_attempt_directory_v1'](Path(sm['attempt_bundle_path']))
        if bundle.attempt_bundle.attempt_bundle_sha256 != sm['attempt_bundle_sha256']:
            raise BindingError('GROUP_SOURCE_BUNDLE_MISMATCH')
        a1path = Path(rows['L-A1']['call_dir']) / 'validated_artifact.json'; a1 = read_json(a1path)
        if a1['local_result_sha256'] != rows['L-A1']['validated_artifact_sha256']:
            raise BindingError('A1_ARTIFACT_MISMATCH')
        locals_.append(a1); a1_paths[a1['local_result_sha256']] = a1path
        accesses[sid] = read_json(unit / 'task_access_record.json')
        pack = read_json(unit / 'analyzer_evidence_pack.json')
        traces = {x.model_call_index: x for x in bundle.traces}
        calls = {x.model_call_index: x for x in bundle.policy_calls}
        for error in a1['error_instances']:
            signatures.append(core.api['build_group_signature_binding'](local_result=a1, error=error,
                evidence_pack=pack, action_traces_by_call=traces))
            selected = core.api['select_dev_source_call'](local_result=a1, error=error)
            if selected.get('formal_eligible') is not True:
                continue
            ci = selected['source_call_index']; call = calls.get(ci)
            if call is None:
                continue
            state = core.domain_hash('V1232Q_CURRENT_ROUND_ANALYZER_GROUP_SOURCE_CONTEXT_V1', {
                'round_id': rid, 'parent_policy_id': pid, 'source_unit_id': sid,
                'source_bundle_sha256': sm['attempt_bundle_sha256'], 'model_call_index': ci,
                'observation_sha256': call.observation_sha256, 'menu_sha256': call.admissible_commands_sequence_sha256,
                'executed_history_sha256': call.executed_history_sha256, 'prompt_sha256': call.prompt_sha256,
                'round_start_memory_snapshot_sha256': binding['_request']['round_start_memory_snapshot_sha256']})
            context = {'source_unit_id': sid, 'local_result_sha256': a1['local_result_sha256'],
                'error_instance_id': error['error_instance_id'], 'source_state_sha256': state,
                'menu_sha256': call.admissible_commands_sequence_sha256, 'source_call_index': ci,
                'public_task_goal': call.public_task_goal, 'observation': call.observation,
                'admissible_commands': list(call.admissible_commands),
                'executed_history': [{'action': a, 'resulting_observation': o} for a, o in call.executed_history],
                'interface_feedback_before': call.interface_feedback_before, 'budget_before': dict(call.budget_before),
                'source_context_identity_role': 'ANALYZER_GROUP_BINDING_ONLY_F0F1_REPLAY_REBIND_REQUIRED'}
            key = (a1['local_result_sha256'], error['error_instance_id'])
            if key in contexts:
                raise BindingError('DUPLICATE_GROUP_SOURCE_CONTEXT')
            contexts[key] = context
            source_lookup[state] = {'source_unit_id': sid, 'bundle_path': sm['attempt_bundle_path'],
                'bundle_sha256': sm['attempt_bundle_sha256'], 'source_call_index': ci, 'context': context}
    if not signatures:
        raise BindingError('NO_A1_SIGNATURES_REQUIRES_EXISTING_CAMPAIGN_GOVERNANCE')
    groups = core.api['build_group_manifests'](local_results=locals_,
        mechanical_signatures={(s['local_result_sha256'], s['error_instance_id']): s for s in signatures})
    closed, partial, absent = core.q.classify_source_closed_groups(groups, contexts)
    if not closed:
        raise BindingError('NO_SOURCE_CLOSED_GROUPS')
    synths = core.api['build_group_synthesis_inputs'](closed, source_bindings=contexts)
    prepared = []
    for group, synth in zip(closed, synths, strict=True):
        directory = root / 'groups' / group['group_id']
        members = [contexts[(m['local_result_sha256'], m['error_instance_id'])] for m in synth['member_rows']]
        for filename, value in [('group_manifest.json', group), ('group_synthesis_input.json', synth), ('source_contexts.json', members)]:
            immutable_json(directory / filename, value)
        prepared.append({'group': group, 'synthesis': synth, 'contexts': members, 'root': directory,
            'a1_paths': [a1_paths[m['local_result_sha256']] for m in synth['member_rows']]})
    immutable_json(root / 'GROUP_PREPARATION_CENSUS.json', {'round_id': rid, 'complete_groups': len(closed),
        'partial_groups': len(partial), 'no_source_groups': len(absent), 'censored_sources': censored,
        'group_refs': [file_ref(p['root'] / 'group_manifest.json') for p in prepared],
        'sources': source_lookup})
    return prepared, accesses, source_lookup
