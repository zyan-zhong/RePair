from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
from copy import deepcopy
import json
from pre_evidence import build_view,enrich_pair_view,require_later_round

def enabled(binding,authority):
    from exact_bindings import read_json,read_ref
    if binding['round_id']==authority['excluded_round_id']:return False
    req=read_ref(binding['refs']['request'])
    current=read_json(Path(authority['owner_root'])/'request_bindings'/(req['request_sha256']+'.json'))
    r=current['request'];r={**r,'file_sha256':r.get('file_sha256',r.get('sha256'))}
    if read_ref(r)!=req:raise ValueError('PRE_OWNER_CURRENT_REQUEST_CHANGED')
    return require_later_round(binding,authority,current=current)

def collect_data(binding,values,core,prepared,out,calls,tail,universe):
    from exact_bindings import read_json,read_ref,file_ref
    local=Path(binding['output_root'])/'local';sources=[];a1s={}
    source_index=read_json(local/'SOURCE_UNITS.json')
    for row in source_index['rows']:
        sm=read_ref(row['source_manifest']);unit=Path(row['source_manifest']['path']).parent
        pack=read_json(unit/'analyzer_evidence_pack.json')
        if core.domain_hash('ANALYZER_EVIDENCE_PACK_V1',pack,excluded_field='evidence_pack_sha256')!=pack['evidence_pack_sha256']:
            raise ValueError('PRE_PACK_CONTENT_SHA_MISMATCH')
        access=read_json(unit/'task_access_record.json')
        if access.get('dataset_split')!='train' or access.get('teacher_call_permitted') is not True:
            raise ValueError('PRE_TRAIN_ACCESS_REQUIRED')
        sources.append({'source_unit_id':row['source_unit_id'],'manifest':sm,'manifest_ref':row['source_manifest'],
            'pack':pack,'pack_ref':file_ref(unit/'analyzer_evidence_pack.json')})
    for item in prepared:
        for path in item['a1_paths']:
            v=read_json(path);identity=core.api['validated_artifact_identity'](stage_id='L-A1',artifact=v)
            if identity not in item['group']['source_local_result_sha256s']:raise ValueError('PRE_LOCAL_GROUP_LINEAGE')
            a1s[identity]={'artifact':v,'ref':file_ref(path)}
    return {'binding':binding,'values':values,'prepared':prepared,'calls':calls,'sources':sources,'local_a1':a1s,
        'tail':tail,'universe':universe,'local_census':read_json(local/'GROUP_PREPARATION_CENSUS.json'),
        'capability':read_json(Path(out)/'ANALYZER_CAPABILITY_PROFILE_V1.json'),
        'behavior':read_json(Path(out)/'ANALYZER_POLICY_BEHAVIOR_PROFILE_V1.json')}

