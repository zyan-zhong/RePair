"""Mechanical current bindings from the registered historical SELECT grid.

Deployment registration: native_repo_root, source_refs, code_source_ref, assets
and promotion_rule_ref. assets has exactly the eight names below, each an exact
{path,sha256} file ref. Historical diagnostic candidate identities are never
copied. Only pool/grid, I1/environment/tokenizer and server capabilities are reused.
"""
from pathlib import Path
import re

from continuity_binding.api import read_ref, read_bytes_ref, native_request, write_once
from .native import Native, ARRAY_CONFIG
from .materialize import need
from .execute import _registered_decider

ASSET_FILES = {
    'historical_protocol':None, 'binding_identity':None,
    'task_access':'CLEAN_SELECT_TASK_ACCESS_MANIFEST_V1.json',
    'server_runtime':'SELECT_SERVER_RUNTIME_MANIFEST_V1.json',
    'environment_runtime':'ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_V1.json',
    'gamefile_identity':'CLEAN_SELECT_GAMEFILE_IDENTITY_MANIFEST_V1.json',
    'raw_protocol':'CLEAN_SELECT_RAW_PROTOCOL_BINDING_V1.json',
    'tokenizer_identity':'CLEAN_SELECT_TOKENIZER_IDENTITY_V1.json',
}


