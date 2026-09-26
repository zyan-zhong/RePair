#!/usr/bin/env python3
import argparse
from pathlib import Path
from pchsi.analyzer.gold_panel import select_gold_panels
from pchsi.reference_loop.canonical import strict_json_loads,write_new_json
p=argparse.ArgumentParser(); p.add_argument("--eligible",required=True); p.add_argument("--output",required=True); a=p.parse_args()
write_new_json(Path(a.output),select_gold_panels(strict_json_loads(Path(a.eligible).read_bytes())))