@contextmanager
def install(authority,source_ref):
    import adapter,pre_stage
    from exact_bindings import immutable_json,file_ref,read_json,canonical
    from training_binding import strategy_source
    native_group=adapter.run_group_tail;native_pre=adapter.run_pre
    pending={}
    def group(binding,values,core,prepared,accesses,out):
        if not enabled(binding,authority):return native_group(binding,values,core,prepared,accesses,out)
        calls=[];native=core.u.execute_or_reuse
        def record(**kw):
            result=native(**kw);row={'stage':kw['stage_id'],'condition':kw['condition_id'],'result':result}
            if result['status']=='ACCEPTED':
                path=Path(result['call_dir'])/'validated_artifact.json';artifact=read_json(path)
                if core.api['validated_artifact_identity'](stage_id=kw['stage_id'],artifact=artifact)!=result['validated_artifact_sha256']:
                    raise ValueError('PRE_ACCEPTED_ANALYSIS_SHA_MISMATCH')
                row.update(artifact=artifact,artifact_ref=file_ref(path))
            calls.append(row);return result
        with patch.object(core.u,'execute_or_reuse',record):
            tail,universe=native_group(binding,values,core,prepared,accesses,out)
        view=build_view(collect_data(binding,values,core,prepared,out,calls,tail,universe))
        path=Path(out)/'REGISTERED_READABLE_PLANNER_PRE_EVIDENCE_V1.json';immutable_json(path,view)
        index={'schema_id':'REGISTERED_PLANNER_PRE_EVIDENCE_INDEX_V1','round_id':binding['round_id'],
            'source_extension':source_ref,'view_ref':file_ref(path),'pair_universe_sha256':universe['pair_universe_sha256'],
            'analyzer_terminal_sha256':tail['terminal_sha256']}
        immutable_json(Path(out)/'REGISTERED_PLANNER_PRE_EVIDENCE_INDEX_V1.json',index)
        pending[binding['round_id']]=view
        return tail,universe
    def pre(binding,values,core,tail,universe,out):
        if not enabled(binding,authority):return native_pre(binding,values,core,tail,universe,out)
        view=pending[binding['round_id']];native_sealed=pre_stage.sealed;native_translate=core.x.translate_pair_universe
        native_prompt=strategy_source.extend_pre_prompt;native_render=core.rr.render_stage_request
        def translate(u,domain_hash):
            value=enrich_pair_view(native_translate(u,domain_hash),view)
            value['view_sha256']=domain_hash(value['schema_id'],value,excluded_field='view_sha256')
            return value
        def seal(c,schema,value,field):
            if schema=='STRONG_RESEARCHER_BLIND_PRE_INPUT_V3':
                value={**value,'analyzer_evidence_view':view,'registered_evidence_projection_source':source_ref}
            return native_sealed(c,schema,value,field)
        def prompt(text):
            return native_prompt(text)+('\nUse analyzer_evidence_view: it contains the registered current TRAIN failure census, '
                'public task context, local hypotheses with support and counterevidence, group mechanisms, component '
                'attributions, policy profiles and Formal-X scope. Review these with the governed Researcher Memory '
                'when selecting the principal bottleneck and experiment. These diagnoses are hypotheses, not causal '
                'effect labels. Do not infer content from opaque hashes or invent missing source details.\n')
        def render(*,stage_id,projection,**kwargs):
            bundle=native_render(stage_id=stage_id,projection=projection,**kwargs)
            if stage_id=='R-PRE-PRIMARY-V2':
                if projection['blind_input']['analyzer_evidence_view']!=view:raise ValueError('PRE_RENDERED_EVIDENCE_MISSING')
                request=bundle['provider_request'];raw=canonical(request)
                # Conservative byte upper bound on tokens, derived from the
                # registered same-model context policy rather than sample counts.
                maximum=authority['planner_context_policy']['min_model_context_window_tokens']-request['max_output_tokens']
                if len(raw)>maximum:raise ValueError('PRE_REGISTERED_CONTEXT_BUDGET_EXCEEDED_NO_SEND')
                immutable_json(Path(out)/'READABLE_PRE_REQUEST_PREFLIGHT.json',{
                    'schema_id':'REGISTERED_READABLE_PRE_REQUEST_PREFLIGHT_V1','request_body_sha256':bundle['request_body_sha256'],
                    'request_bytes':len(raw),'conservative_input_byte_budget':maximum,'view_sha256':view['view_sha256'],
                    'source_extension':source_ref,'candidate_count':len(universe['pair_table']),
                    'current_round_retroactive_change':False,'filesystem_discovery_used':False})
            return bundle
        with patch.object(core.x,'translate_pair_universe',translate),patch.object(pre_stage,'sealed',seal),\
             patch.object(strategy_source,'extend_pre_prompt',prompt),patch.object(core.rr,'render_stage_request',render):
            return native_pre(binding,values,core,tail,universe,out)
    with patch.object(adapter,'run_group_tail',group),patch.object(adapter,'run_pre',pre):yield
