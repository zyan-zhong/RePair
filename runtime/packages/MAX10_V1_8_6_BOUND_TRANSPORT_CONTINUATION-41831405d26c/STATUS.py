from pathlib import Path
import json,argparse,time
ROOT=Path(__file__).resolve().parent
def show():
    a=json.loads((ROOT/'AUTHORITY.json').read_bytes());owner=Path(a['owner_root']);p=owner/'LIVE_STATUS.json'
    if not p.is_file():return 'Formal Max-10 | status not materialized'
    v=json.loads(p.read_bytes());lines=['Formal Max-10 | '+str(v.get('stage')),
        'Valid rounds: '+str(v.get('valid_round_count',v.get('valid_rounds','?')))+' / '+str(v.get('max_rounds','?'))+' | invalid attempts: '+str(v.get('invalid_attempt_count',v.get('invalid_attempts','?'))),
        'Round: '+str(v.get('round_id')),'Resident: '+str(v.get('host'))+' '+str(v.get('pid'))]
    execution=json.loads(Path(a['immutable_refs']['local_execution']['path']).read_bytes())
    if execution.get('round_id')==v.get('round_id'):
        rows=execution['rows'];lines+=['Local slots closed: '+str(len(rows))+' | accepted: '+str(sum(x['status']=='ACCEPTED' for x in rows))+' | skipped: '+str(sum(x['status']=='QUARANTINED_SOURCE_SKIPPED' for x in rows))]
    chain=owner/'CHAIN_PROGRESS.json'
    if chain.is_file():
        c=json.loads(chain.read_bytes())
        if c.get('round_id')==v.get('round_id'):lines+=['Current: '+str(c.get('stage_id'))+' | '+str(c.get('state')),'Stage updated: '+str(c.get('updated_utc'))]
    if v.get('rollout'):lines+=['Rollout: '+json.dumps(v['rollout'])]
    lines+=['Updated: '+str(v.get('updated_utc'))]
    if v.get('stop_reason') or v.get('error'):lines+=['Stop: '+str(v.get('stop_reason') or v.get('error'))]
    return '\n'.join(lines)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--watch',action='store_true');p.add_argument('--interval',type=float,default=5);args=p.parse_args()
    while True:
        if args.watch:print('\033[2J\033[H',end='')
        print(show(),flush=True)
        if not args.watch:break
        time.sleep(max(1,args.interval))
