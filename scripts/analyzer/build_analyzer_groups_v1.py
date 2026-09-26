#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from pchsi.analyzer.grouping import build_group_manifests
from pchsi.reference_loop.canonical import strict_json_loads,write_new_json
def main():
 p=argparse.ArgumentParser(); p.add_argument("--local-results",required=True)
 p.add_argument("--mechanical-signatures",required=True); p.add_argument("--output",required=True)
 a=p.parse_args(); results=strict_json_loads(Path(a.local_results).read_bytes())
 raw=strict_json_loads(Path(a.mechanical_signatures).read_bytes())
 signatures={(x["local_result_sha256"],x["error_instance_id"]):x for x in raw}
 write_new_json(Path(a.output),{"schema_id":"ANALYZER_GROUP_COLLECTION_V1",
     "groups":build_group_manifests(results,signatures)})
if __name__=="__main__": main()
