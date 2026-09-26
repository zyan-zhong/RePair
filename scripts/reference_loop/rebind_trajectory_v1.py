#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from pchsi.reference_loop.bundle_reader import validate_attempt_bundle
from pchsi.reference_loop.rebinding import rebind_trajectory_file

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-root", required=True)
    parser.add_argument("--pi1-identity", required=True)
    parser.add_argument("--task-access-revalidation", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    bundle = validate_attempt_bundle(Path(args.bundle_root))
    value = rebind_trajectory_file(
        bundle=bundle,
        pi1_identity_path=Path(args.pi1_identity),
        task_access_revalidation_path=Path(
            args.task_access_revalidation
        ),
        output_path=Path(args.output),
    )
    print("TRAJECTORY_REBINDING_MANIFEST_V1_PASS")
    print("SOURCE_BUNDLE_SHA256=" + bundle.attempt_bundle_sha256)
    print("MANIFEST_SHA256=" + str(value["manifest_sha256"]))
    print("OUTPUT=" + str(Path(args.output).resolve()))

if __name__ == "__main__":
    main()
