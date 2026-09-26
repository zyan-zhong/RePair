"""Matched representation templates for Failure Memory B-DIRECT."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
    strict_json_loads,
)
from pchsi.memory.dev_snapshot_loader import (
    LoadedDevSnapshotMemberV2,
)
from pchsi.memory.projection_common import (
    ProjectionBuildDispositionV1,
)
from pchsi.memory.single_cue_failure_summary import (
    SingleCuePolicyViewV1,
)


TEMPLATE_SCHEMA_V1 = (
    "FAILURE_MEMORY_MATCHED_REPRESENTATION_TEMPLATE_V1"
)
TEMPLATE_DOMAIN_V1 = (
    "FAILURE_MEMORY_MATCHED_REPRESENTATION_TEMPLATE_ID_V1"
)


@dataclass(frozen=True, slots=True)
class RepresentationArmV1:
    arm_id: str
    availability: str
    reason: str | None
    representation_class: str
    artifact_sha256: str | None
    policy_visible_payload: object | None
    token_count: int
    retrieval_mode: str

    def __post_init__(self) -> None:
        if self.arm_id not in {
            "M0",
            "M1",
            "M2",
            "M3",
            "NEG",
            "D1",
            "D2",
        }:
            raise ValueError("unknown representation arm")
        if self.availability not in {
            "AVAILABLE",
            "UNAVAILABLE",
            "REQUIRES_STATE_GATE",
            "DIAGNOSTIC_NOT_BOUND",
        }:
            raise ValueError("unknown arm availability")
        if (
            self.availability == "AVAILABLE"
            and self.policy_visible_payload is None
            and self.arm_id != "M0"
        ):
            raise ValueError("available Memory arm requires payload")
        if self.arm_id == "M0":
            if (
                self.availability != "AVAILABLE"
                or self.policy_visible_payload != []
                or self.artifact_sha256 is not None
                or self.token_count != 0
            ):
                raise ValueError("M0 must be the common empty Memory slot")
        if type(self.token_count) is not int or self.token_count < 0:
            raise ValueError("arm token_count invalid")
        if not isinstance(self.retrieval_mode, str) or not self.retrieval_mode:
            raise ValueError("retrieval_mode required")

    def to_dict(self) -> dict[str, object]:
        return {
            "arm_id": self.arm_id,
            "availability": self.availability,
            "reason": self.reason,
            "representation_class": self.representation_class,
            "artifact_sha256": self.artifact_sha256,
            "policy_visible_payload": self.policy_visible_payload,
            "token_count": self.token_count,
            "retrieval_mode": self.retrieval_mode,
        }


@dataclass(frozen=True, slots=True)
class MatchedRepresentationTemplateV1:
    schema_id: str
    schema_version: int
    snapshot_sha256: str
    memory_lineage_id: str
    record_version: int
    arms: tuple[RepresentationArmV1, ...]
    core_matched_ready: bool
    template_sha256: str | None = None

    _ARM_ORDER: ClassVar[tuple[str, ...]] = (
        "M0",
        "M1",
        "M2",
        "M3",
        "NEG",
        "D1",
        "D2",
    )

    def __post_init__(self) -> None:
        if self.schema_id != TEMPLATE_SCHEMA_V1 or self.schema_version != 1:
            raise ValueError("representation template schema mismatch")
        if type(self.arms) is not tuple or len(self.arms) != 7:
            raise ValueError("representation template requires seven arm slots")
        if tuple(item.arm_id for item in self.arms) != self._ARM_ORDER:
            raise ValueError("representation arm order mismatch")
        expected_ready = all(
            next(
                arm
                for arm in self.arms
                if arm.arm_id == arm_id
            ).availability
            == "AVAILABLE"
            for arm_id in ("M1", "M2", "M3")
        )
        if self.core_matched_ready is not expected_ready:
            raise ValueError("core_matched_ready mismatch")

        expected = sha256_bytes(
            TEMPLATE_DOMAIN_V1.encode("utf-8")
            + b"\0"
            + canonical_json_bytes(
                self._payload_without_sha()
            )
        )
        if self.template_sha256 is None:
            object.__setattr__(
                self,
                "template_sha256",
                expected,
            )
        elif self.template_sha256 != expected:
            raise ValueError("representation template SHA mismatch")

    def _payload_without_sha(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "snapshot_sha256": self.snapshot_sha256,
            "memory_lineage_id": self.memory_lineage_id,
            "record_version": self.record_version,
            "arms": [
                item.to_dict()
                for item in self.arms
            ],
            "core_matched_ready": self.core_matched_ready,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._payload_without_sha(),
            "template_sha256": self.template_sha256,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())


def _available_arm(
    *,
    arm_id: str,
    representation_class: str,
    artifact_sha256: str,
    payload: object,
    token_count: int,
) -> RepresentationArmV1:
    return RepresentationArmV1(
        arm_id=arm_id,
        availability="AVAILABLE",
        reason=None,
        representation_class=representation_class,
        artifact_sha256=artifact_sha256,
        policy_visible_payload=payload,
        token_count=token_count,
        retrieval_mode="DIRECT_FIXED_RECORD_NO_RETRIEVAL",
    )


def _unavailable(
    *,
    arm_id: str,
    representation_class: str,
    reason: str,
    availability: str = "UNAVAILABLE",
) -> RepresentationArmV1:
    return RepresentationArmV1(
        arm_id=arm_id,
        availability=availability,
        reason=reason,
        representation_class=representation_class,
        artifact_sha256=None,
        policy_visible_payload=None,
        token_count=0,
        retrieval_mode="DIRECT_FIXED_RECORD_NO_RETRIEVAL",
    )


def build_matched_representation_template_v1(
    *,
    snapshot_sha256: str,
    member: LoadedDevSnapshotMemberV2,
    single_cue: SingleCuePolicyViewV1,
) -> MatchedRepresentationTemplateV1:
    record = member.record
    binding = member.fm2.record_binding

    if (
        single_cue.record_binding != binding
        or member.fm1.record_binding != binding
    ):
        raise ValueError(
            "M1/M2/M3 must bind the same exact record lineage/version"
        )

    m0 = RepresentationArmV1(
        arm_id="M0",
        availability="AVAILABLE",
        reason=None,
        representation_class="M0",
        artifact_sha256=None,
        policy_visible_payload=[],
        token_count=0,
        retrieval_mode="DIRECT_FIXED_RECORD_NO_RETRIEVAL",
    )

    if (
        member.fm1.build_disposition
        is ProjectionBuildDispositionV1.ELIGIBLE
        and member.fm1.policy_visible_payload is not None
        and member.fm1.token_count is not None
    ):
        m1 = _available_arm(
            arm_id="M1",
            representation_class="FM1",
            artifact_sha256=sha256_file(
                member.member_directory / "fm1.json"
            ),
            payload=(
                member.fm1.policy_visible_payload.to_dict()
            ),
            token_count=(
                member.fm1.token_count.policy_visible_token_count
            ),
        )
    else:
        m1 = _unavailable(
            arm_id="M1",
            representation_class="FM1",
            reason=member.fm1.build_disposition.value,
        )

    if (
        single_cue.build_disposition
        is ProjectionBuildDispositionV1.ELIGIBLE
        and single_cue.policy_visible_payload() is not None
        and single_cue.token_count is not None
    ):
        m2 = _available_arm(
            arm_id="M2",
            representation_class="SINGLE_CUE",
            artifact_sha256=sha256_bytes(
                single_cue.canonical_bytes()
            ),
            payload=single_cue.policy_visible_payload(),
            token_count=(
                single_cue.token_count.policy_visible_token_count
            ),
        )
    else:
        m2 = _unavailable(
            arm_id="M2",
            representation_class="SINGLE_CUE",
            reason=single_cue.build_disposition.value,
        )

    if (
        member.fm2.build_disposition
        is ProjectionBuildDispositionV1.ELIGIBLE
        and member.fm2.policy_visible_payload is not None
        and member.fm2.token_count is not None
    ):
        m3 = _available_arm(
            arm_id="M3",
            representation_class="FM2",
            artifact_sha256=sha256_file(
                member.member_directory / "fm2.json"
            ),
            payload=member.fm2.policy_visible_payload.to_dict(),
            token_count=(
                member.fm2.token_count.policy_visible_token_count
            ),
        )
    else:
        m3 = _unavailable(
            arm_id="M3",
            representation_class="FM2",
            reason=member.fm2.build_disposition.value,
        )

    if (
        member.fm2.policy_visible_payload is not None
        and member.fm2.policy_visible_payload.non_applicability_cues
    ):
        neg = _unavailable(
            arm_id="NEG",
            representation_class="FM2",
            reason=(
                "REGISTERED_NON_APPLICABILITY_EXISTS_BUT_CURRENT_STATE_"
                "MUST_PASS_B6_BEFORE_FORCED_EXPOSURE"
            ),
            availability="REQUIRES_STATE_GATE",
        )
    else:
        neg = _unavailable(
            arm_id="NEG",
            representation_class="FM2",
            reason="NO_REGISTERED_NON_APPLICABILITY_CUE",
        )

    d1 = _unavailable(
        arm_id="D1",
        representation_class="LONGER_HISTORY_DIAGNOSTIC",
        reason="DIAGNOSTIC_REQUIRES_SEPARATE_SOURCE_STATE_BINDING",
        availability="DIAGNOSTIC_NOT_BOUND",
    )
    d2 = _unavailable(
        arm_id="D2",
        representation_class="RANDOM_FM2_SECONDARY_STRESS",
        reason="SECONDARY_STRESS_CONTROL_NOT_SELECTED",
        availability="DIAGNOSTIC_NOT_BOUND",
    )

    arms = (
        m0,
        m1,
        m2,
        m3,
        neg,
        d1,
        d2,
    )

    return MatchedRepresentationTemplateV1(
        schema_id=TEMPLATE_SCHEMA_V1,
        schema_version=1,
        snapshot_sha256=snapshot_sha256,
        memory_lineage_id=record.memory_lineage_id,
        record_version=record.record_version,
        arms=arms,
        core_matched_ready=all(
            arm.availability == "AVAILABLE"
            for arm in (m1, m2, m3)
        ),
        template_sha256=None,
    )