def materialize_registered_inputs(*, registration, request_ref, parent_ref,
                                 candidate_ref, current_runtime_ref, sink):
    from pchsi.reference_loop.canonical import domain_hash
    from pchsi.evaluation.canonical_evidence import canonical_json_bytes, sha256_bytes
    from pchsi.evaluation.distillation_access import TaskAccessManifestV1, DistillationAccessClass
    from pchsi.evaluation.select_policy_runtime import SelectServerRuntimeManifestV1
    native = Native.load(registration['native_repo_root'], registration['source_refs'])
    assets = registration['assets']
    need(set(assets) == set(ASSET_FILES), 'REGISTERED_SELECT_ASSET_SET')
    documents = {key:read_ref(ref) for key,ref in assets.items()}
    readiness = native.readiness()
    historical_canonical = readiness.canonical_json_bytes
    original, identity = documents['historical_protocol'], documents['binding_identity']
    config = read_ref(native.sources[str(native.root/ARRAY_CONFIG)])
    need(assets['historical_protocol']['sha256'] == config['protocol']['file_sha256'], 'REGISTERED_SELECT_PROTOCOL_FILE')
    need(sha256_bytes(historical_canonical(identity)) == config['binding_sha256'], 'REGISTERED_SELECT_BINDING_IDENTITY')
    need(original['protocol_sha256'] == domain_hash(original['schema_id'], original, excluded_field='protocol_sha256')
         == identity['select_protocol_sha256'], 'REGISTERED_SELECT_PROTOCOL_DOMAIN')
    need(original['protocol_frozen'] is True and original['promotion_eligible'] is False,
         'HISTORICAL_SELECT_DIAGNOSTIC_IDENTITY')
    for key, filename in ASSET_FILES.items():
        if filename is not None:
            need(sha256_bytes(historical_canonical(documents[key])) == identity['artifacts'][filename],
                 'REGISTERED_SELECT_ASSET_IDENTITY:' + key)
    grid = original['grid']
    readiness.verify_frozen_protocol_grid(grid)
    access = TaskAccessManifestV1.from_json(read_bytes_ref(assets['task_access']))
    need(access.record_count == grid['task_count'], 'REGISTERED_SELECT_TASK_COUNT')
    for task,row in zip(access.records,grid['index_crosswalk']):
        need(task.manifest_index == row['select_local_index'] and task.task_id == row['task_id'] and
             task.gamefile_sha256 == row['gamefile_sha256'] and task.dataset_split == 'train' and
             task.access_class is DistillationAccessClass.SELECT_SUMMARY_ONLY, 'REGISTERED_SELECT_TASK_CROSSWALK')
    source = read_ref(registration['code_source_ref'])
    need(source.get('schema') == 'REGISTERED_EXACT_GIT_BLOB_SOURCE_CACHE_V2' and source.get('missing_tracked_paths') == [],
         'REGISTERED_CURRENT_CODE_CAPTURE')
    head, tree = source['registered_commit'], source['tree_git_sha1']
    need(re.fullmatch('[0-9a-f]{40}',head) is not None and re.fullmatch('[0-9a-f]{40}',tree) is not None,
         'REGISTERED_CURRENT_CODE_COMMIT_TREE')
    start = read_ref(request_ref); native_request(start)
    runtime = read_ref(current_runtime_ref)
    need(current_runtime_ref['sha256'] == start['policy_runtime_binding_sha256'] and
         runtime['policy_runtime_manifest_sha256'] == start['parent_policy_artifact_sha256'], 'SELECT_CURRENT_RUNTIME_IDENTITY')
    parent, candidate = read_ref(parent_ref), read_ref(candidate_ref)
    need(parent['policy_id'] == start['parent_policy_id'] and parent['artifact_sha256'] == start['parent_policy_artifact_sha256'],
         'SELECT_CURRENT_PARENT_IDENTITY')
    for key in ('round_id','request_sha256','execution_attempt_id','parent_policy_id','parent_policy_artifact_sha256'):
        need(candidate[key] == start[key], 'SELECT_CURRENT_CANDIDATE_IDENTITY:' + key)
    # No criterion is inferred from this historical protocol's diagnostic measurements.
    rule_ref = registration.get('promotion_rule_ref')
    need(isinstance(rule_ref,dict), 'FORMAL_FROZEN_PROMOTION_RULE_NOT_REGISTERED')
    rule = read_ref(rule_ref); _registered_decider(native,rule)
    old_raw, tokenizer = documents['raw_protocol'], documents['tokenizer_identity']
    need(old_raw['select_protocol_sha256'] == original['protocol_sha256'] and
         old_raw['i1_request_schema_sha256'] == original['model_binding']['policy_request_schema_sha256'],
         'SELECT_FROZEN_RAW_PROTOCOL_IDENTITY')
    expected_contract = {'profile_id':old_raw['interface_profile_id'],'request_kind':'I1',
                         'serialization_schema_sha256':old_raw['i1_serialization_schema_sha256']}
    need(runtime['continuation_request_contract'] == expected_contract and
         runtime['chat_template_sha256'] == old_raw['chat_template_sha256'], 'SELECT_CURRENT_FROZEN_I1_INTERFACE')
    for name,value in grid['episode_budget'].items():
        need(old_raw[name] == value, 'SELECT_REGISTERED_EPISODE_BUDGET:' + name)
    original_server = SelectServerRuntimeManifestV1.from_dict(documents['server_runtime'])
    need(original_server.tokenizer_identity_manifest_sha256 ==
         sha256_bytes(historical_canonical(tokenizer)), 'SELECT_TOKENIZER_IDENTITY')
    for item in (parent,candidate):
        need(item['base_model_repository'] == tokenizer['base_model_repository'] and
             item['base_model_revision'] == tokenizer['base_model_revision'] == runtime['tokenizer_revision'],
             'SELECT_CURRENT_BASE_TOKENIZER_IDENTITY')
    sink = Path(sink).absolute()
    if parent['kind'] == 'BASE_MODEL':
        base_ref = parent_ref
    else:
        contract = read_ref(candidate['training_config_ref'])
        fields = contract['parent']
        need(fields['policy_id'] == start['parent_policy_id'], 'SELECT_TRAINING_BASE_PARENT')
        base = {'schema_id':'CURRENT_OFFOFF_POLICY_BINDING_V1','kind':'BASE_MODEL',
            'policy_id':'BASE-'+fields['base_model_artifact_manifest_sha256'],
            'artifact_sha256':fields['base_model_artifact_manifest_sha256'],
            'artifact_root':runtime['base_model_local_path'],
            'artifact_manifest':{'path':fields['base_model_artifact_manifest_path'],
                                 'sha256':fields['base_model_artifact_manifest_sha256']},
            'base_model_repository':fields['base_model_repository'], 'base_model_revision':fields['base_model_revision']}
        base_ref = write_once(sink/'CLEAN_BASE_POLICY.json',base)
    base_manifest = read_ref(read_ref(base_ref)['artifact_manifest'])
    for name,spec in tokenizer['files'].items():
        need(base_manifest['files'].get(name) == spec, 'SELECT_FROZEN_BASE_TOKENIZER_MEMBER:' + name)
    current_raw = {**old_raw,'fixed_head':head}
    for field, filename in (('raw_policy_prompt_source_sha256','raw_policy_prompt'),
                            ('runtime_core_source_sha256','runtime_core'),('raw_policy_parser_source_sha256','raw_policy_parser')):
        ref = native.sources[str(native.root/f'src/pchsi/evaluation/{filename}.py')]
        read_bytes_ref(ref); current_raw[field] = ref['sha256']
    raw_ref = write_once(sink/'CURRENT_SELECT_RAW_PROTOCOL_BINDING.json',current_raw)
    server = original_server.to_dict()
    server.pop('static_lora_registry')
    server['manifest_id'] = 'CURRENT-SELECT-'+start['request_sha256']
    count = sum(item['kind'] == 'LORA_ADAPTER' for item in (parent,candidate))
    server['max_loras'] = max(server['max_loras'],count)
    server['max_cpu_loras'] = max(server['max_cpu_loras'],count)
    protocol = {'schema_id':'CURRENT_REGISTERED_OFFOFF_PROTOCOL_V1','request_sha256':start['request_sha256'],
        'round_id':start['round_id'],'access_class':'TRAIN_SELECT','memory_state':'OFF','harness_state':'OFF',
        'protocol_frozen':True,'benchmark_feedback_authorized':False,'primary_statistical_unit':'unique_task',
        'task_access_ref':assets['task_access'],'task_ids':[row.task_id for row in access.records],
        'replicate_seeds':grid['replicate_seeds'],'episode_budget':grid['episode_budget'],
        'policy_request_schema_sha256':old_raw['i1_request_schema_sha256'],
        'raw_protocol_sha256':sha256_bytes(historical_canonical(current_raw)),
        'evaluator_commit':head,'runtime_core_commit':head,'design_merge_commit':head,
        'promotion_rule_ref':rule_ref, 'registered_assets':assets,'code_source_ref':registration['code_source_ref'],
        'historical_candidate_reused':False,'historical_promotion_eligibility_inherited':False}
    infrastructure = {'base_policy_ref':base_ref,'environment_runtime_ref':assets['environment_runtime'],
        'gamefile_identity_ref':assets['gamefile_identity'],'server_runtime_parameters':server,
        'tokenizer_identity_ref':assets['tokenizer_identity'],'raw_protocol_ref':raw_ref}
    return {'protocol_ref':write_once(sink/'CURRENT_OFFOFF_PROTOCOL.json',protocol),
        'infrastructure_ref':write_once(sink/'CURRENT_OFFOFF_INFRASTRUCTURE.json',infrastructure),
        'base_policy_ref':base_ref}
