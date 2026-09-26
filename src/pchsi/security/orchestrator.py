"""Non-executing command surface for the S1 backend-probe candidate."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

from .execution_gate import (
    EXECUTION_NOT_APPROVED_MARKER,
    ExecutionNotApprovedError,
    require_execution_approval,
)


DESIGN_ID = "S1_COLLECTOR_BACKEND_PROBE_V1"
BACKEND_ID = "ROOTLESS_RESTRICTED_ROOT_NAMESPACE_SANDBOX_V2"
DESIGN_COMMIT = "6199510501841ce3ce3d9ca6da87d70f10d4c787"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m pchsi.security.orchestrator",
    )

    mode = parser.add_mutually_exclusive_group(
        required=True,
    )
    mode.add_argument(
        "--describe",
        action="store_true",
    )
    mode.add_argument(
        "--execute",
        action="store_true",
    )

    parser.add_argument(
        "--approval-path",
        type=Path,
        default=None,
    )

    return parser


def main(
    argv: Sequence[str] | None = None,
) -> int:
    arguments = build_parser().parse_args(argv)

    if arguments.describe:
        print(f"design_id={DESIGN_ID}")
        print(f"backend_id={BACKEND_ID}")
        print(f"design_commit={DESIGN_COMMIT}")
        print("BACKEND_PROBE_EXECUTION=NOT_APPROVED")
        return 0

    try:
        require_execution_approval(
            approval_path=arguments.approval_path,
            expected_design_commit=DESIGN_COMMIT,
            expected_artifact_manifest_sha256=None,
        )
    except ExecutionNotApprovedError as error:
        print(str(error), file=sys.stderr)
        return 77

    print(
        f"{EXECUTION_NOT_APPROVED_MARKER}: unreachable closed gate",
        file=sys.stderr,
    )
    return 77


if __name__ == "__main__":
    raise SystemExit(main())
# ---------------------------------------------------------------------------
# Task 11: pure dataset-bound description helper
# ---------------------------------------------------------------------------

def describe_dataset_bound_backend(record: object) -> dict[str, object]:
    from .execution_gate import BackendProbeExecutionRecord

    if not isinstance(record, BackendProbeExecutionRecord):
        raise TypeError("record must be BackendProbeExecutionRecord")

    return {
        "design_id": DESIGN_ID,
        "backend_id": BACKEND_ID,
        "dataset_version": record.dataset_identity.dataset_version,
        "logical_root_id": record.dataset_identity.logical_root_id,
        "external_execution_decision_reference": (
            record.external_execution_decision_reference
        ),
        "BACKEND_PROBE_EXECUTION": "NOT_APPROVED",
    }
