#!/usr/bin/env python3
"""Rebuild active calibrated DEV snapshot V2 from immutable Package-A records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from transformers import AutoTokenizer

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
    strict_json_loads,
)
from pchsi.memory.dev_descriptive_snapshot_v2 import (
    audit_calibrated_snapshot_v2,
    build_calibrated_snapshot_v2,
    publish_calibrated_snapshot_v2,
)
from pchsi.memory.matched_raw_view import (
    build_fm1_matched_raw_episodic_view_v1,
)
from pchsi.memory.policy_projection import (
    build_failure_memory_policy_projection_v1,
)
from pchsi.memory.procedural_builder import (
    ProceduralFailureMemoryRecordV1,
)
from pchsi.memory.projection_common import (
    ProjectionBuildDispositionV1,
    ProjectionClassV1,
)
from pchsi.memory.retrieval_key import (
    MemoryRetrievalKeyV1,
)
from pchsi.memory.sequence_failure_experience import (
    SequenceFailureExperienceV1,
)
from pchsi.memory.token_budget_contract import (
    FailureMemoryTokenBudgetContractV1,
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


def _load_canonical(
    path: Path,
    parser,
    expected_sha: str | None = None,
):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"invalid canonical input: {path}")
    raw = path.read_bytes()
    if expected_sha is not None and sha256_bytes(raw) != expected_sha:
        raise ValueError(f"SHA mismatch: {path}")
    value = parser(raw)
    if value.canonical_bytes() != raw:
        raise ValueError(f"non-canonical input: {path}")
    return value, raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--materialization-manifest", required=True)
    parser.add_argument("--candidate-root", required=True)
    parser.add_argument("--token-budget-contract", required=True)
    parser.add_argument("--runtime-binding", required=True)
    parser.add_argument("--historical-snapshot-sha256", required=True)
    parser.add_argument("--package-a-sealed-head", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    contract, contract_raw = _load_canonical(
        Path(args.token_budget_contract),
        FailureMemoryTokenBudgetContractV1.from_json,
    )

    manifest_path = Path(args.materialization_manifest)
    manifest_raw = manifest_path.read_bytes()
    manifest = strict_json_loads(manifest_raw)
    if not isinstance(manifest, dict):
        raise SystemExit("STOP=MATERIALIZATION_MANIFEST_NOT_OBJECT")
    items = manifest.get("items")
    if not isinstance(items, list) or len(items) != 3:
        raise SystemExit("STOP=EXPECTED_THREE_PACKAGE_A_MATERIALIZATION_ITEMS")

    runtime = strict_json_loads(
        Path(args.runtime_binding).read_bytes()
    )
    if not isinstance(runtime, dict):
        raise SystemExit("STOP=RUNTIME_BINDING_NOT_OBJECT")
    if (
        contract.tokenizer_revision
        != runtime["tokenizer_identity_manifest_sha256"]
    ):
        raise SystemExit("STOP=TOKENIZER_REVISION_CONTRACT_RUNTIME_MISMATCH")

    tokenizer = LocalTokenizerCounter(
        tokenizer_id=contract.tokenizer_id,
        tokenizer_revision=contract.tokenizer_revision,
        local_path=Path(runtime["base_model_local_path"]),
    )

    candidate_root = Path(args.candidate_root)
    if candidate_root.is_symlink() or not candidate_root.is_dir():
        raise SystemExit("STOP=PACKAGE_A_CANDIDATE_ROOT_INVALID")

    member_artifacts = []
    fm1_eligible = 0
    fm1_token_ineligible = 0
    fm2_eligible = 0

    for item in items:
        candidate_id = item["candidate_id"]
        candidate_dir = candidate_root / candidate_id
        if candidate_dir.is_symlink() or not candidate_dir.is_dir():
            raise SystemExit(
                "STOP=PACKAGE_A_CANDIDATE_DIRECTORY_MISSING:"
                + candidate_id
            )

        record, record_bytes = _load_canonical(
            candidate_dir / "governed_record.json",
            ProceduralFailureMemoryRecordV1.from_json,
        )
        key, key_bytes = _load_canonical(
            candidate_dir / "retrieval_key.json",
            MemoryRetrievalKeyV1.from_json,
        )

        paths = item["source_experience_paths"]
        shas = item["source_experience_sha256s"]
        if (
            not isinstance(paths, list)
            or not isinstance(shas, list)
            or len(paths) != 1
            or len(shas) != 1
        ):
            raise SystemExit(
                "STOP=ACTIVE_SNAPSHOT_REQUIRES_ONE_SOURCE_EXPERIENCE:"
                + candidate_id
            )

        experience, _ = _load_canonical(
            Path(paths[0]),
            SequenceFailureExperienceV1.from_json,
            shas[0],
        )

        fm1 = build_fm1_matched_raw_episodic_view_v1(
            record=record,
            experience=experience,
            tokenizer=tokenizer,
            hard_ceiling=contract.single_record_hard_ceiling,
        )
        fm2 = build_failure_memory_policy_projection_v1(
            record=record,
            projection_class=ProjectionClassV1.FM2,
            tokenizer=tokenizer,
            hard_ceiling=contract.single_record_hard_ceiling,
        )

        if (
            fm1.build_disposition
            is ProjectionBuildDispositionV1.ELIGIBLE
        ):
            fm1_eligible += 1
        elif (
            fm1.build_disposition
            is ProjectionBuildDispositionV1
            .PROJECTION_INELIGIBLE_TOKEN_BUDGET
        ):
            fm1_token_ineligible += 1
        else:
            raise SystemExit(
                "STOP=ACTIVE_SNAPSHOT_FM1_BLOCKING_DISPOSITION:"
                + candidate_id
                + ":"
                + fm1.build_disposition.value
            )

        if (
            fm2.build_disposition
            is not ProjectionBuildDispositionV1.ELIGIBLE
        ):
            raise SystemExit(
                "STOP=ACTIVE_SNAPSHOT_FM2_NOT_ELIGIBLE:"
                + candidate_id
                + ":"
                + fm2.build_disposition.value
            )
        fm2_eligible += 1

        # The retrieval key and rebuilt projections must bind the same record.
        for binding in (
            key.record_binding,
            fm1.record_binding,
            fm2.record_binding,
        ):
            if (
                binding.memory_lineage_id
                != record.memory_lineage_id
                or binding.record_version
                != record.record_version
                or binding.canonical_record_sha256
                != record.canonical_record_sha256
            ):
                raise SystemExit(
                    "STOP=ACTIVE_SNAPSHOT_RECORD_BINDING_MISMATCH:"
                    + candidate_id
                )

        member_artifacts.append(
            (
                record_bytes,
                key_bytes,
                fm1.canonical_bytes(),
                fm2.canonical_bytes(),
            )
        )

    snapshot, files = build_calibrated_snapshot_v2(
        package_a_sealed_head=args.package_a_sealed_head,
        historical_package_a_snapshot_sha256=(
            args.historical_snapshot_sha256
        ),
        token_budget_contract=contract,
        source_materialization_manifest_sha256=sha256_bytes(
            manifest_raw
        ),
        member_artifacts=tuple(member_artifacts),
    )

    output_root = Path(args.output_root)
    if output_root.is_symlink():
        raise SystemExit("STOP=ACTIVE_SNAPSHOT_OUTPUT_SYMLINK")
    output_root.mkdir(parents=True, exist_ok=True)

    final = output_root / snapshot.snapshot_sha256
    if final.exists():
        rebuilt = audit_calibrated_snapshot_v2(
            snapshot_directory=final,
            expected_snapshot_sha256=snapshot.snapshot_sha256,
        )
        if rebuilt != snapshot:
            raise SystemExit("STOP=EXISTING_ACTIVE_SNAPSHOT_MISMATCH")
    else:
        final = publish_calibrated_snapshot_v2(
            output_root=output_root,
            snapshot=snapshot,
            member_files=files,
        )

    receipt = {
        "schema_id": "FAILURE_MEMORY_CALIBRATED_SNAPSHOT_V2_RECEIPT",
        "schema_version": 2,
        "snapshot_sha256": snapshot.snapshot_sha256,
        "snapshot_directory": str(final),
        "historical_package_a_snapshot_sha256": (
            args.historical_snapshot_sha256
        ),
        "token_budget_contract_sha256": (
            contract.contract_sha256
        ),
        "single_record_hard_ceiling": (
            contract.single_record_hard_ceiling
        ),
        "library_total_hard_ceiling": (
            contract.library_total_hard_ceiling
        ),
        "member_count": len(snapshot.members),
        "fm1_eligible_count": fm1_eligible,
        "fm1_token_ineligible_count": fm1_token_ineligible,
        "fm2_eligible_count": fm2_eligible,
        "effect_authority": "UNTESTED",
        "previous_package_a_exposure": (
            "NOT_EXPOSED_PACKAGE_A"
        ),
        "memory_on_execution_used": False,
    }
    receipt_path = output_root / (
        "active_snapshot_receipt_"
        + snapshot.snapshot_sha256
        + ".json"
    )
    receipt_bytes = canonical_json_bytes(receipt)
    if receipt_path.exists():
        if receipt_path.read_bytes() != receipt_bytes:
            raise SystemExit("STOP=ACTIVE_SNAPSHOT_RECEIPT_MISMATCH")
    else:
        receipt_path.write_bytes(receipt_bytes)

    print(
        "ACTIVE_DEV_SNAPSHOT_V2_SHA256="
        + snapshot.snapshot_sha256
    )
    print(
        "ACTIVE_DEV_SNAPSHOT_V2_FM1_ELIGIBLE_COUNT="
        + str(fm1_eligible)
    )
    print(
        "ACTIVE_DEV_SNAPSHOT_V2_FM1_TOKEN_INELIGIBLE_COUNT="
        + str(fm1_token_ineligible)
    )
    print("ACTIVE_DEV_SNAPSHOT_V2_FM2_ELIGIBLE_COUNT=3")
    print(
        "ACTIVE_DEV_SNAPSHOT_V2_SINGLE_RECORD_HARD_CEILING="
        + str(contract.single_record_hard_ceiling)
    )
    print(
        "ACTIVE_DEV_SNAPSHOT_V2_LIBRARY_TOTAL_HARD_CEILING="
        + str(contract.library_total_hard_ceiling)
    )
    print("ACTIVE_DEV_SNAPSHOT_V2_PUBLISHED_AND_AUDITED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
