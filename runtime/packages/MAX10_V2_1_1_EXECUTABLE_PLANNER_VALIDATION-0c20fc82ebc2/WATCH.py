"""Small read-only window over the registered validation and its typed index."""
from pathlib import Path
import argparse,hashlib,json,os,time
ROOT=Path(__file__).resolve().parent
def read(path):return json.loads(Path(path).read_bytes())
def view():
    a=read(ROOT/'AUTHORITY.json');root=Path(a['experiment_root']);path=root/'VALIDATION_PROGRESS.json'
    if not path.is_file():return ['Strategy validation | not started']
    status=read(path);pid=status['pid'];proc=Path('/proc',str(pid),'cmdline')
    try:alive=bool(proc.read_bytes())
    except OSError:alive=False
    lines=['Guarded strategy validation | '+status['stage'],
        'Validation limit: 1 | reused R5 rollout and Analyzer | new formal rounds: 0',
        'Resident: '+status['host']+' '+str(pid)+' | '+('alive' if alive else 'not running')]
    p=root/'analyzer/pre/source_reviews/REVIEW_PROGRESS.json'
    if p.is_file():
        review=read(p);lines.append('PRE reviews: '+str(review['completed_calls'])+' / '+str(review.get('planned_map_calls','?'))+' | '+review['state'])
    p=root/'analyzer/pre/ACCEPTED_PRE_REF.json'
    if p.is_file():lines.append('PRE selected states: '+str(read(p)['selected_state_count']))
    index=root/'analyzer/h44/REGISTERED_H44_EXECUTION_INDEX.json'
    if index.is_file():
        row=read(index);ref=row['option_registry_ref'];raw=Path(ref['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=ref.get('file_sha256',ref.get('sha256')):raise ValueError('MONITOR_INDEX_REF_CHANGED')
        causal=Path(row['execution_run_root']);p=causal/'EXECUTION_PLAN.json'
        if p.is_file():
            plan=read(p);branches=plan['handoff']['branch_plan'];done=scientific=invalid=0
            for b in branches:
                terminal=causal/'branches'/b['branch_key_sha256']/'BRANCH_TERMINAL.json'
                if terminal.is_file():
                    done+=1;record=read(terminal);ok=record.get('scientific_outcome_produced') is True and record.get('evidence_complete') is True
                    scientific+=int(ok);invalid+=int(not ok)
            lines.append(f'F0/F1: {done} / {len(branches)} | scientific: {scientific} | invalid: {invalid}')
        p=causal/'verifier/ENVIRONMENT_RESULT_PACKAGE.json'
        if p.is_file():lines.append('Causal effects: '+json.dumps(read(p)['stable_effect_counts']))
        p=causal/'process/PROCESS_EFFECT_SUMMARY.json'
        if p.is_file():lines.append('Progress effects (research only): '+json.dumps(read(p)['counts']))
    if 'error' in status:lines.append('STOP: '+status['error_type']+':'+status['error'])
    p=root/'VALIDATION_RESULT.json'
    if p.is_file():lines.append('Outcome: '+read(p)['outcome'])
    lines.append('Updated: '+status['updated_utc']);lines.append('Evidence: '+str(root))
    return lines
def main():
    p=argparse.ArgumentParser();p.add_argument('--watch',action='store_true');args=p.parse_args()
    while True:
        if args.watch:print('\033[2J\033[H',end='')
        try:print('\n'.join(view()),flush=True)
        except Exception as exc:print('Monitor read unavailable: '+str(exc),flush=True)
        if not args.watch:return 0
        time.sleep(5)
if __name__=='__main__':raise SystemExit(main())
