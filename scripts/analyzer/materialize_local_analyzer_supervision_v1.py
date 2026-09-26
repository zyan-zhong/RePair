#!/usr/bin/env python3
import argparse
from pathlib import Path
from pchsi.analyzer.supervision_materializer import materialize_local_analyzer_supervision
from pchsi.reference_loop.canonical import strict_json_loads,write_new_json
p=argparse.ArgumentParser(); p.add_argument("--traces",required=True); p.add_argument("--output",required=True); a=p.parse_args()
traces=strict_json_loads(Path(a.traces).read_bytes()); write_new_json(Path(a.output),materialize_local_analyzer_supervision(traces))
