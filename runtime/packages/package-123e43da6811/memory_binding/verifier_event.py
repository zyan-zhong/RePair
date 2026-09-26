"""Project the existing verifier's complete paired evidence into native events."""
import json
from pathlib import Path
from .current_source import canonical,read_ref,sha
from .producer import write_once


def validate_verifier(*,plan_ref,verifier_ref,request):
    plan=json.loads(read_ref(plan_ref));verifier=json.loads(read_ref(verifier_ref))
    for value,field in ((plan,'plan_sha256'),(verifier,'environment_result_package_sha256')):
        if value.get(field)!=sha(canonical({key:val for key,val in value.items() if key!=field})):
            raise ValueError('MEMORY_VERIFIER_CONTENT_IDENTITY')
    if plan.get('source_request')!=request or plan['round_id']!=request['round_id']:
        raise ValueError('MEMORY_CURRENT_PLAN_REQUEST_IDENTITY')
    if (verifier.get('schema_id')!='CURRENT_ROUND_INDEPENDENT_VERIFIER_RESULT_V1' or
            verifier.get('round_id')!=request['round_id'] or verifier.get('plan_sha256')!=plan['plan_sha256']):
        raise ValueError('MEMORY_CURRENT_VERIFIER_IDENTITY')
    return plan,verifier


def build_shadow_event(*,request,record,eligible,access,local_result_sha256,candidate_sha256,
                       source_state_sha256,plan,verifier,verifier_ref,output_root):
    from pchsi.memory.round_maintenance import (MemoryRecordBindingV1,MemoryShadowEventV1,
        MemorySourcePartitionV1,VerifierEffectV1)
    from pchsi.research_intelligence.human_f0f1_runtime import classify_pair_effect_v1,aggregate_five_pair_effects_v1
    if access.round_id!=request['round_id'] or access.request_sha256!=request['request_sha256'] or access.access_class!='TRAIN_UPDATE':
        raise ValueError('MEMORY_EVENT_CURRENT_SOURCE_AUTHORITY')
    states=[row for row in verifier['state_results'] if row['source_state_sha256']==source_state_sha256]
    if len(states)!=1 or states[0]['source_candidate_sha256']!=candidate_sha256:
        raise ValueError('MEMORY_EVENT_CANDIDATE_STATE_IDENTITY')
    state=states[0]
    rows=[row for row in verifier['pair_results'] if row['source_state_sha256']==source_state_sha256]
    seeds=plan['handoff']['paired_seeds']
    if len(rows)!=len(seeds) or {row['replicate_index'] for row in rows}!=set(range(len(seeds))):
        raise ValueError('MEMORY_EVENT_COMPLETE_REGISTERED_PAIR_SET')
    by_sha={row['evidence_sha256']:row for row in verifier['branch_records']}
    effects=[];complete=[];arms={'F0':[],'F1':[]}
    for row in sorted(rows,key=lambda x:x['replicate_index']):
        index=row['replicate_index']
        if row['source_candidate_sha256']!=candidate_sha256 or row['paired_seed']!=seeds[index]:
            raise ValueError('MEMORY_EVENT_PAIR_IDENTITY')
        found={}
        for arm in arms:
            evidence=row[arm.lower()+'_evidence_sha256']
            branch=None if evidence is None else by_sha.get(evidence)
            if evidence is not None and branch is None: raise ValueError('MEMORY_EVENT_BRANCH_REF_MISSING')
            if branch is not None:
                if evidence!=sha(canonical({k:v for k,v in branch.items() if k!='evidence_sha256'})):
                    raise ValueError('MEMORY_EVENT_BRANCH_HASH')
                if any(branch.get(k)!=v for k,v in {'source_state_sha256':source_state_sha256,
                        'source_candidate_sha256':candidate_sha256,'arm':arm,'replicate_index':index,
                        'continuation_seed':seeds[index]}.items()):
                    raise ValueError('MEMORY_EVENT_BRANCH_IDENTITY')
            found[arm]=branch
            arms[arm].append({'replicate_index':index,'paired_seed':seeds[index],'evidence_sha256':evidence})
        f0,f1=found['F0'],found['F1']
        ok=all(value and value.get('evidence_complete') is True and value.get('scientific_outcome_produced') is True
               for value in (f0,f1)) and f1.get('option_environment_step_count',0)>0
        effect=classify_pair_effect_v1(f0_success=f0.get('terminal_success') if f0 else None,
            f1_success=f1.get('terminal_success') if f1 else None,f0_complete=bool(ok),f1_complete=bool(ok))
        if row.get('complete')!=bool(ok) or row.get('effect')!=effect['effect']:
            raise ValueError('MEMORY_EVENT_NATIVE_PAIR_CLASSIFICATION')
        effects.append(effect['effect']);complete.append(bool(ok))
    aggregate=aggregate_five_pair_effects_v1(effects)
    if state['stable_effect']!=aggregate['stable_effect'] or plan['handoff']['stable_direction_min_pairs']!=4:
        raise ValueError('MEMORY_EVENT_NATIVE_AGGREGATE_CLASSIFICATION')
    # Each arm ref retains the entire frozen repetition set. No convenient pair is selected.
    refs={arm:write_once(Path(output_root)/(arm+'_PAIRED_EVIDENCE.json'),canonical({
        'schema_id':'MEMORY_REGISTERED_ARM_EVIDENCE_V1','round_id':request['round_id'],
        'source_state_sha256':source_state_sha256,'source_candidate_sha256':candidate_sha256,
        'arm':arm,'verifier_ref':verifier_ref,'pairs':values})) for arm,values in arms.items()}
    event=MemoryShadowEventV1(round_id=request['round_id'],record_binding=MemoryRecordBindingV1(
        memory_lineage_id=record.memory_lineage_id,record_version=record.record_version,
        canonical_record_sha256=record.canonical_record_sha256),source_partition=MemorySourcePartitionV1.TRAIN_UPDATE,
        analyzer_finding_sha256=local_result_sha256,candidate_repair_sha256=candidate_sha256,
        verifier_effect=VerifierEffectV1(aggregate['stable_effect'].title()),
        f0_evidence_sha256=refs['F0']['file_sha256'],f1_evidence_sha256=refs['F1']['file_sha256'],
        evidence_complete=bool(eligible and all(complete)),evaluation_contamination_clean=True)
    return event,write_once(Path(output_root)/'MEMORY_SHADOW_EVENT_V1.json',canonical(event.to_dict()))
