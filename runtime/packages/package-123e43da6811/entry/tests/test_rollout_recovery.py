from pathlib import Path
import importlib.util
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def module():
    path = ROOT/'entry/rollout_recovery.py'
    assert path.is_file(), 'typed invalid rollout route missing'
    spec = importlib.util.spec_from_file_location('rollout_recovery_tests',path)
    value = importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value


def test_known_local_resource_failure_is_retryable_without_scientific_reuse():
    result=module().classify_errors(fatal_errors=['SHARD_PREEXISTING_ENDPOINT_OCCUPIED'],
        cell_errors=['PolicyTransportError','ABORTED_AFTER_PRIOR_INFRASTRUCTURE_OR_PROTOCOL_INVALID'],protocol_invalid_count=0)
    assert result=='SAFE_LOCAL_RESOURCE_ISOLATION'


@pytest.mark.parametrize('fatal,cells,protocol',[
    (['unknown'],[],0),([],['UnknownError'],0),([],['PolicyTransportError'],1),([],[],0)])
def test_unknown_or_protocol_failure_cannot_authorize_restart(fatal,cells,protocol):
    assert module().classify_errors(fatal_errors=fatal,cell_errors=cells,
        protocol_invalid_count=protocol)=='UNSAFE_OR_UNKNOWN'


def test_stopped_array_requires_all_registered_tasks_terminal():
    m=module();rows='123_0|COMPLETED|0:0\n123_1|FAILED|1:0\n'
    assert m.accounting_inactive('123',2,rows)
    assert not m.accounting_inactive('123',2,'123_0|COMPLETED|0:0\n')
    assert not m.accounting_inactive('123',2,'123_0|COMPLETED|0:0\n123_1|RUNNING|0:0\n')
    assert not m.accounting_inactive('123',2,'999_0|COMPLETED|0:0\n999_1|COMPLETED|0:0\n')


def test_waits_for_cleanup_and_accounting_before_retry(tmp_path):
    m=module();manifest=tmp_path/'manifest.json';manifest.write_text('{}')
    now=[0];calls=[]
    def query(value):
        calls.append(value)
        if len(calls)<3:raise m.AuthorityError('INVALID_ROLLOUT_ALL_SHARDS_TERMINAL_REQUIRED')
        return {'all_registered_shards_terminal':True}
    result=m.wait_inactive({'manifest_path':str(manifest)},settings={'publication_grace_seconds':60,'poll_seconds':10},
        output_root=tmp_path,clock=lambda:now[0],sleep=lambda n:now.__setitem__(0,now[0]+n),query=query)
    assert result['all_registered_shards_terminal'] and now[0]==20 and len(calls)==3


def test_cleanup_wait_does_not_reset_deadline_after_restart(tmp_path):
    m=module();manifest=tmp_path/'manifest.json';manifest.write_text('{}')
    m.put(tmp_path/'INVALID_ARRAY_WAIT_START.json',m.canonical({'start_epoch':0,'manifest_ref':m.ref(manifest)}))
    def query(value):raise m.AuthorityError('INVALID_ROLLOUT_ARRAY_NOT_PROVEN_INACTIVE')
    with pytest.raises(m.AuthorityError,match='ACCOUNTING_GRACE_EXPIRED'):
        m.wait_inactive({'manifest_path':str(manifest)},settings={'publication_grace_seconds':60,'poll_seconds':10},
            output_root=tmp_path,clock=lambda:61,sleep=lambda n:pytest.fail('must not restart deadline'),query=query)


def test_retry_rebinds_only_consumer_identity_in_previous_select_context(tmp_path):
    m=module()
    from analyzer_binding.aggregate_context import project_previous_select_context,validate_previous_select_context,COUNT_FIELDS
    start={'schema_id':'ROUND_ROLLOUT_COLLECTION_REQUEST_V1','round_id':'r2','request_sha256':'b'*64,
        'round_start_memory_snapshot_sha256':'c'*64,'parent_policy_id':'parent'}
    nxt={**start,'request_sha256':'d'*64}
    summary={**{k:0 for k in COUNT_FIELDS},'schema_id':'CURRENT_TRAIN_SELECT_AGGREGATE_V1',
        'round_id':'r1','request_sha256':'a'*64,'parent_policy_id':'parent','candidate_policy_id':'candidate',
        'evidence_access_class':'TRAIN_SELECT','memory_state':'OFF','harness_state':'OFF',
        'benchmark_feedback_used':False,'primary_statistical_unit':'unique_task',
        'replicates_are_not_independent_tasks':True,'replicate_seeds':[17],'mean_task_success_rate_delta':0}
    closed={'schema_id':'FORMAL_NATIVE_ROUND_RESULT_V1','round_id':'r1','request_sha256':'a'*64,
        'parent_policy_id':'parent','candidate_policy_id':'candidate','next_parent_policy_id':'parent',
        'outcome':'ROLLED_BACK','benchmark_feedback_used':False}
    context=project_previous_select_context(summary=summary,summary_sha256='e'*64,closed_result=closed,next_request=start)
    context_path=tmp_path/'previous.json';m.put(context_path,m.canonical(context))
    other={'path':'registered-memory','file_sha256':'f'*64}
    index={'schema_id':'CURRENT_FORMAL_RESIDENT_INPUT_INDEX_V1','request_sha256':start['request_sha256'],
        'round_id':'r2','refs':{'previous_select_context':m.ref(context_path),'memory':other}}
    index_path=tmp_path/'old_index.json';m.put(index_path,m.canonical(index))
    new=m.obj(m.rebind_retry_index(m.ref(index_path),start,nxt,tmp_path/'retry'))
    projected=m.obj({'path':new['refs']['previous_select_context']['path'],
        'sha256':new['refs']['previous_select_context']['file_sha256']})
    assert projected=={**context,'consumer_request_sha256':nxt['request_sha256']}
    validate_previous_select_context(projected,current_request=nxt)
    assert new['refs']['memory']==other and new['request_sha256']==nxt['request_sha256']
    assert m.obj(m.ref(index_path))==index
