"""One registered contract correction; reuse every frozen scientific result."""
from pathlib import Path
import json,hashlib

INDEX='REGISTERED_POST_CONTRACT_EXECUTION_INDEX.json'

def read_ref(ref):
    p=Path(ref['path']);raw=p.read_bytes()
    if p.is_symlink() or hashlib.sha256(raw).hexdigest()!=ref.get('file_sha256',ref.get('sha256')):raise ValueError('POST_RECOVERY_REFERENCE_SHA')
    return json.loads(raw)

def check_original(a):
    r={k:read_ref(v) for k,v in a['post_recovery_refs'].items()}
    call=r['call/logical_call.json'];attempt=r['call/attempt_000.json'];error=r['call/validation_error.json']
    if (call['terminal_method_status']!='SEMANTIC_INVALID' or attempt['terminal_attempt_status']!='SUCCEEDED'
        or error['message']!='NATIVE_FORMAL_MATCHED_SEEDS_REQUIRED'
        or attempt['logical_call_id']!=call['logical_call_id']
        or attempt['raw_response_sha256']!=a['post_recovery_refs']['call/raw_response.json']['file_sha256']):
        raise ValueError('POST_RECOVERY_NOT_REGISTERED_CONTRACT_DEFECT')
    if r['ROUND_EXECUTION_TERMINAL.json']['status']!='POST_NOT_ACCEPTED_NO_RESEND':raise ValueError('POST_RECOVERY_WRONG_ORIGINAL_TERMINAL')
    return r

def target(a,identity):
    return Path(a['post_original_run_root'])/'post_contract_recoveries'/identity/'h44/run'

def resolve(original):
    p=Path(original);ix=p/INDEX
    if not ix.exists():return p
    index=json.loads(ix.read_bytes());a=read_ref(index['source_authority'])
    if index.get('schema_id')!='REGISTERED_POST_CONTRACT_EXECUTION_INDEX_V1':raise ValueError('POST_RECOVERY_INDEX_SCHEMA')
    if index['original_run_root']!=str(p) or a['post_original_run_root']!=str(p):raise ValueError('POST_RECOVERY_INDEX_IDENTITY')
    manifest=Path(index['source_manifest']['path']).read_bytes()
    if Path(index['source_manifest']['path'])!=Path(index['source_authority']['path']).parent/'PACKAGE_FILES.sha256':raise ValueError('POST_RECOVERY_INDEX_SOURCE_LAYOUT')
    rows={name:sha for sha,name in (line.split(maxsplit=1) for line in manifest.decode().splitlines())}
    if rows.get('AUTHORITY.json')!=index['source_authority']['file_sha256']:raise ValueError('POST_RECOVERY_INDEX_AUTHORITY_MANIFEST')
    if hashlib.sha256(manifest).hexdigest()!=index['source_manifest']['file_sha256']:raise ValueError('POST_RECOVERY_INDEX_MANIFEST')
    expected=target(a,index['source_manifest']['file_sha256'])
    if str(expected)!=index['execution_run_root']:raise ValueError('POST_RECOVERY_INDEX_LOCATION')
    if a['post_recovery_round_id']!=index['round_id']:raise ValueError('POST_RECOVERY_INDEX_ROUND')
    return expected

def materialize(a,identity,source,*,publish):
    from exact_bindings import immutable_bytes,immutable_json,file_ref,read_ref as native_read
    r=check_original(a);old=Path(a['post_original_run_root']);new=target(a,identity)
    # Finite declarations only: registered plan, verifier, dataset and capture.
    keep=['EXECUTION_PLAN.json','GPU_JOB_TERMINAL.json',
          'verifier/ENVIRONMENT_RESULT_PACKAGE.json','post/CURRENT_NATIVE_DATASET_CONTEXT.json']
    copied=[]
    for name in keep:
        ref=a['post_recovery_refs'][name];raw=native_read(ref,as_bytes=True)
        immutable_bytes(new/name,raw);copied.append({'member':name,'source':ref,'copy':file_ref(new/name)})
    plan=r['EXECUTION_PLAN.json'];verifier=r['verifier/ENVIRONMENT_RESULT_PACKAGE.json']
    if verifier['plan_sha256']!=plan['plan_sha256']:raise ValueError('POST_RECOVERY_VERIFIER_PLAN')
    branches={b['branch_key_sha256']:b for b in verifier['branch_records']}
    for row in plan['handoff']['branch_plan']:
        key=row['branch_key_sha256'];name='branches/'+key+'/BRANCH_TERMINAL.json'
        ref=file_ref(old/name);value=native_read(ref)
        if value!=branches[key]:raise ValueError('POST_RECOVERY_BRANCH_VERIFIER_MISMATCH')
        immutable_bytes(new/name,native_read(ref,as_bytes=True));copied.append({'member':name,'source':ref,'copy':file_ref(new/name)})
    # The captured input index owns every archive member and SHA.
    import sys
    request=r['H44_ADAPTER_REQUEST.json'];sys.path.insert(0,request['h44_root'])
    from io_utils import verify_extract
    verify_extract(Path(request['capture']['path']),request['capture']['file_sha256'],new/'input')
    # This exact manifest was materialized by the registered actor overlay.
    ref=a['post_recovery_refs']['input/pre_root/EXACT_RUNTIME_MANIFEST.json']
    immutable_bytes(new/'input/pre_root/EXACT_RUNTIME_MANIFEST.json',native_read(ref,as_bytes=True))
    record={'schema_id':'REGISTERED_POST_CONTRACT_RECOVERY_V1','round_id':plan['round_id'],
        'original_logical_call_ref':a['post_recovery_refs']['call/logical_call.json'],
        'original_raw_response_ref':a['post_recovery_refs']['call/raw_response.json'],
        'original_failed_terminal_ref':a['post_recovery_refs']['ROUND_EXECUTION_TERMINAL.json'],
        'native_seed_choices_modified':False,'original_failure_preserved_in_denominator':True,
        'new_request_reason':'CORRECTED_PREVIOUSLY_UNDISCLOSED_NATIVE_EXECUTION_CONTRACT',
        'same_logical_call_resend_authorized':False,'new_corrected_contract_calls_maximum':1,
        'scientific_branch_reexecution_count':0,'copied_exact_assets':copied,
        'source_authority':file_ref(source/'AUTHORITY.json'),'source_manifest':file_ref(source/'PACKAGE_FILES.sha256')}
    immutable_json(new/'POST_CONTRACT_RECOVERY.json',record)
    index={'schema_id':'REGISTERED_POST_CONTRACT_EXECUTION_INDEX_V1','original_run_root':str(old),
        'execution_run_root':str(new),'round_id':plan['round_id'],
        'source_authority':file_ref(source/'AUTHORITY.json'),'source_manifest':file_ref(source/'PACKAGE_FILES.sha256')}
    if publish:immutable_json(old/INDEX,index)
    return index
