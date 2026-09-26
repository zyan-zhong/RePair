from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

import pchsi.security.execution_preflight as preflight
from pchsi.security.execution_preflight import (
    EXPECTED_PROBE_IDS,
    PREFLIGHT_STATUS,
    PreflightError,
    build_preflight_bundle,
    observe_dataset_identity,
    parse_mountinfo,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
CLI_PATH = (
    REPO_ROOT
    / "scripts"
    / "security"
    / "prepare_backend_probe_execution.py"
)
SCHEMA_PATH = (
    REPO_ROOT
    / "configs"
    / "security"
    / "schemas"
    / "backend_probe_execution_decision_v1.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_cli():
    spec = importlib.util.spec_from_file_location(
        "s1_prepare_backend_probe_execution",
        CLI_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _probe_stem(probe_id: str) -> str:
    return probe_id.lower()


def _make_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Path | str]:
    repository = tmp_path / "repository"
    manifests_root = repository / "configs/security/probes"
    sources_root = repository / "native/s1_backend_probe/probes"
    scripts_root = repository / "scripts/security"
    security_root = repository / "src/pchsi/security"

    manifests_root.mkdir(parents=True)
    sources_root.mkdir(parents=True)
    scripts_root.mkdir(parents=True)
    security_root.mkdir(parents=True)

    for probe_id in EXPECTED_PROBE_IDS:
        stem = _probe_stem(probe_id)
        source = sources_root / f"{stem}.c"
        source.write_text(
            f'const char *probe_id = "{probe_id}";\n',
            encoding="utf-8",
        )
        manifest = manifests_root / f"{stem}.json"
        manifest.write_text(
            json.dumps(
                {
                    "execution_status": "NOT_APPROVED",
                    "payload_sha256": _sha256(source),
                    "permitted_side_effects": [],
                    "probe_id": probe_id,
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    (scripts_root / "run_backend_probe.py").write_text(
        "closed = True\n",
        encoding="utf-8",
    )
    (security_root / "execution_gate.py").write_text(
        "closed = True\n",
        encoding="utf-8",
    )

    dataset = tmp_path / "dataset" / "json_2.1.1"
    for split_name in ("train", "valid_seen", "valid_unseen"):
        (dataset / split_name).mkdir(parents=True)

    legacy_manifest = tmp_path / "legacy_manifest.jsonl"
    legacy_manifest.write_text('{"task":"example"}\n', encoding="utf-8")

    input_contract = tmp_path / "input_contract.json"
    input_contract.write_text('{"schema_version":1}\n', encoding="utf-8")

    binary = tmp_path / "pchsi-s1-backend-probe"
    binary.write_bytes(b"reviewed-binary-fixture\n")
    monkeypatch.setattr(
        preflight,
        "CANDIDATE_BINARY_SHA256",
        _sha256(binary),
    )

    profile = tmp_path / "probe_profiles.json"
    profile.write_text('{"profiles":[]}\n', encoding="utf-8")

    schema = tmp_path / "decision_schema.json"
    schema.write_text('{"schema_version":1}\n', encoding="utf-8")

    mountinfo = tmp_path / "mountinfo"
    mountinfo.write_text(
        "1 0 0:1 / / rw - rootfs rootfs rw\n"
        f"2 1 0:2 / {dataset.as_posix()} rw - ext4 /dev/fake rw\n",
        encoding="utf-8",
    )

    output_parent = tmp_path / "outputs"
    output_parent.mkdir()

    return {
        "repository_root": repository,
        "preflight_source_commit": "a" * 40,
        "dataset_root": dataset,
        "legacy_manifest": legacy_manifest,
        "input_contract": input_contract,
        "logical_root_id": "ALFWORLD_JSON_2_1_1_ROOT_V1",
        "mountinfo_path": mountinfo,
        "native_binary": binary,
        "profile_description": profile,
        "decision_schema": schema,
        "output_parent": output_parent,
    }


def _build(
    fixture: dict[str, Path | str],
    *,
    output_name: str,
) -> tuple[dict[str, object], Path]:
    output_root = (
        fixture["output_parent"] / output_name  # type: ignore[operator]
    )
    result = build_preflight_bundle(
        repository_root=fixture["repository_root"],  # type: ignore[arg-type]
        preflight_source_commit=(fixture["preflight_source_commit"]),  # type: ignore[arg-type]
        dataset_root=fixture["dataset_root"],  # type: ignore[arg-type]
        legacy_manifest=fixture["legacy_manifest"],  # type: ignore[arg-type]
        input_contract=fixture["input_contract"],  # type: ignore[arg-type]
        logical_root_id=fixture["logical_root_id"],  # type: ignore[arg-type]
        mountinfo_path=fixture["mountinfo_path"],  # type: ignore[arg-type]
        native_binary=fixture["native_binary"],  # type: ignore[arg-type]
        profile_description=fixture["profile_description"],  # type: ignore[arg-type]
        decision_schema=fixture["decision_schema"],  # type: ignore[arg-type]
        output_root=output_root,
    )
    return result, output_root


def test_parse_mountinfo_uses_longest_matching_mount(
    tmp_path: Path,
) -> None:
    target = tmp_path / "dataset"
    target.mkdir()
    result = parse_mountinfo(
        (
            "1 0 0:1 / / rw - rootfs rootfs rw\n"
            f"9 1 0:9 / {target.as_posix()} rw - ceph ceph rw\n"
        ),
        target=target,
    )

    assert result.mount_id == 9
    assert result.mount_point == target.as_posix()
    assert result.filesystem_type == "ceph"


def test_dataset_identity_is_exact_and_dataset_bound(
    tmp_path: Path,
) -> None:
    dataset = tmp_path / "json_2.1.1"
    for split_name in ("train", "valid_seen", "valid_unseen"):
        (dataset / split_name).mkdir(parents=True)

    legacy = tmp_path / "legacy.jsonl"
    legacy.write_text("legacy\n", encoding="utf-8")
    contract = tmp_path / "contract.json"
    contract.write_text("contract\n", encoding="utf-8")

    identity = observe_dataset_identity(
        dataset_root=dataset,
        legacy_manifest=legacy,
        input_contract=contract,
        logical_root_id="DATASET_ROOT_V1",
        mountinfo_text=(
            f"7 1 0:7 / {dataset.as_posix()} rw - ext4 /dev/fake rw\n"
        ),
    )

    assert identity.dataset_version == "json_2.1.1"
    assert identity.logical_root_id == "DATASET_ROOT_V1"
    assert identity.train_present is True
    assert identity.valid_seen_present is True
    assert identity.valid_unseen_present is True
    assert identity.legacy_manifest_exact_file_sha256 == _sha256(legacy)
    assert identity.input_contract_sha256 == _sha256(contract)
    assert identity.resolved_mount_id == 7
    assert identity.filesystem_type == "ext4"


def test_dataset_symlink_is_rejected(tmp_path: Path) -> None:
    dataset = tmp_path / "real"
    for split_name in ("train", "valid_seen", "valid_unseen"):
        (dataset / split_name).mkdir(parents=True)
    link = tmp_path / "linked"
    link.symlink_to(dataset, target_is_directory=True)

    legacy = tmp_path / "legacy"
    legacy.write_text("x", encoding="utf-8")
    contract = tmp_path / "contract"
    contract.write_text("x", encoding="utf-8")

    with pytest.raises(PreflightError, match="symbolic"):
        observe_dataset_identity(
            dataset_root=link,
            legacy_manifest=legacy,
            input_contract=contract,
            logical_root_id="DATASET_ROOT_V1",
            mountinfo_text=(
                f"7 1 0:7 / {dataset.as_posix()} rw - ext4 /dev/fake rw\n"
            ),
        )


def test_missing_split_is_rejected(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset"
    (dataset / "train").mkdir(parents=True)
    (dataset / "valid_seen").mkdir()

    legacy = tmp_path / "legacy"
    legacy.write_text("x", encoding="utf-8")
    contract = tmp_path / "contract"
    contract.write_text("x", encoding="utf-8")

    with pytest.raises(PreflightError, match="valid_unseen"):
        observe_dataset_identity(
            dataset_root=dataset,
            legacy_manifest=legacy,
            input_contract=contract,
            logical_root_id="DATASET_ROOT_V1",
            mountinfo_text=(
                f"7 1 0:7 / {dataset.as_posix()} rw - ext4 /dev/fake rw\n"
            ),
        )


def test_preflight_writes_exact_closed_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_fixture(tmp_path, monkeypatch)
    result, output_root = _build(fixture, output_name="first")

    assert result["status"] == PREFLIGHT_STATUS
    assert sorted(path.name for path in output_root.iterdir()) == [
        "backend_probe_execution_decision_template.json",
        "backend_probe_execution_preflight.json",
        "backend_probe_execution_preflight.json.sha256",
    ]

    manifest = json.loads(
        (
            output_root
            / "backend_probe_execution_preflight.json"
        ).read_text(encoding="utf-8")
    )
    template = json.loads(
        (
            output_root
            / "backend_probe_execution_decision_template.json"
        ).read_text(encoding="utf-8")
    )

    assert manifest["status"] == PREFLIGHT_STATUS
    assert manifest["probe_ids"] == list(EXPECTED_PROBE_IDS)
    assert manifest["execution_boundaries"] == {
        "alfworld_execution": "NOT_APPROVED",
        "backend_probe_execution": "NOT_APPROVED",
        "model_execution": "NOT_APPROVED",
        "read_only_inventory_execution": "NOT_APPROVED",
    }
    assert template["decision"] == "NOT_GRANTED"
    assert template["one_shot"] is True
    assert template["inventory_execution_approved"] is False
    assert template["alfworld_execution_approved"] is False
    assert template["model_execution_approved"] is False


def test_preflight_bytes_are_deterministic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_fixture(tmp_path, monkeypatch)
    first_result, first = _build(fixture, output_name="first")
    second_result, second = _build(fixture, output_name="second")

    assert first_result == second_result
    for name in (
        "backend_probe_execution_preflight.json",
        "backend_probe_execution_preflight.json.sha256",
        "backend_probe_execution_decision_template.json",
    ):
        assert (first / name).read_bytes() == (second / name).read_bytes()


def test_output_inside_repository_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_fixture(tmp_path, monkeypatch)
    repository = fixture["repository_root"]
    assert isinstance(repository, Path)

    with pytest.raises(PreflightError, match="outside"):
        build_preflight_bundle(
            repository_root=repository,
            preflight_source_commit=(fixture["preflight_source_commit"]),  # type: ignore[arg-type]
            dataset_root=fixture["dataset_root"],  # type: ignore[arg-type]
            legacy_manifest=fixture["legacy_manifest"],  # type: ignore[arg-type]
            input_contract=fixture["input_contract"],  # type: ignore[arg-type]
            logical_root_id=fixture["logical_root_id"],  # type: ignore[arg-type]
            mountinfo_path=fixture["mountinfo_path"],  # type: ignore[arg-type]
            native_binary=fixture["native_binary"],  # type: ignore[arg-type]
            profile_description=fixture["profile_description"],  # type: ignore[arg-type]
            decision_schema=fixture["decision_schema"],  # type: ignore[arg-type]
            output_root=repository / "preflight-output",
        )


def test_cli_execute_remains_closed(capsys: pytest.CaptureFixture[str]) -> None:
    cli = _load_cli()
    result = cli.main(["--execute"])

    assert result == 77
    assert "PCHSI_EXECUTION_NOT_APPROVED" in capsys.readouterr().err


def test_cli_describe_is_nonexecuting(
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli = _load_cli()
    result = cli.main(["--describe"])

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["executes_probe"] is False
    assert payload["backend_probe_execution"] == "NOT_APPROVED"


def test_decision_schema_keeps_nonprobe_scopes_false() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    properties = schema["properties"]

    assert properties["inventory_execution_approved"]["const"] is False
    assert properties["alfworld_execution_approved"]["const"] is False
    assert properties["model_execution_approved"]["const"] is False


def test_new_production_files_have_no_execution_surface() -> None:
    sources = (
        (
            REPO_ROOT
            / "src/pchsi/security/execution_preflight.py"
        ).read_text(encoding="utf-8"),
        CLI_PATH.read_text(encoding="utf-8"),
    )
    forbidden = (
        "import subprocess",
        "import socket",
        "import ctypes",
        "os.system(",
        "os.exec",
        "os.spawn",
        "unshare(",
        "mount(",
        "pivot_root(",
        "seccomp(",
        "landlock_restrict_self(",
        "env.step(",
        "import alfworld",
        "import vllm",
        "import torch",
    )

    for source in sources:
        for token in forbidden:
            assert token not in source


def test_not_granted_template_does_not_claim_enablement_commit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture = _make_fixture(tmp_path, monkeypatch)
    _, output_root = _build(fixture, output_name="source-binding")

    manifest = json.loads(
        (
            output_root
            / "backend_probe_execution_preflight.json"
        ).read_text(encoding="utf-8")
    )
    template = json.loads(
        (
            output_root
            / "backend_probe_execution_decision_template.json"
        ).read_text(encoding="utf-8")
    )

    assert manifest["preflight_source_commit"] == "a" * 40
    assert "source_commit" not in manifest
    assert template["preflight_source_commit"] == "a" * 40
    assert template["execution_enablement_source_commit"] is None


def test_decision_schema_requires_real_enablement_only_when_approved() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    properties = schema["properties"]

    assert properties["preflight_source_commit"]["pattern"] == (
        "^[0-9a-f]{40}$"
    )
    assert properties["execution_enablement_source_commit"]["oneOf"] == [
        {"type": "null"},
        {
            "pattern": "^[0-9a-f]{40}$",
            "type": "string",
        },
    ]

    conditions = schema["allOf"]
    not_granted = next(
        item
        for item in conditions
        if item["if"]["properties"]["decision"]["const"]
        == "NOT_GRANTED"
    )
    approved = next(
        item
        for item in conditions
        if item["if"]["properties"]["decision"]["const"]
        == "BACKEND_PROBE_EXECUTION_APPROVED"
    )

    assert (
        not_granted["then"]["properties"][
            "execution_enablement_source_commit"
        ]["const"]
        is None
    )
    assert approved["then"]["required"] == [
        "execution_enablement_source_commit"
    ]
