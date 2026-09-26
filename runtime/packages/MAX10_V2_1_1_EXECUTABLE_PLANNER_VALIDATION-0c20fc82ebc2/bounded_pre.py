"""Registered, capacity-bounded PRE review and complete-strategy materialization."""
from contextlib import ExitStack, contextmanager
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import json
import os

from strategy_planner import MAP_PROMPT, TEXT_FIELDS, plan_schema, validate_review, derive_universe, check_final_strategies
from pre_capacity import build_review_packets, pack_review_packets, verify_review_coverage, restore_projection, canonical, digest

STAGE='R-PRE-PRIMARY-V2'
REVIEW_SCHEMA='REGISTERED_STRATEGY_SOURCE_REVIEWS_V1'


def review_schema(max_text=8192):
    item=plan_schema(max_text)
    item['properties']['fragment_id']={'type':'string'}
    item['required'].append('fragment_id')
    return {'type':'object','additionalProperties':False,'required':['reviews'],
        'properties':{'reviews':{'type':'array','items':item}}}


def enrich_items(items, contexts, pairs):
    result=[]
    for item in items:
        state=item['source'].get('source_state_sha256')
        result.append({**item,'exact_source_context':contexts.get(state),'original_candidate_pair':pairs.get(state)})
    return result


@contextmanager
def review_runtime(core, values, root, authority, contexts, pairs):
    import jsonschema
    from exact_bindings import immutable_json, immutable_bytes, file_ref
    root=Path(root);prompt=root/'REVIEW_PROMPT.txt';schema_path=root/'REVIEW_SCHEMA.json'
    prompt_text=MAP_PROMPT+'''\nReturn one review per fragment, preserving its packet_id and fragment_id.
Read all parts, including global history and records without candidates. For a
fragmented source, distinguish partial evidence and uncertainty; later aggregation
will examine ALL fragment reviews before freezing that source's strategy. Output
concise strategy fields that fit the parent model context, not long essays.\n'''
    immutable_bytes(prompt,prompt_text.encode())
    # Each send reviews one complete source fragment; portfolio growth no
    # longer squeezes every generated semantic field to a shorter string.
    max_text=8192  # Existing native Dual-View field ceiling, not a task choice.
    schema,_=core.schema_compatibility.normalize_const_types(review_schema(max_text))
    immutable_json(schema_path,schema)
    manifest=core.x.build_overlay_manifest(values['runtime_manifest'],file_ref(prompt)['file_sha256'],file_ref(schema_path)['file_sha256'],core.domain_hash)
    row=manifest['stage_rows'][-1]
    row.update(prompt_relative_path=str(prompt.absolute()),output_schema_relative_path=str(schema_path.absolute()),
        output_schema_id=REVIEW_SCHEMA,prompt_template_id=REVIEW_SCHEMA,
        required_projection_identity_fields=['experiment_id','source_projection_sha256','items'])
    manifest['runtime_manifest_sha256']=core.domain_hash('UNIFIED_COGNITIVE_RUNTIME_MANIFEST_V1',manifest,excluded_field='runtime_manifest_sha256')
    immutable_json(root/'REVIEW_RUNTIME_MANIFEST.json',manifest)
    validator=jsonschema.Draft202012Validator(schema)
    native_render=core.rr.render_stage_request
    def render(**kw):
        bundle=native_render(**kw)
        if len(canonical(bundle['provider_request']))>authority['context_window_tokens']-bundle['provider_request']['max_output_tokens']:
            raise ValueError('REVIEW_PACKER_WIRE_BOUND_VIOLATION')
        return bundle
    def validate(*,stage_id,text,raw_response_sha256,projection):
        value=json.loads(text);validator.validate(value)
        expected={i['fragment_id']:i for i in projection['items']}
        if len(value['reviews'])!=len(expected) or {r['fragment_id'] for r in value['reviews']}!=set(expected):
            raise ValueError('REVIEW_FRAGMENT_COVERAGE_MISMATCH')
        for review in value['reviews']:
            item=expected[review['fragment_id']];state=item['source'].get('source_state_sha256')
            validate_review(review,packet_id=item['packet_id'],context=contexts.get(state),pair=pairs.get(state))
        return {**value,'review_sha256':core.domain_hash(REVIEW_SCHEMA,value)}
    def artifact_identity(*,stage_id,artifact):
        expected=core.domain_hash(REVIEW_SCHEMA,{k:v for k,v in artifact.items() if k!='review_sha256'})
        if artifact['review_sha256']!=expected:raise ValueError('REVIEW_ARTIFACT_HASH')
        return expected
    with ExitStack() as stack:
        stack.enter_context(patch.object(core.rr,'load_runtime_manifest',lambda *a,**kw:manifest))
        stack.enter_context(patch.object(core.orch,'load_runtime_manifest',lambda *a,**kw:manifest))
        stack.enter_context(patch.object(core.orch,'validate_stage_output',validate))
        stack.enter_context(patch.object(core.orch,'validated_artifact_identity',artifact_identity))
        # Packing uses the unguarded exact renderer. Only sends use the bound guard.
        stack.enter_context(patch.object(core.orch,'render_stage_request',render))
        yield manifest,native_render,artifact_identity


