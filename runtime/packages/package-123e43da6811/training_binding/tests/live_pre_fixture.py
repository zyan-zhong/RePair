from pathlib import Path
import copy, hashlib, importlib.util, json, sys
from types import SimpleNamespace

work, out = map(Path, sys.argv[1:]); repo = work / 'v17/native_bba_full'
sys.path[:0] = [str(work / 'v17/live_adapter'), str(work / 'v17'), str(repo / 'src')]
xroot = work / 'v16/reference/PCHSI_CAMPAIGN_DYNAMIC_STRONG_PLANNER_PRE_RESUME_STABLE_MEMORY_CENSUS_AND_AUTONOMOUS_INFRA_RECOVERY_V1_23_2X'
sys.path.insert(0, str(xroot))
def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value
x = load('existing_x', xroot / 'v1232x_driver.py')
old = load('existing_test', xroot / 'tests/test_v1232x_contracts.py')
compat = load('compat', work / 'reference_g2/PCHSI_PAPER_CRITICAL_CAUSAL_ROUND_EXECUTION_V1_23_3H4_4/structured_output_schema_compatibility.py')
from pchsi.reference_loop.canonical import domain_hash
from pchsi.cognitive_runtime import request_renderer as rr
from pchsi.cognitive_runtime.identity import build_scientific_unit_identity, build_logical_call_record, build_transport_attempt_record
from pchsi.cognitive_runtime.manifest import load_runtime_manifest
from pchsi.evaluation.action_trace import sha256_string_sequence
from exact_bindings import canonical, digest, immutable_json, immutable_bytes, read_json, file_ref
from pre_stage import run_pre
from h44_input import materialize_capture
from training_binding.strategy_source import candidate_evidence_refs
from training_binding.capture import load_captured_pre_strategy_receipt

universe = old.u_pair_fixture(2)
for row in universe['pair_table']:
    row['task_family'] = 'fixture-family'
    row['source_context']['menu_sha256'] = sha256_string_sequence(row['source_context']['admissible_commands'])
    for condition in ('A2', 'A3'):
        candidate = row[condition]['candidate']; candidate.update(schema_id='ANALYZER_REPAIR_CANDIDATE_V1', schema_version=1,
            candidate_kind='FAILURE_REPAIR', source_proposal_sha256=digest(condition.encode()),
            menu_sha256=row['source_context']['menu_sha256'], requires_environment_verification=True,
            live_menu_revalidation_required=True, all_intervention_actions_count_against_environment_budget=True)
        candidate['candidate_sha256'] = domain_hash(candidate['schema_id'], candidate, excluded_field='candidate_sha256')
        row[condition]['candidate_sha256'] = candidate['candidate_sha256']

def fill(schema):
    if 'const' in schema: return copy.deepcopy(schema['const'])
    if 'enum' in schema: return schema['enum'][0]
    kind = schema.get('type')
    if isinstance(kind, list): kind = next(x for x in kind if x != 'null')
    if kind == 'object': return {key: fill(schema['properties'][key]) for key in schema.get('required', [])}
    if kind == 'array': return [fill(schema['items']) for _ in range(schema.get('minItems', 0))]
    if kind == 'boolean': return False
    if kind in ('integer', 'number'): return schema.get('minimum', 0)
    return 'a' * 64 if schema.get('pattern') == '^[0-9a-f]{64}$' else 'fixture'

