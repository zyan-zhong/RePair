#!/usr/bin/env python3
"""Materialize B-DIRECT representation templates from the active snapshot V2.

No policy/model/environment/retrieval execution occurs here.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from transformers import AutoTokenizer

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_file,
    strict_json_loads,
)
from pchsi.memory.dev_snapshot_loader import (
    load_calibrated_dev_snapshot_v2,
)
from pchsi.memory.representation_ablation import (
    build_matched_representation_template_v1,
)
from pchsi.memory.single_cue_failure_summary import (
    build_single_cue_policy_view_v1,
)


class LocalTokenizerCounter:
    def __init__(
        self,
        *,
        tokenizer_id: str,
        tokenizer_revision: str,
        local_path: Path,
    ):
        self.tokenizer_id = tokenizer_id
        self.tokenizer_revision = tokenizer_revision
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


def _write_once(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        view = memoryview(data)
        while view:
            count = os.write(fd, view)
            if count <= 0:
                raise OSError("os.write made no progress")
            view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dependency-binding", required=True)
    parser.add_argument("--token-budget-contract", required=True)
    parser.add_argument("--runtime-binding", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    dependency = strict_json_loads(
        Path(args.dependency_binding).read_bytes()
    )
    if (
        not isinstance(dependency, dict)
        or dependency.get("schema_id")
        != "PACKAGE_B_FAILURE_MEMORY_DEPENDENCY_V1"
    ):
        raise SystemExit("STOP=PACKAGE_B_DEPENDENCY_BINDING_INVALID")

    runtime = strict_json_loads(
        Path(args.runtime_binding).read_bytes()
    )
    if not isinstance(runtime, dict):
        raise SystemExit("STOP=RUNTIME_BINDING_NOT_OBJECT")

    loaded = load_calibrated_dev_snapshot_v2(
        snapshot_directory=Path(
            dependency["active_snapshot_external_directory"]
        ),
        expected_snapshot_sha256=dependency[
            "active_snapshot_sha256"
        ],
        token_budget_contract_path=Path(
            args.token_budget_contract
        ),
        expected_token_budget_contract_sha256=dependency[
            "token_budget_contract_sha256"
        ],
    )

    contract = loaded.token_budget_contract
    if (
        contract.tokenizer_revision
        != runtime["tokenizer_identity_manifest_sha256"]
    ):
        raise SystemExit("STOP=B_DIRECT_TOKENIZER_REVISION_MISMATCH")

    tokenizer = LocalTokenizerCounter(
        tokenizer_id=contract.tokenizer_id,
        tokenizer_revision=contract.tokenizer_revision,
        local_path=Path(runtime["base_model_local_path"]),
    )

    output_root = Path(args.output_root)
    if output_root.exists() or output_root.is_symlink():
        raise SystemExit("STOP=B_DIRECT_OUTPUT_ROOT_EXISTS")
    output_root.mkdir(parents=True)

    template_rows = []
    matched_count = 0

    for member in loaded.members:
        cue = build_single_cue_policy_view_v1(
            fm2=member.fm2,
            fm2_artifact_sha256=sha256_file(
                member.member_directory / "fm2.json"
            ),
            tokenizer=tokenizer,
            hard_ceiling=contract.single_record_hard_ceiling,
        )

        template = build_matched_representation_template_v1(
            snapshot_sha256=loaded.snapshot.snapshot_sha256,
            member=member,
            single_cue=cue,
        )

        target = output_root / (
            member.record.memory_lineage_id
            + ".v"
            + str(member.record.record_version)
        )
        target.mkdir(mode=0o700)

        _write_once(
            target / "single_cue.json",
            cue.canonical_bytes(),
        )
        _write_once(
            target / "representation_template.json",
            template.canonical_bytes(),
        )

        if template.core_matched_ready:
            matched_count += 1

        template_rows.append(
            {
                "memory_lineage_id": (
                    member.record.memory_lineage_id
                ),
                "record_version": (
                    member.record.record_version
                ),
                "template_sha256": template.template_sha256,
                "core_matched_ready": (
                    template.core_matched_ready
                ),
                "fm1_availability": (
                    member.fm1_availability.value
                ),
                "fm2_availability": (
                    member.fm2_availability.value
                ),
                "single_cue_disposition": (
                    cue.build_disposition.value
                ),
            }
        )

    index = {
        "schema_id": "PACKAGE_B_DIRECT_REPRESENTATION_INDEX_V1",
        "schema_version": 1,
        "snapshot_sha256": loaded.snapshot.snapshot_sha256,
        "token_budget_contract_sha256": contract.contract_sha256,
        "record_count": len(loaded.members),
        "core_matched_record_count": matched_count,
        "records": template_rows,
        "b_direct_infrastructure_ready": True,
        "pi1_matched_memory_representation_ablation_ready": (
            matched_count >= 3
        ),
        "scientific_execution_authorized": False,
    }
    _write_once(
        output_root / "representation_index.json",
        canonical_json_bytes(index),
    )

    print("B_DIRECT_RECORD_COUNT=" + str(len(loaded.members)))
    print(
        "B_DIRECT_CORE_MATCHED_RECORD_COUNT="
        + str(matched_count)
    )
    print("B_DIRECT_INFRASTRUCTURE_READY")

    if matched_count >= 3:
        print(
            "PI1_MATCHED_MEMORY_REPRESENTATION_ABLATION_READY"
        )
    else:
        print(
            "PI1_MATCHED_MEMORY_REPRESENTATION_ABLATION_NOT_READY"
        )

    print("SCIENTIFIC_EXECUTION_AUTHORIZED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
