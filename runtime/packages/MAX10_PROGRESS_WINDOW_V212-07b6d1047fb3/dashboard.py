"""Terminal presentation only. Numbers and verdicts are supplied by receipts."""
import os,re,textwrap

COLORS={'ERROR':'41;97','RUN':'42;30','DONE':'42;30','REUSED':'46;30',
        'WAIT':'43;30','CHECK':'43;30','UNKNOWN':'43;30','STOP':'43;30','PENDING':'100;97','SKIP':'100;97'}

def clean(value):
    return ''.join(c if c>=' ' and c!='\x7f' else ' ' for c in str(value))

def use_color(mode,tty,environ=None):
    env=os.environ if environ is None else environ
    return mode=='always' or (mode=='auto' and tty and 'NO_COLOR' not in env and env.get('TERM')!='dumb')

def badge(state,color):
    label=clean(state).ljust(7)
    return '\x1b['+COLORS.get(state,COLORS['UNKNOWN'])+'m '+label+' \x1b[0m' if color else ' '+label+' '

def progress_bar(done,total,width=18):
    if done is None or total is None:return '['+'?'*width+']   -- '
    if total==0:return '['+'-'*width+']  n/a '
    if done<0 or done>total:return '['+'!'*width+'] INVALID'
    filled=int(width*done/total)
    return '['+'#'*filled+'-'*(width-filled)+'] '+f'{100*done/total:5.1f}%'.replace('.0%','%')

def stage_state(done,total,*,active=False,waiting=False,verified=False,failed=False,reused=False):
    if failed:return 'ERROR'
    if reused:return 'REUSED'
    if verified:return 'DONE'
    if active and total is not None and total>0 and done==total:return 'CHECK'
    if active:return 'WAIT' if waiting else 'RUN'
    return 'PENDING'

def overall_state(stage,alive,terminal=False):
    if terminal:return 'DONE'
    if stage=='STOPPED' or alive is False:return 'ERROR'
    if alive is None:return 'UNKNOWN'
    return 'RUN'

def row(name,done=None,total=None,*,state='PENDING',detail='',updated=None,unit=''):
    return dict(name=name,done=done,total=total,state=state,detail=detail,updated=updated,unit=unit)

def lifecycle_rows(life,active=''):
    t=life.get('training') or {};e=life.get('offoff') or {};rows=[]
    queue=(life.get('queue') or {}).get('stdout','').splitlines()
    queued=bool(queue) and all('|PENDING|' in line or '|CONFIGURING|' in line for line in queue)
    steps=t.get('published_steps');limit=t.get('planned_steps')
    completed=t.get('state')=='TRAINING_RESULT_PUBLISHED'
    rows.append(row('Training',steps,limit,state=stage_state(steps,limit,active=active in ('TRAINING','TRAIN'),waiting=queued,verified=completed),
        unit='steps',detail='loss='+str(t['loss']) if t.get('loss') is not None else t.get('state','No training request yet')))
    total=e.get('total_pairs');is_eval=active in ('TRAIN_SELECT','TRAIN_SELECT_OFFOFF','OFFOFF')
    for label in ('parent','candidate'):
        done=e.get('published_'+label,e.get(label) if e.get('cutover') else None)
        detail='published episodes; final audit pending'
        if label=='parent' and e.get('reused_parent'):detail+='; reused='+str(e['reused_parent'])
        if e.get('outcome'):detail='Outcome: '+e['outcome']
        rows.append(row('Eval '+label,done,total,state=stage_state(done,total,active=is_eval,waiting=queued,verified=bool(e.get('outcome'))),unit='episodes',detail=detail))
    rows.append(row('Acceptance',int(bool(e.get('outcome'))),1,state='DONE' if e.get('outcome') else 'WAIT' if is_eval else 'PENDING',
        detail=e.get('outcome','Memory OFF / Harness OFF; receipt-based decision')))
    q=life.get('queue')
    if q is not None:
        for r in rows:
            if r['state']=='RUN' and (r['name']=='Training' or r['name'].startswith('Eval ')):
                if q.get('returncode'):r['state']='UNKNOWN';r['detail']+='; queue query unavailable'
                elif not q.get('stdout','').strip():r['state']='WAIT';r['detail']+='; no active registered job, waiting for receipt'
    return rows

def render(s,color=False,width=110,details=False):
    width=max(60,width);lines=[]
    def plain(text,indent=''):
        lines.extend(textwrap.wrap(clean(text),width=width,initial_indent=indent,subsequent_indent=indent) or [''])
    lines.append('='*width)
    header=clean(s.get('title','PCHSI'))+' | '+clean(s.get('phase',''))
    plain(header);lines.append(badge(s.get('state','UNKNOWN'),color)+' '+clean(s.get('resident','')))
    plain('Round: '+str(s.get('round_id','pending')))
    if s.get('scope'):plain(s['scope'])
    plain('Refreshed: '+str(s.get('refreshed','?'))+' | Stage updated: '+str(s.get('updated','?')))
    lines.append('-'*width)
    for r in s.get('rows',[]):
        done='?' if r['done'] is None else str(r['done']);total='?' if r['total'] is None else str(r['total'])
        bar=progress_bar(r['done'],r['total'],width=18 if width>=80 else 10)
        label=clean(r['name'])[:17].ljust(17)
        line=label+' '+badge(r['state'],color)+' '+bar+' '+done+'/'+total
        if r.get('unit'):line+=' '+clean(r['unit'])
        plain_length=len(re.sub(r'\x1b\[[0-9;]*m','',line))
        if not details and r.get('detail') and width-plain_length>12:
            extra=clean(r['detail']);space=width-plain_length-3
            line+=' | '+(extra if len(extra)<=space else extra[:max(0,space-3)]+'...')
        lines.append(line)
        detail=r.get('detail','')
        if r.get('unit'):detail=r['unit']+' | '+detail
        if r.get('updated'):detail+=' | updated '+str(r['updated'])
        if detail and details:plain(detail,'  ')
    lines.append('-'*width)
    for note in s.get('notes',[]):plain(note)
    if s.get('jobs'):plain('Jobs: '+' | '.join(s['jobs']))
    if s.get('evidence') and details:plain('Evidence: '+str(s['evidence']))
    plain('RUN/DONE=green | WAIT/CHECK/UNKNOWN=yellow | ERROR=red | REUSED=cyan')
    plain('Published work != acceptance. --details: full evidence. Ctrl-C closes this view only.')
    lines.append('='*width)
    return '\n'.join(lines)
