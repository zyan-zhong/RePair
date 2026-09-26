from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from pchsi.evaluation.alfworld_adapter import (
    SpawnedAlfworldAdapter,
)
from pchsi.evaluation.canonical_evidence import (
    sha256_file,
    strict_json_loads,
)
from pchsi.memory.source_state_contracts import (
    RegisteredReplaySourceV1,
    SourceStateReplayReportV1,
)
from pchsi.memory.source_state_replay import (
    replay_source_decision_state_v1,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _require_manifest_authority_commit(
    manifest: object,
) -> str:
    if not isinstance(manifest, dict):
        raise SystemExit(
            "STOP=REPLAY_MANIFEST_NOT_OBJECT"
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
            "STOP=REPLAY_AUTHORITY_COMMIT_INVALID"
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
            "STOP=REPLAY_AUTHORITY_COMMIT_MISMATCH"
        )

    return authority_commit


def _load_source(
    path: Path,
    expected_sha256: str,
) -> RegisteredReplaySourceV1:
    if path.is_symlink() or not path.is_file():
        raise ValueError(
            "replay source path invalid"
        )
    data = path.read_bytes()
    if (
        hashlib.sha256(data).hexdigest()
        != expected_sha256
    ):
        raise ValueError(
            "replay source SHA mismatch"
        )
    source = RegisteredReplaySourceV1.from_json(
        data
    )
    if source.canonical_bytes() != data:
        raise ValueError(
            "replay source must be canonical"
        )
    gamefile = Path(source.exact_gamefile)
    if (
        gamefile.is_symlink()
        or not gamefile.is_file()
    ):
        raise ValueError(
            "registered exact gamefile invalid"
        )
    if (
        sha256_file(gamefile)
        != source.source_gamefile_sha256
    ):
        raise ValueError(
            "gamefile SHA mismatch"
        )
    return source


def _load_report(
    path: Path,
) -> SourceStateReplayReportV1:
    if path.is_symlink() or not path.is_file():
        raise ValueError(
            "replay report path invalid"
        )
    data = path.read_bytes()
    payload = strict_json_loads(data)
    if not isinstance(payload, dict):
        raise TypeError(
            "replay report must be object"
        )
    report = SourceStateReplayReportV1(
        schema_id=payload["schema_id"],
        schema_version=payload[
            "schema_version"
        ],
        source_fingerprint_sha256=payload[
            "source_fingerprint_sha256"
        ],
        replay_fingerprint_sha256=payload[
            "replay_fingerprint_sha256"
        ],
        transition_count=payload[
            "transition_count"
        ],
        status=payload["status"],
        failure_code=payload["failure_code"],
        report_sha256=payload[
            "report_sha256"
        ],
    )
    if report.canonical_bytes() != data:
        raise ValueError(
            "replay report must be canonical"
        )
    return report


def qualify_case_with_adapter_factory_v1(
    *,
    source,
    adapter_factory,
):
    first = replay_source_decision_state_v1(
        source=source,
        adapter=adapter_factory(source),
    )
    second = replay_source_decision_state_v1(
        source=source,
        adapter=adapter_factory(source),
    )
    expected = (
        source.expected_source_fingerprint
        .fingerprint_sha256
    )
    if any(
        value != expected
        for value in (
            first.source_fingerprint_sha256,
            first.replay_fingerprint_sha256,
            second.source_fingerprint_sha256,
            second.replay_fingerprint_sha256,
        )
    ):
        raise ValueError(
            "independent reconstruction "
            "fingerprint mismatch"
        )
    if (
        first.transition_count
        != len(source.transitions)
        or second.transition_count
        != len(source.transitions)
    ):
        raise ValueError(
            "independent reconstruction "
            "transition count mismatch"
        )
    return first, second


def _audit_existing_case(
    *,
    case: dict[str, object],
    root: Path,
) -> None:
    source = _load_source(
        Path(case["replay_source_path"]),
        case["replay_source_sha256"],
    )
    target = root / case["case_id"]
    if target.is_symlink() or not target.is_dir():
        raise SystemExit(
            "STOP=MISSING_REPLAY_EVIDENCE"
        )

    first = _load_report(
        target / "reconstruction_a.json"
    )
    second = _load_report(
        target / "reconstruction_b.json"
    )
    expected = (
        source.expected_source_fingerprint
        .fingerprint_sha256
    )
    if any(
        value != expected
        for value in (
            first.source_fingerprint_sha256,
            first.replay_fingerprint_sha256,
            second.source_fingerprint_sha256,
            second.replay_fingerprint_sha256,
        )
    ):
        raise SystemExit(
            "STOP=REPLAY_EVIDENCE_FINGERPRINT_MISMATCH"
        )
    if (
        first.transition_count
        != len(source.transitions)
        or second.transition_count
        != len(source.transitions)
    ):
        raise SystemExit(
            "STOP=REPLAY_EVIDENCE_TRANSITION_COUNT_MISMATCH"
        )


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
    parser.add_argument(
        "--execute-environment-only",
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
            "STOP=REPLAY_MANIFEST_PATH_INVALID"
        )

    raw = manifest_path.read_bytes()
    if (
        hashlib.sha256(raw).hexdigest()
        != args.manifest_sha256
    ):
        raise SystemExit(
            "STOP=REPLAY_MANIFEST_SHA_MISMATCH"
        )

    manifest = json.loads(raw)
    _require_manifest_authority_commit(
        manifest
    )
    cases = manifest["cases"]

    if args.audit_existing:
        if args.output_root is None:
            raise SystemExit(
                "STOP=REPLAY_AUDIT_OUTPUT_ROOT_MISSING"
            )
        root = Path(args.output_root)
        if root.is_symlink() or not root.is_dir():
            raise SystemExit(
                "STOP=REPLAY_OUTPUT_ROOT_INVALID"
            )
        for case in cases:
            _audit_existing_case(
                case=case,
                root=root,
            )
        print(
            "SOURCE_STATE_REPLAY_QUALIFICATION_AUDIT_PASS"
        )
        return 0

    if not args.execute_environment_only:
        for case in cases:
            _load_source(
                Path(
                    case["replay_source_path"]
                ),
                case[
                    "replay_source_sha256"
                ],
            )
        print(
            "SOURCE_STATE_REPLAY_QUALIFICATION_MANIFEST_VALID"
        )
        return 0

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
            "STOP=REPLAY_OUTPUT_ROOT_MISSING"
        )
    root = Path(args.output_root)
    if root.is_symlink() or not root.is_dir():
        raise SystemExit(
            "STOP=REPLAY_OUTPUT_ROOT_INVALID"
        )

    for case in cases:
        source = _load_source(
            Path(
                case["replay_source_path"]
            ),
            case["replay_source_sha256"],
        )

        def factory(value):
            return SpawnedAlfworldAdapter.start(
                exact_gamefile=Path(
                    value.exact_gamefile
                ),
                registration_id=case[
                    "registration_id"
                ],
                runtime_manifest_sha256=(
                    value.runtime_manifest_sha256
                ),
            )

        first, second = (
            qualify_case_with_adapter_factory_v1(
                source=source,
                adapter_factory=factory,
            )
        )

        target = root / case["case_id"]
        if target.exists() or target.is_symlink():
            raise FileExistsError(str(target))
        target.mkdir(mode=0o700)
        (
            target / "reconstruction_a.json"
        ).write_bytes(first.canonical_bytes())
        (
            target / "reconstruction_b.json"
        ).write_bytes(second.canonical_bytes())

        _audit_existing_case(
            case=case,
            root=root,
        )

    print(
        "SOURCE_STATE_REPLAY_ENVIRONMENT_ONLY_QUALIFICATION_PASS"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
