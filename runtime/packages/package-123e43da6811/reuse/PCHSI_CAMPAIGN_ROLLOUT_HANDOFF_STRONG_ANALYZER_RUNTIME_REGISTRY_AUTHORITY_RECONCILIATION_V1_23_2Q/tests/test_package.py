from pathlib import Path
from types import SimpleNamespace
import hashlib
import importlib.util
import json
import ast

ROOT=Path(__file__).resolve().parents[1]
SRC=(ROOT/'v1232q_driver.py').read_text()


def load_driver():
    spec=importlib.util.spec_from_file_location('v1232q_driver_test',ROOT/'v1232q_driver.py')
    module=importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_no_current_run_literals():
    for x in ('166443','34072dedc0234050307459c77f24a9763fe2a470ae74e0078eceaa87ef417b49','ea091bcdc2a9bcd239ec57d40dec423003ff68a8','2843'):
        assert x not in SRC


def test_no_new_provider_client_or_rollout_execution():
    assert 'openai.' not in SRC.lower()
    assert 'sbatch' not in SRC
    assert 'env.step' not in SRC
    assert 'run_registry_v1.py' in SRC


def test_path_recovery_uses_shard_authority_not_null_global_path():
    assert 'recover_bundle_authorities(' in SRC
    assert "PCHSI_V1232S_SHARD_TERMINALS_V1.json" in SRC
    assert "sr.get('attempt_bundle_root')" in SRC
    assert "sr.get('execution_attempt_id')" in SRC
    assert "bundle_path=root/attempt_id" in SRC
    assert "Path(str(row['attempt_bundle_path'])).resolve()" not in SRC
    assert "filesystem_wide_discovery_used':False" in SRC
    assert "human_path_selection_performed':False" in SRC


def test_selected_bundle_bytes_validated_before_output_or_provider_calls():
    recover_pos=SRC.index('resolved_authorities,path_reconciliation=recover_bundle_authorities(')
    validate_pos=SRC.index("b=validate_attempt_bundle(Path(a['bundle_path']))")
    output_pos=SRC.index("out=badcase/'new_human_pi1/control")
    runtime_pos=SRC.index('rc=run_registry(repo,regpath,liveout)')
    assert recover_pos < validate_pos < output_pos < runtime_pos


def test_fixed_head_import_surface_preflight_before_output_and_calls():
    assert 'assert_fixed_head_api_contract(repo)' in SRC
    assert SRC.index('api=assert_fixed_head_api_contract(repo)') < SRC.index("out=badcase/'new_human_pi1/control")
    assert 'inspect.signature' in SRC
    assert 'FIXED_HEAD_REQUIRED_SYMBOL_MISSING' in SRC
    assert 'FIXED_HEAD_CALLABLE_SIGNATURE_DRIFT' in SRC
    assert 'ATTEMPT_RECEIPT_FROM_JSON_SURFACE_MISSING' in SRC
    assert 'EPISODE_ARTIFACT_FROM_JSON_SURFACE_MISSING' in SRC
    for name in ('build_round_analyzer_resource_budget','validate_round_analyzer_resource_budget','select_failure_only_u_reg','build_clean_analyzer_task_access_record','build_local_u_reg_manifest'):
        assert name in SRC


def test_canonical_grouping_api_not_singular_or_approximate():
    assert "api['build_group_synthesis_inputs']" in SRC
    assert 'build_group_synthesis_input,' not in SRC
    assert 'build_group_manifests(\n        local_results=local_results,\n        mechanical_signatures=mechanical_signatures,' in SRC
    assert 'build_group_synthesis_inputs(\n        source_closed_groups,\n        source_bindings=source_contexts,' in SRC
    assert "group.get('membership_records')" in SRC
    assert "synth['member_rows']" in SRC


def test_historical_act3_attempt_loader_reused():
    assert 'materialize_sequence_failure_experience_v1.py' in SRC
    assert "load_attempt_directory_v1=api['load_attempt_directory_v1']" in SRC
    assert "raw=load_attempt_directory_v1(Path(meta['bundle_path']))" in SRC
    assert 'raw.traces' in SRC and 'raw.policy_calls' in SRC
    assert 'bundle.public_transitions' not in SRC


