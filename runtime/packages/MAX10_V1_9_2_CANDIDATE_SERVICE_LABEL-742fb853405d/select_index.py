from pathlib import Path
import json,hashlib
INDEX='REGISTERED_OFFOFF_EXECUTION_INDEX.json'

def checked(ref):
    p=Path(ref['path']);raw=p.read_bytes()
    if p.is_symlink() or hashlib.sha256(raw).hexdigest()!=ref.get('sha256',ref.get('file_sha256')):raise ValueError('SELECT_INDEX_REFERENCE_SHA')
    return json.loads(raw)

def resolve(root):
    root=Path(root);p=root/INDEX
    if not p.exists():return root
    value=json.loads(p.read_bytes());a=checked(value['source_authority'])
    manifest=Path(value['source_manifest']['path']).read_bytes();identity=hashlib.sha256(manifest).hexdigest()
    if identity!=value['source_manifest']['file_sha256']:raise ValueError('SELECT_INDEX_SOURCE_SHA')
    if Path(value['source_manifest']['path'])!=Path(value['source_authority']['path']).parent/'PACKAGE_FILES.sha256':raise ValueError('SELECT_INDEX_SOURCE_LAYOUT')
    rows={name:sha for sha,name in (line.split(maxsplit=1) for line in manifest.decode().splitlines())}
    if rows.get('AUTHORITY.json')!=value['source_authority']['file_sha256']:raise ValueError('SELECT_INDEX_AUTHORITY_SHA')
    if value['schema_id']!='REGISTERED_OFFOFF_EXECUTION_INDEX_V1' or value['original_root']!=str(root) or a['original_offoff_root']!=str(root):raise ValueError('SELECT_INDEX_IDENTITY')
    expected=root/'registered_candidate_bindings'/identity
    if str(expected)!=value['execution_root'] or value['round_id']!=a['label_recovery_round_id']:raise ValueError('SELECT_INDEX_TARGET')
    return expected

def register(root,a,identity,source,publish=True):
    from exact_bindings import file_ref,immutable_json,read_ref
    root=Path(root)
    if str(root)!=a['original_offoff_root']:raise ValueError('CURRENT_SELECT_ROOT')
    for ref in a['preserved_training_select_refs'].values():read_ref(ref,as_bytes=True)
    # Original materialization failed before binding/parallel/job creation.
    for name in ['binding/CURRENT_NATIVE_OFFOFF_EXECUTION_BINDING.json','parallel/CURRENT_NATIVE_OFFOFF_PARALLEL_BINDING.json','jobs']:
        if (root/name).exists():raise ValueError('ORIGINAL_SELECT_ALREADY_STARTED_NO_REBIND:'+name)
    target=root/'registered_candidate_bindings'/identity
    value={'schema_id':'REGISTERED_OFFOFF_EXECUTION_INDEX_V1','original_root':str(root),'execution_root':str(target),
        'round_id':a['label_recovery_round_id'],'source_authority':file_ref(source/'AUTHORITY.json'),'source_manifest':file_ref(source/'PACKAGE_FILES.sha256'),
        'training_reexecution_authorized':False,'candidate_weight_change':False}
    if publish:immutable_json(root/INDEX,value)
    return target
