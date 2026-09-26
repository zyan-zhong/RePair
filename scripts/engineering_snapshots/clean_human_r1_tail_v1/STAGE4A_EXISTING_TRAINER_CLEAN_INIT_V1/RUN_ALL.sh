#!/usr/bin/env bash
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
if [ -z "$HERE" ]; then exit 2; fi
if cd "$HERE"; then :; else exit 2; fi
if sha256sum -c PACKAGE_FILES.sha256; then :; else exit 2; fi
PY="${PYTHON:-/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python}"
# The request binds the existing repository; this is not a model import.
if "$PY" -B - "$@" <<'PY'
from pathlib import Path
import json,os,subprocess,sys
root=Path.cwd();request_path=root/'current_request.json'
args=sys.argv[1:]
if '--request' in args:request_path=Path(args[args.index('--request')+1])
r=json.loads(request_path.read_text())
trainer=Path(r['repo'])/'scripts/engineering_snapshots/training_pipeline/round_generic_training_stage_v2_1_hardening_build'
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join([str(Path(r['repo'])/'src'),str(trainer),str(root)]))
p=subprocess.run([sys.executable,'-B','-m','unittest','discover','-s',str(root/'tests'),'-v'],env=env,check=False)
if p.returncode:raise SystemExit(p.returncode)
p=subprocess.run([sys.executable,'-B',str(root/'run_stage.py'),*args],env=env,check=False)
raise SystemExit(p.returncode)
PY
then exit 0
else RC=$?; exit "$RC"
fi