calls = []
select_any = True
orch = SimpleNamespace(load_runtime_manifest=load_runtime_manifest, validate_stage_output=None, validated_artifact_identity=None)
def execute_one(**kw):
    calls.append(kw)
    rendered = rr.render_stage_request(stage_id=kw['stage_id'], projection=kw['projection'])
    value = fill(rendered['provider_request']['text']['format']['schema'])
    view = kw['projection']['blind_input']['registered_candidate_universe']; contract = kw['projection']['dynamic_contract']
    reviews = []
    for i, row in enumerate(view['pair_table']):
        review = fill(json.loads(x.SCHEMA_PATH.read_bytes())['properties']['state_reviews']['items'])
        review.update(state_index=i, source_state_sha256=row['source_state_sha256'], task_family='fixture-family',
            preferred_condition='A2', preferred_candidate_sha256=row['A2']['candidate_sha256'],
            alternative_condition='A3', alternative_candidate_sha256=row['A3']['candidate_sha256'],
            selected_for_verification=i == 0 and select_any, state_portfolio_disposition='SELECTED' if i == 0 and select_any else 'DEFERRED_LOW_VALUE', verification_cost_branch_runs=10)
        reviews.append(review)
    value.update(round_id=kw['round_id'], blind_input_sha256=kw['projection']['blind_input_sha256'], state_reviews=reviews,
        selected_state_count=1, unused_state_budget=1, selected_source_state_sha256s=[reviews[0]['source_state_sha256']],
        selected_candidate_sha256s=[reviews[0]['preferred_candidate_sha256']], selected_condition_counts={'A2': 1, 'A3': 0},
        selected_bottleneck_id='fixture-bottleneck', primary_record_sha256='0' * 64)
    bottleneck = fill(json.loads(x.SCHEMA_PATH.read_bytes())['properties']['candidate_bottlenecks']['items'])
    bottleneck.update(candidate_id='fixture-bottleneck', status='SELECTED'); value['candidate_bottlenecks'] = [bottleneck]
    value['verification_plan'].update(paired_repetitions_per_state=5, branch_arms_per_repetition=2, branch_runs_per_state=10,
        selected_state_budget_ceiling=2, selected_branch_run_budget=10)
    value['resource_plan']['expected_environment_branch_runs'] = 10
    c = view['pair_table'][0]['A2']['candidate']
    value['training_strategies'] = [{'source_state_sha256': c['source_state_sha256'], 'source_candidate_sha256': c['candidate_sha256'],
        'strategy': {**{key: 'Fixture source-grounded semantic field' for key in ('principal_bottleneck', 'current_subgoal', 'expected_next_event',
            'expected_state_change', 'progress_criterion', 'recovery_trigger', 'fallback_condition')},
            'action': c['exact_action'], 'evidence_refs': candidate_evidence_refs(c)}}]
    if not select_any:
        value.update(selected_state_count=0, unused_state_budget=2, selected_source_state_sha256s=[], selected_candidate_sha256s=[],
            selected_condition_counts={'A2': 0, 'A3': 0}, training_strategies=[])
        value['verification_plan']['selected_branch_run_budget'] = 0
        value['resource_plan']['expected_environment_branch_runs'] = 0
    response = canonical({'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(value)}]}]})
    artifact = orch.validate_stage_output(stage_id=kw['stage_id'], text=json.dumps(value), raw_response_sha256=digest(response), projection=kw['projection'])
    logical_id = x.expected_logical_call_id(unit_identity=kw['unit_identity'], round_id=kw['round_id'], policy_version=kw['policy_version'],
        request_body_sha256=rendered['request_body_sha256'], domain_hash=domain_hash)
    call = Path(kw['output_root']) / logical_id
    expected = dict(logical_call_id=logical_id, scientific_unit_identity_sha256=kw['unit_identity']['identity_sha256'], stage_id=kw['stage_id'],
        condition_id=None, round_id=kw['round_id'], policy_version=kw['policy_version'], request_body_sha256=rendered['request_body_sha256'], runtime_manifest_sha256=rendered['runtime_manifest_sha256'])
    logical = build_logical_call_record(**expected, role='TRAINING_RESEARCHER', terminal_method_status='ACCEPTED', contributing_attempt_id=logical_id + ':0')
    raw_request = canonical(rendered['provider_request'])
    attempt = build_transport_attempt_record(logical_call_id=logical_id, transport_attempt_id=logical_id + ':0', transport_attempt_index=0,
        bytes_transmission_state='CONFIRMED_SENT', retry_class='INITIAL', retry_reason=None, retry_authority='NOT_APPLICABLE', provider_response_id='fixture',
        terminal_attempt_status='SUCCEEDED', ambiguous_post_send_disposition_id=None, raw_request_sha256=digest(raw_request), raw_response_sha256=digest(response),
        input_tokens=None, output_tokens=None, reasoning_tokens=None, latency_ms=None, cost_usd=None)
    for name, data in [('logical_call.json', logical), ('attempt_000.json', attempt), ('validated_artifact.json', artifact)]: immutable_json(call / name, data)
    immutable_bytes(call / 'raw_request.json', raw_request); immutable_bytes(call / 'raw_response.json', response)
orch.execute_one = execute_one
x.partition_predecessor_memory_candidates = lambda inputs, **kw: (inputs, [])
x.resolve_stable_memory_authority = lambda *a, **kw: {'train_side_records': []}
core = SimpleNamespace(x=x, repo=repo, domain_hash=domain_hash, schema_compatibility=compat, rr=rr, orch=orch, identity=build_scientific_unit_identity,
    researcher_purpose=SimpleNamespace(ROUND_RESEARCH_PLANNING='fixture'),
    researcher_view=lambda **kw: SimpleNamespace(to_dict=lambda: {'view_sha256': 'c' * 64, **kw}))
binding = {'round_id': 'native-pre-fixture', 'parent_policy_id': 'fixture-parent', 'refs': {},
    'source_registration': {'scientific_repo_head': 'bba400738a7a53d0402552ecc3576f736ca0eec8', 'scientific_git_object_root': str(work / 'v17/registered_git_cache')}}
values = {'f0f1_protocol': old.protocol(), 'request': {'round_start_memory_snapshot_sha256': 'd' * 64}, 'researcher_view': {'fixture': True, 'heldout_aggregate_metrics': {}}, 'runtime_manifest': load_runtime_manifest()}
pre_root = out / 'pre'
accepted, handoff = run_pre(binding, values, core, {'terminal_sha256': 'e' * 64}, universe, pre_root)
assert len(calls) == 1 and handoff['selected_state_count'] == 1
again, _ = run_pre(binding, values, core, {'terminal_sha256': 'e' * 64}, universe, pre_root)
assert again == accepted and len(calls) == 1
receipt = read_json(Path(accepted['pre_strategy_receipt']['path']))
assert receipt['source_pre_primary_record_sha256'] == accepted['pre_primary_record_sha256']
assert 'training_strategies' not in read_json(Path(accepted['artifact']['path']))
assert read_json(pre_root / 'NATIVE_LABELS_SOURCE_SEAL.json')['registered_git_bytes_verified'] is True

# Exercise actual capture transport with a separately native-validated empty
# portfolio fixture. It is never passed to the live round dispatcher.
select_any = False
pre_root = out / 'empty_portfolio_pre'
accepted, handoff = run_pre(binding, values, core, {'terminal_sha256': 'e' * 64}, universe, pre_root)
receipt = read_json(Path(accepted['pre_strategy_receipt']['path']))
request_path, runtime_path = out / 'request.json', out / 'runtime.json'
immutable_json(request_path, {'round_id': binding['round_id']}); immutable_json(runtime_path, {'fixture': True})
binding['refs'].update(request=file_ref(request_path), actor_runtime=file_ref(runtime_path))
capture = materialize_capture(binding, values, core, pre_root, accepted, handoff, {}, out / 'capture')
import zipfile
extract = out / 'extracted'
with zipfile.ZipFile(capture['path']) as archive: archive.extractall(extract)
loaded = load_captured_pre_strategy_receipt(extract)
assert loaded.receipt == receipt
expected_raw = {ref['path']: Path(ref['path']).read_bytes() for ref in (receipt[k] for k in
    ('accepted_pre_ref', 'accepted_raw_request_ref', 'accepted_raw_response_ref', 'accepted_logical_ref', 'accepted_attempt_ref'))}
pre_root.rename(out / 'detached_original_pre')
for ref in (receipt[k] for k in ('accepted_pre_ref', 'accepted_raw_request_ref', 'accepted_raw_response_ref', 'accepted_logical_ref', 'accepted_attempt_ref')):
    assert loaded.read_ref(ref) == expected_raw[ref['path']]
loaded.validate()
print('NATIVE_PRE_SAME_CALL_CAPTURE_PASS')
