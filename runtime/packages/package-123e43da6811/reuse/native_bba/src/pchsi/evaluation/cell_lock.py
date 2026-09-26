"""Scientific cell-lock construction and lock/bundle correspondence."""
from __future__ import annotations

from .canonical_evidence import require_lower_sha256
from .episode_artifact import AttemptBundleBytes
from .schema_models import (
    EpisodeArtifactV1,
    ScientificCellLockV1,
)


class CellLockMismatchError(ValueError):
    """A lock does not identify exactly the supplied scientific bundle."""


def _scientific_status(value: str) -> str:
    allowed = {
        "SCIENTIFIC_OUTCOME_COMPLETE_SUCCESS",
        "SCIENTIFIC_OUTCOME_COMPLETE_TASK_FAILURE",
    }
    if value not in allowed:
        raise ValueError(
            "scientific cell lock requires a completed scientific outcome"
        )
    return value


def build_scientific_cell_lock(
    *,
    episode_artifact: EpisodeArtifactV1,
    bundle: AttemptBundleBytes,
    run_schedule_sha256: str,
) -> ScientificCellLockV1:
    if not isinstance(episode_artifact, EpisodeArtifactV1):
        raise TypeError(
            "episode_artifact must be EpisodeArtifactV1"
        )
    if not isinstance(bundle, AttemptBundleBytes):
        raise TypeError("bundle must be AttemptBundleBytes")
    schedule_sha = require_lower_sha256(
        "run_schedule_sha256",
        run_schedule_sha256,
    )
    status = _scientific_status(
        episode_artifact.scientific_outcome_status
    )
    if (
        episode_artifact.episode_semantic_sha256
        != bundle.episode_semantic_sha256
    ):
        raise CellLockMismatchError(
            "episode semantic identity does not match bundle"
        )

    return ScientificCellLockV1(
        schema_id="E1_SCIENTIFIC_CELL_LOCK_V1",
        schema_version=1,
        run_id=episode_artifact.run_id,
        scheduled_cell_id=(
            episode_artifact.scheduled_cell_id
        ),
        execution_attempt_id=(
            episode_artifact.execution_attempt_id
        ),
        run_schedule_sha256=schedule_sha,
        episode_semantic_sha256=(
            bundle.episode_semantic_sha256
        ),
        attempt_bundle_sha256=(
            bundle.attempt_bundle_sha256
        ),
        scientific_outcome_status=status,
        evaluator_commit=episode_artifact.evaluator_commit,
    )


def validate_cell_lock_matches_bundle(
    *,
    lock: ScientificCellLockV1,
    episode_artifact: EpisodeArtifactV1,
    bundle: AttemptBundleBytes,
) -> None:
    if not isinstance(lock, ScientificCellLockV1):
        raise TypeError("lock must be ScientificCellLockV1")
    if not isinstance(episode_artifact, EpisodeArtifactV1):
        raise TypeError(
            "episode_artifact must be EpisodeArtifactV1"
        )
    if not isinstance(bundle, AttemptBundleBytes):
        raise TypeError("bundle must be AttemptBundleBytes")

    expected = {
        "run_id": episode_artifact.run_id,
        "scheduled_cell_id": (
            episode_artifact.scheduled_cell_id
        ),
        "execution_attempt_id": (
            episode_artifact.execution_attempt_id
        ),
        "episode_semantic_sha256": (
            bundle.episode_semantic_sha256
        ),
        "attempt_bundle_sha256": (
            bundle.attempt_bundle_sha256
        ),
        "scientific_outcome_status": (
            episode_artifact.scientific_outcome_status
        ),
        "evaluator_commit": (
            episode_artifact.evaluator_commit
        ),
    }
    for name, expected_value in expected.items():
        if getattr(lock, name) != expected_value:
            raise CellLockMismatchError(
                f"cell lock {name} does not match bundle"
            )
