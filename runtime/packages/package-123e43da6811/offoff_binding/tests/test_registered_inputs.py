"""Real registered SELECT assets; policy files/rule are explicit interface fixtures."""
from dataclasses import fields
import hashlib
from pathlib import Path
import pytest
from continuity_binding.api import read_ref,write_once
from offoff_binding.native import Native,REQUIRED
from offoff_binding.registered_inputs import materialize_registered_inputs
from pchsi.round_control.rollout_collection import RoundRolloutCollectionRequestV1

ROOT = Path(__file__).resolve().parents[4]
REPO = ROOT/'work/v17/native_bba_full'


def file_ref(path): return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


@pytest.mark.parametrize('lora_parent',[False,True])
def test_real_frozen_355_task_assets_generate_current_bindings(tmp_path,lora_parent):
    names = {'historical_protocol':'server_select_sources_05/protocol.json',
        'binding_identity':'server_select_index_06/BINDING_IDENTITY.json',
        'task_access':'server_select_assets_07/CLEAN_SELECT_TASK_ACCESS_MANIFEST_V1.json',
        'server_runtime':'server_select_assets_07/SELECT_SERVER_RUNTIME_MANIFEST_V1.json',
        'environment_runtime':'server_select_assets_07/ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_V1.json',
        'gamefile_identity':'server_select_assets_07/CLEAN_SELECT_GAMEFILE_IDENTITY_MANIFEST_V1.json',
        'raw_protocol':'server_select_protocol_08/CLEAN_SELECT_RAW_PROTOCOL_BINDING_V1.json',
        'tokenizer_identity':'server_select_protocol_08/CLEAN_SELECT_TOKENIZER_IDENTITY_V1.json'}
    assets = {name:file_ref(ROOT/'work/v17'/relative) for name,relative in names.items()}
    source = tmp_path/'fixture_rule.py'
    source.write_text('def decide(*,frozen_rule,aggregate):\n return {"decision":"ROLLBACK","decision_rule_id":frozen_rule["decision_rule_id"]}\n')
    source_ref = file_ref(source)
    rule_ref = write_once(tmp_path/'rule.json',{'decision_rule_id':'FIXTURE_ONLY','decision_producer':{'source_ref':source_ref,'entrypoint':'decide'}})
    registration = {'native_repo_root':str(REPO),'source_refs':[file_ref(REPO/name) for name in REQUIRED]+[source_ref],
        'assets':assets,'code_source_ref':file_ref(ROOT/'work/v17/NATIVE_BBA_FULL_SOURCE_RECEIPT_V2.json'),
        'promotion_rule_ref':rule_ref}
    runtime_ref = file_ref(ROOT/'work/v17/current_clean_runtime_fixture.json')
    runtime = read_ref(runtime_ref)
    sha_fields = {f.name:'a'*64 for f in fields(RoundRolloutCollectionRequestV1)
                  if f.name.endswith('_sha256') and f.name!='request_sha256'}
    sha_fields.update(policy_runtime_binding_sha256=runtime_ref['sha256'],
        parent_policy_artifact_sha256=runtime['policy_runtime_manifest_sha256'])
    start=RoundRolloutCollectionRequestV1(round_id='fixture',execution_attempt_id='fixture-attempt',
        parent_policy_id='fixture-parent',execution_namespace='fixture',rollout_seed=17,**sha_fields).to_dict()
    tokenizer=read_ref(assets['tokenizer_identity'])
    # This manifest is a metadata fixture only; full materialize() subsequently
    # requires actual weight/tokenizer bytes and the original clean-base audit.
    manifest_ref=write_once(tmp_path/'fixture-base-manifest.json',{'files':tokenizer['files']})
    parent={'kind':'LORA_ADAPTER' if lora_parent else 'BASE_MODEL','policy_id':start['parent_policy_id'],
        'artifact_sha256':start['parent_policy_artifact_sha256'],'artifact_manifest':manifest_ref,
        'base_model_repository':tokenizer['base_model_repository'],'base_model_revision':tokenizer['base_model_revision']}
    contract_ref=write_once(tmp_path/'contract.json',{'parent':{'policy_id':start['parent_policy_id'],
        'base_model_artifact_manifest_sha256':manifest_ref['sha256'],'base_model_artifact_manifest_path':manifest_ref['path'],
        'base_model_repository':tokenizer['base_model_repository'],'base_model_revision':tokenizer['base_model_revision']}})
    candidate={**parent,'kind':'LORA_ADAPTER','policy_id':'fixture-candidate','artifact_sha256':'c'*64,
        'training_config_ref':contract_ref, **{k:start[k] for k in ('round_id','request_sha256','execution_attempt_id',
            'parent_policy_id','parent_policy_artifact_sha256')}}
    args=dict(registration=registration,request_ref=write_once(tmp_path/'request.json',start),
        parent_ref=write_once(tmp_path/'parent.json',parent),candidate_ref=write_once(tmp_path/'candidate.json',candidate),
        current_runtime_ref=runtime_ref,sink=tmp_path/'out')
    out=materialize_registered_inputs(**args)
    assert materialize_registered_inputs(**args)==out
    protocol=read_ref(out['protocol_ref']);infra=read_ref(out['infrastructure_ref'])
    assert len(protocol['task_ids'])==355 and len(protocol['replicate_seeds'])==5
    assert protocol['episode_budget']=={'max_consecutive_nonexecuted_attempts':3,'max_environment_steps':30,'max_policy_attempts':60}
    assert protocol['promotion_rule_ref']==rule_ref
    assert protocol['evaluator_commit']=='bba400738a7a53d0402552ecc3576f736ca0eec8'
    assert 'static_lora_registry' not in infra['server_runtime_parameters']
    assert infra['server_runtime_parameters']['max_loras']==(2 if lora_parent else 1)
    assert infra['server_runtime_parameters']['max_cpu_loras']==(2 if lora_parent else 1)
    assert protocol['historical_candidate_reused'] is False
    with pytest.raises(ValueError,match='PROMOTION_RULE_NOT_REGISTERED'):
        materialize_registered_inputs(**{**args,'registration':{**registration,'promotion_rule_ref':None},'sink':tmp_path/'missing-rule'})
    assert not (tmp_path/'missing-rule').exists()
