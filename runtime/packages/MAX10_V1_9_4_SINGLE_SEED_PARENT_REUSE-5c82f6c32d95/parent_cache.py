"""Flat, authority-bound TRAIN_SELECT reuse. Original episodes stay in their round."""
from pathlib import Path
import json

def equivalent(source,current):
    old=dict(source);new=dict(current);seeds=new.pop('seeds');registered=old.pop('seeds')
    if len(seeds)!=1 or seeds!=registered[:1] or old!=new:
        raise ValueError('PARENT_SELECT_CACHE_SEMANTIC_CONTRACT_MISMATCH')

def cache_choice(outcome,inherited,terminal_ref,arm):
    if outcome=='PROMOTED' or (outcome=='ROLLED_BACK' and inherited is None):
        return {'source_terminal_ref':terminal_ref,'source_arm':arm}
    if outcome in ('ROLLED_BACK','NO_TRAINING_UPDATE') and inherited is not None:return inherited
    raise ValueError('PARENT_SELECT_CACHE_CLOSED_SOURCE_MISSING')

def ref(path):
    import hashlib
    path=Path(path);return {'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

def contract(c,arm):
    """Exclude only administrative identities and the other registered model."""
    protocol=c['protocol'];policy=c[arm];condition,runtime,*_=c['bundles'][arm]
    runtime=runtime.to_dict();condition=condition.to_dict();server=c['server'].to_dict()
    for key in ('manifest_id','server_runtime_manifest_sha256'):runtime.pop(key)
    condition.pop('policy_runtime_manifest_sha256')
    for key in ('manifest_id','static_lora_registry','max_cpu_loras'):server.pop(key)
    return {'seeds':protocol['replicate_seeds'],
        'weights':{k:policy[k] for k in ('artifact_sha256','artifact_manifest','artifact_root','kind','policy_id','base_model_repository','base_model_revision')},
        'condition':condition,'runtime':runtime,'server':server,
        'protocol':{k:protocol[k] for k in ('access_class','benchmark_feedback_authorized','memory_state','harness_state','episode_budget','task_ids','task_access_ref','policy_request_schema_sha256','raw_protocol_sha256','evaluator_commit','runtime_core_commit','design_merge_commit')},
        'infra':{k:c['infra'][k] for k in ('environment_runtime_ref','gamefile_identity_ref','tokenizer_identity_ref')}}

def index_path(driver,request):
    return driver._binding_path(request).parent/'parent_select_cache'/request['request_sha256']/'AUTHORITY.json'

def next_cache(driver,start,result,next_request):
    from continuity_binding.api import read_ref,write_once
    old=index_path(driver,start);inherited=read_ref(ref(old))['origin'] if old.exists() else None
    # Original Driver.build_next has already validated the closed native result.
    terminal_ref=result.get('terminal_ref')
    if terminal_ref:terminal_ref={'path':terminal_ref['path'],'sha256':terminal_ref.get('sha256',terminal_ref.get('file_sha256'))}
    origin=cache_choice(result['outcome'],inherited,terminal_ref,'candidate' if result['outcome']=='PROMOTED' else 'parent')
    terminal=read_ref(origin['source_terminal_ref'])
    if terminal['outcome'] not in ('PROMOTED','ROLLED_BACK'):raise ValueError('CACHE_SOURCE_NOT_CLOSED_SELECT')
    binding=read_ref(terminal['binding_ref']);policy=read_ref(binding['input_refs'][origin['source_arm']+'_ref'])
    if (policy['policy_id'],policy['artifact_sha256'])!=(next_request['parent_policy_id'],next_request['parent_policy_artifact_sha256']):raise ValueError('CACHE_NEXT_PARENT_LINEAGE')
    return write_once(index_path(driver,next_request),{'schema_id':'REGISTERED_RETAINED_PARENT_SELECT_CACHE_V1',
        'request_sha256':next_request['request_sha256'],'parent_policy_id':policy['policy_id'],'parent_policy_artifact_sha256':policy['artifact_sha256'],
        'origin':origin,'closed_round_request_sha256':start['request_sha256'],'closed_round_outcome':result['outcome'],
        'source_binding_ref':terminal['binding_ref'],'source_summary_ref':terminal['summary_ref'],
        'restricted_evidence_only':True,'fresh_observation_claimed':False})

class Cache:
    def __init__(self,binding_ref,context):
        from continuity_binding.api import read_ref
        from offoff_binding.native import Native
        from offoff_binding.materialize import prepare
        from pchsi.evaluation.select_result_audit import derive_expected_select_cells_from_master_schedules
        self.read=read_ref;self.current=context;self.binding_ref=binding_ref
        self.authority_ref=context['protocol']['parent_select_cache_ref'];a=read_ref(self.authority_ref)
        if a['schema_id']!='REGISTERED_RETAINED_PARENT_SELECT_CACHE_V1' or a['request_sha256']!=context['start']['request_sha256']:raise ValueError('CACHE_REQUEST_AUTHORITY')
        if (a['parent_policy_id'],a['parent_policy_artifact_sha256'])!=(context['parent']['policy_id'],context['parent']['artifact_sha256']):raise ValueError('CACHE_PARENT_AUTHORITY')
        self.origin=a['origin'];self.arm=self.origin['source_arm'];terminal=read_ref(self.origin['source_terminal_ref'])
        if self.arm not in ('parent','candidate') or terminal['outcome']!=('PROMOTED' if self.arm=='candidate' else 'ROLLED_BACK'):raise ValueError('CACHE_SOURCE_MUST_BE_RETAINED_ARM')
        if a['source_binding_ref']!=terminal['binding_ref'] or a['source_summary_ref']!=terminal['summary_ref']:raise ValueError('CACHE_SOURCE_TERMINAL_AUTHORITY')
        self.summary=read_ref(terminal['summary_ref']);self.binding=read_ref(terminal['binding_ref'])
        self.native=Native.load(self.binding['native_repo_root'],self.binding['source_refs'])
        self.source=prepare(native=self.native,**self.binding['input_refs'])
        equivalent(contract(self.source,self.arm),contract(context,'parent'))
        self.source_audit=read_ref(self.summary['identity_audit_ref'])
        if self.source_audit['binding_ref']!=terminal['binding_ref']:raise ValueError('CACHE_SOURCE_AUDIT_BINDING')
        count=self.binding['paired_cell_count'];audit_rows=self.source_audit['rows']
        if len(self.source_audit['execution_roots_by_ordinal'])!=count or len(audit_rows)!=2*count or {(r['label'],r['ordinal']) for r in audit_rows}!={(arm,n) for arm in ('parent','candidate') for n in range(count)}:raise ValueError('CACHE_SOURCE_CLOSED_COMPLETE_GRID_REQUIRED')
        if self.source_audit['schema_id']=='CURRENT_OFFOFF_COVERAGE_CUTOVER_AUDIT_V1':
            # One explicit physical source binding, not a recursive receipt graph.
            physical=read_ref(self.source_audit['source_binding_ref'])
            self.native=Native.load(physical['native_repo_root'],physical['source_refs'])
            self.source=prepare(native=self.native,**physical['input_refs'])
            equivalent(contract(self.source,self.arm),contract(context,'parent'))
            source_roots=['']*physical['paired_cell_count']
            for row in audit_rows:source_roots[row['source_ordinal']]=self.source_audit['execution_roots_by_ordinal'][row['ordinal']]
            self.source_audit={**self.source_audit,'execution_roots_by_ordinal':source_roots}
        self.live,self.audit,_,_,_,self.loader=self.native.runners();self.audit_native=self.audit.load_native(self.native.root)
        cells=self.source['bundles'][self.arm][2].cells
        self.ordinal={c.condition_cell_id:i for i,c in enumerate(cells)}
        expected=derive_expected_select_cells_from_master_schedules(schedules={k:b[2] for k,b in self.source['bundles'].items()},authorized_schedule_sha256={k:b[5] for k,b in self.source['bundles'].items()})
        self.expected={c.condition_cell_id:c for c in expected if c.schedule_name==self.arm}
        self.closed_rows={(r['label'],r.get('source_ordinal',r['ordinal'])):r for r in self.source_audit['rows']}
        self.receipts={};self.validated={}
        for cell in context['bundles']['parent'][2].cells:
            if cell.condition_cell_id not in self.ordinal:raise ValueError('CACHE_COMPLETE_FIXED_GRID_REQUIRED')

    def audit_cell(self,ordinal,*,allow_replay):
        from offoff_binding.execute import _audit_one
        from parent_replay import metric_for_source
        cell=self.current['bundles']['parent'][2].cells[ordinal];source_ordinal=self.ordinal[cell.condition_cell_id]
        root=Path(self.source_audit['execution_roots_by_ordinal'][source_ordinal])/self.arm
        if str(root) not in self.receipts:
            rows=self.live.load_receipts(root/'cell_receipts.jsonl');ids=[r['condition_cell_id'] for r in rows]
            if len(ids)!=len(set(ids)):raise ValueError('CACHE_DUPLICATE_SOURCE_CELL')
            self.receipts[str(root)]=dict(zip(ids,rows))
        row=self.receipts[str(root)][cell.condition_cell_id]
        closed=self.closed_rows[(self.arm,source_ordinal)]
        if 'parent_reuse' in closed:raise ValueError('CACHE_ORIGIN_MUST_BE_PHYSICAL_NO_RECURSIVE_REUSE')
        for k in ('execution_attempt_id','attempt_bundle_sha256'):
            if row[k]!=closed[k]:raise ValueError('CACHE_CLOSED_CELL_CHANGED')
        loaded=self.loader.load_attempt_directory_v1(root/'evaluator_run/attempts'/row['execution_attempt_id'])
        metadata=_audit_one(audit=self.audit,native_audit=self.audit_native,loaded=loaded,row=row,expected=self.expected[cell.condition_cell_id],
            bundle=self.source['bundles'][self.arm],protocol=self.source['protocol'],infra=self.source['infra'],access=self.source['access'],root=root/'evaluator_run')
        metric=metric_for_source(cache=self,root=root,loaded=loaded,row=row,allow_replay=allow_replay)
        return row,{**metadata,'parent_reuse':{'authority_ref':self.authority_ref,'source_terminal_ref':self.origin['source_terminal_ref'],
            'source_arm':self.arm,'source_ordinal':source_ordinal,'original_episode_root':str(root/'evaluator_run/attempts'/row['execution_attempt_id']),
            'metric_ref':metric,'fresh_model_episode':False}}

    def record_path(self,root,ordinal):
        cell=self.current['bundles']['parent'][2].cells[ordinal]
        return Path(root)/'parent/reused_cells'/cell.condition_cell_id/'REUSE.json'

    def adopt(self,ordinal,root):
        from continuity_binding.api import write_once
        row,metadata=self.audit_cell(ordinal,allow_replay=True)
        value={'schema_id':'TRAIN_SELECT_REUSED_PARENT_CELL_V1','binding_ref':self.binding_ref,'ordinal':ordinal,'original_receipt':row,'metadata':metadata}
        write_once(self.record_path(root,ordinal),value)
        return row,metadata

    def audit_adopted(self,ordinal,root):
        value=self.read(ref(self.record_path(root,ordinal)))
        row,metadata=self.audit_cell(ordinal,allow_replay=False)
        if value!={'schema_id':'TRAIN_SELECT_REUSED_PARENT_CELL_V1','binding_ref':self.binding_ref,'ordinal':ordinal,'original_receipt':row,'metadata':metadata}:raise ValueError('CACHE_ADOPTED_CELL_CHANGED')
        return row,metadata

    def rows(self,root):
        values=[]
        for n in range(len(self.current['bundles']['parent'][2].cells)):
            path=self.record_path(root,n)
            if path.exists():
                value=self.read(ref(path))
                if value['binding_ref']!=self.binding_ref or value['ordinal']!=n:raise ValueError('CACHE_REUSE_GRID_IDENTITY')
                values.append(value['original_receipt'])
        return values

def cache_for(binding_ref,context):
    return Cache(binding_ref,context) if 'parent_select_cache_ref' in context['protocol'] else None

def receipts(cache,live,path):
    path=Path(path)
    if cache is not None and path.parent.name=='parent':return cache.rows(path.parent.parent)
    return live.load_receipts(path)
