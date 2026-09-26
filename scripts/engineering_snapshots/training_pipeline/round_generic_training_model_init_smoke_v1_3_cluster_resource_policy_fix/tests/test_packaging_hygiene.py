from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_package_tree_contains_no_python_bytecode_cache() -> None:
    cache_dirs = [
        path
        for path in ROOT.rglob("__pycache__")
        if path.is_dir()
    ]
    pyc_files = [
        path
        for path in ROOT.rglob("*.pyc")
        if path.is_file()
    ]
    assert cache_dirs == []
    assert pyc_files == []


def test_package_inventory_excludes_python_bytecode_cache() -> None:
    text = (
        ROOT / "PACKAGE_FILES.sha256"
    ).read_text(encoding="utf-8")

    assert "__pycache__" not in text
    assert ".pyc" not in text


def test_verifier_checks_cache_absence_before_and_after_tests() -> None:
    text = (
        ROOT / "00_VERIFY_PACKAGE.sh"
    ).read_text(encoding="utf-8")

    assert "PACKAGE_CONTAINS_TRANSIENT_PYTHON_CACHE" in text
    assert "PACKAGE_GENERATED_TRANSIENT_PYTHON_CACHE" in text
    assert "PACKAGE_TRANSIENT_PYTHON_CACHE_ABSENCE_PASS" in text
    assert "PACKAGE_TRANSIENT_PYTHON_CACHE_POSTVERIFY_PASS" in text
