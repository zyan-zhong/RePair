from __future__ import annotations

from pathlib import Path

import pytest

from pchsi.reference_loop.historical_bridge import (
    _published_attempt_directories,
)


def test_published_attempt_directories_excludes_staging(
    tmp_path: Path,
) -> None:
    root = tmp_path / "attempts"
    root.mkdir()
    (root / ".staging").mkdir()
    first = root / "e1-t0000-s0000000017-a000"
    second = root / "e1-t0001-s0000000017-a000"
    first.mkdir()
    second.mkdir()

    attempts, infrastructure = _published_attempt_directories(root)

    assert [path.name for path in attempts] == [
        "e1-t0000-s0000000017-a000",
        "e1-t0001-s0000000017-a000",
    ]
    assert infrastructure == [".staging"]


def test_published_attempt_directories_rejects_unknown_directory(
    tmp_path: Path,
) -> None:
    root = tmp_path / "attempts"
    root.mkdir()
    (root / ".staging").mkdir()
    (root / "mystery-retry").mkdir()

    with pytest.raises(ValueError, match="unknown directory"):
        _published_attempt_directories(root)


def test_published_attempt_directories_rejects_symlink(
    tmp_path: Path,
) -> None:
    root = tmp_path / "attempts"
    root.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (root / "e1-t0000-s0000000017-a000").symlink_to(
        target,
        target_is_directory=True,
    )

    with pytest.raises(ValueError, match="symlink"):
        _published_attempt_directories(root)
