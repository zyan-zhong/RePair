"""Narrow registered hooks shared by PRE, controller, GPU and training replay."""
from contextlib import contextmanager,ExitStack
from pathlib import Path
from unittest.mock import patch
from copy import deepcopy
import hashlib,json,sys
import cue_strategy as cue


def checked(ref):
    raw=Path(ref['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ref.get('sha256',ref.get('file_sha256')):
        raise ValueError('STRATEGY_REFERENCE_SHA_MISMATCH')
    return json.loads(raw)


def plans_for(registry):
    plans={p['strategy_plan_sha256']:cue.validate_plan(p) for p in registry['plans']}
    if len(plans)!=len(registry['plans']):raise ValueError('DUPLICATE_STRATEGY_PLAN')
    return plans


@contextmanager
def training_scope(registry):
    from training_binding import strategy_source as source
    from strategy_planner import check_final_strategies
    plans=plans_for(registry);original=source.validate_pre_strategies;derive=source.derive_current_verified_rows
    import types
    native_schema=source.extend_pre_schema
    original=types.FunctionType(original.__code__,{**original.__globals__,'extend_pre_schema':native_schema},original.__name__,original.__defaults__,original.__closure__)
    original.__kwdefaults__=source.validate_pre_strategies.__kwdefaults__
    def validate(strategies,**kwargs):
        selected={c['candidate_sha256']:plans[c['source_proposal_sha256']] for c in kwargs['selected_candidates']}
        candidates={c['candidate_sha256']:c for c in kwargs['selected_candidates']}
        expanded=[]
        for row in strategies:
            candidate=candidates.get(row['source_candidate_sha256'])
            if candidate is None:raise ValueError('STRATEGY_REFERENCE_NOT_SELECTED')
            plan=selected[row['source_candidate_sha256']]
            if set(row)!={'source_state_sha256','source_candidate_sha256','strategy_plan_sha256'} or row['source_state_sha256']!=plan['source_state_sha256'] or row['strategy_plan_sha256']!=plan['strategy_plan_sha256']:
                raise ValueError('STRATEGY_REFERENCE_IDENTITY')
            expanded.append({'source_state_sha256':row['source_state_sha256'],'source_candidate_sha256':row['source_candidate_sha256'],
                'strategy':{**deepcopy(plan['strategy']),'evidence_refs':source.candidate_evidence_refs(candidate)}})
        strategies=expanded
        check_final_strategies(strategies,selected)
        result=original(strategies,**kwargs)
        for row in result:
            candidate=row['complete_registered_candidate'];plan=selected[candidate['candidate_sha256']]
            row['causal_verification_scope']=cue.SCOPE
            row['complete_strategy_contract']=cue.bind_contract(candidate,plan)
            row['same_pre_strategy_reference_expansion']={'strategy_plan_sha256':plan['strategy_plan_sha256'],
                'raw_response_modified':False,'scientific_choices_changed':False,'registered_before_final_pre':True}
        return result
    def verified(**kw):
        plan=kw['plan'];verifier=kw['verifier']
        validate_persisted_branches(plan,verifier['branch_records'],registry)
        rows=derive(**kw)
        for row in rows:
            if row['verification']['causal_verification_scope']!=cue.SCOPE:
                raise ValueError('STRATEGY_TRAINING_CAUSAL_SCOPE_CHANGED')
        return rows
    with patch.object(source,'validate_pre_strategies',validate),patch.object(source,'derive_current_verified_rows',verified):yield


def validate_persisted_branches(plan,branches,registry):
    from pchsi.research_intelligence.human_f0f1_runtime import load_continuation_runtime_binding_v2
    plans=plans_for(registry)
    bindings={x['binding']['branch_key_sha256']:x['binding'] for x in plan['branch_bindings']}
    for record in branches:
        if not record.get('evidence_complete') or not record.get('scientific_outcome_produced'):continue
        binding=bindings[record['branch_key_sha256']]
        contract=checked({'path':binding['typed_contract_path'],'sha256':binding['typed_contract_file_sha256']})
        cue.validate_contract(contract)
        if contract['plan']!=plans[contract['plan']['strategy_plan_sha256']]:raise ValueError('STRATEGY_PLAN_REGISTRY_DRIFT')
        runtime=load_continuation_runtime_binding_v2(Path(binding['runtime_path']),
            expected_file_sha256=binding['runtime_file_sha256'],expected_model=binding['policy_model'])
        cue.validate_branch_evidence(record,contract,arm=binding['arm'],native_runtime=runtime,expected_seed=binding['paired_seed'])


def instrument_verifier(module, registry, registry_ref, implementation_ref):
    original=module.verify_plan
    if getattr(original,'_cue_verifier',False):return
    def verify(plan_path,run_root):
        plan=module.read_json(plan_path)
        if plan.get('cue_strategy_registry_ref')!=registry_ref or plan.get('strategy_implementation_ref')!=implementation_ref:
            raise ValueError('STRATEGY_PLAN_IMPLEMENTATION_BINDING')
        records=[]
        for branch in plan['branch_bindings']:
            path=Path(run_root)/'branches'/branch['binding']['branch_key_sha256']/'BRANCH_TERMINAL.json'
            if path.is_file():
                value=module.read_json(path)
                if value.get('evidence_sha256')!=module.sha(module.canonical({k:v for k,v in value.items() if k!='evidence_sha256'})):
                    raise ValueError('STRATEGY_BRANCH_FILE_HASH')
                records.append(value)
        validate_persisted_branches(plan,records,registry)
        write=module.put_json
        def put(path,value):
            if value.get('schema_id')=='CURRENT_ROUND_INDEPENDENT_VERIFIER_RESULT_V1':
                # Native GPU and login controller persist the same native shape.
                # Scope is already hash-bound in plan and each branch contract.
                pass
            return write(path,value)
        with patch.object(module,'put_json',put):
            result=original(plan_path,run_root)
        if result.get('status')=='VERIFIED_COMPLETE':
            from process_effect import summarize
            summarize(plan,result,run_root)
        return result
    verify._cue_verifier=True;module.verify_plan=verify


@contextmanager
def worker_scope(registry_ref, implementation_ref, *, gpu_entry=None):
    import option_adapter,native_branch,round_plan,independent_verifier,controller
    registry=checked(registry_ref);checked(implementation_ref)
    restore=cue.install_dispatch(option_adapter,native_branch,round_plan,plans_for(registry))
    original_put=round_plan.put_json
    def put(path,value):
        if value.get('schema_id')=='CURRENT_ACCEPTED_PRE_NATIVE_EXECUTION_PLAN_V1':
            value.update(cue_strategy_registry_ref=registry_ref,strategy_implementation_ref=implementation_ref,
                causal_verification_scope=cue.SCOPE,standalone_action_causal_effect_claimed=False)
            value['scope_notice']={**value['scope_notice'],
                'causal_verification_scope':cue.SCOPE,'cue_strategy_registry_ref':registry_ref,
                'f1_treatment':'Registered public phase rules followed, when needed, by the frozen parent with the complete strategy cue.',
                'f0_treatment':'Unchanged frozen parent continuation.',
                'standalone_action_causal_effect_claimed':False,
                'new_plans_reviewed_by_historical_analyzer_x':False}
            from process_effect import register
            value['process_metric_registration_ref']=register(value,Path(path).parent,implementation_ref)
            value['plan_sha256']=round_plan.sha(round_plan.canonical({k:v for k,v in value.items() if k!='plan_sha256'}))
        return original_put(path,value)
    old_verify=independent_verifier.verify_plan
    instrument_verifier(independent_verifier,registry,registry_ref,implementation_ref)
    with ExitStack() as stack:
        stack.callback(restore)
        stack.callback(setattr,independent_verifier,'verify_plan',old_verify)
        stack.enter_context(patch.object(round_plan,'put_json',put))
        # Native controller imports verify_plan inside run_controller; patch
        # its source module above, not a nonexistent controller global.
        if gpu_entry is not None:stack.enter_context(patch.object(controller,'_registered_gpu_entry',Path(gpu_entry)))
        stack.enter_context(training_scope(registry))
        # GPU branch execution receives this registration through its frozen plan.
        # Controller materialization itself does not start any environment.
        yield


def replay_closed_h44(result, *, native=None):
    """Replay the native verifier with the exact implementation recorded in plan."""
    if native is None:
        from entry.driver import replay_closed_h44 as native
    import reuse
    refs=result['stage_evidence_refs'];plan=checked(refs['execution_plan'])
    registry_ref=plan['cue_strategy_registry_ref'];implementation_ref=plan['strategy_implementation_ref']
    registry=checked(registry_ref);checked(implementation_ref)
    load=reuse.load_file
    def wrapped(name,path):
        module=load(name,path)
        if name=='_resident_original_h44_verifier':instrument_verifier(module,registry,registry_ref,implementation_ref)
        return module
    with patch.object(reuse,'load_file',wrapped):return native(result)
