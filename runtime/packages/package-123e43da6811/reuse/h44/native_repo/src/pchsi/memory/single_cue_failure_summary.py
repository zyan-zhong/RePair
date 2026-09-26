"""Canonical single-cue Failure Memory Policy view for B-DIRECT."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    require_lower_sha256,
    sha256_bytes,
    strict_json_loads,
)
from pchsi.memory.policy_projection import (
    FailureMemoryPolicyProjectionV1,
)
from pchsi.memory.policy_view_safety import (
    PolicyViewSafetyReportV1,
    audit_policy_visible_payload_v1,
)
from pchsi.memory.projection_common import (
    PolicyTokenizerCounterV1,
    ProjectionBuildDispositionV1,
    ProjectionClassV1,
    ProjectionRecordBindingV1,
    ProjectionTokenCountV1,
    count_policy_visible_tokens_v1,
)


SCHEMA_ID = "SINGLE_CUE_POLICY_VIEW_V1"
DOMAIN = "SINGLE_CUE_POLICY_VIEW_ID_V1"


@dataclass(frozen=True, slots=True)
class SingleCuePolicyViewV1:
    schema_id: str
    schema_version: int
    record_binding: ProjectionRecordBindingV1
    source_fm2_artifact_sha256: str
    source_fm2_payload_sha256: str | None
    failure_pattern_index: int
    cue_text: str | None
    policy_visible_payload_sha256: str | None
    token_count: ProjectionTokenCountV1 | None
    safety_report: PolicyViewSafetyReportV1 | None
    build_disposition: ProjectionBuildDispositionV1
    canonical_sha256: str | None = None

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_id",
            "schema_version",
            "record_binding",
            "source_fm2_artifact_sha256",
            "source_fm2_payload_sha256",
            "failure_pattern_index",
            "cue_text",
            "policy_visible_payload_sha256",
            "token_count",
            "safety_report",
            "build_disposition",
            "canonical_sha256",
        }
    )

    def __post_init__(self) -> None:
        if self.schema_id != SCHEMA_ID or self.schema_version != 1:
            raise ValueError("single-cue schema mismatch")
        if not isinstance(
            self.record_binding,
            ProjectionRecordBindingV1,
        ):
            raise TypeError("single-cue record binding type mismatch")
        require_lower_sha256(
            "source_fm2_artifact_sha256",
            self.source_fm2_artifact_sha256,
        )
        if self.source_fm2_payload_sha256 is not None:
            require_lower_sha256(
                "source_fm2_payload_sha256",
                self.source_fm2_payload_sha256,
            )
        if self.failure_pattern_index != 0:
            raise ValueError("single-cue failure_pattern_index must equal 0")
        if self.cue_text is not None and (
            not isinstance(self.cue_text, str)
            or not self.cue_text
        ):
            raise ValueError("cue_text must be nonempty str or None")
        if self.policy_visible_payload_sha256 is not None:
            require_lower_sha256(
                "policy_visible_payload_sha256",
                self.policy_visible_payload_sha256,
            )
        if self.token_count is not None and not isinstance(
            self.token_count,
            ProjectionTokenCountV1,
        ):
            raise TypeError("single-cue token_count type mismatch")
        if self.safety_report is not None:
            if not isinstance(
                self.safety_report,
                PolicyViewSafetyReportV1,
            ):
                raise TypeError("single-cue safety report type mismatch")
            if (
                self.safety_report.projection_class
                is not ProjectionClassV1.FM2
            ):
                raise ValueError("single-cue safety class must be FM2")

        if (
            self.build_disposition
            is ProjectionBuildDispositionV1.ELIGIBLE
        ):
            if any(
                value is None
                for value in (
                    self.source_fm2_payload_sha256,
                    self.cue_text,
                    self.policy_visible_payload_sha256,
                    self.token_count,
                    self.safety_report,
                )
            ):
                raise ValueError("eligible single-cue view lacks evidence")
            if (
                self.token_count.policy_visible_token_count
                > self.token_count.hard_ceiling
            ):
                raise ValueError("eligible single-cue exceeds ceiling")
            if (
                self.safety_report.static_status != "PASS"
                or self.safety_report.critical_safety_failure
                or self.safety_report.static_failure_codes
            ):
                raise ValueError("eligible single-cue requires safe PASS")
            payload = {
                "failure_cue": self.cue_text,
            }
            recomputed = audit_policy_visible_payload_v1(
                projection_class=ProjectionClassV1.FM2,
                policy_visible_payload=payload,
                has_nonempty_recovery=False,
            )
            if (
                recomputed.projection_sha256
                != self.policy_visible_payload_sha256
                or recomputed != self.safety_report
            ):
                raise ValueError("single-cue safety/payload binding mismatch")

        expected = sha256_bytes(
            DOMAIN.encode("utf-8")
            + b"\0"
            + canonical_json_bytes(
                self._payload_without_sha()
            )
        )
        if self.canonical_sha256 is None:
            object.__setattr__(
                self,
                "canonical_sha256",
                expected,
            )
        elif self.canonical_sha256 != expected:
            raise ValueError("single-cue canonical SHA mismatch")

    def _payload_without_sha(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "record_binding": self.record_binding.to_dict(),
            "source_fm2_artifact_sha256": (
                self.source_fm2_artifact_sha256
            ),
            "source_fm2_payload_sha256": (
                self.source_fm2_payload_sha256
            ),
            "failure_pattern_index": self.failure_pattern_index,
            "cue_text": self.cue_text,
            "policy_visible_payload_sha256": (
                self.policy_visible_payload_sha256
            ),
            "token_count": (
                None
                if self.token_count is None
                else self.token_count.to_dict()
            ),
            "safety_report": (
                None
                if self.safety_report is None
                else self.safety_report.to_dict()
            ),
            "build_disposition": self.build_disposition.value,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._payload_without_sha(),
            "canonical_sha256": self.canonical_sha256,
        }

    def policy_visible_payload(self) -> dict[str, object] | None:
        if (
            self.build_disposition
            is not ProjectionBuildDispositionV1.ELIGIBLE
        ):
            return None
        return {
            "failure_cue": self.cue_text,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "SingleCuePolicyViewV1":
        if not isinstance(value, dict) or frozenset(value) != cls._KEYS:
            raise ValueError("single-cue fields mismatch")
        return cls(
            schema_id=value["schema_id"],
            schema_version=value["schema_version"],
            record_binding=ProjectionRecordBindingV1.from_dict(
                value["record_binding"]
            ),
            source_fm2_artifact_sha256=value[
                "source_fm2_artifact_sha256"
            ],
            source_fm2_payload_sha256=value[
                "source_fm2_payload_sha256"
            ],
            failure_pattern_index=value[
                "failure_pattern_index"
            ],
            cue_text=value["cue_text"],
            policy_visible_payload_sha256=value[
                "policy_visible_payload_sha256"
            ],
            token_count=(
                None
                if value["token_count"] is None
                else ProjectionTokenCountV1.from_dict(
                    value["token_count"]
                )
            ),
            safety_report=(
                None
                if value["safety_report"] is None
                else PolicyViewSafetyReportV1.from_dict(
                    value["safety_report"]
                )
            ),
            build_disposition=ProjectionBuildDispositionV1(
                value["build_disposition"]
            ),
            canonical_sha256=value["canonical_sha256"],
        )

    @classmethod
    def from_json(
        cls,
        value: str | bytes,
    ) -> "SingleCuePolicyViewV1":
        return cls.from_dict(strict_json_loads(value))


def build_single_cue_policy_view_v1(
    *,
    fm2: FailureMemoryPolicyProjectionV1,
    fm2_artifact_sha256: str,
    tokenizer: PolicyTokenizerCounterV1,
    hard_ceiling: int,
) -> SingleCuePolicyViewV1:
    require_lower_sha256(
        "fm2_artifact_sha256",
        fm2_artifact_sha256,
    )

    if (
        fm2.projection_class
        is not ProjectionClassV1.FM2
        or fm2.build_disposition
        is not ProjectionBuildDispositionV1.ELIGIBLE
        or fm2.policy_visible_payload is None
        or fm2.policy_visible_payload_sha256 is None
    ):
        return SingleCuePolicyViewV1(
            schema_id=SCHEMA_ID,
            schema_version=1,
            record_binding=fm2.record_binding,
            source_fm2_artifact_sha256=fm2_artifact_sha256,
            source_fm2_payload_sha256=(
                fm2.policy_visible_payload_sha256
            ),
            failure_pattern_index=0,
            cue_text=None,
            policy_visible_payload_sha256=None,
            token_count=None,
            safety_report=None,
            build_disposition=(
                ProjectionBuildDispositionV1
                .PROJECTION_INELIGIBLE_DESCRIPTIVE_ELIGIBILITY
            ),
            canonical_sha256=None,
        )

    if not fm2.policy_visible_payload.failure_pattern:
        return SingleCuePolicyViewV1(
            schema_id=SCHEMA_ID,
            schema_version=1,
            record_binding=fm2.record_binding,
            source_fm2_artifact_sha256=fm2_artifact_sha256,
            source_fm2_payload_sha256=(
                fm2.policy_visible_payload_sha256
            ),
            failure_pattern_index=0,
            cue_text=None,
            policy_visible_payload_sha256=None,
            token_count=None,
            safety_report=None,
            build_disposition=(
                ProjectionBuildDispositionV1
                .PROJECTION_INELIGIBLE_DESCRIPTIVE_ELIGIBILITY
            ),
            canonical_sha256=None,
        )

    cue = fm2.policy_visible_payload.failure_pattern[0].text
    payload = {
        "failure_cue": cue,
    }
    report = audit_policy_visible_payload_v1(
        projection_class=ProjectionClassV1.FM2,
        policy_visible_payload=payload,
        has_nonempty_recovery=False,
    )
    if report.static_status == "FAIL":
        return SingleCuePolicyViewV1(
            schema_id=SCHEMA_ID,
            schema_version=1,
            record_binding=fm2.record_binding,
            source_fm2_artifact_sha256=fm2_artifact_sha256,
            source_fm2_payload_sha256=(
                fm2.policy_visible_payload_sha256
            ),
            failure_pattern_index=0,
            cue_text=None,
            policy_visible_payload_sha256=None,
            token_count=None,
            safety_report=report,
            build_disposition=(
                ProjectionBuildDispositionV1
                .PROJECTION_INELIGIBLE_POLICY_VIEW_SAFETY
            ),
            canonical_sha256=None,
        )

    count = count_policy_visible_tokens_v1(
        policy_visible_payload=payload,
        tokenizer=tokenizer,
        hard_ceiling=hard_ceiling,
    )
    if count.policy_visible_token_count > hard_ceiling:
        return SingleCuePolicyViewV1(
            schema_id=SCHEMA_ID,
            schema_version=1,
            record_binding=fm2.record_binding,
            source_fm2_artifact_sha256=fm2_artifact_sha256,
            source_fm2_payload_sha256=(
                fm2.policy_visible_payload_sha256
            ),
            failure_pattern_index=0,
            cue_text=None,
            policy_visible_payload_sha256=None,
            token_count=count,
            safety_report=report,
            build_disposition=(
                ProjectionBuildDispositionV1
                .PROJECTION_INELIGIBLE_TOKEN_BUDGET
            ),
            canonical_sha256=None,
        )

    return SingleCuePolicyViewV1(
        schema_id=SCHEMA_ID,
        schema_version=1,
        record_binding=fm2.record_binding,
        source_fm2_artifact_sha256=fm2_artifact_sha256,
        source_fm2_payload_sha256=(
            fm2.policy_visible_payload_sha256
        ),
        failure_pattern_index=0,
        cue_text=cue,
        policy_visible_payload_sha256=(
            report.projection_sha256
        ),
        token_count=count,
        safety_report=report,
        build_disposition=ProjectionBuildDispositionV1.ELIGIBLE,
        canonical_sha256=None,
    )
