import json,sys
from signature_entry import verify,load
print('SIGNATURE_OVERLAY_SHA='+verify())
if '--server' in sys.argv:
    a,base,identity=load();print(json.dumps(base.preflight()))
print('PROVIDER_SEND_COUNT=0')
