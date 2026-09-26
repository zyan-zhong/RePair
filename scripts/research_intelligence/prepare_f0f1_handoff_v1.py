#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os
from pathlib import Path
from pchsi.reference_loop.canonical import canonical_json_bytes,domain_hash
from pchsi.research_intelligence.human_reference_round import build_f0f1_handoff

def main():
 p=argparse.ArgumentParser();p.add_argument('--human-pre',required=True);p.add_argument('--repair-portfolio',required=True);p.add_argument('--output',required=True);a=p.parse_args()
 pre=json.loads(Path(a.human_pre).read_text()); portfolio=json.loads(Path(a.repair_portfolio).read_text()); out=build_f0f1_handoff(human_pre=pre,portfolio_payload=portfolio);out['handoff_sha256']=domain_hash('HUMAN_REFERENCE_F0F1_HANDOFF_V1',out)
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True);fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 try: os.write(fd,canonical_json_bytes(out));os.fsync(fd)
 finally: os.close(fd)
 print('F0F1_HANDOFF_PREPARED='+out['handoff_sha256'])
if __name__=='__main__': main()
