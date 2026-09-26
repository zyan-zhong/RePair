"""Unified observational window; closing it never stops the resident."""
from pathlib import Path
import argparse,json,os,shutil,sys,time
from datetime import datetime,timezone
from dashboard import render,use_color,row

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--authority',default=str(Path(__file__).with_name('AUTHORITY.json')))
    modes=p.add_mutually_exclusive_group();modes.add_argument('--formal',action='store_true');modes.add_argument('--validation',action='store_true')
    p.add_argument('--watch',action='store_true');p.add_argument('--json',action='store_true')
    p.add_argument('--color',choices=['auto','always','never'],default='auto');p.add_argument('--interval',type=float)
    p.add_argument('--frames',type=int);p.add_argument('--width',type=int)
    p.add_argument('--details',action='store_true')
    args=p.parse_args();a=json.loads(Path(args.authority).read_bytes())
    interval=args.interval if args.interval is not None else a['refresh_seconds']
    if not 1<=interval<=60:p.error('interval must be between 1 and 60 seconds')
    if args.frames is not None and args.frames<1:p.error('frames must be positive')
    mode='formal' if args.formal else 'validation' if args.validation else 'auto'
    from collector import Collector
    collector=None;frames=0
    while True:
        try:
            if collector is None:collector=Collector(a)
            s=collector.collect(mode)
        except Exception as exc:
            s={'title':'PCHSI monitor','state':'UNKNOWN','phase':'MONITOR_READ_UNAVAILABLE',
               'refreshed':datetime.now(timezone.utc).isoformat(timespec='seconds'),
               'rows':[row(name,state='UNKNOWN') for name in ['Rollout','Analyzer L','Analyzer G','Analyzer C','Analyzer P','Analyzer X','PRE sources','PRE decision','F0/F1','POST','Training','Eval parent','Eval candidate','Acceptance','Memory closure','Paper export']],
               'notes':[type(exc).__name__+': '+str(exc),'Observer will retry. This is not a training verdict.']}
        color=use_color(args.color,sys.stdout.isatty()) and not args.json
        if args.watch and sys.stdout.isatty() and not args.json and os.environ.get('TERM')!='dumb':print('\x1b[2J\x1b[H',end='')
        print(json.dumps(s,ensure_ascii=False) if args.json else render(s,color=color,width=args.width or shutil.get_terminal_size((110,40)).columns,details=args.details),flush=True)
        frames+=1
        if not args.watch or args.frames is not None and frames>=args.frames:return 0 if s['phase']!='MONITOR_READ_UNAVAILABLE' else 2
        time.sleep(interval)

if __name__=='__main__':
    try:raise SystemExit(main())
    except KeyboardInterrupt:pass
