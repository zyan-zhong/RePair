"""One explicit execution index; original partial materialization stays immutable."""
from pathlib import Path
import json,hashlib

def read_ref(ref):
    raw=Path(ref['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ref.get('file_sha256',ref.get('sha256')):raise ValueError('EXECUTION_INDEX_REFERENCE_SHA')
    return json.loads(raw)

def resolve_run(default_run):
    default=Path(default_run);path=default.parent/'REGISTERED_H44_EXECUTION_INDEX.json'
    if not path.exists():return default
    index=json.loads(path.read_bytes())
    if index['schema_id']!='REGISTERED_H44_EXECUTION_INDEX_V1' or index['original_run_root']!=str(default):raise ValueError('H44_EXECUTION_INDEX_IDENTITY')
    source=read_ref(index['source_authority']);registry=read_ref(index['option_registry_ref'])
    from typed_options import digest
    if digest(registry)!=index['registration_sha256']:raise ValueError('H44_EXECUTION_INDEX_REGISTRATION_SHA')
    if registry['round_id']!=index['round_id'] or registry['capture_ref']!=index['capture_ref']:raise ValueError('H44_EXECUTION_INDEX_REGISTRY')
    run=Path(index['execution_run_root'])
    if run!=default.parent/'registered_executions'/index['registration_sha256']/'h44/run':raise ValueError('H44_EXECUTION_INDEX_LOCATION')
    return run

def assert_unsubmitted(root,plan):
    root=Path(root)
    for name in ['SBATCH_SUBMISSION_INTENT.json','SBATCH_COMPLETION.json','GPU_JOB_TERMINAL.json','ROUND_EXECUTION_TERMINAL.json','service/LAUNCH_CONTRACT.json']:
        if (root/name).exists():raise ValueError('H44_MATERIALIZATION_RECOVERY_ALREADY_SUBMITTED:'+name)
    # Finite frozen population, including the originally unbound branches.
    for b in plan['handoff']['branch_plan']:
        branch=root/'branches'/b['branch_key_sha256']
        for name in ['BRANCH_INTENT.json','BRANCH_TERMINAL.json']:
            if (branch/name).exists():raise ValueError('H44_MATERIALIZATION_RECOVERY_BRANCH_STARTED')

def register(binding,capture,out,authority,source_ref):
    from exact_bindings import read_ref as native_read,file_ref,immutable_json
    from typed_options import validate_annex,digest
    out=Path(out);pre=Path(binding['output_root'])/'pre'
    accepted=native_read(file_ref(pre/'ACCEPTED_PRE_REF.json'));handoff=native_read(accepted['handoff'])
    receipt=native_read(accepted['pre_strategy_receipt'])
    candidates=[s['candidate'] for s in handoff['selected_states']]
    if binding['round_id']==authority['materialization_round_id']:
        representation={'path':str(Path(source_ref['path']).parent/authority['frozen_registration_member']),'file_sha256':authority['frozen_registration_sha256']}
        frozen=native_read(representation)
        if receipt['pre_strategy_receipt_sha256']!=frozen['pre_strategy_receipt_sha256'] or accepted['artifact']['file_sha256']!=frozen['accepted_pre_ref']['sha256']:raise ValueError('FROZEN_PRE_MATERIALIZATION_IDENTITY')
        rows=frozen['execution_contracts']
        old=native_read(authority['partial_plan_ref']);assert_unsubmitted(Path(authority['partial_plan_ref']['path']).parent,old)
    else:
        from pchsi.cognitive_runtime.response import parse_provider_response,extract_output_text
        raw=native_read(receipt['accepted_raw_response_ref'],as_bytes=True)
        value=json.loads(extract_output_text(parse_provider_response(raw)))
        rows=value.get('execution_contracts')
        if rows is None:raise ValueError('ACCEPTED_PRE_TYPED_EXECUTION_ANNEX_MISSING')
        representation=receipt['accepted_raw_response_ref']
    validate_annex(rows,candidates)
    registry={'schema_id':'REGISTERED_CURRENT_PRE_OPTION_REGISTRY_V1','round_id':binding['round_id'],
        'parent_policy_id':binding['parent_policy_id'],'accepted_pre_ref':accepted['artifact'],
        'capture_ref':capture,'handoff_ref':accepted['handoff'],'representation_ref':representation,
        'execution_contracts':rows,'source_authority':source_ref,'candidate_reselection_performed':False,
        'provider_call_count_added':0,'partial_portfolio_execution_allowed':False}
    identity=digest(registry);parent=out/'registered_executions'/identity
    path=parent/'OPTION_REGISTRY.json';immutable_json(path,registry)
    index={'schema_id':'REGISTERED_H44_EXECUTION_INDEX_V1','round_id':binding['round_id'],
        'original_run_root':str(out/'run'),'execution_run_root':str(parent/'h44/run'),
        'registration_sha256':identity,'option_registry_ref':file_ref(path),'capture_ref':capture,'source_authority':source_ref}
    immutable_json(out/'REGISTERED_H44_EXECUTION_INDEX.json',index)
    return index
