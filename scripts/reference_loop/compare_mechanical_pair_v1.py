#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
from pchsi.reference_loop.bundle_reader import validate_attempt_bundle
from pchsi.reference_loop.paired import (
    extract_mechanical_paired_evidence_file,
)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--left-bundle", required=True)
    parser.add_argument("--right-bundle", required=True)
    parser.add_argument("--pair-id", required=True)
    parser.add_argument(
        "--pair-kind",
        choices=("MATCHED_CONDITION", "F0F1"),
        required=True,
    )
    parser.add_argument("--intervention-model-call-index", type=int)
    parser.add_argument("--repair-registration-sha256")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    left = validate_attempt_bundle(Path(args.left_bundle))
    right = validate_attempt_bundle(Path(args.right_bundle))
    value = extract_mechanical_paired_evidence_file(
        left=left,
        right=right,
        pair_id=args.pair_id,
        pair_kind=args.pair_kind,
        registered_intervention_model_call_index=(
            args.intervention_model_call_index
        ),
        repair_registration_sha256=(
            args.repair_registration_sha256
        ),
        output_path=Path(args.output),
    )
    print("MECHANICAL_PAIRED_EVIDENCE_V1_PASS")
    print("PAIR_ALIGNMENT_STATUS=" + str(value["pair_alignment_status"]))
    print("EVIDENCE_SHA256=" + str(value["evidence_sha256"]))

if __name__ == "__main__":
    main()
