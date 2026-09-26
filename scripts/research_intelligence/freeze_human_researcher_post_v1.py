#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from pchsi.research_intelligence.human_reference_round import freeze_post
from pchsi.research_intelligence.product_isolation import assert_separate_roots

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output-dir',required=True);p.add_argument('--human-root',required=True);p.add_argument('--benchmark-root',required=True);a=p.parse_args();assert_separate_roots(Path(a.human_root),Path(a.benchmark_root));result=freeze_post(json.loads(Path(a.input).read_text()),Path(a.output_dir));print('HUMAN_POST_FROZEN='+result['post_record_sha256'])
if __name__=='__main__': main()
