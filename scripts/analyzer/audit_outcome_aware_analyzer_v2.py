#!/usr/bin/env python3
from pathlib import Path
import argparse
REQUIRED=[
 "grouping.py","component_attribution.py","crosscheck.py","candidate_projector.py",
 "role_trace.py","supervision_materializer.py","metrics.py","gold_panel.py",
 "success_optimization.py","repair_decomposition.py","experiment_registry.py",
]
def main():
 p=argparse.ArgumentParser(); p.add_argument("--repo-root",required=True); a=p.parse_args()
 root=Path(a.repo_root); prod=root/"src/pchsi/analyzer"
 for name in REQUIRED:
  if not (prod/name).is_file(): raise SystemExit(f"missing {name}")
 for path in prod.rglob("*.py"):
  text=path.read_text().lower()
  for forbidden in ("env.step(","import alfworld","from openai","from anthropic"):
   if forbidden in text: raise SystemExit(f"forbidden runtime marker {forbidden}: {path}")
 assert "SECONDARY_NON_BLOCKING" in (prod/"success_optimization.py").read_text()
 assert "POST_BENEFIT_SECONDARY" in (prod/"repair_decomposition.py").read_text()
 print("OUTCOME_AWARE_ANALYZER_V2_STATIC_SCIENTIFIC_AUDIT_PASS")
if __name__=="__main__": main()
