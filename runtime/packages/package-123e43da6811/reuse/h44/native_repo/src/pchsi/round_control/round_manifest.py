from __future__ import annotations

from dataclasses import dataclass

from .common import hashed_payload, require_sha256, require_text
from .role_authority import AuthorityPhaseV1


@dataclass(frozen=True)
class CleanRoundDataPlaneV1:
    train_update_manifest_sha256: str
    train_select_manifest_sha256: str
    train_audit_manifest_sha256: str

    def __post_init__(self) -> None:
        for name, value in (
            ("train_update_manifest_sha256", self.train_update_manifest_sha256),
            ("train_select_manifest_sha256", self.train_select_manifest_sha256),
            ("train_audit_manifest_sha256", self.train_audit_manifest_sha256),
        ):
            require_sha256(name, value)
        if len(
            {
                self.train_update_manifest_sha256,
                self.train_select_manifest_sha256,
                self.train_audit_manifest_sha256,
            }
        ) != 3:
            raise ValueError("clean round data-plane manifests must be distinct")

    def to_dict(self) -> dict[str, str]:
        return {
            "train_update_manifest_sha256": self.train_update_manifest_sha256,
            "train_select_manifest_sha256": self.train_select_manifest_sha256,
            "train_audit_manifest_sha256": self.train_audit_manifest_sha256,
        }


@dataclass(frozen=True)
class GenericRoundManifestV1:
    round_id: str
    parent_policy_id: str
    parent_policy_artifact_sha256: str
    authority_phase: AuthorityPhaseV1
    data_plane: CleanRoundDataPlaneV1
    concrete_binding_registry_sha256: str
    lifecycle_sha256: str
    trace_capture_required: bool
    benchmark_feedback_authorized: bool
    scientific_execution_authorized: bool
    manifest_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "GENERIC_ROUND_MANIFEST_V1",
            "schema_version": 1,
            "round_id": self.round_id,
            "parent_policy_id": self.parent_policy_id,
            "parent_policy_artifact_sha256": self.parent_policy_artifact_sha256,
            "authority_phase": self.authority_phase.value,
            "data_plane": self.data_plane.to_dict(),
            "concrete_binding_registry_sha256": (
                self.concrete_binding_registry_sha256
            ),
            "lifecycle_sha256": self.lifecycle_sha256,
            "trace_capture_required": self.trace_capture_required,
            "benchmark_feedback_authorized": self.benchmark_feedback_authorized,
            "scientific_execution_authorized": self.scientific_execution_authorized,
            "manifest_sha256": self.manifest_sha256,
        }


def freeze_generic_round_manifest(
    *,
    round_id: str,
    parent_policy_id: str,
    parent_policy_artifact_sha256: str,
    authority_phase: AuthorityPhaseV1,
    data_plane: CleanRoundDataPlaneV1,
    concrete_binding_registry_sha256: str,
    lifecycle_sha256: str,
) -> GenericRoundManifestV1:
    require_text("round_id", round_id)
    require_text("parent_policy_id", parent_policy_id)
    require_sha256("parent_policy_artifact_sha256", parent_policy_artifact_sha256)
    require_sha256(
        "concrete_binding_registry_sha256",
        concrete_binding_registry_sha256,
    )
    require_sha256("lifecycle_sha256", lifecycle_sha256)
    if not isinstance(authority_phase, AuthorityPhaseV1):
        raise TypeError("authority_phase must be AuthorityPhaseV1")

    payload = {
        "schema_id": "GENERIC_ROUND_MANIFEST_V1",
        "schema_version": 1,
        "round_id": round_id,
        "parent_policy_id": parent_policy_id,
        "parent_policy_artifact_sha256": parent_policy_artifact_sha256,
        "authority_phase": authority_phase.value,
        "data_plane": data_plane.to_dict(),
        "concrete_binding_registry_sha256": concrete_binding_registry_sha256,
        "lifecycle_sha256": lifecycle_sha256,
        "trace_capture_required": True,
        "benchmark_feedback_authorized": False,
        "scientific_execution_authorized": False,
    }
    hashed = hashed_payload(
        domain="GENERIC_ROUND_MANIFEST_V1",
        hash_field="manifest_sha256",
        payload=payload,
    )
    return GenericRoundManifestV1(
        round_id=round_id,
        parent_policy_id=parent_policy_id,
        parent_policy_artifact_sha256=parent_policy_artifact_sha256,
        authority_phase=authority_phase,
        data_plane=data_plane,
        concrete_binding_registry_sha256=concrete_binding_registry_sha256,
        lifecycle_sha256=lifecycle_sha256,
        trace_capture_required=True,
        benchmark_feedback_authorized=False,
        scientific_execution_authorized=False,
        manifest_sha256=hashed["manifest_sha256"],
    )
