
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

import json
import stat
import subprocess
import sys

import pytest

from pchsi.evaluation.environment_runtime_manifest import (
    EnvironmentRuntimeManifestV1,
    build_environment_runtime_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    REPO_ROOT
    / "scripts/evaluation/build_environment_runtime_manifest.py"
)


def test_environment_builder_uses_only_explicit_fixture_inputs(
    tmp_path: Path,
) -> None:
    inputs, python_executable = make_fixture_inputs(tmp_path)
    output = tmp_path / "cli.json"

    command = [
        sys.executable,
        str(SCRIPT),
        "--python-version",
        inputs.python_version,
        "--python-executable",
        str(python_executable),
        "--alfworld-version",
        inputs.alfworld_version,
        "--textworld-version",
        inputs.textworld_version,
        "--gym-version",
        inputs.gym_version,
    ]
    for item in inputs.source_identities:
        command.extend(
            [
                "--source",
                f"{item.logical_name}={item.source_path}",
            ]
        )
    command.extend(["--output", str(output)])

    result = subprocess.run(
        command,
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr
    assert (
        json.loads(result.stdout)["status"]
        == "ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_CREATED"
    )
    assert output.is_file()

    import ast

    source_text = SCRIPT.read_text(encoding="utf-8")
    tree = ast.parse(source_text, filename=str(SCRIPT))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(
                alias.name.split(".", 1)[0]
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None:
                imported_roots.add(
                    node.module.split(".", 1)[0]
                )

    assert imported_roots.isdisjoint(
        {"alfworld", "textworld", "gym", "pkg_resources"}
    )


def test_environment_builder_is_no_clobber_and_deterministic(
    tmp_path: Path,
) -> None:
    inputs, _ = make_fixture_inputs(tmp_path)
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    one = build_environment_runtime_manifest(
        inputs=inputs,
        output_path=first,
    )
    two = build_environment_runtime_manifest(
        inputs=inputs,
        output_path=second,
    )

    assert first.read_bytes() == second.read_bytes()
    assert one == two
    assert stat.S_IMODE(first.stat().st_mode) == 0o600

    with pytest.raises(FileExistsError):
        build_environment_runtime_manifest(
            inputs=inputs,
            output_path=first,
        )
