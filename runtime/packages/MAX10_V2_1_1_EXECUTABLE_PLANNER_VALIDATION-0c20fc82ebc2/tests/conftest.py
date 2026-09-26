import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import os,json
root=Path(__file__).resolve().parents[1]
native=os.environ.get('PCHSI_TEST_NATIVE_H44')
if native is None and (root/'AUTHORITY.json').is_file():
    native=json.loads((root/'AUTHORITY.json').read_bytes())['native_h44_root']
if native:
    sys.path.extend([native,str(Path(native)/'native_repo/src')])
