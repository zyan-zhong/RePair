#!/usr/bin/env python3
from pathlib import Path
import argparse,json
def main():
 p=argparse.ArgumentParser(); p.add_argument("--repo-root",required=True); root=Path(p.parse_args().repo_root); text=(root/"src/pchsi/analyzer/metrics.py").read_text()
 for token in ("exact_binomial_two_sided","risk_difference_b_minus_a","relative_risk_b_over_a","holm_adjust","registered_secondary_contrast_report","method_failure_reason_census","infrastructure_reason_census"):
  if token not in text: raise SystemExit(f"missing statistics contract: {token}")
 registry=json.loads((root/"configs/analyzer/analyzer_metric_registry_v1.json").read_text())
 if registry.get("secondary_contrast_adjustment")!="HOLM" or len(registry.get("registered_secondary_contrasts",[]))!=3: raise SystemExit("registered contrast freeze missing")
 print("ANALYZER_STATISTICS_CLOSURE_STATIC_AUDIT_PASS")
if __name__=="__main__": main()
