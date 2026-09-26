
from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path


def make_fixture_inputs(tmp_path: Path):
    from pchsi.evaluation.environment_runtime_manifest import (
        EnvironmentRuntimeInputs,
        SourceIdentity,
    )

    python_executable = tmp_path / "python"
    python_executable.write_bytes(b"fixture-python\n")

    identities = []
    for logical_name, filename in (
        ("AlfredTWEnv", "alfred_tw_env.py"),
        ("AlfredDemangler", "demangler.py"),
        ("AlfredInfos", "infos.py"),
        (
            "textworld.gym.register_games",
            "register_games.py",
        ),
    ):
        path = tmp_path / filename
        path.write_text(
            f"# {logical_name}\n",
            encoding="utf-8",
        )
        identities.append(
            SourceIdentity(
                logical_name=logical_name,
                source_path=str(path.resolve()),
                sha256=hashlib.sha256(
                    path.read_bytes()
                ).hexdigest(),
            )
        )

    inputs = EnvironmentRuntimeInputs(
        python_version="3.12.13",
        python_executable_sha256=hashlib.sha256(
            python_executable.read_bytes()
        ).hexdigest(),
        alfworld_version="0.4.2",
        textworld_version="1.6.2",
        gym_version="0.26.2",
        source_identities=tuple(identities),
        wrapper_order=(
            "AlfredDemangler(shuffle=false)",
            "AlfredInfos",
        ),
        env_infos=(
            "won",
            "admissible_commands",
            "extra.gamefile",
        ),
        batch_size=1,
        asynchronous=False,
        auto_reset=False,
        max_episode_steps=31,
        process_start_method="spawn",
    )
    return inputs, python_executable

import pytest

from pchsi.evaluation.environment_runtime_manifest import (
    EnvironmentRuntimeManifestV1,
    build_environment_runtime_manifest,
)


def test_environment_manifest_binds_exact_runtime_and_source_hashes(
    tmp_path: Path,
) -> None:
    inputs, _ = make_fixture_inputs(tmp_path)
    output = tmp_path / "manifest.json"

    manifest = build_environment_runtime_manifest(
        inputs=inputs,
        output_path=output,
    )

    assert isinstance(
        manifest,
        EnvironmentRuntimeManifestV1,
    )
    assert manifest.python_version == "3.12.13"
    assert tuple(
        item.logical_name
        for item in manifest.source_identities
    ) == (
        "AlfredTWEnv",
        "AlfredDemangler",
        "AlfredInfos",
        "textworld.gym.register_games",
    )
    assert EnvironmentRuntimeManifestV1.from_json(
        output.read_bytes()
    ) == manifest


def test_environment_manifest_requires_frozen_wrapper_and_envinfo_contract(
    tmp_path: Path,
) -> None:
    inputs, _ = make_fixture_inputs(tmp_path)

    with pytest.raises(ValueError, match="wrapper_order"):
        build_environment_runtime_manifest(
            inputs=replace(
                inputs,
                wrapper_order=(
                    "AlfredInfos",
                    "AlfredDemangler(shuffle=false)",
                ),
            ),
            output_path=tmp_path / "bad-wrapper.json",
        )

    with pytest.raises(ValueError, match="env_infos"):
        build_environment_runtime_manifest(
            inputs=replace(
                inputs,
                env_infos=(
                    "won",
                    "admissible_commands",
                    "facts",
                ),
            ),
            output_path=tmp_path / "bad-info.json",
        )


def test_environment_manifest_requires_spawn_and_31_steps(
    tmp_path: Path,
) -> None:
    inputs, _ = make_fixture_inputs(tmp_path)

    with pytest.raises(ValueError, match="spawn"):
        build_environment_runtime_manifest(
            inputs=replace(
                inputs,
                process_start_method="fork",
            ),
            output_path=tmp_path / "fork.json",
        )

    with pytest.raises(ValueError, match="31"):
        build_environment_runtime_manifest(
            inputs=replace(
                inputs,
                max_episode_steps=30,
            ),
            output_path=tmp_path / "steps.json",
        )
