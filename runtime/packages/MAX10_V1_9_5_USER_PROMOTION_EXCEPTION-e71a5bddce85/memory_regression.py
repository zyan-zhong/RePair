"""Real closed evidence, isolated next-index and native PRE sealing; no provider."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import tempfile

def run(a):
    from continuity_binding.api import read_ref,write_once
    from research_memory import installed,read_index
    from parent_cache import ref
    from entry.driver import ExistingComponentRoundDriver as Driver
    import adapter,pre_stage
    from pchsi.reference_loop.canonical import domain_hash
    old=read_ref(a['research_memory_bootstrap_closed_result_ref'])
    nxt=read_ref(ref(Path(a['authorized_round_result_path']).parent/'INTENT.json'))['start']
    with tempfile.TemporaryDirectory(prefix='research-memory-no-provider-') as tmp:
        config={**a,'owner_root':tmp,'research_memory_activation_after_round_index':0}
        binding={'round_index':1}
        write_once(Path(tmp)/'request_bindings'/(nxt['request_sha256']+'.json'),{'round_index':2})
        def next_(driver,start,result,governance):return nxt
        def pre_(binding,values,core,tail,universe,out):
            return pre_stage.sealed(core,'STRONG_RESEARCHER_BLIND_PRE_INPUT_V3',{'round_id':values['request']['round_id']},'blind_input_sha256')
        with patch.object(Driver,'build_next',next_),patch.object(adapter,'run_pre',pre_),installed(config):
            stub=SimpleNamespace(_binding=lambda start:binding)
            assert Driver.build_next(stub,old,old,None)==nxt
            index=read_index(config,nxt);assert len(index['lesson_refs'])==1
            core=SimpleNamespace(domain_hash=domain_hash)
            projection=adapter.run_pre({}, {'request':nxt},core,None,None,Path(tmp)/'pre')
            memory=projection['prior_closed_round_research_memory'];assert memory['index_ref']==ref(Path(tmp)/'request_bindings/research_lessons'/nxt['request_sha256']/'AUTHORITY.json')
            post=read_ref(old['stage_evidence_refs']['post_artifact']);assert memory['lessons'][0]['researcher_post']['lesson']==post['lesson']
            assert 'source_round_promotion_was_user_exception' not in memory['lessons'][0] and 'source_result_ref' not in memory['lessons'][0]
            assert projection['blind_input_sha256']==domain_hash(projection['schema_id'],projection,excluded_field='blind_input_sha256')
            receipt=read_ref(ref(Path(tmp)/'pre/REGISTERED_RESEARCH_MEMORY_CONSUMPTION.json'))
            assert receipt['attached_before_provider_request'] and receipt['readable_lesson_count']==1
            assert Driver.build_next(stub,old,old,None)==nxt
    print('REAL_CLOSED_EVIDENCE_NEXT_INDEX_NATIVE_PRE_SEAL_IDEMPOTENCE_PASS provider_calls=0',flush=True)
    import json,copy
    from research_memory import project,researcher_view
    attempt=Path(a['authorized_round_result_path']).parent
    binding=read_ref(ref(attempt/'CURRENT_ANALYZER_BINDING.json'));core=adapter.load_cores(binding)
    projection_path=attempt/'analyzer/pre/V1232V_PRE_PROJECTION_V1.json';projection_ref=ref(projection_path)
    projection=copy.deepcopy(read_ref(projection_ref));manifest=read_ref(ref(attempt/'analyzer/pre/EXACT_RUNTIME_MANIFEST.json'))
    lesson=project(start=old,result=old,post=read_ref(old['stage_evidence_refs']['post_artifact']),memory=read_ref(old['stage_evidence_refs']['memory_materialization']))
    projection['blind_input']['prior_closed_round_research_memory']={'lessons':[researcher_view({**lesson,'source_round_promotion_was_user_exception':True})]}
    blind=projection['blind_input'];blind['blind_input_sha256']=domain_hash(blind['schema_id'],blind,excluded_field='blind_input_sha256');projection['blind_input_sha256']=blind['blind_input_sha256']
    with patch.object(core.rr,'load_runtime_manifest',lambda *args,**kwargs:manifest):
        rendered=core.rr.render_stage_request(stage_id='R-PRE-PRIMARY-V2',projection=projection)
    payload=json.dumps(rendered['provider_request'],ensure_ascii=False)
    assert 'prior_closed_round_research_memory' in payload and lesson['researcher_post']['lesson'] in payload
    assert 'source_round_promotion_was_user_exception' not in payload
    assert ref(projection_path)==projection_ref
    print('NATIVE_PROVIDER_REQUEST_CONTAINS_READABLE_LESSON_WITHOUT_HUMAN_SELECTION_METADATA_NO_SEND_PASS',flush=True)
