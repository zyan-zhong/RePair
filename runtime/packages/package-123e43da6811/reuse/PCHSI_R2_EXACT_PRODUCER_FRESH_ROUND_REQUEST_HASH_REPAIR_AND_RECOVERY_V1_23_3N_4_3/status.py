from pathlib import Path
import argparse,json
from recovery_core import load_json
p=argparse.ArgumentParser();p.add_argument('--round-tail-state-root',type=Path,required=True);a=p.parse_args()
owner=load_json(a.round_tail_state_root/'R2_NATIVE_PRODUCER_RECOVERY_OWNER_V1.json');root=Path(owner['root'])
print('RECOVERY_ROOT='+str(root))
for name in ('RECOVERY_TERMINAL.json','RECOVERY_STATUS.json','RESIDENT_LAUNCH.json','SUBMISSION_RECEIPT.json','READY.json'):
    path=root/name
    if path.is_file():
        print('OBSERVED_ARTIFACT='+name);print(json.dumps(load_json(path),ensure_ascii=False,indent=2));break
print('FULL_MAX10_AUTONOMOUS_CAMPAIGN_RELEASED=false')
