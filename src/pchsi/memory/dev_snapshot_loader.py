"""Strict loader for calibrated immutable Failure Memory DEV snapshots."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from pchsi.memory.dev_descriptive_snapshot_v2 import (
    MemoryDevDescriptiveSnapshotV2,
    audit_calibrated_snapshot_v2,
)
from pchsi.memory.matched_raw_view import (
    FM1MatchedRawEpisodicViewV1,
)
from pchsi.memory.policy_projection import (
    FailureMemoryPolicyProjectionV1,
)
from pchsi.memory.procedural_builder import (
    ProceduralFailureMemoryRecordV1,
)
from pchsi.memory.projection_common import (
    ProjectionBuildDispositionV1,
)
from pchsi.memory.retrieval_key import (
    MemoryRetrievalKeyV1,
)
from pchsi.memory.token_budget_contract import (
    FailureMemoryTokenBudgetContractV1,
)


class FM1AvailabilityV1(str, Enum):
    FM1_ELIGIBLE = "FM1_ELIGIBLE"
    FM1_UNAVAILABLE_TOKEN_BUDGET = (
        "FM1_UNAVAILABLE_TOKEN_BUDGET"
    )
    FM1_UNAVAILABLE_OTHER = "FM1_UNAVAILABLE_OTHER"


class FM2AvailabilityV1(str, Enum):
    FM2_ELIGIBLE = "FM2_ELIGIBLE"
    FM2_UNAVAILABLE = "FM2_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class LoadedDevSnapshotMemberV2:
    record: ProceduralFailureMemoryRecordV1
    retrieval_key: MemoryRetrievalKeyV1
    fm1: FM1MatchedRawEpisodicViewV1
    fm2: FailureMemoryPolicyProjectionV1
    fm1_availability: FM1AvailabilityV1
    fm2_availability: FM2AvailabilityV1
    member_directory: Path


@dataclass(frozen=True, slots=True)
class LoadedDevSnapshotV2:
    snapshot: MemoryDevDescriptiveSnapshotV2
    token_budget_contract: FailureMemoryTokenBudgetContractV1
    members: tuple[LoadedDevSnapshotMemberV2, ...]
    snapshot_directory: Path


def _fm1_availability(
    fm1: FM1MatchedRawEpisodicViewV1,
) -> FM1AvailabilityV1:
    if (
        fm1.build_disposition
        is ProjectionBuildDispositionV1.ELIGIBLE
    ):
        return FM1AvailabilityV1.FM1_ELIGIBLE
    if (
        fm1.build_disposition
        is ProjectionBuildDispositionV1
        .PROJECTION_INELIGIBLE_TOKEN_BUDGET
    ):
        return (
            FM1AvailabilityV1
            .FM1_UNAVAILABLE_TOKEN_BUDGET
        )
    return FM1AvailabilityV1.FM1_UNAVAILABLE_OTHER


def _fm2_availability(
    fm2: FailureMemoryPolicyProjectionV1,
) -> FM2AvailabilityV1:
    if (
        fm2.build_disposition
        is ProjectionBuildDispositionV1.ELIGIBLE
    ):
        return FM2AvailabilityV1.FM2_ELIGIBLE
    return FM2AvailabilityV1.FM2_UNAVAILABLE


def load_calibrated_dev_snapshot_v2(
    *,
    snapshot_directory: Path,
    expected_snapshot_sha256: str,
    token_budget_contract_path: Path,
    expected_token_budget_contract_sha256: str,
) -> LoadedDevSnapshotV2:
    snapshot_directory = Path(snapshot_directory)
    if (
        snapshot_directory.is_symlink()
        or snapshot_directory.name == "latest"
    ):
        raise ValueError(
            "snapshot loader forbids symlink/latest"
        )

    contract_path = Path(
        token_budget_contract_path
    )
    if contract_path.is_symlink() or not contract_path.is_file():
        raise ValueError("token-budget contract path invalid")
    contract = FailureMemoryTokenBudgetContractV1.from_json(
        contract_path.read_bytes()
    )
    if (
        contract.contract_sha256
        != expected_token_budget_contract_sha256
    ):
        raise ValueError("token-budget contract SHA mismatch")

    snapshot = audit_calibrated_snapshot_v2(
        snapshot_directory=snapshot_directory,
        expected_snapshot_sha256=expected_snapshot_sha256,
    )

    if (
        snapshot.token_budget_contract_sha256
        != contract.contract_sha256
    ):
        raise ValueError("snapshot/contract binding mismatch")
    if (
        snapshot.single_record_hard_ceiling
        != contract.single_record_hard_ceiling
        or snapshot.library_total_hard_ceiling
        != contract.library_total_hard_ceiling
        or snapshot.max_record_count
        != contract.max_record_count
    ):
        raise ValueError("snapshot token-budget fields mismatch")

    members = []
    for member in snapshot.members:
        root = snapshot_directory / member.relative_directory
        record = ProceduralFailureMemoryRecordV1.from_json(
            (root / "governed_record.json").read_bytes()
        )
        key = MemoryRetrievalKeyV1.from_json(
            (root / "retrieval_key.json").read_bytes()
        )
        fm1 = FM1MatchedRawEpisodicViewV1.from_json(
            (root / "fm1.json").read_bytes()
        )
        fm2 = FailureMemoryPolicyProjectionV1.from_json(
            (root / "fm2.json").read_bytes()
        )

        members.append(
            LoadedDevSnapshotMemberV2(
                record=record,
                retrieval_key=key,
                fm1=fm1,
                fm2=fm2,
                fm1_availability=(
                    _fm1_availability(fm1)
                ),
                fm2_availability=(
                    _fm2_availability(fm2)
                ),
                member_directory=root,
            )
        )

    return LoadedDevSnapshotV2(
        snapshot=snapshot,
        token_budget_contract=contract,
        members=tuple(members),
        snapshot_directory=snapshot_directory,
    )
