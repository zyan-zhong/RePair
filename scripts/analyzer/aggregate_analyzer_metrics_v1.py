#!/usr/bin/env python3
import argparse
from pathlib import Path
from pchsi.analyzer.metrics import aggregate_repair_discovery_by_condition,registered_secondary_contrast_report
from pchsi.reference_loop.canonical import strict_json_loads,write_new_json
p=argparse.ArgumentParser(); p.add_argument("--rows",required=True); p.add_argument("--u-reg",required=True); p.add_argument("--protected-rows"); p.add_argument("--output",required=True); a=p.parse_args()
rows=strict_json_loads(Path(a.rows).read_bytes()); u=strict_json_loads(Path(a.u_reg).read_bytes()); protected=[] if a.protected_rows is None else strict_json_loads(Path(a.protected_rows).read_bytes())
report=aggregate_repair_discovery_by_condition(rows,registered_universe=u,protected_rows=protected); report["registered_secondary_contrasts"]=registered_secondary_contrast_report(rows); write_new_json(Path(a.output),report)
