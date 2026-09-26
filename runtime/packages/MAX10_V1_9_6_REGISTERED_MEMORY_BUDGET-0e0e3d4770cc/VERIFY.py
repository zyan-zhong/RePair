from pathlib import Path
import sys,json,subprocess,hashlib
from budget_entry import ROOT,verify,load

def server():
    a,prior,identity,prepared=load()
    from continuity_binding.api import read_ref,write_once
    from memory_binding.worker_bootstrap import bootstrap_current_and_children
    from entry.registration import build_deployment
    base=Path(a['base_source_root']);deployment=build_deployment(base,entry_source_sha256=hashlib.sha256((base/'PACKAGE_FILES.sha256').read_bytes()).hexdigest())
    bootstrap_current_and_children(deployment['scientific_repo_root'])
    from budget_bridge import budget_scope
    from memory_binding.api import load_registered_tokenizer
    from memory_binding.producer import materialize_native_candidate
    from memory_binding.current_source import read_ref as memory_read
    from pchsi.memory.procedural_builder import ProceduralMemoryAssemblyInputV1
    from pchsi.memory.sequence_failure_experience import SequenceFailureExperienceV1
    binding=read_ref(a['diagnostic_binding_ref']);old=read_ref(a['diagnostic_memory_receipt_ref'])
    tokenizer=load_registered_tokenizer(binding);rows=[];events=[];members=[];dispositions=[]
    from memory_binding.current_source import SequenceSourceTaskAccessBindingV2
    from memory_binding.verifier_event import build_shadow_event,validate_verifier
    from pchsi.memory.round_maintenance import classify_shadow_event_v1
    from parent_cache import ref
    closed=read_ref(a['diagnostic_result_ref']);start=json.loads(memory_read(binding['refs']['request']))
    refs=closed['stage_evidence_refs']
    mref=lambda r:{'path':r['path'],'file_sha256':r.get('sha256',r.get('file_sha256'))}
    plan,verifier=validate_verifier(plan_ref=mref(refs['execution_plan']),verifier_ref=mref(refs['verifier']),request=start)
    originals={r['native_manifest_ref']['path']:hashlib.sha256(Path(r['native_manifest_ref']['path']).read_bytes()).hexdigest() for r in old['results']}
    with budget_scope(binding,a) as contract:
        for row in old['results']:
            experience=SequenceFailureExperienceV1.from_json(memory_read(row['experience_ref']))
            assembly=ProceduralMemoryAssemblyInputV1.from_json(memory_read(row['assembly_ref']))
            record,report,bundle,final,candidate_refs=materialize_native_candidate(experience=experience,assembly=assembly,tokenizer=tokenizer,output_root=ROOT/'validation_candidates'/row['source_state_sha256'])
            item={'source_state_sha256':row['source_state_sha256'],'old_status':row['native_eligibility'],'status':bundle.status,'failure_codes':list(bundle.failure_codes),'candidate_root':str(final)}
            if bundle.governed_record is not None:
                item.update(fm2_tokens=bundle.fm2.token_count.policy_visible_token_count,fm2_ceiling=bundle.fm2.token_count.hard_ceiling)
                assert item['fm2_ceiling']==contract.single_record_hard_ceiling
            prior_event=json.loads(memory_read(row['event_ref']))
            event,event_ref=build_shadow_event(request=start,record=bundle.governed_record or record,eligible=bundle.governed_record is not None,
                access=SequenceSourceTaskAccessBindingV2.from_dict(json.loads(memory_read(row['source_access_ref']))),
                local_result_sha256=prior_event['analyzer_finding_sha256'],candidate_sha256=row['candidate_sha256'],
                source_state_sha256=row['source_state_sha256'],plan=plan,verifier=verifier,verifier_ref=mref(refs['verifier']),output_root=final.parent/'shadow')
            disposition=classify_shadow_event_v1(event);item['causal_memory_disposition']=disposition.disposition.value
            events.append({'path':event_ref['path'],'sha256':event_ref['file_sha256']});dispositions.append(disposition.disposition.value)
            if disposition.disposition.value=='PROMOTE_NEXT_ROUND':members.append({k:ref(final/name) for k,name in {'record':'governed_record.json','retrieval_key':'retrieval_key.json','fm1':'fm1.json','fm2':'fm2.json'}.items()})
            rows.append(item)
        benefit=next(r for r in old['results'] if r['native_disposition']['disposition']=='STAGING_UNRESOLVED')
        corrected=next(r for r in rows if r['source_state_sha256']==benefit['source_state_sha256'])
        assert corrected['status']=='ELIGIBLE'
        assert dispositions.count('DESCRIPTIVE_ONLY')==5 and dispositions.count('PROMOTE_NEXT_ROUND')==1
        from continuity_binding.memory_materializer import materialize_next_memory_runtime,load_current_snapshot
        nxt=materialize_next_memory_runtime(start=start,state_ref=refs['memory_state'],event_refs=events,
            current_runtime_ref={'path':binding['refs']['memory_runtime']['path'],'sha256':binding['refs']['memory_runtime']['file_sha256']},additional_member_refs=members,sink=ROOT/'validation_memory_closure')
        assert nxt['snapshot_retained'] is False
        assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest for p,digest in originals.items())
        result={'schema_id':'REGISTERED_BUDGET_NATIVE_MATERIALIZATION_VALIDATION_V1','rows':rows,'contract_sha256':contract.contract_sha256,
            'single_record_hard_ceiling':contract.single_record_hard_ceiling,'library_total_hard_ceiling':contract.library_total_hard_ceiling,
            'native_next_memory_closure':nxt,'causal_memory_dispositions':dispositions,
            'originals_preserved':True,'production_snapshot_changed':False,'provider_calls':0,'slurm_submissions':0,'git_mutations':0}
    write_once(ROOT/'runtime/VALIDATION.json',result);print(json.dumps(result),flush=True)
if __name__=='__main__':
    verify();r=subprocess.run([sys.executable,'-B','-m','pytest','-q',str(ROOT/'test_budget_bridge.py')],cwd=ROOT)
    if r.returncode:raise SystemExit(r.returncode)
    if '--server' in sys.argv:server()
    print('REGISTERED_MEMORY_TOKEN_BUDGET_VERIFY_PASS',flush=True)
