#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--repo-root",required=True)
    root=Path(parser.parse_args().repo_root).resolve()
    authority=(root/"src/pchsi/analyzer/authorities.py").read_text()
    router=(root/"src/pchsi/analyzer/outcome_router.py").read_text()
    sampling=(root/"src/pchsi/analyzer/analysis_sampling.py").read_text()
    local=(root/"src/pchsi/analyzer/local_results.py").read_text()
    schema=(root/"src/pchsi/analyzer/schema_contract.py").read_text()
    assert "POST_EPISODE_DEV_ONLY" in authority
    assert "def route_episode(evidence_pack" in router
    assert "Exact approved precedence" in router
    assert "policy:" not in sampling
    assert "approval_sha256" in sampling and "census_sha256" in sampling
    assert "largest_remainder" in sampling
    assert "duplicate error_instance_id" in local
    assert "A2/A3 cannot generate" in local
    assert "mechanical evidence reference does not exist" in local
    assert "object schema must set additionalProperties=false" in schema
    for forbidden in ("openai","anthropic","env.step(","alfworld"):
        for path in (root/"src/pchsi/analyzer").rglob("*.py"):
            if forbidden in path.read_text().lower():
                raise SystemExit(f"forbidden runtime marker {forbidden}: {path}")
    print("ANALYZER_BATCH1_SCIENTIFIC_HARDENING_STATIC_AUDIT_PASS")
    return 0


if __name__=="__main__": raise SystemExit(main())
