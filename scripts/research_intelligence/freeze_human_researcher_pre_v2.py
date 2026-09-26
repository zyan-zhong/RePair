#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path
from pchsi.research_intelligence.human_reference_round import (
    freeze_pre,
    validate_evidence_binding,
)
from pchsi.research_intelligence.product_isolation import assert_separate_roots


def load(path: str) -> dict[str, object]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON object required")
    return value


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--evidence-binding", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--human-root", required=True)
    p.add_argument("--benchmark-root", required=True)
    a = p.parse_args()
    assert_separate_roots(Path(a.human_root), Path(a.benchmark_root))
    binding = load(a.evidence_binding)
    validate_evidence_binding(binding)
    result = freeze_pre(
        load(a.input), Path(a.output_dir), evidence_binding=binding
    )
    print("HUMAN_PRE_FROZEN=" + result["pre_record_sha256"])


if __name__ == "__main__":
    main()
