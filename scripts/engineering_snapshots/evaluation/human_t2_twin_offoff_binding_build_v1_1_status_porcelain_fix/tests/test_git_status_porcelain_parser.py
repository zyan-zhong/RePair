import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_builder():
    spec = importlib.util.spec_from_file_location(
        "twin_builder_for_test",
        ROOT / "twin_builder.py",
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_porcelain_v1_z_parser_preserves_exact_paths() -> None:
    module = _load_builder()

    raw = (
        " M configs/evaluation/schemas/"
        "select_server_runtime_manifest_v1.json\0"
        " M configs/evaluation/schemas/"
        "select_policy_runtime_manifest_v1.json\0"
        " M src/pchsi/evaluation/select_execution_identity.py\0"
        "?? tests/evaluation/"
        "test_generic_select_policy_artifact_binding_v1.py\0"
    )

    assert module.parse_git_status_porcelain_v1_z(raw) == {
        "configs/evaluation/schemas/"
        "select_server_runtime_manifest_v1.json",
        "configs/evaluation/schemas/"
        "select_policy_runtime_manifest_v1.json",
        "src/pchsi/evaluation/select_execution_identity.py",
        "tests/evaluation/"
        "test_generic_select_policy_artifact_binding_v1.py",
    }


def test_builder_uses_machine_stable_porcelain_status() -> None:
    text = (
        ROOT / "twin_builder.py"
    ).read_text(encoding="utf-8")

    assert '"--porcelain=v1"' in text
    assert '"-z"' in text
    assert "line[3:]" not in text
    assert '"--short"' not in text
