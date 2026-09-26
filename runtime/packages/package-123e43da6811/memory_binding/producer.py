"""Native factual reconstruction, assembly and candidate materialization adapters."""
from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path

from .current_source import build_current_source_access, canonical, read_ref, sha
from .same_call import FIELDS, validate_boundaries


def file_ref(path):
    path=Path(path).absolute()
    return {'path':str(path),'file_sha256':sha(path.read_bytes())}


def write_once(path,raw):
    path=Path(path).absolute()
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError('MEMORY_OUTPUT_ALIAS')
    path.parent.mkdir(parents=True,exist_ok=True)
    try:
        with path.open('xb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
    except FileExistsError:
        if path.read_bytes()!=raw: raise ValueError('IMMUTABLE_MEMORY_CONFLICT:' + str(path))
    return file_ref(path)


def domain(name,value):
    # Memory domain hashes use canonical evidence bytes including the terminal LF.
    return sha(name.encode('utf8')+b'\0'+canonical(value))


def load_attempt(repo,path):
    source=Path(repo)/'scripts/memory/materialize_sequence_failure_experience_v1.py'
    spec=importlib.util.spec_from_file_location('_current_memory_native_attempt_loader',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.load_attempt_directory_v1(Path(path))


def build_experience(*,source,request_ref,train_manifest_ref,local_result,error,condition,raw_response_sha256):
    from pchsi.memory.sequence_failure_experience import (
        RegisteredFailureSequenceWindowV1,build_sequence_failure_experience_v1)
    access,row=build_current_source_access(request_ref=request_ref,train_manifest_ref=train_manifest_ref,source=source)
    source=replace(source,task_access_record_line_index=access.task_access_record_line_index,task_access_record_bytes=row)
    identity=domain('STRONG_ANALYZER_MEMORY_WINDOW_REGISTRATION_V2',{
        'local_result_sha256':local_result['local_result_sha256'],'error_instance_id':error['error_instance_id'],
        'raw_response_sha256':raw_response_sha256,'request_sha256':access.request_sha256})
    registration=RegisteredFailureSequenceWindowV1(
        schema_id='REGISTERED_FAILURE_SEQUENCE_WINDOW_V1',schema_version=1,
        registration_id=identity,registration_authority_type='REGISTERED_BOUNDARY_LABEL',
        registration_protocol_id='STRONG_ANALYZER_ACCEPTED_CURRENT_TRAIN_UPDATE_V2',
        registration_artifact_sha256=raw_response_sha256,registration_record_sha256=sha(canonical(error)),
        source_bundle_sha256=source.attempt_bundle.attempt_bundle_sha256,
        source_attempt_id=source.episode_artifact.execution_attempt_id,source_task_id=source.episode_artifact.task_id,
        source_round=access.round_id,source_condition=condition,
        relevant_start_model_call_index=error['relevant_start_call_index'],
        registered_failure_onset_model_call_index=error['trigger_call_index'],
        final_model_call_index=error['critical_window_end_call_index'],
        registered_recovery_start_model_call_index=None,registered_recovery_final_model_call_index=None)
    experience=build_sequence_failure_experience_v1(source=source,task_access_binding=access,registration=registration)
    return experience,access


def build_assembly(*,experience,local_result,error,boundary,raw_response_sha256,logical_call_id,candidate=None):
    from pchsi.memory.applicability import (ApplicabilityBoundarySetV1,BoundaryTypeV1,
        BoundaryVerificationStatusV1,MemoryBoundaryClauseV1,NonApplicabilityDispositionV1,RevalidationRequirementV1)
    from pchsi.memory.procedural_record import MemoryAuthorityTypeV1 as Authority,MemoryEvidenceRefV1 as Ref,ProceduralMemoryLineageV1
    from pchsi.memory.procedural_builder import ProceduralMemoryAssemblyInputV1
    from pchsi.memory.semantic_recovery import (SemanticHypothesisAnnotationV1,SemanticAnnotationTypeV1,SemanticConfidenceV1,ProposedRecoveryV1)
    validate_boundaries([boundary],{'error_instances':[error]})
    if boundary['status']!='REGISTERED': return None
    experience_ref=Ref('SEQUENCE_FAILURE_EXPERIENCE_V1',experience.experience_id,sha(experience.canonical_bytes()))
    identity=domain('STRONG_ANALYZER_MEMORY_ASSEMBLY_V2',{'experience_id':experience.experience_id,
        'raw_response_sha256':raw_response_sha256,'error_instance_id':error['error_instance_id'],
        'candidate_sha256':None if candidate is None else candidate['candidate_sha256']})
    value=boundary['applicability']
    def clauses(key):
        result=[]
        for index,text in enumerate(value[key]):
            rid=domain('STRONG_ANALYZER_MEMORY_BOUNDARY_V2',{'assembly_identity':identity,'field':key,'index':index,'text':text})
            result.append(MemoryBoundaryClauseV1(boundary_type=BoundaryTypeV1(key.upper()),
                boundary_authority=Authority.REGISTERED_BOUNDARY,origin_role='STRONG_ANALYZER',registration_id=rid,
                origin_artifact_ref=Ref('REGISTERED_BOUNDARY_ARTIFACT',rid,raw_response_sha256),condition_text=text,
                source_refs=(experience_ref,),verification_status=BoundaryVerificationStatusV1.REGISTERED_UNVERIFIED))
        return tuple(result)
    applicability=ApplicabilityBoundarySetV1(**{key:clauses(key) for key in FIELDS},
        revalidation_requirement=RevalidationRequirementV1(value['revalidation_requirement']),
        non_applicability_disposition=NonApplicabilityDispositionV1(value['non_applicability_disposition']))
    semantic=[]
    for hypothesis in error['mechanism_hypotheses']:
        hid=domain('STRONG_ANALYZER_MEMORY_HYPOTHESIS_V2',{'assembly_identity':identity,'hypothesis_id':hypothesis['hypothesis_id']})
        semantic.append(SemanticHypothesisAnnotationV1(annotation_id=hid,
            annotation_type=SemanticAnnotationTypeV1.CANDIDATE_MECHANISM,authority_type=Authority.SEMANTIC_HYPOTHESIS,
            text=hypothesis['statement'],supporting_refs=(experience_ref,),
            counterevidence_refs=tuple(Ref('SEMANTIC_ANNOTATION_ARTIFACT',
                hid+'#counterevidence_refs/'+str(i),raw_response_sha256)
                for i,_ in enumerate(hypothesis.get('counterevidence_refs',[]))),
            # Analyzer confidence is numeric; no native bin thresholds exist.
            # Preserve the exact value in the origin artifact and do not invent bins.
            semantic_confidence=SemanticConfidenceV1.UNSPECIFIED,
            origin_role='STRONG_ANALYZER',origin_identity=logical_call_id,
            origin_artifact_ref=Ref('SEMANTIC_ANNOTATION_ARTIFACT',hid,raw_response_sha256)))
    proposed=()
    if candidate is not None:
        from pchsi.reference_loop.canonical import domain_hash
        if candidate['candidate_sha256']!=domain_hash(candidate['schema_id'],candidate,excluded_field='candidate_sha256'):
            raise ValueError('MEMORY_SELECTED_CANDIDATE_IDENTITY')
        steps=(candidate['exact_action'],) if candidate['exact_action'] is not None else tuple(candidate['option_actions'])
        if not steps: raise ValueError('MEMORY_SELECTED_CANDIDATE_ACTIONS_REQUIRED')
        proposed=(ProposedRecoveryV1(proposal_id=candidate['candidate_sha256'],authority_type=Authority.RECOVERY_PROPOSAL,
            procedure_steps=steps,source_refs=(experience_ref,),origin_role='STRONG_ANALYZER_GROUP_PROPOSAL',
            origin_identity=candidate['source_proposal_sha256'],origin_artifact_ref=Ref('RECOVERY_PROPOSAL_ARTIFACT',
                candidate['candidate_sha256'],sha(canonical(candidate)))),)
    lineage=domain('PROCEDURAL_MEMORY_LINEAGE_FROM_SOURCE_EXPERIENCE_V1',{
        'experience_id':experience.experience_id,'source_bundle_sha256':experience.source_bundle_sha256})
    return ProceduralMemoryAssemblyInputV1(schema_id='PROCEDURAL_MEMORY_ASSEMBLY_REGISTRATION_V1',schema_version=1,
        registration_id=identity,lineage=ProceduralMemoryLineageV1(lineage,1,None),
        creation_event_id=identity,creator_role='STRONG_ANALYZER_ACCEPTED_CURRENT_ROUND_BUILDER',
        source_experience_refs=(experience_ref,),applicability=applicability,semantic_hypotheses=tuple(semantic),
        observed_recovery_bindings=(),proposed_recoveries=proposed,relations=(),created_snapshot_candidate=None)


def materialize_native_candidate(*,experience,assembly,tokenizer,output_root):
    from pchsi.memory.candidate_materialization import (CandidateMaterializationItemV1,candidate_id_for_item_v1,
        materialize_candidate_item_v1,audit_candidate_directory_v1)
    from pchsi.memory.lifecycle_relations import EvaluationContaminationStatusV1
    root=Path(output_root).absolute();root.mkdir(parents=True,exist_ok=True)
    exp_ref=write_once(root/'source_experience.json',experience.canonical_bytes())
    assembly_ref=write_once(root/'assembly_registration.json',assembly.canonical_bytes())
    # CLEAN follows the verified current TRAIN_UPDATE source gate, not a model claim.
    contamination=EvaluationContaminationStatusV1.CLEAN
    args=dict(source_experience_sha256s=(exp_ref['file_sha256'],),assembly_registration_sha256=assembly_ref['file_sha256'],
              previous_record_sha256=None,evaluation_contamination_status=contamination)
    item=CandidateMaterializationItemV1(candidate_id=candidate_id_for_item_v1(**args),
        source_experience_paths=(exp_ref['path'],),assembly_registration_path=assembly_ref['path'],previous_record_path=None,**args)
    final=root/item.candidate_id
    # Native dry run constructs and validates the same immutable objects. Publication
    # stays native; a preexisting candidate is audited and compared, never overwritten.
    record,report,bundle,_=materialize_candidate_item_v1(item=item,tokenizer=tokenizer,output_root=None,execute=False)
    if final.exists():
        audit_candidate_directory_v1(final)
        if (final/'initial_record.json').read_bytes()!=record.canonical_bytes():
            raise ValueError('EXISTING_NATIVE_MEMORY_CANDIDATE_DRIFT')
        if (final/'source_integrity_report.json').read_bytes()!=report.canonical_bytes():
            raise ValueError('EXISTING_NATIVE_MEMORY_SOURCE_REPORT_DRIFT')
        if bundle is not None and bundle.governed_record is not None:
            for name,value in (('governed_record.json',bundle.governed_record),('fm1.json',bundle.fm1),('fm2.json',bundle.fm2)):
                if (final/name).read_bytes()!=value.canonical_bytes():
                    raise ValueError('EXISTING_NATIVE_MEMORY_PROJECTION_DRIFT:'+name)
    else:
        materialize_candidate_item_v1(item=item,tokenizer=tokenizer,output_root=root,execute=True)
        audit_candidate_directory_v1(final)
    return record,report,bundle,final,{'experience':exp_ref,'assembly':assembly_ref}


def partition_for_record(record,access,assembly_ref):
    from pchsi.memory.consumer_views import (MemorySourcePartitionBindingV1,MemorySourcePartitionV1,
        MemoryPartitionAuthorityScopeV1)
    payload={'memory_lineage_id':record.memory_lineage_id,'source_partition':'TRAIN_UPDATE',
        'source_collection_manifest_sha256':access.task_manifest_sha256,
        'task_access_authority_sha256':sha(canonical(access.to_dict())),
        'record_provenance_authority_sha256':assembly_ref['file_sha256']}
    return MemorySourcePartitionBindingV1(memory_lineage_id=record.memory_lineage_id,
        source_partition=MemorySourcePartitionV1.TRAIN_UPDATE,
        partition_authority_sha256=domain('MEMORY_SOURCE_PARTITION_AUTHORITY_V1',payload),
        authority_scope=MemoryPartitionAuthorityScopeV1.FULL_TRAIN_SOURCE_PROVENANCE,
        **{key:value for key,value in payload.items() if key.endswith('_sha256')})
