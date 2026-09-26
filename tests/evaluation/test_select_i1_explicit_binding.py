"""Explicit I1 opt-in for the existing SELECT evaluator; no live execution."""
from dataclasses import replace
import importlib.util
from pathlib import Path
import json
import pytest
from pchsi.evaluation import select_execution_identity as se
from pchsi.evaluation.canonical_evidence import canonical_json_bytes, sha256_bytes
from pchsi.evaluation.condition_run_schedule import condition_cell_id
from pchsi.evaluation.policy_execution_profile import I1_EXECUTION_PROFILE_V1
from pchsi.evaluation.interface_isolation_request import i1_structured_serialization_schema_dict


def identity(name='CLEAN-T2-CANDIDATE', model=None, seed=17):
    return se.SelectExecutionIdentityV1(
        evaluation_context=se.P4_SELECT_EVALUATION_CONTEXT,
        logical_condition_id=name, checkpoint_instance_id=name,
        training_seed=seed, served_model_name=model or name,
        adapter_bundle_sha256='a'*64, access_class='SELECT_SUMMARY_ONLY',
        policy_condition_id=name,
        condition_cell_id=condition_cell_id(policy_condition_id=name, manifest_index=0, seed=17),
        task_access_manifest_sha256='1'*64,policy_condition_manifest_sha256='2'*64,
        condition_run_schedule_sha256='3'*64,select_policy_runtime_manifest_sha256='4'*64)


def test_explicit_select_i1_api_exists():
    assert callable(getattr(se, 'build_select_i1_execution_profile', None)), 'MISSING_EXPLICIT_SELECT_I1_API'
    assert callable(getattr(se, 'select_i1_request_contract_sha256', None))


def profile(i=None):
    return se.build_select_i1_execution_profile(i or identity(),
        request_contract_sha256=se.select_i1_request_contract_sha256())


def test_legacy_raw_factory_is_unchanged():
    old=se.build_select_execution_profile(identity())
    assert old.request_kind=='R0'
    se.validate_select_execution_profile_binding(identity=identity(),profile=old)
    assert old.build_request(prompt_text='x',seed=17,request_id='r').to_wire_dict()['structured_outputs'] is None


def test_unbound_legacy_i1_still_rejected():
    with pytest.raises(ValueError,match='RAW request semantics'):
        se.validate_select_execution_profile_binding(identity=identity(),profile=I1_EXECUTION_PROFILE_V1)


def test_opt_in_requires_exact_schema_in_episode_config():
    p=profile()
    for h in (None,'f'*64):
        with pytest.raises(ValueError,match='request contract'):
            se.validate_select_execution_profile_binding(identity=identity(),profile=p,
                expected_request_schema_sha256=h)
    se.validate_select_execution_profile_binding(identity=identity(),profile=p,
        expected_request_schema_sha256=se.select_i1_request_contract_sha256())


def test_identity_cannot_be_transplanted():
    with pytest.raises(ValueError,match='identity'):
        se.validate_select_execution_profile_binding(identity=identity('OTHER'),profile=profile(),
            expected_request_schema_sha256=se.select_i1_request_contract_sha256())


def test_arbitrary_model_uses_original_i1_factory_not_i2():
    p=profile(identity(model='ROUND-CANDIDATE-SERVED'))
    req=p.build_request(prompt_text='RAW_POLICY_PROMPT_V1\nx',seed=31,request_id='q')
    wire=req.to_wire_dict()
    assert wire['model']=='ROUND-CANDIDATE-SERVED'
    assert wire['structured_outputs']=={'json':i1_structured_serialization_schema_dict()}
    assert 'enum' not in wire['structured_outputs']['json']['properties']['action']
    old=se.build_select_execution_profile(identity(model='ROUND-CANDIDATE-SERVED')).build_request(
        prompt_text=req.prompt_text,seed=31,request_id='q').to_wire_dict()
    assert [k for k in wire if wire[k]!=old[k]]==['structured_outputs']
    with pytest.raises(ValueError):
        p.build_request(prompt_text='x',seed=17,request_id='q',admissible_commands=('look',))


def test_request_contract_cannot_be_faked():
    with pytest.raises(ValueError,match='request contract'):
        se.build_select_i1_execution_profile(identity(),request_contract_sha256='0'*64)


def test_wire_check_rejects_missing_i1_wrong_model_or_seed():
    p=profile();wire=p.build_request(prompt_text='x',seed=17,request_id='r').to_wire_dict()
    se.validate_select_i1_wire_v1(identity=identity(),raw=canonical_json_bytes(wire),
       expected_prompt='x',expected_seed=17,expected_request_id='r',
       expected_request_schema_sha256=se.select_i1_request_contract_sha256())
    for key,value in [('structured_outputs',None),('model','other'),('seed',31),('temperature',0.7)]:
        changed={**wire,key:value}
        with pytest.raises(ValueError):
            se.validate_select_i1_wire_v1(identity=identity(),raw=canonical_json_bytes(changed),
               expected_prompt='x',expected_seed=17,expected_request_id='r',
               expected_request_schema_sha256=se.select_i1_request_contract_sha256())


