from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from pchsi.memory.candidate_materialization import (
    CandidateMaterializationItemV1,
    audit_candidate_directory_v1,
    materialize_candidate_item_v1,
)
from pchsi.memory.lifecycle_relations import (
    EvaluationContaminationStatusV1,
)
from pchsi.memory.package_a_execution_ledgers import (
    write_package_a_materialization_ledgers_v1,
)


REPO_ROOT = Path(__file__).resolve().parents[2]

PACKAGE_A_LEDGER_KINDS = (
    "MEMORY_EVENT_LEDGER_V1",
    "MEMORY_RECORD_EFFECT_LEDGER_V1",
    "MEMORY_PROMOTION_LEDGER_V1",
    "MEMORY_EXPOSURE_LEDGER_V1",
)


class LocalTokenizerCounter:
    def __init__(
        self,
        tokenizer_id: str,
        tokenizer_revision: str,
        local_path: Path,
    ):
        self.tokenizer_id = tokenizer_id
        self.tokenizer_revision = tokenizer_revision

        from transformers import AutoTokenizer

        self._tok = AutoTokenizer.from_pretrained(
            str(local_path),
            local_files_only=True,
            trust_remote_code=False,
        )

    def count_tokens(self, text: str) -> int:
        return len(
            self._tok.encode(
                text,
                add_special_tokens=False,
            )
        )


def _require_manifest_authority_commit(
    manifest: object,
) -> str:
    if not isinstance(manifest, dict):
        raise SystemExit(
            "STOP=MATERIALIZATION_MANIFEST_NOT_OBJECT"
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
            "STOP=MATERIALIZATION_AUTHORITY_COMMIT_INVALID"
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
            "STOP=MATERIALIZATION_AUTHORITY_COMMIT_MISMATCH"
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
    parser.add_argument("--output-root")
    parser.add_argument("--ledger-root")
    parser.add_argument("--event-time-utc")
    parser.add_argument(
        "--execute",
        action="store_true",
    )
    parser.add_argument(
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
    authority_commit = (
        _require_manifest_authority_commit(
            manifest
        )
    )

    tokenizer = LocalTokenizerCounter(
        manifest["tokenizer_id"],
        manifest["tokenizer_revision"],
        Path(manifest["tokenizer_local_path"]),
    )

    items = tuple(
        CandidateMaterializationItemV1(
            candidate_id=item["candidate_id"],
            source_experience_paths=tuple(
                item["source_experience_paths"]
            ),
            source_experience_sha256s=tuple(
                item["source_experience_sha256s"]
            ),
            assembly_registration_path=item[
                "assembly_registration_path"
            ],
            assembly_registration_sha256=item[
                "assembly_registration_sha256"
            ],
            previous_record_path=item[
                "previous_record_path"
            ],
            previous_record_sha256=item[
                "previous_record_sha256"
            ],
            evaluation_contamination_status=(
                EvaluationContaminationStatusV1(
                    item[
                        "evaluation_contamination_status"
                    ]
                )
            ),
        )
        for item in manifest["items"]
    )

    if args.audit_existing:
        if args.output_root is None:
            raise SystemExit(
                "STOP=MATERIALIZATION_AUDIT_OUTPUT_ROOT_MISSING"
            )
        for item in items:
            audit_candidate_directory_v1(
                Path(args.output_root)
                / item.candidate_id
            )
        print(
            "FAILURE_MEMORY_STAGING_CANDIDATES_AUDIT_PASS"
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
        if args.output_root is None:
            raise SystemExit(
                "STOP=MATERIALIZATION_OUTPUT_ROOT_MISSING"
            )
        if args.ledger_root is None:
            raise SystemExit(
                "STOP=PACKAGE_A_LEDGER_ROOT_MISSING"
            )
        if args.event_time_utc is None:
            raise SystemExit(
                "STOP=PACKAGE_A_EVENT_TIME_MISSING"
            )

    for item in items:
        (
            initial_record,
            source_report,
            eligibility_bundle,
            _,
        ) = materialize_candidate_item_v1(
            item=item,
            tokenizer=tokenizer,
            output_root=(
                None
                if args.output_root is None
                else Path(args.output_root)
            ),
            execute=args.execute,
        )

        if args.execute:
            write_package_a_materialization_ledgers_v1(
                ledger_root=Path(
                    args.ledger_root
                ),
                candidate_id=item.candidate_id,
                initial_record=initial_record,
                source_report=source_report,
                eligibility_bundle=(
                    eligibility_bundle
                ),
                event_time_utc=(
                    args.event_time_utc
                ),
                repository_commit=(
                    authority_commit
                ),
            )

    print(
        "FAILURE_MEMORY_STAGING_MATERIALIZATION_PASS"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
