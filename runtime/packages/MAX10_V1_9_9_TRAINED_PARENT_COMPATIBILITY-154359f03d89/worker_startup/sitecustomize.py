import os,sys
from pathlib import Path
if os.environ.get('PCHSI_REGISTERED_TRAINED_RUNTIME_ENTRY'):
    try:
        root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
        from runtime_overlay import start_worker
        start_worker(root)
    except Exception as error:
        raise SystemExit('REGISTERED_TRAINED_WORKER_BOOTSTRAP_FAILED:'+str(error)) from error
