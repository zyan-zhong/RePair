#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from pchsi.reference_loop.approved_materialization import (
    materialize_approved_reference_loop_foundation,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", required=True)
    parser.add_argument("--approval", required=True)
    parser.add_argument("--lineage-bridge", required=True)
    parser.add_argument("--mechanical-panel", required=True)
    parser.add_argument("--protected-task-access", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    manifest = materialize_approved_reference_loop_foundation(
        review_path=Path(args.review),
        approval_path=Path(args.approval),
        lineage_bridge_path=Path(args.lineage_bridge),
        mechanical_panel_path=Path(args.mechanical_panel),
        protected_task_access_path=Path(args.protected_task_access),
        output_root=Path(args.output_root),
    )
    print("REFERENCE_LOOP_ANALYZER_EVIDENCE_FOUNDATION_V1_PASS")
    print("ROW_COUNT=" + str(manifest["row_count"]))
    print("PI1_IDENTITY_SHA256=" + str(manifest["pi1_identity_sha256"]))
    print("MANIFEST_SHA256=" + str(manifest["manifest_sha256"]))
    print("OUTPUT_ROOT=" + str(Path(args.output_root).resolve()))


if __name__ == "__main__":
    main()
