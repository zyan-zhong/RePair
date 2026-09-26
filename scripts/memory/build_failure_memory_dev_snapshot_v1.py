from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from pchsi.memory.dev_descriptive_snapshot import (
    audit_memory_dev_descriptive_snapshot_v1,
    build_memory_dev_descriptive_snapshot_v1,
    publish_memory_dev_descriptive_snapshot_v1,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _require_manifest_authority_commit(
    manifest: object,
) -> str:
    if not isinstance(manifest, dict):
        raise SystemExit(
            "STOP=SNAPSHOT_MANIFEST_NOT_OBJECT"
        )

    authority_commit = manifest.get(
        "authority_commit"
    )
    if (
        not isinstance(authority_commit, str)
        or len(authority_commit) != 40
        or any(
            ch not in "0123456789abcdef"
            for ch in authority_commit
        )
    ):
        raise SystemExit(
            "STOP=SNAPSHOT_AUTHORITY_COMMIT_INVALID"
        )

    checked_out = subprocess.check_output(
        [
            "git",
            "-C",
            str(REPO_ROOT),
            "rev-parse",
            "HEAD",
        ],
        text=True,
    ).strip()

    if checked_out != authority_commit:
        raise SystemExit(
            "STOP=SNAPSHOT_AUTHORITY_COMMIT_MISMATCH"
        )

    return authority_commit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        required=True,
    )
    parser.add_argument(
        "--manifest-sha256",
        required=True,
    )
    parser.add_argument(
        "--candidate-root",
        required=True,
    )
    parser.add_argument(
        "--snapshot-root",
        required=True,
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--execute",
        action="store_true",
    )
    modes.add_argument(
        "--audit-existing",
        action="store_true",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if (
        manifest_path.is_symlink()
        or not manifest_path.is_file()
    ):
        raise SystemExit(
            "STOP=MATERIALIZATION_MANIFEST_PATH_INVALID"
        )
    raw = manifest_path.read_bytes()
    if (
        hashlib.sha256(raw).hexdigest()
        != args.manifest_sha256
    ):
        raise SystemExit(
            "STOP=MATERIALIZATION_MANIFEST_SHA_MISMATCH"
        )

    manifest = json.loads(raw)
    _require_manifest_authority_commit(
        manifest
    )

    candidate_root = Path(
        args.candidate_root
    )
    if (
        candidate_root.is_symlink()
        or not candidate_root.is_dir()
    ):
        raise SystemExit(
            "STOP=CANDIDATE_ROOT_INVALID"
        )

    candidate_dirs = tuple(
        candidate_root
        / item["candidate_id"]
        for item in manifest["items"]
        if (
            candidate_root
            / item["candidate_id"]
            / "governed_record.json"
        ).is_file()
    )

    snapshot, files = (
        build_memory_dev_descriptive_snapshot_v1(
            candidate_directories=(
                candidate_dirs
            ),
            source_materialization_manifest_sha256=(
                args.manifest_sha256
            ),
            tokenizer_id=manifest[
                "tokenizer_id"
            ],
            tokenizer_revision=manifest[
                "tokenizer_revision"
            ],
        )
    )

    print(
        "SNAPSHOT_SHA256="
        + snapshot.snapshot_sha256
    )
    print(
        "SNAPSHOT_MEMBER_COUNT="
        + str(len(snapshot.members))
    )

    snapshot_root = Path(
        args.snapshot_root
    )
    if (
        snapshot_root.is_symlink()
        or not snapshot_root.is_dir()
    ):
        raise SystemExit(
            "STOP=SNAPSHOT_ROOT_INVALID"
        )

    if args.audit_existing:
        audit_memory_dev_descriptive_snapshot_v1(
            snapshot_directory=(
                snapshot_root
                / snapshot.snapshot_sha256
            ),
            expected_snapshot_sha256=(
                snapshot.snapshot_sha256
            ),
        )
        print(
            "MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_AUDIT_PASS"
        )
        return 0

    if args.execute:
        if (
            os.environ.get(
                "CODE_APPROVED_FAILURE_MEMORY_PACKAGE_A_V1"
            )
            != "CODE_APPROVED_FAILURE_MEMORY_PACKAGE_A_V1"
        ):
            raise SystemExit(
                "STOP=PACKAGE_A_CODE_APPROVAL_MISSING"
            )
        if (
            os.environ.get(
                "PACKAGE_A_EXECUTION_APPROVED"
            )
            != "PACKAGE_A_EXECUTION_APPROVED"
        ):
            raise SystemExit(
                "STOP=PACKAGE_A_EXECUTION_APPROVAL_MISSING"
            )

        final = (
            publish_memory_dev_descriptive_snapshot_v1(
                output_root=(
                    snapshot_root
                ),
                snapshot=snapshot,
                member_files=files,
            )
        )
        audit_memory_dev_descriptive_snapshot_v1(
            snapshot_directory=final,
            expected_snapshot_sha256=(
                snapshot.snapshot_sha256
            ),
        )
        print(
            "SNAPSHOT_DIRECTORY="
            + str(final)
        )
        print(
            "MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_PUBLISHED_AND_AUDITED"
        )
        return 0

    print(
        "MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_DRY_RUN_PASS"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