def test_round_start_memory_uses_exact_rollout_request_authority():
    assert "memory_sha=req.get('round_start_memory_snapshot_sha256')" in SRC
    assert 'ROUND_START_MEMORY_SNAPSHOT_AUTHORITY_MISSING' in SRC
    assert 'ROLLOUT_REQUEST_SHA_MISMATCH' in SRC
    assert "persistent!={('PERSISTENT_FAILURE_EXPERIENCE_V1',memory_snapshot_sha)}" in SRC


def test_group_source_context_not_claimed_f0f1_authority():
    assert 'ANALYZER_GROUP_BINDING_ONLY_F0F1_REPLAY_REBIND_REQUIRED' in SRC
    assert 'source_contexts_are_analyzer_group_bindings_not_f0f1_replay_authority' in SRC


def test_group_projection_compatible_source_context_array():
    assert "write_new_value(gr/'source_contexts.json',members)" in SRC
    assert "'schema_id':'V1232Q_GROUP_SOURCE_CONTEXTS_V1'" not in SRC


def test_group_denominator_preserved_no_topup():
    assert 'source_closed_groups,partial_groups,no_source_groups=classify_source_closed_groups' in SRC
    assert "'group_top_up_performed':False" in SRC
    assert "'human_group_selection_performed':False" in SRC
    assert 'NO_SOURCE_CLOSED_GROUPS' in SRC


def test_signature_failure_is_fail_closed_not_dropped():
    assert 'V1232Q_ACT3_SIGNATURE_COMPILATION_FAIL_CLOSED' in SRC
    assert 'return 21' in SRC


def test_no_automatic_retry_or_human_selection():
    assert "automatic_retry_performed':False" in SRC
    assert "human_disposition_required':False" in SRC
    assert "human_group_selection_performed':False" in SRC


def test_shell_has_no_strict_flags():
    s=(ROOT/'RUN_V1232Q.sh').read_text()
    assert 'set -e' not in s and 'set -u' not in s and 'pipefail' not in s


def test_recover_bundle_authority_from_null_index_path(tmp_path):
    d=load_driver()
    state=tmp_path/'state'; state.mkdir()
    shard=state/'shards'/'0000'; (shard/'cell_terminals').mkdir(parents=True)
    attempts=shard/'rollout_run'/'attempts'; attempts.mkdir(parents=True)
    ledger=shard/'rollout_run'/'attempt_ledger'; ledger.mkdir(parents=True)
    attempt_id='e1-t0000-s0000000017-a001'
    bundle=attempts/attempt_id; bundle.mkdir()
    episode={
        'execution_attempt_id':attempt_id,'task_id':'task-0','task_index':0,
        'task_type':'pick_and_place_simple','gamefile_sha256':'a'*64,
        'episode_semantic_sha256':'b'*64,'success':False,
    }
    (bundle/'attempt.json').write_text(json.dumps(episode))
    terminal_payload={
        'receipt_kind':'TERMINAL','execution_attempt_id':attempt_id,
        'attempt_bundle_sha256':'c'*64,'episode_semantic_sha256':'b'*64,
    }
    terminal=ledger/f'{attempt_id}.terminal.json'; terminal.write_text(json.dumps(terminal_payload))
    sidecar_obj={
        'schema_id':'ROUND_ROLLOUT_CELL_TERMINAL_V1','schema_version':1,
        'global_ordinal':0,'shard_id':0,'scientific_cell_id':'cell-0',
        'execution_attempt_id':attempt_id,'task_index':0,'task_id':'task-0',
        'status':'SCIENTIFIC_FAILURE','success':False,
        'scientific_outcome_status':'SCIENTIFIC_OUTCOME_COMPLETE_TASK_FAILURE',
        'operational_finalization_status':'PUBLISHED','termination_reason':'TASK_TERMINAL',
        'attempt_terminal_path':str(terminal),'attempt_bundle_root':str(attempts),
    }
    sidecar=shard/'cell_terminals'/'00000.json'
    sidecar.write_text(json.dumps(sidecar_obj,sort_keys=True,separators=(',',':'))+'\n')
    side_sha=hashlib.sha256(sidecar.read_bytes()).hexdigest()
    shard_row={**sidecar_obj,'terminal_receipt_sha256':side_sha}
    d.write_new_json(shard/'PCHSI_V1232S_SHARD_TERMINALS_V1.json',{
        'schema_id':'PCHSI_V1232S_SHARD_TERMINALS_V1','schema_version':1,
        'shard_id':0,'rows':[shard_row],
    })
    index={'schema_id':'ROUND_SHARDED_ATTEMPT_BUNDLE_INDEX_V1','schema_version':1,'row_count':1,'rows':[{
        'global_ordinal':0,'scientific_cell_id':'cell-0','shard_id':0,
        'attempt_bundle_path':None,'attempt_terminal_path':str(terminal),
    }]}
    handoff={'shard_count':1}

    class FakeReceipt:
        @classmethod
        def from_json(cls,b):
            x=json.loads(b)
            return SimpleNamespace(**x)
    class FakeEpisode:
        @classmethod
        def from_json(cls,b):
            return SimpleNamespace(**json.loads(b))

    resolved,receipt=d.recover_bundle_authorities(
        state_root=state,handoff=handoff,index=index,failure_ids=['cell-0'],
        attempt_receipt_type=FakeReceipt,episode_artifact_type=FakeEpisode,
    )
    assert resolved['cell-0']['bundle_path']==bundle
    assert resolved['cell-0']['execution_attempt_id']==attempt_id
    assert receipt['null_index_attempt_bundle_path_count']==1
    assert receipt['resolution_authority']=='BOUNDED_SHARD_TERMINAL_ATTEMPT_BUNDLE_ROOT_PLUS_EXECUTION_ATTEMPT_ID'
    assert receipt['filesystem_wide_discovery_used'] is False


