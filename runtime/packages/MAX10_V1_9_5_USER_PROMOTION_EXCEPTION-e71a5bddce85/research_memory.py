"""Carry accepted closed-round research lessons through a flat typed index."""
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import patch
from collections import Counter

POST_FIELDS=('lesson','next_round_implication','observed_outcome','hypothesis_status','alternative_explanations','unexpected_evidence','protocol_audit')

def project(*,start,result,post,memory):
    if result.get('schema_id')!='FORMAL_NATIVE_ROUND_RESULT_V1' or result.get('outcome') not in ('PROMOTED','ROLLED_BACK','NO_TRAINING_UPDATE') or result.get('benchmark_feedback_used') is not False:
        raise ValueError('RESEARCH_MEMORY_REQUIRES_CLOSED_VALID_TRAIN_ROUND')
    if not (start['round_id']==result['round_id']==post['round_id']==memory['round_id']) or start['request_sha256']!=result['request_sha256'] or start['request_sha256']!=memory['request_sha256']:
        raise ValueError('RESEARCH_MEMORY_SOURCE_ROUND')
    if post.get('schema_id')!='API_RESEARCHER_POST_PRIMARY_V1' or not all(k in post for k in POST_FIELDS):raise ValueError('ACCEPTED_STRUCTURED_POST_LESSON_REQUIRED')
    return {'schema_id':'CLOSED_TRAIN_RESEARCH_ROUND_LESSON_V1','source_round_id':start['round_id'],'source_request_sha256':start['request_sha256'],
        'researcher_post':{k:post[k] for k in POST_FIELDS},'analyzer_memory_inventory':dict(Counter(r['status'] for r in memory['results'])),
        'analyzer_memory_dispositions':dict(Counter(r.get('native_disposition',{}).get('disposition','UNRESOLVED') for r in memory['results'])),
        'source_access':'TRAIN_UPDATE','research_reference_only':True,'current_round_causal_labels_authorized':False,
        'training_supervision_authorized':False,'policy_action_authorized':False,'heldout_per_task_data_included':False,
        'post_authored_before_model_selection':True,'source_round_promotion_was_user_exception':result.get('human_scientific_decision_count',0)>0}

def index_path(a,request):return Path(a['owner_root'])/'request_bindings/research_lessons'/request['request_sha256']/'AUTHORITY.json'

def researcher_view(lesson):
    # Audit-only intervention identities and source paths never enter blind PRE.
    keys=('schema_id','source_round_id','source_request_sha256','researcher_post','analyzer_memory_inventory',
        'analyzer_memory_dispositions','source_access','research_reference_only','current_round_causal_labels_authorized',
        'training_supervision_authorized','policy_action_authorized','heldout_per_task_data_included')
    return {key:lesson[key] for key in keys}

def read_index(a,request):
    from continuity_binding.api import read_ref
    from parent_cache import ref
    path=index_path(a,request)
    if not path.exists():return None
    value=read_ref(ref(path))
    if value.get('schema_id')!='REGISTERED_PRIOR_RESEARCH_LESSON_INDEX_V1' or value.get('consumer_request_sha256')!=request['request_sha256']:raise ValueError('RESEARCH_MEMORY_CONSUMER_IDENTITY')
    seen=set()
    for source in value['lesson_refs']:
        lesson=read_ref(source);key=lesson['source_request_sha256']
        if key in seen or key==request['request_sha256'] or lesson.get('source_access')!='TRAIN_UPDATE' or lesson.get('research_reference_only') is not True:raise ValueError('RESEARCH_MEMORY_SOURCE_SCOPE')
        seen.add(key)
    return value