def _fixture():
    path=Path(__file__).with_name('test_interface_isolation_evaluator.py')
    spec=importlib.util.spec_from_file_location('_existing_i1_evaluator_fixtures',path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def run_episode(tmp_path,responses,steps,wrong_hash=False):
    from pchsi.evaluation.episode_evaluator import EpisodeDependencies,run_single_episode
    from pchsi.evaluation.distillation_access import DistillationAccessClass
    from pchsi.evaluation.policy_client import PolicyClient
    m=_fixture(); i=identity(); old=m._config()
    cfg=replace(old,cell=se.SelectBoundEpisodeCellV1(
        scheduled_cell_id=i.condition_cell_id,task_index=0,task_id='train-test-0',seed=17,
        policy_condition_id=i.policy_condition_id,access_class=DistillationAccessClass.SELECT_SUMMARY_ONLY,
        execution_identity=i),execution_attempt_id=i.condition_cell_id+'-a000',
        task=replace(old.task,task_id='train-test-0',split='train'),
        split_access_sha256=i.task_access_manifest_sha256,run_schedule_sha256=i.condition_run_schedule_sha256,
        task_access_manifest_sha256=i.task_access_manifest_sha256,
        policy_condition_manifest_sha256=i.policy_condition_manifest_sha256,
        condition_run_schedule_sha256=i.condition_run_schedule_sha256,
        access_class=i.access_class,policy_condition_id=i.policy_condition_id,condition_cell_id=i.condition_cell_id,
        evaluation_context=i.evaluation_context,select_execution_identity=i,
        policy_runtime_manifest_sha256=i.select_policy_runtime_manifest_sha256,
        policy_request_schema_sha256='0'*64 if wrong_hash else se.select_i1_request_contract_sha256())
    class Transport:
        def __init__(self): self.calls=[]
        def post_exact(self,*,path,body,headers):
            v=json.loads(body);self.calls.append(v)
            payload={'id':'provider-'+str(len(self.calls)), 'model':v['model'],
                'choices':[{'message':{'content':responses[len(self.calls)-1]},'finish_reason':'stop','token_ids':[4,5]}],
                'usage':{'prompt_tokens':3,'completion_tokens':2},'prompt_token_ids':[1,2,3]}
            return 200,{'x-request-id':payload['id'],'content-type':'application/json'},canonical_json_bytes(payload)
    t=Transport();e=m._Environment(steps=steps);pub=m._Publisher()
    deps=EpisodeDependencies(environment=e,policy_client=PolicyClient(transport=t),
       prompt_renderer=m._Renderer(),artifact_publisher=pub,policy_execution_profile=profile(i))
    result=run_single_episode(config=cfg,dependencies=deps)
    return result,t,e


def test_original_evaluator_rejects_menu_errors_without_repair(tmp_path):
    result,t,e=run_episode(tmp_path,['{"action":"illegal"}']*3,[])
    assert result.success is False
    assert not e.step_calls and len(t.calls)==3
    assert all(x['structured_outputs']['json']==i1_structured_serialization_schema_dict() for x in t.calls)
    assert all(x['messages'][0]['content'].startswith('RAW_POLICY_PROMPT_V1') for x in t.calls)
    assert result.final_budget.inadmissible_action_count==3


def test_original_evaluator_accepts_valid_action_and_publishes(tmp_path):
    from pchsi.evaluation.alfworld_contracts import StepPublicState
    m=_fixture()
    result,t,e=run_episode(tmp_path,['{"action":"look"}'],[
       StepPublicState(observation='Done',menu=m._menu(('look',)),score=1,done=True,won=True)])
    assert result.success is True and e.step_calls==['look']
    assert result.attempt_bundle is not None
    assert result.operational_finalization_status.value=='PUBLISHED'


def test_wrong_config_request_hash_fails_before_transport(tmp_path):
    with pytest.raises(ValueError,match='request contract'):
        run_episode(tmp_path,['{"action":"look"}'],[],wrong_hash=True)


def test_i1_result_audit_api_exists():
    from pchsi.evaluation import select_result_audit as audit
    assert callable(getattr(audit,'audit_select_i1_policy_calls_v1',None)), 'MISSING_SELECT_I1_RESULT_AUDIT'


def test_audit_checks_original_prompt_factory_and_request_bytes(tmp_path):
    from pchsi.evaluation import select_result_audit as audit
    from pchsi.evaluation.policy_call_evidence import PolicyCallEvidenceV1
    result,_,_=run_episode(tmp_path,['{"action":"illegal"}']*3,[])
    calls=tuple(PolicyCallEvidenceV1.from_json(x) for x in result.attempt_bundle.policy_calls_jsonl.splitlines())
    audit.audit_select_i1_policy_calls_v1(identity=identity(),policy_calls=calls,
        evaluation_seed=17,expected_request_schema_sha256=se.select_i1_request_contract_sha256())
    for seed,contract in [(31,se.select_i1_request_contract_sha256()),(17,'a'*64)]:
        with pytest.raises(ValueError):
            audit.audit_select_i1_policy_calls_v1(identity=identity(),policy_calls=calls,
                evaluation_seed=seed,expected_request_schema_sha256=contract)
    with pytest.raises(ValueError,match='no policy-call'):
        audit.audit_select_i1_policy_calls_v1(identity=identity(),policy_calls=(),
            evaluation_seed=17,expected_request_schema_sha256=se.select_i1_request_contract_sha256())


def test_i1_contract_cannot_fall_back_to_old_raw_factory():
    with pytest.raises(ValueError,match='request contract'):
        se.validate_select_execution_profile_binding(identity=identity(),
            profile=se.build_select_execution_profile(identity()),
            expected_request_schema_sha256=se.select_i1_request_contract_sha256())