def execute_reviews(binding, values, core, projection, root, authority):
    from exact_bindings import immutable_json,read_json,file_ref
    root=Path(root)
    evidence=projection['blind_input']['analyzer_evidence_view']
    contexts={r['source_state_sha256']:r for r in evidence['source_contexts']}
    pairs={r['source_state_sha256']:r for r in projection['blind_input']['registered_candidate_universe']['pair_table']}
    inventory=build_review_packets(projection)
    def projected(items):return {'experiment_id':authority['experiment_id'],'review_phase':'REVIEW_OR_REDUCE',
        'source_projection_sha256':inventory['projection_canonical_sha256'],'items':enrich_items(items,contexts,pairs)}
    access={'schema_id':'V1232V_RESEARCH_PLANNER_PRE_TASK_ACCESS_V1','schema_version':1,
        'task_id':binding['round_id'],'gamefile_sha256':inventory['projection_canonical_sha256'],
        'access_class':'TRAIN_UPDATE_RESEARCH_PLANNER_VISIBLE','dataset_split':'train',
        'teacher_call_permitted':True,'training_permitted':False,'select_evaluation_permitted':False,
        'confirmatory_permitted':False,'benchmark_result_values_visible':False,'policy_action_authority':False}
    results=[];receipts=[]
    def status(**fields):
        from datetime import datetime,timezone
        target=root/'REVIEW_PROGRESS.json';target.parent.mkdir(parents=True,exist_ok=True)
        tmp=target.with_suffix('.tmp')
        tmp.write_text(json.dumps({'schema_id':'REGISTERED_PRE_REVIEW_PROGRESS_V1',
            'updated_utc':datetime.now(timezone.utc).isoformat(),'completed_calls':len(receipts),**fields})+'\n')
        os.replace(tmp,target)
    with review_runtime(core,values,root,authority,contexts,pairs) as (manifest,render,artifact_identity):
        output_budget=manifest['stage_rows'][-1]['max_output_tokens']
        def wire(items):return render(stage_id=STAGE,projection=projected(items))['provider_request']
        plan=pack_review_packets(inventory,render=wire,context_limit=authority['context_window_tokens'],max_output=output_budget)
        if restore_projection(plan)!=projection:raise ValueError('REVIEW_EVIDENCE_ROUNDTRIP')
        immutable_json(root/'REVIEW_COVERAGE_PLAN.json',plan)

        def call(items, phase):
            payload=projected(items)
            unit_sha=core.domain_hash('REGISTERED_PRE_REVIEW_UNIT_V1',payload)
            unit=core.identity(scientific_unit_type='ROUND',scientific_unit_id=unit_sha,
                source_unit_manifest_sha256=inventory['projection_canonical_sha256'],
                task_set_manifest_sha256=projection['dynamic_pair_universe_sha256'],task_id=None,gamefile_sha256=None,
                group_manifest_sha256=None,round_evidence_package_sha256=projection['blind_input']['analyzer_terminal_sha256'])
            bundle=render(stage_id=STAGE,projection=payload)
            if len(canonical(bundle['provider_request']))>authority['context_window_tokens']-output_budget:
                raise ValueError('REVIEW_PHASE_ENVELOPE_BOUND_VIOLATION')
            status(state='WAITING_PROVIDER',phase=phase,planned_map_calls=sum(len(b['items']) for b in plan['batches']),
                current_request_sha256=bundle['request_body_sha256'])
            options=dict(runtime_root=root/'calls',unit_identity=unit,stage_id=STAGE,
                condition_id=None,round_id=binding['round_id'],policy_version=binding['parent_policy_id'],
                projection=payload,task_access=access,domain_hash=core.domain_hash,
                api={'render_stage_request':render,'execute_one':core.orch.execute_one,'validated_artifact_identity':artifact_identity})
            from review_boundary import execute_review
            result=execute_review(core.u.execute_or_reuse,options,core,authority['review_boundary_contract'],
                file_ref(Path(__file__).with_name('review_boundary.py')),root/'REVIEW_BOUNDARY_TRACE.jsonl')
            if result['status']!='ACCEPTED':raise ValueError('STRATEGY_REVIEW_NOT_ACCEPTED:'+str(result))
            path=Path(result['call_dir'])/'validated_artifact.json';artifact=read_json(path)
            artifact_identity(stage_id=STAGE,artifact=artifact)
            receipts.append({'phase':phase,'artifact_ref':file_ref(path),'logical_call_ref':file_ref(Path(result['call_dir'])/'logical_call.json'),
                'request_body_sha256':bundle['request_body_sha256'],'wire_bytes':len(canonical(bundle['provider_request']))})
            status(state='ACCEPTED',phase=phase,planned_map_calls=sum(len(b['items']) for b in plan['batches']),last_logical_call_id=result['logical_call_id'])
            return artifact['reviews']

        # The phase is part of exact wire sizing too; reserve it during packing.
        for batch in plan['batches']:
            for item in batch['items']:
                results.extend(call([item],'SOURCE_MAP'))
        verify_review_coverage(plan,[r['fragment_id'] for r in results])
        by_packet={p['packet_id']:[] for p in inventory['packets']}
        for row in results:by_packet[row['packet_id']].append(row)
        reduced=[]
        for packet in inventory['packets']:
            rows=by_packet[packet['packet_id']]
            if len(rows)==1:reduced.append(rows[0]);continue
            # Every oversized source is reviewed fully before source-level reduction.
            current=rows
            while len(current)>1:
                chunks=[];chunk=[]
                def make(rs):
                    item={'packet_id':packet['packet_id'],'kind':packet['kind'],'source':packet['source'],
                        'parts':[{'review':r} for r in rs]}
                    item['fragment_id']=digest(item);return item
                for review in current:
                    probe=make(chunk+[review])
                    if chunk and len(canonical(wire([probe])))>authority['context_window_tokens']-output_budget:
                        chunks.append(chunk);chunk=[]
                    chunk.append(review)
                if chunk:chunks.append(chunk)
                if len(chunks)>=len(current):raise ValueError('REVIEW_REDUCTION_OUTPUT_CANNOT_FIT_REGISTERED_CONTEXT')
                current=[call([make(chunk)],'COMPLETE_SOURCE_REDUCE')[0] for chunk in chunks]
            reduced.extend(current)
    receipt={'schema_id':'REGISTERED_COMPLETE_PRE_REVIEW_RECEIPT_V1','experiment_id':authority['experiment_id'],
        'coverage_plan_ref':file_ref(root/'REVIEW_COVERAGE_PLAN.json'),'all_source_records_reviewed':True,
        'source_record_count':len(inventory['expected_records']),'source_packet_count':len(contexts),
        'calls':receipts,'reviews':reduced,'raw_evidence_truncated':False,
        'aggregation_is_model_summary_not_lossless_original':True}
    immutable_json(root/'COMPLETE_REVIEW_RECEIPT.json',receipt)
    status(state='ALL_SOURCE_REVIEWS_COMPLETE',planned_map_calls=sum(len(b['items']) for b in plan['batches']),all_source_records_reviewed=True)
    return receipt,contexts


