"""One validation invocation over registered source evidence and native stages."""
from contextlib import ExitStack
from pathlib import Path,PurePosixPath
from unittest.mock import patch
import hashlib,importlib.util,json,os,sys,traceback,uuid
ROOT=Path(__file__).resolve().parent

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify():
    seen=set()
    for line in (ROOT/'PACKAGE_FILES.sha256').read_text().splitlines():
        expected,name=line.split(maxsplit=1);p=PurePosixPath(name)
        if p.is_absolute() or '..' in p.parts or '\\' in name or name in seen:raise ValueError('PACKAGE_MEMBER_INVALID')
        seen.add(name)
        if (ROOT/name).is_symlink() or digest(ROOT/name)!=expected:raise ValueError('PACKAGE_SOURCE_CHANGED:'+name)
    implementation=json.loads((ROOT/'IMPLEMENTATION.json').read_bytes())
    for name,expected in implementation['files'].items():
        if digest(ROOT/name)!=expected:raise ValueError('STRATEGY_IMPLEMENTATION_CHANGED:'+name)
    return digest(ROOT/'PACKAGE_FILES.sha256')

def checked(ref,as_bytes=False):
    raw=Path(ref['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ref.get('sha256',ref.get('file_sha256')):raise ValueError('REGISTERED_INPUT_SHA_CHANGED')
    return raw if as_bytes else json.loads(raw)

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module

def progress(root,stage,**fields):
    from datetime import datetime,timezone
    p=Path(root)/'VALIDATION_PROGRESS.json';p.parent.mkdir(parents=True,exist_ok=True)
    value={'schema_id':'SINGLE_VALIDATION_PROGRESS_V1','stage':stage,'pid':os.getpid(),
        'host':os.uname().nodename,'updated_utc':datetime.now(timezone.utc).isoformat(),
        'validation_limit':1,'formal_round_increment':0,**fields}
    tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(value,sort_keys=True)+'\n');os.replace(tmp,p)

def execute(a,identity,*,preflight):
    import adapter,entry.driver as driver,entry.registration as registration,repair_feedback
    from exact_bindings import file_ref,read_ref,immutable_json
    from reuse import load_cores
    from one_validation import run_validation,NativeOperations
    from strategy_hooks import training_scope,replay_closed_h44
    from entry.campaign_owner import campaign_lock
    root=Path(a['experiment_root']);binding=checked(a['source_binding_ref'])
    deployment=registration.build_deployment(Path(a['native_entry_root']),entry_source_sha256=a['native_entry_manifest_sha256'])
    formal=Path(deployment['formal_state_root'])
    authority={**a['validation_authority'],'implementation_sha256':identity,'deployment':deployment,
        'paper_binding_ref':file_ref(formal/'FORMAL_MAX10_PAPER_TELEMETRY_BINDING_V1.json'),
        'paper_contract_ref':file_ref(formal/'PCHSI_PAPER_ROUND_EXPORT_CONTRACT_V1.json')}
    checked(a['source_campaign_terminal_ref'])
    if checked(a['previous_validation_terminal_ref'])['status']!='VALIDATION_COMPLETE':raise ValueError('PREVIOUS_VALIDATION_NOT_CLOSED')
    values=adapter.validate_binding(binding);core=load_cores(binding)
    class Operations(NativeOperations):
        def __init__(self):self.original_replay=driver.replay_closed_h44
        def replay(self,result):return replay_closed_h44(result,native=self.original_replay)
        def train(self,**kw):
            progress(root,'TRAINING')
            registry=checked(kw['analyzer_binding']['refs']['cue_strategy_registry'])
            import entry.training_job as training_job,types
            phase=training_job._run_phase
            scoped=types.FunctionType(phase.__code__,{**phase.__globals__,'__file__':str(ROOT/'training_worker.py')},phase.__name__,phase.__defaults__,phase.__closure__)
            scoped.__kwdefaults__=phase.__kwdefaults__
            with training_scope(registry),patch.object(training_job,'_run_phase',scoped):return super().train(**kw)
        def offoff(self,**kw):
            progress(root,'TRAIN_SELECT');return super().offoff(**kw)
        def validate_result(self,**kw):
            with patch.object(driver,'replay_closed_h44',self.replay):return super().validate_result(**kw)
        def close(self,**kw):
            progress(root,'MEMORY_CLOSURE');result=super().close(**kw)
            import research_memory
            refs=result['stage_evidence_refs']
            lesson=research_memory.project(start=kw['start'],result=result,post=checked(refs['post_artifact']),memory=checked(refs['memory_materialization']))
            lesson.update(experiment_id=authority['experiment_id'],formal_round_increment=0,independent_new_source_sample_count=0,
                source_refs={k:refs[k] for k in ['post_artifact','post_logical_call','verifier','memory_materialization','memory_closure']})
            immutable_json(root/'tail/VALIDATION_RESEARCH_LESSON.json',lesson)
            result['stage_evidence_refs']['validation_research_lesson']=file_ref(root/'tail/VALIDATION_RESEARCH_LESSON.json')
            return result
    native_dispatch=repair_feedback.WorkerDispatch.run
    def dispatch(instance,argv,*args,**kw):
        if instance.target==a['feedback_worker_ref']['path']:
            if len(argv)<5 or argv[2]!=instance.source:raise ValueError('STRATEGY_WORKER_DISPATCH_BINDING')
            instance.record(argv[4])
            request_path=Path(argv[4]);immutable_json(request_path.parent/'CUE_STRATEGY_WORKER_BINDING.json',{
                'request_ref':file_ref(request_path),'worker_ref':file_ref(ROOT/'strategy_worker.py'),
                'implementation_ref':file_ref(ROOT/'IMPLEMENTATION.json'),'previous_worker_ref':a['feedback_worker_ref']})
            return instance.native.run([*argv[:2],str(ROOT/'strategy_worker.py'),*argv[3:]],*args,**kw)
        return native_dispatch(instance,argv,*args,**kw)
    def pre(*args):
        from bounded_pre import run_pre
        from runtime_setup import cognitive
        progress(root,'STRATEGY_PRE_REVIEW',reused_rollout=True,reused_analyzer=True)
        with cognitive(args[0],a):return run_pre(*args,authority={**a['planner_authority'],'experiment_id':authority['experiment_id']})
    def h44(*args,**kw):
        from runtime_setup import cognitive
        progress(root,'STRATEGY_F0_F1_CAUSAL_VERIFICATION')
        immutable_json(Path(args[0]['output_root'])/'EXACT_ANALYZER_OPERATION_INPUT.json',args[0])
        with cognitive(args[0],a):return adapter.run_h44(*args,**kw)
    if preflight:
        from one_validation import _preflight
        _preflight(binding,values,authority,root)
        from pre_capacity import build_review_packets,pack_review_packets,restore_projection,canonical
        from bounded_pre import review_runtime,enrich_items,STAGE
        p=checked(a['planner_authority']['source_projection_ref']);e=p['blind_input']['analyzer_evidence_view']
        contexts={r['source_state_sha256']:r for r in e['source_contexts']}
        pairs={r['source_state_sha256']:r for r in p['blind_input']['registered_candidate_universe']['pair_table']}
        inventory=build_review_packets(p);sink=root/'preflight'/identity
        with review_runtime(core,values,sink,a['planner_authority'],contexts,pairs) as (manifest,render,_):
            def wire(items):return render(stage_id=STAGE,projection={'experiment_id':authority['experiment_id'],
                'review_phase':'REVIEW_OR_REDUCE','source_projection_sha256':inventory['projection_canonical_sha256'],
                'items':enrich_items(items,contexts,pairs)})['provider_request']
            plan=pack_review_packets(inventory,render=wire,context_limit=a['planner_authority']['context_window_tokens'],
                max_output=manifest['stage_rows'][-1]['max_output_tokens'])
            if restore_projection(plan)!=p:raise ValueError('PREFLIGHT_FULL_COVERAGE_ROUNDTRIP')
        from native_preflight import verify_native_pre
        boundary=verify_native_pre(binding,values,core,{**a['planner_authority'],
            'experiment_id':authority['experiment_id']+'-test-only'},sink,authority['source_files'])
        result={'schema_id':'STRATEGY_VALIDATION_NO_SEND_PREFLIGHT_V1','status':'PASS','provider_calls':0,
            'new_rollouts':0,'sources':len(contexts),'candidate_pairs':len(pairs),'batch_bytes':[b['wire_bytes'] for b in plan['batches']],
            'source_registry_verified':True,'native_binding_verified':True,'frozen_parent_verified':True,
            'complete_end_to_end_execution_verified':False,'native_pre_boundary':boundary,'implementation_sha256':identity}
        immutable_json(sink/'NO_SEND_PREFLIGHT.json',result)
        progress(root,'PREFLIGHT_PASSED',preflight=True,receipt_ref=file_ref(sink/'NO_SEND_PREFLIGHT.json'))
        print(json.dumps(result),flush=True);return 0
    # Same formal admission lock prevents a concurrent incumbent change.
    with campaign_lock(formal/'campaign_owner'),campaign_lock(Path(a['owner_root'])),\
         patch.object(repair_feedback.WorkerDispatch,'run',dispatch):
        checked(a['source_campaign_terminal_ref'])
        result=run_validation(binding=binding,values=values,core=core,authority=authority,experiment_root=root,
            pre_callable=pre,capture_callable=adapter.materialize_capture,h44_callable=h44,native=Operations())
    progress(root,'COMPLETED',result=result);print(json.dumps(result),flush=True);return 0

def main():
    import argparse
    p=argparse.ArgumentParser();mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--preflight',action='store_true');mode.add_argument('--run',action='store_true')
    mode.add_argument('--preflight-and-run',action='store_true');args=p.parse_args()
    identity=verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes())
    predecessor=a['predecessor'];path=Path(predecessor['root'])
    if digest(path/'PACKAGE_FILES.sha256')!=predecessor['manifest_sha256']:raise ValueError('PREDECESSOR_CHANGED')
    progress(a['experiment_root'],'BOOTSTRAPPING_REGISTERED_RUNTIME',preflight=args.preflight)
    sys.path.insert(0,str(path));prior=load_module('_v207_context_entry',path/'context_entry.py')
    prepared=prior.load()
    import entry.main as native_main
    # All existing registered operational/runtime hooks are installed by their
    # normal entry. The stopped campaign main is replaced by this isolated call.
    def current(argv=None):
        if args.preflight_and_run:execute(a,identity,preflight=True)
        return execute(a,identity,preflight=args.preflight)
    try:
        with patch.object(prior,'load',lambda:prepared),patch.object(native_main,'main',current):
            # Native invocation receipts bind the process PID; a new process
            # needs its own invocation, while scientific identity stays fixed.
            return prior.run(uuid.uuid4().hex)
    except Exception as exc:
        progress(a['experiment_root'],'STOPPED',error_type=type(exc).__name__,error=str(exc),preflight=args.preflight)
        raise

if __name__=='__main__':raise SystemExit(main())