def test_recover_bundle_authority_rejects_index_terminal_drift(tmp_path):
    d=load_driver()
    state=tmp_path/'state'; state.mkdir()
    shard=state/'shards'/'0000'; shard.mkdir(parents=True)
    d.write_new_json(shard/'PCHSI_V1232S_SHARD_TERMINALS_V1.json',{
        'schema_id':'PCHSI_V1232S_SHARD_TERMINALS_V1','schema_version':1,
        'shard_id':0,'rows':[{'global_ordinal':0,'shard_id':0,'scientific_cell_id':'cell-0'}],
    })
    index={'schema_id':'ROUND_SHARDED_ATTEMPT_BUNDLE_INDEX_V1','schema_version':1,'row_count':1,'rows':[{
        'global_ordinal':0,'scientific_cell_id':'different','shard_id':0,'attempt_bundle_path':None,'attempt_terminal_path':None,
    }]}
    try:
        d.recover_bundle_authorities(
            state_root=state,handoff={'shard_count':1},index=index,failure_ids=['different'],
            attempt_receipt_type=object,episode_artifact_type=object,
        )
    except RuntimeError as e:
        assert 'INDEX_SHARD_TERMINAL_IDENTITY_MISMATCH' in str(e)
    else:
        raise AssertionError('expected fail closed')


def test_domain_hash_never_receives_literal_sequence_payload():
    tree=ast.parse(SRC)
    for node in ast.walk(tree):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=='domain_hash':
            assert len(node.args)>=2
            assert not isinstance(node.args[1],(ast.List,ast.Tuple,ast.Set,ast.ListComp,ast.SetComp,ast.GeneratorExp))


def test_runtime_registry_reuses_canonical_task_access_manifest_authority():
    assert "'schema_id':'CLEAN_ANALYZER_TASK_ACCESS_MANIFEST_V1'" in SRC
    assert "access_manifest['manifest_sha256']=domain_hash(" in SRC
    assert "'task_access_manifest_sha256':sha256_file(access_manifest_path)" in SRC
    assert "domain_hash('V1232Q_TASK_ACCESS_UNIVERSE_V1'" not in SRC
    assert "task_access_record_sha256':access['task_access_sha256']" in SRC


def test_local_ureg_reused_for_selected_universe_identity():
    assert 'build_local_u_reg_manifest' in SRC
    assert "CLEAN_ANALYZER_LOCAL_U_REG_V1.json" in SRC
    assert "task_set_manifest_sha256=u_reg['u_reg_sha256']" in SRC
    assert "CURRENT_ROUND_TRAIN_UPDATE_FAILURE_UNIVERSE_V1.jsonl" in SRC
    assert "failure_universe_file_sha256=failure_universe_sha" in SRC
