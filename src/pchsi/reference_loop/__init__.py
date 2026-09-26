"""Reference-loop evidence foundation implementation."""
from .bundle_reader import validate_attempt_bundle
from .discovery import discover_reference_loop_inputs
from .identity import (
    Pi1IdentitySourceRegistrationV1,
    build_registration_payload,
    load_pi1_reference_identity,
    materialize_pi1_reference_identity,
)
from .mechanical import extract_mechanical_episode_evidence
from .paired import extract_mechanical_paired_evidence
from .rebinding import build_trajectory_rebinding_manifest
from .task_access import (
    find_access_row,
    load_task_access_revalidation,
    revalidate_task_access,
)

__all__ = [
    "Pi1IdentitySourceRegistrationV1",
    "build_registration_payload",
    "build_trajectory_rebinding_manifest",
    "discover_reference_loop_inputs",
    "extract_mechanical_episode_evidence",
    "extract_mechanical_paired_evidence",
    "find_access_row",
    "load_pi1_reference_identity",
    "load_task_access_revalidation",
    "materialize_pi1_reference_identity",
    "revalidate_task_access",
    "validate_attempt_bundle",
]
