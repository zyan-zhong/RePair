from pathlib import Path

from stage0.authorization import prepare_authorization


def test_authorization_requires_exact_explicit_token(tmp_path: Path) -> None:
    try:
        prepare_authorization(
            output_path=tmp_path / "auth.json",
            supplied_token="wrong",
            package_inventory_sha256="1" * 64,
            preflight_receipt_sha256="2" * 64,
        )
    except ValueError as exc:
        assert "approval" in str(exc).lower()
    else:
        raise AssertionError("wrong approval token was accepted")


def test_authorization_is_reusable_only_when_exact(tmp_path: Path) -> None:
    path = tmp_path / "auth.json"
    first = prepare_authorization(
        output_path=path,
        supplied_token="APPROVE_HUMAN_PILOT_STAGE0_OFFOFF_V1",
        package_inventory_sha256="1" * 64,
        preflight_receipt_sha256="2" * 64,
    )
    second = prepare_authorization(
        output_path=path,
        supplied_token="APPROVE_HUMAN_PILOT_STAGE0_OFFOFF_V1",
        package_inventory_sha256="1" * 64,
        preflight_receipt_sha256="2" * 64,
    )
    assert first == second