def run_pre(binding,values,core,tail,universe,out,*,authority):
    import pre_stage
    from exact_bindings import read_ref,immutable_json,file_ref
    from training_binding import strategy_source
    from cue_strategy import build_plan,execution_identity
    out=Path(out)
    projection=read_ref({**authority['source_projection_ref'],'file_sha256':authority['source_projection_ref'].get('sha256',authority['source_projection_ref'].get('file_sha256'))})
    if projection['round_id']!=binding['round_id'] or projection['blind_input']['parent_policy_id']!=binding['parent_policy_id']:
        raise ValueError('REUSED_PRE_SOURCE_IDENTITY')
    receipt,contexts=execute_reviews(binding,values,core,projection,out/'source_reviews',authority)
    derived,registry=derive_universe(universe,receipt['reviews'],contexts,authority['experiment_id'],core.domain_hash,build_plan,execution_identity)
    registry['review_receipt_ref']=file_ref(out/'source_reviews/COMPLETE_REVIEW_RECEIPT.json')
    immutable_json(out/'DERIVED_STRATEGY_UNIVERSE.json',derived)
    immutable_json(out/'CUE_STRATEGY_REGISTRY.json',registry)
    binding['refs']['cue_strategy_registry']=file_ref(out/'CUE_STRATEGY_REGISTRY.json')
    # A separate new source seal, not a mutation of the historical Analyzer terminal.
    derived_tail={**tail,'schema_id':'REGISTERED_PLANNER_DERIVED_STRATEGY_TAIL_V1',
        'original_analyzer_terminal_sha256':tail['terminal_sha256'],
        'derived_universe_ref':file_ref(out/'DERIVED_STRATEGY_UNIVERSE.json'),
        'review_receipt_ref':registry['review_receipt_ref']}
    derived_tail['terminal_sha256']=core.domain_hash(derived_tail['schema_id'],derived_tail,excluded_field='terminal_sha256')
    immutable_json(out/'DERIVED_STRATEGY_TAIL.json',derived_tail)
    native_sealed=pre_stage.sealed;native_translate=core.x.translate_pair_universe
    native_prompt=strategy_source.extend_pre_prompt
    native_schema=strategy_source.extend_pre_schema
    native_finalize=core.x.finalize_dynamic_primary_pre_v2
    native_render=core.rr.render_stage_request
    def translate(u,domain_hash):
        v=native_translate(u,domain_hash)
        for row,source in zip(v['pair_table'],u['pair_table'],strict=True):
            row['strategy_review']=source['strategy_review']
            for condition in ('A2','A3'):
                row[condition].update({k:source[condition][k] for k in ('strategy_plan','planner_viable','planner_rationale','execution_coverage')})
        v['representation_repair_only']=False;v['scientific_selection_changed']=True
        v['view_sha256']=domain_hash(v['schema_id'],v,excluded_field='view_sha256');return v
    def sealed(c,schema,value,field):
        if schema=='STRONG_RESEARCHER_BLIND_PRE_INPUT_V3':
            compact_receipt={**receipt,'reviews':[{k:v for k,v in review.items() if k!='plans'} for review in receipt['reviews']]}
            value={**value,'experiment_id':authority['experiment_id'],'complete_source_reviews':compact_receipt,
                'strategy_scope':'COMPLETE_REGISTERED_GUARDED_STRATEGY_INTERVENTION',
                'reused_analyzer_evidence_not_new_independent_samples':True}
        return native_sealed(c,schema,value,field)
    def prompt(text):return text+'''\nSTRATEGY VALIDATION EXPERIMENT: evaluate complete registered strategy_plan,
not merely the candidate envelope's initial action. Goals appear beside each source.
All original evidence has been reviewed in the bound source-review calls; their
summaries retain uncertainty and counterevidence. Choose a scientifically useful
portfolio of testable mechanism repairs under the derived budget; there is no
one-state preference and a partial subgoal is eligible when its effect is falsifiable.
Do not equate distractor handling with task completion. New plans were not checked
by historical X. Review their goal alignment, live initial action, progress and
recovery/fallback here. Check execution_coverage and actual registered phases: a
program with no later phases tests one initial action plus parent cue, not enforced
task decomposition or automatic search/recovery. For a high-level hypothesis,
prefer supported plans that actually execute its necessary causal phases. Do not
assume the weak frozen parent will carry out unimplemented prose. Retain useful
local repairs when warranted, with their limited scope explicit. Do not invent
extra phases or select candidates merely to fill a quota.
Reject nonviable or unsupported plans. For each selected
candidate return ONE training_strategies row with source_state_sha256,
source_candidate_sha256 and strategy_plan_sha256. This SHA reference selects the
complete already registered strategy and public phase program. The deterministic
adapter expands those exact bytes and candidate/menu refs, preserving this same
accepted PRE response and original plan provenance. Do not recopy or abbreviate
the plan prose. Entire plan identity is frozen before causal execution. Return
execution_contracts=[]: that legacy field covers fixed short options only; the
complete cue strategy contracts are registered separately and must not be changed.\n'''
    def schema(base):
        from typed_options import annex_schema
        value=native_schema(base)
        value['properties']['execution_contracts']=annex_schema()
        value['required'].append('execution_contracts')
        fields={k:{'type':'string','pattern':'^[0-9a-f]{64}$'} for k in ['source_state_sha256','source_candidate_sha256','strategy_plan_sha256']}
        value['properties']['training_strategies']['items']={'type':'object','properties':fields,'required':list(fields),'additionalProperties':False}
        return value
    def finalize(*,value,**kw):
        from typed_options import validate_annex
        current=deepcopy(value);rows=current.pop('execution_contracts',None)
        accepted=native_finalize(value=current,**kw)
        if rows is not None:
            from pre_stage import selected_candidates
            validate_annex(rows,selected_candidates(accepted,{'pair_table':kw['pair_rows']}))
        return accepted
    def render(**kw):
        bundle=native_render(**kw)
        maximum=authority['context_window_tokens']-bundle['provider_request']['max_output_tokens']
        from lossless_context import encode_bundle
        bundle,proof=encode_bundle(bundle,maximum,core.domain_hash)
        if len(canonical(bundle['provider_request']))>maximum:
            raise ValueError('PRE_REDUCED_PORTFOLIO_EXCEEDS_BOUND_REQUIRES_REVIEW_REDUCTION')
        immutable_json(out/'FINAL_PRE_REQUEST_PREFLIGHT.json',{'request_body_sha256':bundle['request_body_sha256'],
            'request_bytes':len(canonical(bundle['provider_request'])),'input_wire_limit':maximum,
            'lossless_encoding':proof,
            'source_reviews_ref':registry['review_receipt_ref'],'source_count':len(contexts),'pair_count':len(derived['pair_table'])})
        return bundle
    from strategy_hooks import training_scope
    with training_scope(registry),patch.object(core.x,'translate_pair_universe',translate),patch.object(pre_stage,'sealed',sealed),\
         patch.object(strategy_source,'extend_pre_prompt',prompt),patch.object(strategy_source,'extend_pre_schema',schema),\
         patch.object(core.x,'finalize_dynamic_primary_pre_v2',finalize),\
         patch.object(core.rr,'render_stage_request',render),patch.object(core.orch,'render_stage_request',render):
        accepted,handoff=pre_stage.run_pre(binding,values,core,derived_tail,derived,out)
    return {'accepted':accepted,'handoff':handoff,'candidate_universe_ref':file_ref(out/'DERIVED_STRATEGY_UNIVERSE.json')}
