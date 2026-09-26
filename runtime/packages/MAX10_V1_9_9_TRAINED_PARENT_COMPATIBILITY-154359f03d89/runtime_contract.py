"""Strict reader for the existing candidate publisher's trained runtime schema."""
from pathlib import Path
import json,hashlib

TRAINED_SCHEMA='CURRENT_TRAINED_POLICY_RUNTIME_BINDING_V1'
BASE_FIELDS={'schema_id','schema_version','served_model_name','policy_runtime_manifest_sha256',
 'decoding_contract_sha256','policy_base_url','base_model_local_path','tokenizer_revision',
 'chat_template_sha256','context_window_tokens','vllm_version','scientific_execution_authorized','continuation_request_contract'}
TRAINED_FIELDS={'policy_id','base_served_model_name','adapter_path','adapter_bundle_sha256','adapter_rank',
 'adapter_artifact_manifest_ref','final_trainable_parameter_sha256','candidate_policy_ref','current_parent_context','training_result_ref'}

def load_trained_runtime(path,*,expected_file_sha256,expected_model,validate_native_contract,validate_artifacts):
    p=Path(path)
    if p.is_symlink() or not p.is_file():raise ValueError('TRAINED_RUNTIME_REGULAR_FILE_REQUIRED')
    raw=p.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_file_sha256:raise ValueError('TRAINED_RUNTIME_FILE_SHA_MISMATCH')
    value=json.loads(raw)
    if not isinstance(value,dict) or set(value)!=BASE_FIELDS|TRAINED_FIELDS:raise ValueError('TRAINED_RUNTIME_FIELDS_MISMATCH')
    if (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()!=raw:raise ValueError('TRAINED_RUNTIME_NONCANONICAL')
    if value['schema_id']!=TRAINED_SCHEMA or type(value['schema_version']) is not int or value['schema_version']!=1:raise ValueError('TRAINED_RUNTIME_SCHEMA_MISMATCH')
    if value['served_model_name']!=expected_model or value['policy_id']!=expected_model:raise ValueError('TRAINED_RUNTIME_PARENT_MODEL_MISMATCH')
    if value['scientific_execution_authorized'] is not False:raise ValueError('TRAINED_RUNTIME_CANNOT_SELF_AUTHORIZE')
    if type(value['context_window_tokens']) is not int or value['context_window_tokens']<=0:raise ValueError('TRAINED_RUNTIME_CONTEXT_INVALID')
    for field in ('policy_runtime_manifest_sha256','decoding_contract_sha256','chat_template_sha256','adapter_bundle_sha256','final_trainable_parameter_sha256'):
        v=value[field]
        if not isinstance(v,str) or len(v)!=64 or any(c not in '0123456789abcdef' for c in v):raise ValueError('TRAINED_RUNTIME_HASH_INVALID:'+field)
    if value['policy_runtime_manifest_sha256']!=value['adapter_bundle_sha256']:raise ValueError('TRAINED_RUNTIME_BUNDLE_IDENTITY')
    validate_native_contract(value)
    validate_artifacts(value)
    return value
