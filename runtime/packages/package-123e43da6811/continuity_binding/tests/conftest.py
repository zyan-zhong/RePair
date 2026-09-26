"""Local synthetic tests against captured native source; never live science."""
from pathlib import Path
import sys
import importlib.util

WORK = Path(__file__).resolve().parents[3]
H44 = WORK / 'reference_g2/PCHSI_PAPER_CRITICAL_CAUSAL_ROUND_EXECUTION_V1_23_3H4_4'
sys.path.insert(0, str(WORK / 'v17'))
sys.path.insert(0, str(WORK / 'v17/native_bba_full/src'))
spec = importlib.util.spec_from_file_location('captured_h44_io', H44 / 'io_utils.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
sys.modules['captured_h44_io'] = module