@contextmanager
def installed(a):
    import adapter,pre_stage
    from entry.driver import ExistingComponentRoundDriver as Driver
    from continuity_binding.api import read_ref,write_once
    from parent_cache import ref
    original_next=Driver.build_next;original_pre=adapter.run_pre
    def save_lesson(start,result):
        refs=result['stage_evidence_refs'];post=read_ref(refs['post_artifact']);memory=read_ref(refs['memory_materialization'])
        logical=read_ref(refs['post_logical_call'])
        if logical['terminal_method_status']!='ACCEPTED':raise ValueError('RESEARCH_MEMORY_POST_NOT_ACCEPTED')
        value=project(start=start,result=result,post=post,memory=memory)
        value.update(source_refs={k:refs[k] for k in ('post_artifact','post_logical_call','verifier','memory_materialization','memory_closure')},
            source_result_ref=ref(Path(result['attempt_root'])/'DRIVER_ROUND_RESULT.json'))
        # New explicit extension area; old round artifacts and active snapshots are untouched.
        sink=Path(a['owner_root'])/'runtime_extensions/research_lessons'/ref(Path(__file__))['sha256']/start['request_sha256']
        return write_once(sink/'ROUND_LESSON.json',value)
    def next_round(driver,start,result,governance):
        nxt=original_next(driver,start,result,governance)
        if driver._binding(start)['round_index']<a['research_memory_activation_after_round_index']:return nxt
        inherited=read_index(a,start);lessons=list(inherited['lesson_refs']) if inherited else []
        if inherited is None and driver._binding(start)['round_index']==a['research_memory_activation_after_round_index']:
            previous=read_ref(a['research_memory_bootstrap_closed_result_ref'])
            if (previous['next_parent_policy_id'],previous['next_parent_policy_artifact_sha256'])!=(start['parent_policy_id'],start['parent_policy_artifact_sha256']):raise ValueError('RESEARCH_MEMORY_BOOTSTRAP_PARENT_LINEAGE')
            lessons.append(save_lesson(previous,previous))
        if result['outcome']!='PROTOCOL_INFRA_INVALID':
            lesson_ref=save_lesson(start,result)
            if lesson_ref not in lessons:lessons.append(lesson_ref)
        if lessons:
            write_once(index_path(a,nxt),{'schema_id':'REGISTERED_PRIOR_RESEARCH_LESSON_INDEX_V1','consumer_request_sha256':nxt['request_sha256'],
                'consumer_round_id':nxt['round_id'],'lesson_refs':lessons,'source_module_ref':ref(Path(__file__)),'flat_index_no_recursive_discovery':True})
        return nxt
    def pre(binding,values,core,tail,universe,out):
        request=values['request'];owner_binding=read_ref(ref(Path(a['owner_root'])/'request_bindings'/(request['request_sha256']+'.json')))
        if owner_binding['round_index']<=a['research_memory_activation_after_round_index']:return original_pre(binding,values,core,tail,universe,out)
        index=read_index(a,request)
        if index is None:raise ValueError('REGISTERED_PRIOR_RESEARCH_LESSON_INDEX_MISSING')
        index_ref=ref(index_path(a,request));lessons=[researcher_view(read_ref(source)) for source in index['lesson_refs']]
        native_sealed=pre_stage.sealed
        from training_binding import strategy_source
        native_prompt=strategy_source.extend_pre_prompt
        def sealed(c,schema,value,field):
            if schema=='STRONG_RESEARCHER_BLIND_PRE_INPUT_V3':
                value={**value,'prior_closed_round_research_memory':{'index_ref':index_ref,'lessons':lessons}}
                write_once(Path(out)/'REGISTERED_RESEARCH_MEMORY_CONSUMPTION.json',{'schema_id':'REGISTERED_RESEARCH_MEMORY_PRE_CONSUMPTION_V1',
                    'request_sha256':request['request_sha256'],'index_ref':index_ref,'lesson_refs':index['lesson_refs'],
                    'attached_before_provider_request':True,'readable_lesson_count':len(lessons)})
            return native_sealed(c,schema,value,field)
        def prompt(text):return native_prompt(text)+'\nReview prior_closed_round_research_memory: accepted POST lessons and counterexplanations from CLOSED TRAIN rounds. Treat them as fallible research context, not current-round effect labels, proven general repairs, or authority to train/promote. Retain unresolved hypotheses and negative evidence when planning the next experiment.\n'
        with patch.object(pre_stage,'sealed',sealed),patch.object(strategy_source,'extend_pre_prompt',prompt):return original_pre(binding,values,core,tail,universe,out)
    with patch.object(Driver,'build_next',next_round),patch.object(adapter,'run_pre',pre):yield
