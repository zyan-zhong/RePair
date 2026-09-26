from pathlib import Path
import sys

WORK = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(WORK / 'v17'), str(WORK / 'v17/native_bba_full/src')]
