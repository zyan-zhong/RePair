#!/usr/bin/env python3
"""Allocate one canonical offline Analyzer sampling artifact."""

from __future__ import annotations
import argparse
from pathlib import Path

from pchsi.analyzer.analysis_sampling import (
    AnalysisUnit, MechanicalPolicySignals, allocate_analysis_sampling
)
from pchsi.analyzer.authorities import TrajectoryOutcome
from pchsi.reference_loop.canonical import strict_json_loads, write_new_json


def _object(path: Path) -> dict[str, object]:
    value = strict_json_loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError(f"input must be object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--census", required=True)
    parser.add_argument("--units", required=True)
    parser.add_argument("--approval-manifest")
    parser.add_argument("--total-slots", type=int, required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    rows = strict_json_loads(Path(args.units).read_bytes())
    if not isinstance(rows, list):
        raise ValueError("units must be JSON array")
    units = [
        AnalysisUnit(
            unit_id=x["unit_id"], task_id=x["task_id"],
            gamefile_sha256=x["gamefile_sha256"],
            task_family=x.get("task_family"),
            outcome=TrajectoryOutcome(x["outcome"]),
            frozen_order=x["frozen_order"],
            severe_failure=x.get("severe_failure", False),
            regression_failure=x.get("regression_failure", False),
            unresolved_cross_task_failure=x.get(
                "unresolved_cross_task_failure", False
            ),
            success_inefficiency_flag=x.get("success_inefficiency_flag", False),
            regression_guard_priority=x.get("regression_guard_priority", False),
        )
        for x in rows
    ]
    result = allocate_analysis_sampling(
        units=units, census=_object(Path(args.census)),
        total_analysis_budget=args.total_slots,
        signals=MechanicalPolicySignals(),
        approval_manifest_path=(
            None if args.approval_manifest is None else Path(args.approval_manifest)
        ),
    )
    write_new_json(Path(args.output), result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
