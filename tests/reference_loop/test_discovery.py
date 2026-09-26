from __future__ import annotations

from pathlib import Path

from pchsi.reference_loop.discovery import (
    discover_reference_loop_inputs,
)

from ._helpers import write_bundle


def test_discovery_finds_complete_bundle_without_selecting_identity(
    tmp_path: Path,
) -> None:
    write_bundle(tmp_path / "bundle")
    result = discover_reference_loop_inputs(roots=(tmp_path,))

    assert result["complete_bundle_count"] == 1
    assert result["selection_performed"] is False
    assert result["scientific_execution_performed"] is False
    assert result["discovery_status"] == (
        "BLOCKED_NO_PI1_DEV_COMPLETE_TRAJECTORY"
    )
