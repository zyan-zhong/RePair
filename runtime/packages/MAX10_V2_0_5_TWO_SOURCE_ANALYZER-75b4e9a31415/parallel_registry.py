"""Parallelize registered Local sources; retain native identities and dispositions."""
from pathlib import Path
from collections import OrderedDict
from source_parallel import map_sources,check_admission,admission_closed,close_admission,AdmissionClosed

def run_registry(rr,native,*,workers,observe,registry_path,output_root,limit=None,campaign_authority=None):
    registry_path=Path(registry_path);out=Path(output_root)
    reg=rr._obj(registry_path);rr.validate_artifact('RUNTIME_INPUT_REGISTRY_V1',reg)
    if (out/'execution_manifest.json').is_file():
        return native(registry_path=registry_path,output_root=out,limit=limit,campaign_authority=campaign_authority)
    units=reg['units'] if limit is None else reg['units'][:limit]
    if not isinstance(units,list):raise TypeError('registry units must be list')
    out.mkdir(parents=True,exist_ok=True);base=registry_path.resolve().parent
    restarts=0 if campaign_authority is None else campaign_authority.max_infrastructure_attempt_restarts
    grouped=OrderedDict();logical_ids=set()
    for index,unit in enumerate(units):
        identity=rr._obj(base/unit['scientific_unit_identity_path'])
        projection=rr._obj(base/unit['input_projection_path']);access=rr._obj(base/unit['task_access_record_path'])
        for field,expected in [('evidence_pack_sha256','expected_common_evidence_sha256'),
            ('a1_local_result_sha256','expected_a1_local_result_sha256'),('memory_pack_sha256','expected_memory_pack_sha256')]:
            if unit.get(expected) is not None and projection.get(field)!=unit[expected]:
                raise ValueError('registry binding mismatch for '+field)
        logical=rr._logical_id(identity=identity,unit=unit,registry=reg,projection=projection)
        if logical in logical_ids:raise ValueError('DUPLICATE_LOGICAL_DIRECTORY_IN_REGISTRY')
        logical_ids.add(logical)
        grouped.setdefault(str(unit['source_unit_id']),[]).append((index,unit,identity,projection,access,logical))
    def source(item):
        sid,entries=item;rows=[];quarantined=False;terminal_route=None
        for index,unit,identity,projection,access,logical in entries:
            if admission_closed():break
            common={'source_unit_id':sid,'stage_id':unit['stage_id'],'condition_id':unit.get('condition_id'),
                'scientific_unit_id':identity['scientific_unit_id']}
            if quarantined:
                result={'logical_call_id':None,'call_dir':None,'status':'QUARANTINED_SOURCE_SKIPPED',
                    'method_failure_reason':'SOURCE_QUARANTINED_AFTER_AMBIGUOUS_POST_SEND','hard_stop':False,
                    'provider_call_executed':False,'same_logical_call_resend_authorized':False}
            else:
                call=out/logical
                if call.exists():result=rr._adopt_terminal(call)
                else:
                    try:
                        result=rr.execute_one(output_root=out,unit_identity=identity,stage_id=unit['stage_id'],
                            condition_id=unit['condition_id'],round_id=reg['round_id'],policy_version=reg['policy_version'],
                            projection=projection,task_access=access,max_infrastructure_attempt_restarts=restarts)
                    except AdmissionClosed:break
                    result['reused_terminal']=False;result['same_logical_call_resend_authorized']=False
                if result.get('hard_stop') is True:
                    route=rr.classify_hard_stop(row={**common,**result},call_dir=Path(str(result['call_dir'])))
                    if route['route']==rr.QUARANTINE_SOURCE_CONTINUE_UNRELATED:quarantined=True
                    else:terminal_route=str(route['route']);close_admission()
            rows.append((index,{**common,**result}))
        return {'rows':rows,'quarantined':[sid] if quarantined else [],'terminal_route':terminal_route}
    results=map_sources(list(grouped.items()),source,key=lambda x:x[0],workers=workers,observe=observe)
    ordered=sorted(pair for item in results for pair in item['rows'])
    terminal_route=next((x['terminal_route'] for x in results if x['terminal_route'] is not None),None)
    if terminal_route is None and [i for i,_ in ordered]!=list(range(len(units))):raise ValueError('PARALLEL_REGISTRY_INCOMPLETE')
    manifest={'schema_id':'COGNITIVE_RUNTIME_EXECUTION_MANIFEST_V2','schema_version':2,
        'registry_sha256':reg['registry_sha256'],'round_id':reg['round_id'],'policy_version':reg['policy_version'],
        'campaign_authority_sha256':None if campaign_authority is None else campaign_authority.authority_sha256,
        'max_infrastructure_attempt_restarts':restarts,
        'quarantined_source_ids':sorted(s for x in results for s in x['quarantined']),
        'terminal_route':terminal_route,'rows':[row for _,row in ordered]}
    rr.write_new_json(out/'execution_manifest.json',manifest)
    return manifest,20 if terminal_route is not None else 0
