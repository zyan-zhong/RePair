"""Same unified window, with registered pending/active concurrency."""
from pathlib import Path
import argparse,json,subprocess,time,os
ROOT=Path(__file__).resolve().parent

def render_parallel(a,live,registration,status,parallel):
    state=status.get('state','NOT_REGISTERED')
    if state!='ACTIVATED':
        return ['Analyzer concurrency: 1 | 2 sources pending from round '+str(a['parallel_policy']['activation_round_index'])+' | '+state]
    if parallel.get('round_id')!=live.get('round_id') or parallel.get('coordinator_pid')!=live.get('pid'):
        return ['Analyzer concurrency: 2 configured | awaiting this round phase']
    calls=parallel['active_calls'];now=time.time()
    lines=['Analyzer concurrency: '+str(len(calls))+' / '+str(parallel['max_concurrent_sources'])+' sources active | '+parallel['phase'],
        'Sources closed: '+str(parallel['closed_sources'])+' / '+str(parallel['total_sources'])]
    for call in calls:
        lines.append('  '+str(call.get('stage_id',parallel['phase']))+' | '+call['source_key'][:12]+' | '+call['state']+
            ' | '+str(max(0,int(now-call.get('event_unix',call['started_unix']))))+' s')
    if parallel.get('admission_closed'):lines.append('Admission closed; draining already sent requests')
    return lines

def main():
    p=argparse.ArgumentParser();p.add_argument('--watch',action='store_true');p.add_argument('--json',action='store_true');args=p.parse_args()
    a=json.loads((ROOT/'AUTHORITY.json').read_bytes());owner=Path(a['owner_root'])
    def read(path):return json.loads(path.read_bytes()) if path.is_file() else {}
    while True:
        native=subprocess.run([a['registered_python'],'-B',a['status_predecessor']['root']+'/stage_status.py',*(['--json'] if args.json else [])],capture_output=True,text=True,timeout=60)
        live=read(owner/'LIVE_STATUS.json');registration=read(ROOT/'ACTIVATION_REGISTRATION.json');status=read(ROOT/'ACTIVATION_STATUS.json');parallel=read(owner/'ANALYZER_PARALLEL_PROGRESS.json')
        if args.json:
            base=json.loads(native.stdout);base['source_concurrency']={'registration':registration,'activation':status,'progress':parallel};text=json.dumps(base)
        else:
            text=native.stdout.rstrip()
            if status.get('state')=='ACTIVATED' and parallel.get('active_calls') and parallel.get('round_id')==live.get('round_id') and parallel.get('coordinator_pid')==live.get('pid'):
                text='\n'.join(line for line in text.splitlines() if not line.startswith(('Current:','Current request elapsed:','Last stage event:')))
            text+='\n'+'\n'.join(render_parallel(a,live,registration,status,parallel))
        if args.watch:print('\033[2J\033[H',end='')
        print(text,flush=True)
        if not args.watch:break
        time.sleep(5)
if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:pass
