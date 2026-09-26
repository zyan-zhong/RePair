from __future__ import annotations

from pathlib import Path

from pchsi.reference_loop.identity_census import (
    build_pi1_identity_authority_census,
)


def test_identity_census_blocks_when_authorities_are_incomplete(
    tmp_path: Path,
) -> None:
    runtime_root = tmp_path / "runtime"
    select_root = tmp_path / "select"
    checkpoint = tmp_path / "checkpoint"
    runtime_root.mkdir()
    select_root.mkdir()
    checkpoint.mkdir()

    value = build_pi1_identity_authority_census(
        formal_a_runtime_roots=(runtime_root,),
        select_roots=(select_root,),
        checkpoint_root=checkpoint,
    )

    assert value["readiness_status"] == (
        "BLOCKED_IDENTITY_AUTHORITY_CENSUS_INCOMPLETE"
    )
    assert value["selection_performed"] is False
    assert value["identity_registration_created"] is False
    assert value["identity_materialization_created"] is False
