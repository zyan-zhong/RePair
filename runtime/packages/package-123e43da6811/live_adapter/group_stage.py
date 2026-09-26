"""Wire existing U scientific builders; fresh G uses its existing execution core."""
from pathlib import Path

from exact_bindings import BindingError, read_json, immutable_json, canonical
from local_stage import sealed


def run_group_tail(binding, values, core, prepared, accesses, out):
    out = Path(out); api = core.api; rid = binding['round_id']; pid = binding['parent_policy_id']
    snapshot_sha = values['request']['round_start_memory_snapshot_sha256']
    snapshot = api['load_calibrated_dev_snapshot_v2'](
        snapshot_directory=Path(binding['analyzer_snapshot_directory']),
        expected_snapshot_sha256=snapshot_sha,
        token_budget_contract_path=Path(binding['refs']['analyzer_token_contract']['path']),
        expected_token_budget_contract_sha256=values['request']['token_budget_contract_sha256'])
    universe = api['build_group_universe'](round_id=rid,
        group_manifest_sha256s=[p['group']['group_manifest_sha256'] for p in prepared])
    immutable_json(out / 'CLEAN_ANALYZER_GROUP_UNIVERSE_V1.json', universe)
    group_stages = [x for x in values['runtime_manifest']['stage_rows'] if x['stage_id'] in ('G-A2', 'G-A3')]
    prep_sha = core.domain_hash('EXACT_REGISTERED_GROUP_PREPARATION_V1',
        [{'manifest': p['group']['group_manifest_sha256'], 'synthesis': p['synthesis']['group_synthesis_input_sha256']} for p in prepared])
    budget = api['build_round_group_analyzer_resource_authority'](round_id=rid, policy_version=pid,
        producer_role='REFERENCE_EXPERIMENT_CONTRACT', source_authority_sha256=prep_sha,
        group_universe=universe, group_stage_rows=group_stages)
    api['validate_round_group_analyzer_resource_authority'](budget)
    immutable_json(out / 'ROUND_GROUP_ANALYZER_RESOURCE_AUTHORITY_V1.json', budget)
    runtime = out / 'strong_group_runtime'; accepted = []; census = []; contexts = []
    counts = {'g_complete_pair': 0, 'g_quarantined': 0, 'g_incomplete': 0,
              'provider_calls': 0, 'terminal_reuse': 0, 'c_requested': 0, 'x_requested': 0}

    def identity(gid, source_sha, group_sha):
        return core.identity(scientific_unit_type='GROUP', scientific_unit_id=gid,
            source_unit_manifest_sha256=source_sha, task_set_manifest_sha256=universe['group_universe_sha256'],
            task_id=None, gamefile_sha256=None, group_manifest_sha256=group_sha,
            round_evidence_package_sha256=binding['refs']['handoff']['file_sha256'])

    def call(stage, condition, unit, projection, access):
        result = core.u.execute_or_reuse(runtime_root=runtime, unit_identity=unit,
            stage_id=stage, condition_id=condition, round_id=rid, policy_version=pid,
            projection=projection, task_access=access, api=api, domain_hash=core.domain_hash)
        counts['terminal_reuse' if result.get('reused_terminal_call') else 'provider_calls'] += 1
        if result.get('hard_stop') and result.get('status') != 'AMBIGUOUS_POST_SEND':
            raise BindingError('GROUP_GLOBAL_HARD_STOP:' + stage + ':' + str(result['status']))
        return result

    for p in sorted(prepared, key=lambda x: x['group']['group_id']):
        group = p['group']; gid = group['group_id']; directory = out / 'groups' / gid
        contexts.extend(p['contexts'])
        memory = core.u.build_group_memory_pack(contexts=p['contexts'], snapshot=snapshot,
                                               api=api, domain_hash=core.domain_hash)
        memory_path = directory / 'analyzer_memory_pack.json'; immutable_json(memory_path, memory)
        access = api['build_clean_group_task_access_record'](round_id=rid, group_id=gid,
            group_manifest_sha256=group['group_manifest_sha256'], member_contexts=p['contexts'],
            task_access_by_source_unit=accesses)
        paths = {'group_manifest_path': p['root'] / 'group_manifest.json',
                 'group_synthesis_input_path': p['root'] / 'group_synthesis_input.json',
                 'a1_local_result_paths': p['a1_paths'], 'source_contexts_path': p['root'] / 'source_contexts.json'}
        pa2 = api['group_projection_v3'](**paths, memory_pack_path=None)
        pa3 = api['group_projection_v3'](**paths, memory_pack_path=memory_path)
        if core.u.strip_memory_projection(pa2) != core.u.strip_memory_projection(pa3):
            raise BindingError('GROUP_COMMON_EVIDENCE_MISMATCH')
        common_path = directory / 'projection_G_A2.json'; immutable_json(common_path, pa2)
        immutable_json(directory / 'projection_G_A3.json', pa3)
        unit = identity(gid, p['synthesis']['group_synthesis_input_sha256'], group['group_manifest_sha256'])
        results = {}; quarantined = False
        for stage, condition, projection in [('G-A2', 'A2', pa2), ('G-A3', 'A3', pa3)]:
            result = call(stage, condition, unit, projection, access); results[condition] = result
            if result.get('hard_stop') and result['status'] == 'AMBIGUOUS_POST_SEND':
                quarantined = True; break
        complete = all(results.get(c, {}).get('status') == 'ACCEPTED' for c in ('A2', 'A3'))
        counts['g_complete_pair' if complete else ('g_quarantined' if quarantined else 'g_incomplete')] += 1
        census.append({'group_id': gid, **results, 'complete_pair': complete, 'quarantined_ambiguous': quarantined})
        if complete:
            for stage in ('G-A2', 'G-A3'):
                result = core.u.formal_group_stage_result(results, stage)
                path = Path(result['call_dir']) / 'validated_artifact.json'; artifact = read_json(path)
                if api['validated_artifact_identity'](stage_id=stage, artifact=artifact) != result['validated_artifact_sha256']:
                    raise BindingError('GROUP_ACCEPTED_ARTIFACT_MISMATCH')
                accepted.append({'group_id': gid, 'stage': stage, 'path': path, 'artifact': artifact,
                    'access': access, 'group_path': paths['group_manifest_path'],
                    'common_path': common_path, 'memory_path': memory_path})
    if not accepted:
        raise BindingError('NO_COMPLETE_G_PAIRS_REQUIRES_EXISTING_GOVERNANCE')
    attributions = []; x_by_sha = {}; c_records = []; x_records = []
    for item in accepted:
        art = item['artifact']; gsha = art['group_result_sha256']; gid = item['group_id']
        unit = identity(gid + '::' + item['stage'], gsha, art['group_manifest_sha256'])
        result = call('C', None, unit, api['component_projection'](item['path']), item['access'])
        counts['c_requested'] += 1; c_records.append(result)
        if result['status'] == 'ACCEPTED':
            attributions.append(read_json(Path(result['call_dir']) / 'validated_artifact.json'))
    profile = api['aggregate_capability_profile'](attributions,
        registered_group_results={x['artifact']['group_result_sha256']: x['artifact'] for x in accepted})
    behavior = api['build_policy_behavior_profile'](profile)
    immutable_json(out / 'ANALYZER_CAPABILITY_PROFILE_V1.json', profile)
    immutable_json(out / 'ANALYZER_POLICY_BEHAVIOR_PROFILE_V1.json', behavior)
    for item in accepted:
        art = item['artifact']; gsha = art['group_result_sha256']
        if not art.get('source_conditioned_proposals'):
            continue
        projection = api['crosscheck_projection_v2'](target_path=item['path'], target_stage_id=item['stage'],
            group_manifest_path=item['group_path'], common_group_projection_path=item['common_path'],
            memory_pack_path=item['memory_path'] if item['stage'] == 'G-A3' else None)
        unit = core.identity(scientific_unit_type='CROSSCHECK_TARGET', scientific_unit_id=gsha,
            source_unit_manifest_sha256=gsha, task_set_manifest_sha256=universe['group_universe_sha256'],
            task_id=None, gamefile_sha256=None, group_manifest_sha256=art['group_manifest_sha256'],
            round_evidence_package_sha256=binding['refs']['handoff']['file_sha256'])
        result = call('X', None, unit, projection, item['access'])
        counts['x_requested'] += 1; x_records.append(result)
        if result['status'] == 'ACCEPTED':
            x_by_sha[gsha] = read_json(Path(result['call_dir']) / 'validated_artifact.json')
    # These are existing U rules, using exact source contexts rather than root discovery.
    index = core.u.index_source_contexts(contexts); candidates = {}; metas = {}; missing = set()
    for item in accepted:
        art = item['artifact']; gsha = art['group_result_sha256']; condition = item['stage'][2:]
        for proposal in art.get('source_conditioned_proposals', []):
            state = proposal['source_state_sha256']
            if gsha not in x_by_sha:
                missing.add((state, condition)); continue
            disposition = x_by_sha[gsha]['disposition']
            candidate = api['project_candidate'](proposal=proposal,
                source_state=core.u.source_context_for_candidate_projection(index[state]),
                candidate_kind='FAILURE_REPAIR', crosscheck_disposition=disposition)
            candidates.setdefault((state, condition), []).append(candidate)
            metas.setdefault((state, condition, candidate['candidate_sha256']), []).append({
                'group_result_sha256': gsha, 'formal_x_disposition': disposition})
    pairs = []; materializations = []; collisions = 0
    for state in sorted(index):
        mats = {}
        for condition in ('A2', 'A3'):
            mats[condition] = api['materialize_state_condition_k1'](condition_id=condition,
                source_state_sha256=state, candidates=candidates.get((state, condition), []),
                zero_candidate_disposition='METHOD_X_UNAVAILABLE' if (state, condition) in missing else 'NO_FORMAL_PROPOSAL')
            materializations.append(mats[condition])
            collisions += mats[condition]['formal_disposition'] == 'METHOD_INVALID_K1_STATE_BUDGET_COLLISION'
        if not all(mats[c]['formal_disposition'] == 'FORMAL_CANDIDATE_REGISTERED' for c in ('A2', 'A3')):
            continue
        pair = {'state_index': len(pairs), 'source_state_sha256': state,
                'source_context': core.u.source_context_for_candidate_projection(index[state]),
                'source_context_audit': core.u.source_context_audit_summary(index[state])}
        for condition in ('A2', 'A3'):
            csha = mats[condition]['selected_candidate_sha256']
            selected = [x for x in candidates[(state, condition)] if x['candidate_sha256'] == csha]
            if len({canonical(x) for x in selected}) != 1:
                raise BindingError('CANDIDATE_HASH_BYTES_CONFLICT')
            provenance = metas[(state, condition, csha)]
            pair[condition] = {'candidate_sha256': csha, 'candidate': selected[0],
                'selected_execution_identity_sha256': mats[condition]['selected_execution_identity_sha256'],
                'candidate_provenance': provenance,
                'group_result_sha256s': sorted({x['group_result_sha256'] for x in provenance}),
                'formal_x_dispositions': sorted({x['formal_x_disposition'] for x in provenance})}
        pairs.append(pair)
    tail = sealed(core, 'V1232U_STRONG_ANALYZER_TAIL_TERMINAL_V1', {
        'status': 'STRONG_ANALYZER_G_A2_A3_C_P_X_CLOSED', 'round_id': rid, 'parent_policy_id': pid,
        'source_closed_group_count': len(prepared), 'g_complete_pair_group_count': counts['g_complete_pair'],
        'profile_sha256': profile['profile_sha256'], 'policy_profile_sha256': behavior['policy_profile_sha256'],
        'deterministic_p_materialized': True, 'environment_call_count': 0,
        'training_execution_count': 0, 'human_scientific_decision_count': 0}, 'terminal_sha256')
    pair_universe = sealed(core, 'V1232U_DYNAMIC_PLANNER_PAIR_UNIVERSE_V1', {
        'round_id': rid, 'parent_policy_id': pid, 'analyzer_tail_terminal_sha256': tail['terminal_sha256'],
        'complete_pair_count': len(pairs), 'pair_table': pairs, 'k1_collision_count': collisions,
        'legacy_fixed_cardinality_assumed': False, 'dynamic_pre_v2_required': True,
        'environment_call_count': 0, 'training_execution_count': 0, 'human_pair_selection_count': 0}, 'pair_universe_sha256')
    immutable_json(out / 'V1232U_STRONG_ANALYZER_TAIL_TERMINAL_V1.json', tail)
    immutable_json(out / 'V1232U_DYNAMIC_PLANNER_PAIR_UNIVERSE_V1.json', pair_universe)
    # Stable scientific census excludes invocation-dependent provider/reuse counts.
    immutable_json(out / 'GROUP_STAGE_RESULTS.json', {'groups': [
        {'group_id': x['group_id'], 'complete_pair': x['complete_pair'],
         'quarantined_ambiguous': x['quarantined_ambiguous'],
         'calls': {k: x[k]['logical_call_id'] for k in ('A2', 'A3') if k in x}} for x in census],
        'c_calls': [x['logical_call_id'] for x in c_records], 'x_calls': [x['logical_call_id'] for x in x_records],
        'materializations': materializations})
    return tail, pair_universe
