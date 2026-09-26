"""Bounded hooks over registered rendering, closed-round memory and H4.4 worker."""
from pathlib import Path
from contextlib import contextmanager
from copy import deepcopy
from unittest.mock import patch
import json,hashlib,inspect,types
from repair_guidance import OPTION_GUIDANCE,X_GUIDANCE,PRE_GUIDANCE
from trajectory_facts import project,canonical,history_summary

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def checked(ref):
    raw=Path(ref['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ref.get('sha256',ref.get('file_sha256')):raise ValueError('REPAIR_SOURCE_SHA_CHANGED')
    return json.loads(raw)

def eligible(a,binding):
    request=checked(binding['refs']['request']);path=Path(a['owner_root'])/'request_bindings'/(request['request_sha256']+'.json')
    index=json.loads(path.read_bytes())
    if checked(index['request'])!=request:raise ValueError('REPAIR_REQUEST_INDEX_MISMATCH')
    return index['round_index']>=a['repair_activation']['round_index']

def amend(bundle,hash_request):
    stage=bundle['stage_id']
    if stage not in ('G-A2','G-A3','X'):return bundle
    if bundle.get('registered_executable_dependency_guidance'):return bundle
    result=deepcopy(bundle)
    result['provider_request']['input'][0]['content'][0]['text']+=OPTION_GUIDANCE if stage!='X' else X_GUIDANCE
    result['request_body_sha256']=hash_request(result['provider_request'])
    result['registered_executable_dependency_guidance']=True
    return result

@contextmanager
def group_scope(core):
    native=core.api['render_stage_request']
    def render(**kwargs):return amend(native(**kwargs),lambda v:core.domain_hash('COGNITIVE_RUNTIME_PROVIDER_REQUEST_V1',v))
    with patch.dict(core.api,{'render_stage_request':render}),patch.object(core.rr,'render_stage_request',render),\
         patch.object(core.orch,'render_stage_request',render),patch.object(core.runner,'render_stage_request',render):yield

def prior_facts(a,request,root,identity):
    import research_memory
    from exact_bindings import immutable_json
    index=research_memory.read_index(a,request)
    if index is None:raise ValueError('REGISTERED_PRIOR_RESEARCH_LESSON_INDEX_MISSING')
    rows=[];refs=[]
    for ref in index['lesson_refs']:
        lesson=checked(ref);verifier_ref=lesson['source_refs']['verifier'];v=checked(verifier_ref)
        if v['round_id']!=lesson['source_round_id']:raise ValueError('REPAIR_CLOSED_TRAJECTORY_ROUND_MISMATCH')
        facts=project(v);sink=Path(a['owner_root'])/'runtime_extensions'/identity/'trajectory_facts'/verifier_ref.get('sha256',verifier_ref.get('file_sha256'))/'FACTS.json'
        immutable_json(sink,{'source_verifier_ref':verifier_ref,'facts':facts})
        rows.append(history_summary(facts));refs.append({'path':str(sink),'sha256':sha(sink)})
    receipt={'schema_id':'REGISTERED_CLOSED_TRAJECTORY_FACTS_CONSUMPTION_V1','consumer_request_sha256':request['request_sha256'],
        'source_research_index_ref':{'path':str(research_memory.index_path(a,request)),'sha256':sha(research_memory.index_path(a,request))},
        'facts_refs':refs,'closed_train_only':True,'current_round_results_included':False,'provider_calls_added':0}
    immutable_json(Path(root)/'REGISTERED_TRAJECTORY_FACTS_CONSUMPTION.json',receipt)
    return {'schema_id':'PRIOR_CLOSED_TRAIN_TRAJECTORY_FACTS_V1','rounds':rows,'interpretation':'Fallible research context; not current causal labels or training authority.'}

class WorkerDispatch:
    def __init__(self,native,source,target,record):self.native=native;self.source=source;self.target=target;self.record=record
    def __getattr__(self,name):return getattr(self.native,name)
    def run(self,argv,*args,**kwargs):
        if len(argv)>=5 and argv[1]=='-B' and argv[2]==self.source and argv[3]=='--request':
            self.record(argv[4]);argv=[*argv[:2],self.target,*argv[3:]]
        else:raise ValueError('REGISTERED_H44_WORKER_DISPATCH_CHANGED')
        return self.native.run(argv,*args,**kwargs)

@contextmanager
def installed(a,identity,root):
    import adapter,pre_stage
    from training_binding import strategy_source
    from exact_bindings import immutable_json
    activation=a['repair_activation'];intent=checked(activation['intent_ref'])
    if intent['start']['request_sha256']!=activation['request_sha256'] or intent['start']['round_id']!=activation['round_id']:raise ValueError('REPAIR_ACTIVATION_CHANGED')
    native_group,native_pre,native_h44=adapter.run_group_tail,adapter.run_pre,adapter.run_h44
    # This exact closure is the registered V191 worker bridge; no receipt traversal.
    transport=inspect.getclosurevars(native_h44).nonlocals['transport'];namespace=transport.__globals__
    source=str(Path(a['repair_sources']['recipe_contract']['root'])/'recipe_worker.py')
    def group(binding,values,core,*args,**kwargs):
        if not eligible(a,binding):return native_group(binding,values,core,*args,**kwargs)
        with group_scope(core):return native_group(binding,values,core,*args,**kwargs)
    def pre(binding,values,core,tail,universe,out):
        if not eligible(a,binding):return native_pre(binding,values,core,tail,universe,out)
        facts=prior_facts(a,values['request'],out,identity);native_sealed=pre_stage.sealed;native_prompt=strategy_source.extend_pre_prompt
        def sealed(c,schema,value,field):
            if schema=='STRONG_RESEARCHER_BLIND_PRE_INPUT_V3':value={**value,'prior_closed_round_trajectory_facts':facts}
            return native_sealed(c,schema,value,field)
        with patch.object(pre_stage,'sealed',sealed),patch.object(strategy_source,'extend_pre_prompt',lambda text:native_prompt(text)+PRE_GUIDANCE):
            return native_pre(binding,values,core,tail,universe,out)
    def h44(binding,capture,out,*,execute):
        if not eligible(a,binding):return native_h44(binding,capture,out,execute=execute)
        def record(request_path):
            immutable_json(Path(request_path).parent/'REGISTERED_TRAJECTORY_WORKER_BINDING.json',{
                'source_worker':source,'worker':str(Path(root)/'feedback_worker.py'),'authority_ref':{'path':str(Path(root)/'AUTHORITY.json'),'sha256':sha(Path(root)/'AUTHORITY.json')},
                'request_ref':{'path':request_path,'sha256':sha(request_path)},'round_id':binding['round_id']})
        proxy=WorkerDispatch(namespace['subprocess'],source,str(Path(root)/'feedback_worker.py'),record)
        with patch.dict(namespace,{'subprocess':proxy}):return native_h44(binding,capture,out,execute=execute)
    immutable_json(Path(a['owner_root'])/'runtime_extensions'/identity/'EXECUTABLE_DEPENDENCY_FEEDBACK_INSTALLED.json',{
        'activation':activation,'authority_ref':{'path':str(Path(root)/'AUTHORITY.json'),'sha256':sha(Path(root)/'AUTHORITY.json')},'provider_use_claimed':False})
    with patch.object(adapter,'run_group_tail',group),patch.object(adapter,'run_pre',pre),patch.object(adapter,'run_h44',h44):yield
