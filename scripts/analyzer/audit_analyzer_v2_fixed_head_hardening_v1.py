#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse, ast, json

REQUIRED_MODULES=[
 "grouping.py","component_attribution.py","crosscheck.py","candidate_projector.py",
 "role_trace.py","supervision_materializer.py","metrics.py","gold_panel.py",
 "success_optimization.py","repair_decomposition.py","experiment_registry.py",
]
REQUIRED_TESTS=[
 "test_analyzer_fixed_head_bindings_v3.py",
 "test_analyzer_role_trace_hardening_v3.py",
 "test_analyzer_metrics_gold_hardening_v3.py",
 "test_analyzer_protocol_hardening_v3.py",
]

def main():
    p=argparse.ArgumentParser(); p.add_argument("--repo-root",required=True)
    root=Path(p.parse_args().repo_root).resolve()
    prod=root/"src/pchsi/analyzer"
    for name in REQUIRED_MODULES:
        if not (prod/name).is_file(): raise SystemExit(f"missing module {name}")
    for name in REQUIRED_TESTS:
        if not (root/"tests/analyzer"/name).is_file(): raise SystemExit(f"missing hardening test {name}")
    for path in prod.rglob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
        low=path.read_text(encoding="utf-8").lower()
        for forbidden in ("env.step(","import alfworld","from openai","from anthropic"):
            if forbidden in low: raise SystemExit(f"forbidden runtime marker {forbidden}: {path}")
    metrics=json.loads((root/"configs/analyzer/analyzer_metric_registry_v1.json").read_text())
    for name,entry in metrics["metrics"].items():
        for key in ("role","numerator","denominator","missingness","uncertainty_method","claim_status"):
            if key not in entry: raise SystemExit(f"metric {name} missing {key}")
    if metrics.get("weighted_composite_scores_forbidden") is not True:
        raise SystemExit("weighted composite scores not forbidden")
    trace=json.loads((root/"configs/analyzer/schemas/cognitive_role_trace_v1.json").read_text())
    for field in ("request_id","raw_request_sha256","raw_response_sha256","input_tokens",
                  "output_tokens","latency_ms","cost_usd","training_permitted"):
        if field not in trace["required"]: raise SystemExit(f"role trace missing {field}")
    print("ANALYZER_V2_FIXED_HEAD_HARDENING_STATIC_AUDIT_PASS")

if __name__=="__main__":
    main()
