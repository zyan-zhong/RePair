"""Read only registered status, typed indices and finite schedule populations."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,socket,sys
from dashboard import row,stage_state,overall_state,lifecycle_rows

def read(path):return json.loads(Path(path).read_bytes())
def optional(path):return read(path) if Path(path).is_file() else {}
def checked(ref):
    raw=Path(ref['path']).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ref.get('sha256',ref.get('file_sha256')):raise ValueError('REGISTERED_SHA_CHANGED:'+str(ref['path']))
    return json.loads(raw)

def active_stage(stage):
    if stage.startswith('L-'):return 'Analyzer L'
    if stage.startswith('G-'):return 'Analyzer G'
    if stage in ('C','P','X'):return 'Analyzer '+stage
    if stage.startswith('R-PRE'):return 'PRE decision'
    if stage.startswith('R-POST'):return 'POST'
    return stage

def current_progress(value,rid):return value if value.get('round_id')==rid else {}

def choose_scope(mode,index,formal,validation_terminal):
    if mode!='auto':return mode
    # A new explicitly registered formal invocation takes over after validation closure.
    if not index:return 'formal'
    changed_attempt=index.get('source_attempt_root') and formal.get('attempt_root')!=index['source_attempt_root']
    if validation_terminal and (changed_attempt or formal.get('stage') not in ('COMPLETED','STOPPED','NOT_STARTED',None)):return 'formal'
    return 'validation'

def process_alive(status,package=None):
    if status.get('host')!=socket.gethostname():return None
    try:argv=[x.decode() for x in (Path('/proc')/str(status['pid'])/'cmdline').read_bytes().split(b'\0') if x]
    except (OSError,KeyError):return False
    if package:return bool(argv) and any(str(x).startswith(str(package)+'/') and str(x).endswith('.py') for x in argv)
    return bool(argv)

class Collector:
    def __init__(self,config):
        self.config=config;self.base=Path(config['base_root'])
        raw=(self.base/'PACKAGE_FILES.sha256').read_bytes()
        if hashlib.sha256(raw).hexdigest()!=config['base_manifest_sha256']:raise ValueError('MONITOR_PREDECESSOR_MANIFEST_CHANGED')
        for line in raw.decode().splitlines():
            sha,name=line.split(maxsplit=1);p=self.base/name
            if not p.resolve().is_relative_to(self.base.resolve()) or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:raise ValueError('MONITOR_PREDECESSOR_SOURCE_CHANGED:'+name)
        sys.path.insert(0,str(self.base))
        import cognitive_status,lifecycle_status,execution_index,post_recovery,select_index
        self.c=cognitive_status;self.life=lifecycle_status
        self.resolve_causal=lambda p:post_recovery.resolve(execution_index.resolve_run(p))
        self.resolve_select=select_index.resolve;self.cfg=read(self.base/'AUTHORITY.json')
        self.cfg['owner_root']=config['formal_owner_root']

    def collect(self,mode='auto'):
        owner=Path(self.config['formal_owner_root']);formal=optional(owner/'LIVE_STATUS.json')
        index=optional(self.config['active_validation_index'])
        index_before=hashlib.sha256(Path(self.config['active_validation_index']).read_bytes()).hexdigest() if index else None
        if index:
            package=Path(index['package_root']);manifest_raw=(package/'PACKAGE_FILES.sha256').read_bytes()
            if hashlib.sha256(manifest_raw).hexdigest()!=index['package_manifest_sha256']:raise ValueError('VALIDATION_MANIFEST_CHANGED')
            members={n:h for h,n in (l.split(maxsplit=1) for l in manifest_raw.decode().splitlines())}
            index_authority=checked({'path':str(package/'AUTHORITY.json'),'sha256':members['AUTHORITY.json']})
            original=checked(index_authority['source_binding_ref'])
            index={**index,'source_attempt_root':str(Path(original['output_root']).parent)}
        term=optional(Path(index['experiment_root'])/'VALIDATION_TERMINAL.json') if index else {}
        scope=choose_scope(mode,index,formal,bool(term));validation=scope=='validation'
        s={'title':'PCHSI | '+('Single validation' if validation else 'Formal Max-10'),'rows':[],'notes':[],
           'refreshed':datetime.now(timezone.utc).isoformat(timespec='seconds'),'scope':scope}
        def guard(name,fn):
            try:return fn()
            except (OSError,ValueError,KeyError,TypeError) as exc:
                s['notes'].append('Monitor '+name+': '+type(exc).__name__+': '+str(exc));return None
        if validation:
            package=Path(index['package_root']);raw=(package/'PACKAGE_FILES.sha256').read_bytes()
            if hashlib.sha256(raw).hexdigest()!=index['package_manifest_sha256']:raise ValueError('VALIDATION_MANIFEST_CHANGED')
            manifest={n:h for h,n in (l.split(maxsplit=1) for l in raw.decode().splitlines())}
            a=checked({'path':str(package/'AUTHORITY.json'),'sha256':manifest['AUTHORITY.json']})
            root=Path(index['experiment_root'])
            if str(root)!=a['experiment_root']:raise ValueError('VALIDATION_ROOT_IDENTITY')
            status=optional(root/'VALIDATION_PROGRESS.json');binding=checked(a['source_binding_ref'])
            rid=binding['round_id'];source=Path(binding['output_root']);analyzer=root/'analyzer'
            alive=process_alive(status,package);local=checked(a['validation_authority']['source_files']['execution'])
            census=checked(a['validation_authority']['source_files']['census'])
            tail=checked(a['validation_authority']['source_files']['tail'])
            ids=[Path(r['path']).parent.name for r in census['group_refs']]
            calls=guard('Analyzer',lambda:self.c.closed_group_calls(source/'group',rid,binding['parent_policy_id'],ids))
            counts=self.c.summarize(ids,calls) if calls is not None else None
            rollout=guard('Rollout',lambda:checked(binding['refs']['global_terminal']))
            if rollout:rollout={'completed':rollout['scheduled_count'],'scheduled':rollout['scheduled_count'],
                'success':rollout['success_count'],'failure':rollout['failure_count'],'invalid':rollout['protocol_invalid_count']+rollout['infrastructure_invalid_count']}
            sample={'owner':{'round_id':rid,'attempt_root':str(root)}}
            guard('Training/Evaluation',lambda:self.life.extend(sample,self.cfg,reader=lambda _:sample['owner']))
            life=sample.get('lifecycle',{});chain={};local_live={}
            s['scope']='One reused-input validation | formal rounds: '+str(formal.get('valid_rounds','?'))+'/'+str(formal.get('max_rounds','?'))+' | no new formal round'
            stop=optional(root/'VALIDATION_STOP.json');result=optional(root/'VALIDATION_RESULT.json')
        else:
            snap=self.c.snapshot(self.cfg);status=snap['owner'];rid=status.get('round_id');root=Path(status.get('attempt_root',owner));analyzer=root/'analyzer';source=analyzer
            binding=optional(root/'CURRENT_ANALYZER_BINDING.json')
            if binding:analyzer=source=Path(binding['output_root'])
            alive=snap['process_alive'];local=snap.get('local') or {};counts=snap.get('counts');chain=snap.get('chain') or {}
            guard('Lifecycle',lambda:self.life.extend(snap,self.cfg));life=snap.get('lifecycle',{});rollout=life.get('rollout')
            local_live={}
            for p in [status.get('cognitive_progress_path'),str(source/'local/strong_local_runtime/COGNITIVE_PROGRESS.json')]:
                if p:
                    candidate=current_progress(optional(p),rid)
                    if candidate:local_live=candidate;break
            tail=optional(source/'group/V1232U_STRONG_ANALYZER_TAIL_TERMINAL_V1.json')
            if tail and tail.get('round_id')!=rid:raise ValueError('ANALYZER_TAIL_ROUND_MISMATCH')
            term=optional(root/'RESULT.json') if status.get('stage')=='COMPLETED' else {}
            result=term;stop={'message':status.get('stop_reason') or status.get('error')} if status.get('stage')=='STOPPED' else {}
            s['scope']='Valid rounds: '+str(status.get('valid_rounds','?'))+'/'+str(status.get('max_rounds','?'))+' | invalid attempts: '+str(status.get('invalid_attempts','?'))
        phase=status.get('stage','NOT_STARTED')
        s.update(round_id=rid,phase=phase,updated=status.get('updated_utc'),evidence=str(root),
            state=overall_state(phase,alive,terminal=bool(term) or phase=='COMPLETED'),
            resident=str(status.get('host','?'))+' '+str(status.get('pid','?'))+' | '+('alive' if alive is True else 'not running' if alive is False else 'host check unavailable'))
        if stop.get('message'):s['notes'].append('STOP: '+str(stop['message']));s['state']='ERROR'
        if alive is False and not term and phase!='COMPLETED':s['notes'].append('Resident is absent; last recorded phase is not proof of active execution.')
        if result.get('outcome'):s['notes'].append('Outcome: '+result['outcome'])
        current=active_stage(chain.get('stage_id',''));waiting=chain.get('state')=='WAITING_PROVIDER'
        if rollout:
            s['rows'].append(row('Rollout',rollout['completed'],rollout['scheduled'],unit='episodes',
                state=stage_state(rollout['completed'],rollout['scheduled'],active='ROLLOUT' in phase,reused=validation,verified=rollout['completed']==rollout['scheduled']),
                detail='success {success} | failure {failure} | invalid {invalid}'.format(**rollout)))
        else:s['rows'].append(row('Rollout',detail='Schedule not yet registered'))
        rows=local.get('rows',[]);done=len(rows) if local else local_live.get('completed_local_calls')
        total=len(rows) if local else local_live.get('registered_local_calls')
        accepted=sum(r['status']=='ACCEPTED' for r in rows) if local else local_live.get('accepted_local_calls','?')
        s['rows'].append(row('Analyzer L',done,total,state=stage_state(done,total,active=current=='Analyzer L' or bool(local_live.get('current_call')),waiting=waiting,reused=validation,verified=bool(local)),
            detail='accepted '+str(accepted)+' | closed slots include rejected/quarantined',updated=local_live.get('updated_utc'),unit='slots'))
        if counts:
            pairs=counts['complete_pairs'];s['rows'].append(row('Analyzer G',counts['groups_closed'],counts['groups_total'],unit='groups',
                state=stage_state(counts['groups_closed'],counts['groups_total'],active=current=='Analyzer G',waiting=waiting,reused=validation,verified=counts['groups_closed']==counts['groups_total']),detail='complete pairs '+str(pairs)+' | quarantined '+str(counts['quarantined_groups'])))
            for name in ['C','X']:
                v=counts[name];s['rows'].append(row('Analyzer '+name,v['terminal'],v['total'],unit='calls',
                    state=stage_state(v['terminal'],v['total'],active=current=='Analyzer '+name,waiting=waiting,reused=validation,verified=bool(tail)),
                    detail='accepted '+str(v['accepted'])+' | ambiguous '+str(v['ambiguous'])+' | other '+str(v['other'])))
        else:
            s['rows'].extend(row('Analyzer '+x,detail='Total follows registered upstream closure') for x in ['G','C','X'])
        p_done=tail.get('deterministic_p_materialized') is True
        s['rows'].insert(4,row('Analyzer P',int(p_done),1,state='REUSED' if validation else 'DONE' if p_done else 'PENDING',detail='deterministic aggregation receipt'))
        pre=analyzer/'pre';review=optional(pre/'source_reviews/REVIEW_PROGRESS.json');accepted_pre=optional(pre/'ACCEPTED_PRE_REF.json')
        if review:
            n=review['completed_calls'];total=review.get('planned_map_calls');closed=review.get('state')=='ALL_SOURCE_REVIEWS_COMPLETE'
            s['rows'].append(row('PRE sources',n,total,state=stage_state(n,total,active=phase=='STRATEGY_PRE_REVIEW',waiting=review.get('state')=='WAITING_PROVIDER',verified=closed),unit='reviews',detail=review.get('phase',review['state']),updated=review.get('updated_utc')))
        else:s['rows'].append(row('PRE sources',detail='No separate source-review population registered'))
        s['rows'].append(row('PRE decision',int(bool(accepted_pre)),1,state=stage_state(int(bool(accepted_pre)),1,active=current=='PRE decision' or phase=='STRATEGY_PRE_REVIEW',waiting=True,verified=bool(accepted_pre)),unit='decisions',detail='selected states '+str(accepted_pre.get('selected_state_count','pending'))))
        def causal():
            run=self.resolve_causal(analyzer/'h44/run');plan=optional(run/'EXECUTION_PLAN.json')
            if not plan:return None
            if plan['round_id']!=rid:raise ValueError('CAUSAL_ROUND_MISMATCH')
            branches=plan['handoff']['branch_plan'];closed=[]
            for b in branches:
                v=optional(run/'branches'/b['branch_key_sha256']/'BRANCH_TERMINAL.json')
                if v:closed.append(v)
            valid=sum(x.get('scientific_outcome_produced') is True and x.get('evidence_complete') is True for x in closed)
            post_terminal=optional(run/'ROUND_EXECUTION_TERMINAL.json').get('post_terminal',{})
            s['rows'].append(row('F0/F1',len(closed),len(branches),state=stage_state(len(closed),len(branches),active=phase=='STRATEGY_F0_F1_CAUSAL_VERIFICATION',verified=len(closed)==len(branches),failed=valid<len(closed)),unit='branches',detail='scientific '+str(valid)+' | invalid '+str(len(closed)-valid)))
            post_ok=post_terminal.get('training_recommendation') in ('TRAIN','NO_TRAIN')
            s['rows'].append(row('POST',int(post_ok),1,state=stage_state(int(post_ok),1,active=current=='POST' or len(closed)==len(branches) and not post_ok and phase=='STRATEGY_F0_F1_CAUSAL_VERIFICATION',waiting=True,verified=post_ok),unit='decisions',detail=post_terminal.get('training_recommendation','Awaiting registered POST receipt')))
            if 'verified_benefit_count' in post_terminal:s['notes'].append('Stable Benefit: '+str(post_terminal['verified_benefit_count']))
            return run
        run=guard('Causal/POST',causal)
        if run is None:s['rows'].extend([row('F0/F1',detail='Branch population not yet registered'),row('POST',0,1)])
        s['rows'].extend(lifecycle_rows(life,phase))
        def eval_schedule():
            parallel=optional(self.resolve_select(root/'offoff')/'parallel/CURRENT_NATIVE_OFFOFF_PARALLEL_BINDING.json')
            if not parallel:return
            effective_ref=parallel['binding_ref'];correction=None
            if validation and index.get('evaluation_recovery_ref'):
                recovery_ref=index['evaluation_recovery_ref']
                if recovery_ref['path']!=str(package/'RECOVERY_AUTHORITY.json') or recovery_ref['sha256']!=manifest.get('RECOVERY_AUTHORITY.json'):raise ValueError('EVALUATION_RECOVERY_AUTHORITY_NOT_REGISTERED')
                recovery=checked(recovery_ref)
                if checked(recovery['source_parallel_ref'])!=parallel:raise ValueError('EVALUATION_RECOVERY_SOURCE_CHANGED')
                ap=Path(recovery['recovery_root'])/'REGISTERED_CURRENT_SELECT_CUTOVER.json'
                correction=optional(ap)
                if correction:
                    effective_ref=correction['binding_ref']
                    audit=optional(Path(recovery['recovery_root'])/'FULL_CELL_AUDIT.json')
                    progress=optional(Path(recovery['recovery_root'])/'GOAL_RECOVERY_PROGRESS.json')
                    if audit and checked(audit['amendment_ref'])!=correction:raise ValueError('EVALUATION_RECOVERY_GRID_AUTHORITY')
                    total=checked(effective_ref)['paired_cell_count']
                    if audit and audit['audited_cells']==2*total:
                        for r in s['rows']:
                            if r['name'] in ('Eval parent','Eval candidate'):
                                r.update(done=total,total=total,state='REUSED',detail='complete selected-seed episodes audited; no model rerun')
                    if progress:
                        s['rows'].append(row('Goal metric',progress['completed'],progress['total'],unit='captures',
                            state=stage_state(progress['completed'],progress['total'],active=phase=='GOAL_METRIC_RECOVERY',verified=progress['completed']==progress['total']),
                            detail='audited action replay | policy calls 0'))
                    terminal=optional(Path(effective_ref['path']).parent/'CURRENT_NATIVE_OFFOFF_TERMINAL.json')
                    for r in s['rows']:
                        if r['name']=='Acceptance':
                            r.update(done=int(bool(terminal)),total=1,state='DONE' if terminal else 'RUN' if alive and phase=='GOAL_METRIC_RECOVERY' else 'WAIT',detail=terminal.get('outcome','Restoring registered goal tie metric'))
                    s['notes'].append('Extra seeds cancelled; selected-seed full grid reused; no new model episodes.')
            bound=checked(effective_ref)
            if bound['round_id']!=rid:raise ValueError('EVALUATION_ROUND_MISMATCH')
            schedule=checked(bound['output_refs']['PARENT_SCHEDULE.json'])
            s['evaluation_schedule']={'binding_ref':effective_ref,'paired_cell_count':bound['paired_cell_count'],
                'task_count':len({x['task_id'] for x in schedule['cells']}),'seeds':schedule['replicate_seeds']}
            e=s['evaluation_schedule'];s['notes'].append('Eval schedule: '+str(e['task_count'])+' tasks x '+str(len(e['seeds']))+' paired seeds '+str(e['seeds']))
        guard('Evaluation schedule',eval_schedule)
        for stage,label in [('MEMORY_CLOSE','Memory closure'),('EXPORT','Paper export')]:
            receipt=optional(root/'stages'/stage/'RESULT.json') if validation else {}
            ok=bool(receipt) or bool(term)
            s['rows'].append(row(label,int(ok),1,state='DONE' if ok else 'RUN' if phase=='MEMORY_CLOSURE' else 'PENDING',unit='receipts'))
        for message in life.get('stops',[]):s['notes'].append('Stage STOP: '+message);s['state']='ERROR'
        q=life.get('queue') or {};s['jobs']=q.get('stdout','').strip().splitlines()
        if q.get('returncode'):s['notes'].append('Queue query unavailable; receipt counters remain visible.')
        elif not s['jobs']:s['jobs']=['no active registered job; outcomes remain receipt-based']
        elif s['state']=='RUN' and all('|PENDING|' in x or '|CONFIGURING|' in x for x in s['jobs']):s['state']='WAIT'
        if chain and phase not in ('COMPLETED','STOPPED'):
            s['notes'].append('Cognitive: '+str(chain.get('stage_id'))+' | '+str(chain.get('state'))+' | '+str(chain.get('updated_utc')))
        waiting_event=review if review.get('state')=='WAITING_PROVIDER' and phase=='STRATEGY_PRE_REVIEW' else chain if waiting else {}
        if waiting_event.get('updated_utc') and s['state']!='ERROR':
            age=max(0,int((datetime.now(timezone.utc)-datetime.fromisoformat(waiting_event['updated_utc'])).total_seconds()))
            s['notes'].append('Provider wait: '+str(age)+' seconds since registered request event')
        parallel=current_progress(optional(owner/'ANALYZER_PARALLEL_PROGRESS.json'),rid) if not validation else {}
        if parallel and parallel.get('coordinator_pid')==status.get('pid'):s['notes'].append('Analyzer source concurrency: '+json.dumps(parallel,ensure_ascii=True))
        # Finished rows stay finished even when the resident stops later; unfinished current rows expose the stop.
        if s['state']=='ERROR':
            targets={'TRAIN_SELECT':['Eval parent','Eval candidate','Acceptance'],'TRAIN_SELECT_OFFOFF':['Eval parent','Eval candidate','Acceptance'],'TRAINING':['Training'],'STRATEGY_PRE_REVIEW':['PRE sources','PRE decision']}.get(phase,[current])
            for r in s['rows']:
                if r['name'] in targets and r['state'] not in ('DONE','REUSED'):r['state']='ERROR'
        if validation:
            if hashlib.sha256(Path(self.config['active_validation_index']).read_bytes()).hexdigest()!=index_before:raise ValueError('ACTIVE_VALIDATION_CHANGED_RETRY_NEXT_REFRESH')
        else:
            now=optional(owner/'LIVE_STATUS.json')
            if any(now.get(k)!=status.get(k) for k in ['round_id','attempt_root','pid']):raise ValueError('ROUND_CHANGED_RETRY_NEXT_REFRESH')
        return s
