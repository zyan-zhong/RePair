#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from pchsi.reference_loop.historical_bridge import (
    build_source_collection_lineage_bridge_file,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-execution-root", required=True)
    parser.add_argument("--human-approval", required=True)
    parser.add_argument("--runtime-binding", required=True)
    parser.add_argument("--replay-qualification", required=True)
    parser.add_argument(
        "--expected-replay-qualification-sha256",
        required=True,
    )
    parser.add_argument("--protected-task-access", required=True)
    parser.add_argument(
        "--expected-protected-task-access-sha256",
        required=True,
    )
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    value = build_source_collection_lineage_bridge_file(
        source_execution_root=Path(args.source_execution_root),
        human_approval_path=Path(args.human_approval),
        runtime_binding_path=Path(args.runtime_binding),
        replay_qualification_path=Path(args.replay_qualification),
        expected_replay_qualification_sha256=(
            args.expected_replay_qualification_sha256
        ),
        protected_task_access_path=Path(args.protected_task_access),
        expected_protected_task_access_sha256=(
            args.expected_protected_task_access_sha256
        ),
        output_path=Path(args.output),
    )
    print("SOURCE_COLLECTION_PI1_LINEAGE_BRIDGE_V1_PASS")
    print("SOURCE_BUNDLE_COUNT=" + str(value["source_bundle_count"]))
    print(
        "HUMAN_REGISTERED_CASE_COUNT="
        + str(value["human_registered_case_count"])
    )
    print("ACCESS_CLASS_COUNTS=" + repr(value["access_class_counts"]))
    print("BRIDGE_STATUS=" + str(value["bridge_status"]))
    print("BRIDGE_SHA256=" + str(value["bridge_sha256"]))
    print("OUTPUT=" + str(Path(args.output).resolve()))


if __name__ == "__main__":
    main()
