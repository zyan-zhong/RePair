"""Freeze already-reviewed distillation governance inputs offline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from pchsi.evaluation.condition_run_schedule import (
    ConditionRunScheduleV1,
)
from pchsi.evaluation.distillation_access import (
    HistoricalAccessAuditV1,
    TaskAccessManifestV1,
)
from pchsi.evaluation.distillation_governance import (
    freeze_governance_inputs,
)
from pchsi.evaluation.policy_condition import (
    PolicyConditionManifestV1,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="freeze_distillation_governance.py",
    )
    parser.add_argument(
        "--historical-access-audit",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--task-access-manifest",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--policy-condition-manifest",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--condition-run-schedule",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = freeze_governance_inputs(
        historical_access_audit=HistoricalAccessAuditV1.from_json(
            args.historical_access_audit.read_bytes()
        ),
        task_access_manifest=TaskAccessManifestV1.from_json(
            args.task_access_manifest.read_bytes()
        ),
        policy_condition=PolicyConditionManifestV1.from_json(
            args.policy_condition_manifest.read_bytes()
        ),
        schedule=ConditionRunScheduleV1.from_json(
            args.condition_run_schedule.read_bytes()
        ),
        output_dir=args.output_dir,
    )
    print(
        json.dumps(
            {
                "output_dir": str(result.output_dir),
                "governance_freeze_index_sha256": (
                    result.governance_freeze_index_sha256
                ),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
