"""Call the real Stage0 cell owner and episode evaluator with native test doubles.

Only environment/transport/tokenizer/publication I/O are fixtures; no GPU, model,
environment task or scientific campaign runs in these tests.
"""
from functools import partial
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import sys
import os
from types import SimpleNamespace, ModuleType

from test_binding import fixture, REPO
from offoff_binding.materialize import prepare
from offoff_binding.execute import _audit_one
from continuity_binding.api import write_once, read_ref
from pchsi.evaluation.canonical_evidence import canonical_json_bytes
from pchsi.evaluation.alfworld_contracts import StepPublicState, GamefileIdentityLatch, ResetPublicState
from pchsi.evaluation.select_execution_identity import build_select_i1_execution_profile, validate_select_execution_profile_binding
from pchsi.evaluation.budget import BudgetLimits
from pchsi.evaluation.schema_models import EpisodeArtifactV1
from pchsi.evaluation.select_result_audit import ExpectedSelectCellV1


def test_original_cell_owner_invokes_real_i1_evaluator(tmp_path, monkeypatch):
    if sys.platform == 'win32':
        # Test-only import bridge. The Linux live entrypoint rejects Windows.
        shim = ModuleType('fcntl'); shim.LOCK_EX = 1; shim.LOCK_UN = 2
        shim.flock = lambda *_: None
        monkeypatch.setitem(sys.modules, 'fcntl', shim)
    args = fixture(tmp_path, lora_parent=True)
    context = prepare(**args)
    native = args['native']
    live, audit, aggregate, server, types, loader = native.runners()
    if sys.platform == 'win32':
        monkeypatch.setattr(sys.modules['stage0.common'], 'fsync_directory', lambda *_: None)
        import pchsi.evaluation.artifact_publisher as publication
        monkeypatch.setattr(publication, '_fsync_directory', lambda *_: None)
        def binary_write(*, path, payload, fsync_file):
            with path.open('xb') as handle:
                handle.write(payload); handle.flush()
                if fsync_file:
                    os.fsync(handle.fileno())
        monkeypatch.setattr(publication, '_write_file_no_clobber', binary_write)
        def fsync_writable_file(path):
            with path.open('r+b') as handle:
                os.fsync(handle.fileno())
        monkeypatch.setattr(publication, '_fsync_file', fsync_writable_file)
        monkeypatch.setattr(publication, '_rename_directory_native_noreplace',
                            publication._rename_directory_guarded_posix)
    source = REPO / 'tests/evaluation/test_interface_isolation_evaluator.py'
    spec = importlib.util.spec_from_file_location('_native_offoff_test_io', source)
    io = importlib.util.module_from_spec(spec); spec.loader.exec_module(io)
    environment = io._Environment(steps=[StepPublicState(observation='Done', menu=io._menu(('look',)), score=1, done=True, won=True)])
    environment.reset = lambda: ResetPublicState(observation='Your task is to: inspect the room\nYou are in a room.',
        menu=io._menu(('look', 'inventory')), gamefile_latch=GamefileIdentityLatch(
            resolved_gamefile=context['access'].records[0].gamefile))
    transport_calls = []
    class Transport:
        def post_exact(self, *, path, body, headers):
            request = json.loads(body); transport_calls.append(request)
            value = {'id': 'fixture-provider', 'model': request['model'],
                'choices': [{'message': {'content': '{"action":"look"}'}, 'finish_reason': 'stop', 'token_ids': [4, 5]}],
                'usage': {'prompt_tokens': 3, 'completion_tokens': 2}, 'prompt_token_ids': [1, 2, 3]}
            return 200, {'x-request-id': 'fixture-provider', 'content-type': 'application/json'}, canonical_json_bytes(value)
    types['SpawnedAlfworldAdapter'] = SimpleNamespace(start=lambda **_: environment)
    types['LocalTokenizerPromptRenderer'] = lambda **_: io._Renderer()
    types['HuggingFaceTokenizerFactory'] = lambda: object()
    types['HttpPolicyTransport'] = lambda **_: Transport()
    native_evaluator = types['run_single_episode']; results = []
    def capture(**kwargs):
        value = native_evaluator(**kwargs); results.append(value); return value
    types['run_single_episode'] = capture
    i1 = context['protocol']['policy_request_schema_sha256']
    types['build_select_execution_profile'] = lambda identity: build_select_i1_execution_profile(identity, request_contract_sha256=i1)
    types['validate_select_execution_profile_binding'] = lambda *, identity, profile: validate_select_execution_profile_binding(
        identity=identity, profile=profile, expected_request_schema_sha256=i1)
    types['EpisodeExecutionConfig'] = partial(types['EpisodeExecutionConfig'], budget_limits=BudgetLimits(**context['protocol']['episode_budget']))
    live.TASK_ACCESS_SHA256 = context['protocol']['task_access_ref']['sha256']
    live.BASE_MODEL_PATH = Path(context['base']['artifact_root'])
    live.CURRENT_RUN_NAMESPACE = 'fixture-current-offoff'
    condition, runtime, schedule, condition_sha, runtime_sha, schedule_sha = context['bundles']['candidate']
    protocol, infra = context['protocol'], context['infra']
    preflight = {name: protocol[name] for name in ('evaluator_commit', 'runtime_core_commit', 'design_merge_commit', 'raw_protocol_sha256')}
    preflight.update(environment_runtime_manifest_sha256=infra['environment_runtime_ref']['sha256'],
        gamefile_identity_manifest_sha256=infra['gamefile_identity_ref']['sha256'],
        policy_request_schema_sha256=i1, base_model_revision=context['server'].base_model_revision,
        chat_template_sha256=context['server'].chat_template_sha256)
    receipt = live._recover_or_execute_cell(label='candidate', cell=schedule.cells[0],
        task_access_record=context['access'].records[0], condition=condition, runtime=runtime,
        condition_sha=condition_sha, runtime_sha=runtime_sha, schedule_sha=schedule_sha,
        preflight=preflight, base_url='http://127.0.0.1:1', types=types, attempt_auditor=loader,
        condition_root=tmp_path / 'fixture-execution')
    assert receipt['success'] is True
    assert receipt['memory_state'] == receipt['harness_state'] == 'OFF'
    assert transport_calls[0]['model'] == runtime.served_model_name
    assert transport_calls[0]['structured_outputs']['json']
    assert environment.step_calls == ['look']
    assert results[0].attempt_bundle is not None
    evaluator_root = tmp_path / 'fixture-execution/evaluator_run'
    loaded = loader.load_attempt_directory_v1(evaluator_root / 'attempts' / receipt['execution_attempt_id'])
    expected = ExpectedSelectCellV1(schedule_name='candidate', condition_cell_id=schedule.cells[0].condition_cell_id,
        manifest_index=0, task_id=schedule.cells[0].task_id, evaluation_seed=schedule.cells[0].seed,
        policy_condition_manifest_sha256=condition_sha, condition_run_schedule_sha256=schedule_sha)
    _audit_one(audit=audit, native_audit=audit.load_native(native.root), loaded=loaded, row=receipt,
        expected=expected, bundle=context['bundles']['candidate'], protocol=protocol, infra=infra,
        access=context['access'], root=evaluator_root)
    # Native receipt recovery must not invoke the evaluator or transport twice.
    again = live._recover_or_execute_cell(label='candidate', cell=schedule.cells[0],
        task_access_record=context['access'].records[0], condition=condition, runtime=runtime,
        condition_sha=condition_sha, runtime_sha=runtime_sha, schedule_sha=schedule_sha,
        preflight=preflight, base_url='http://127.0.0.1:1', types=types, attempt_auditor=loader,
        condition_root=tmp_path / 'fixture-execution')
    assert again == receipt and len(results) == len(transport_calls) == 1
    # Build all actual native attempts under the native Stage4D partition, then
    # replay original Stage4E audits and aggregate them. Only the decision source
    # here is an explicitly registered fixture, never a production rule.
    import hashlib
    from offoff_binding.materialize import materialize
    from offoff_binding.parallel import materialize_parallel, finalize_parallel
    decider = tmp_path/'fixture_decider.py'
    decider.write_text('def decide(*, frozen_rule, aggregate):\n    assert frozen_rule["fixture_only"]\n    return {"decision":"ROLLBACK","decision_rule_id":frozen_rule["decision_rule_id"]}\n')
    decider_ref = {'path':str(decider),'sha256':hashlib.sha256(decider.read_bytes()).hexdigest()}
    native.sources[str(decider)] = decider_ref
    rule_ref = write_once(tmp_path/'parallel-fixture-rule.json', {'fixture_only':True,'decision_rule_id':'FIXTURE_ONLY',
        'decision_producer':{'source_ref':decider_ref,'entrypoint':'decide'}})
    args['protocol_ref'] = write_once(tmp_path/'parallel-protocol.json', {**protocol,'promotion_rule_ref':rule_ref})
    binding_ref = materialize(**args,sink=tmp_path/'parallel-binding')
    parallel_ref = materialize_parallel(binding_ref,sink=tmp_path/'parallel')
    parallel = read_ref(parallel_ref)
    assert parallel['array_policy']['worker_budget_seconds'] == 11700
    assert parallel['array_policy']['max_partial_resumptions'] == 1
    def new_environment(**_):
        env = io._Environment(steps=[StepPublicState(observation='Done',menu=io._menu(('look',)),score=1,done=True,won=True)])
        env.reset = environment.reset
        return env
    types['SpawnedAlfworldAdapter'] = SimpleNamespace(start=new_environment)
    for shard in parallel['shards']:
        for ordinal in shard['ordinals']:
            for label, bundle in context['bundles'].items():
                condition,runtime,schedule,condition_sha,runtime_sha,schedule_sha = bundle
                live._recover_or_execute_cell(label=label,cell=schedule.cells[ordinal],
                    task_access_record=context['access'].records[0],condition=condition,runtime=runtime,
                    condition_sha=condition_sha,runtime_sha=runtime_sha,schedule_sha=schedule_sha,
                    preflight=preflight,base_url='http://127.0.0.1:1',types=types,attempt_auditor=loader,
                    condition_root=Path(shard['execution_root'])/label)
        write_once(Path(shard['execution_root']).parent/'SHARD_STATUS_000.json',
            {'schema_id':'CURRENT_NATIVE_OFFOFF_SHARD_STATUS_V1','parallel_ref':parallel_ref,
             'shard_id':shard['shard_id'],'resumption_ordinal':0,'assigned_pair_count':len(shard['ordinals']),
             'parent_cell_count':len(shard['ordinals']),'candidate_cell_count':len(shard['ordinals']),
             'graceful_partial':False,'complete':True})
    terminal_ref = finalize_parallel(parallel_ref)
    terminal = read_ref(terminal_ref)
    assert terminal['outcome'] == 'ROLLED_BACK'
    summary = read_ref(terminal['summary_ref'])
    assert summary['paired_cell_count'] == 2 and summary['total_condition_cell_count'] == 4
    assert summary['parent_success_cells'] == summary['candidate_success_cells'] == 2
    assert finalize_parallel(parallel_ref) == terminal_ref
    from offoff_binding.execute import validate_completed_offoff_terminal
    assert validate_completed_offoff_terminal(terminal_ref)
    # A terminal/status cannot hide missing native publication evidence.
    first = parallel['shards'][0]
    ledger = Path(first['execution_root'])/'parent/cell_receipts.jsonl'
    ledger.write_bytes(b'')
    import pytest
    with pytest.raises(ValueError, match='COMPLETE_ASSIGNED_GRID'):
        validate_completed_offoff_terminal(terminal_ref)
