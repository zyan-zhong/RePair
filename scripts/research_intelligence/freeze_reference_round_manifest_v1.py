#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path
from pchsi.research_intelligence.human_reference_round import freeze_round_manifest

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args();result=freeze_round_manifest(json.loads(Path(a.input).read_text()),Path(a.output));print('REFERENCE_ROUND_MANIFEST_FROZEN='+result['reference_round_manifest_sha256'])
if __name__=='__main__': main()
