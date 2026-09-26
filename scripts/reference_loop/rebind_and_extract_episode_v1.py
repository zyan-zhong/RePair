#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from pchsi.reference_loop.bundle_reader import validate_attempt_bundle
from pchsi.reference_loop.mechanical import (
    extract_mechanical_episode_evidence_file,
)
from pchsi.reference_loop.rebinding import rebind_trajectory_file

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-root", required=True)
    parser.add_argument("--pi1-identity", required=True)
    parser.add_argument("--task-access-revalidation", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    output = Path(args.output_dir)
    if output.exists() or output.is_symlink():
        raise SystemExit("STOP=OUTPUT_DIR_EXISTS")
    output.mkdir(parents=True)
    bundle = validate_attempt_bundle(Path(args.bundle_root))
    sidecar = rebind_trajectory_file(
        bundle=bundle,
        pi1_identity_path=Path(args.pi1_identity),
        task_access_revalidation_path=Path(
            args.task_access_revalidation
        ),
        output_path=output / "TRAJECTORY_REBINDING_MANIFEST_V1.json",
    )
    facts = extract_mechanical_episode_evidence_file(
        bundle=bundle,
        output_path=output / "MECHANICAL_EPISODE_EVIDENCE_V1.json",
    )
    print("TRAJECTORY_REBINDING_AND_MECHANICAL_EVIDENCE_PASS")
    print("BUNDLE_SHA256=" + bundle.attempt_bundle_sha256)
    print("REBINDING_SHA256=" + str(sidecar["manifest_sha256"]))
    print("MECHANICAL_SHA256=" + str(facts["evidence_sha256"]))
    print("OUTPUT_DIR=" + str(output.resolve()))

if __name__ == "__main__":
    main()
