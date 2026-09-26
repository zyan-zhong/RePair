from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PackageContractTests(unittest.TestCase):
    def test_mainline_is_chinese_first(self):
        text = (ROOT / "README_CN.md").read_text(encoding="utf-8")
        self.assertIn("中文科研主线", text)
        self.assertIn("人工参考轮", text)
        self.assertIn("Strong", text)

    def test_no_strict_shell_modes(self):
        text = "\n".join(p.read_text() for p in ROOT.glob("*.sh"))
        self.assertNotIn("set -e", text)
        self.assertNotIn("set -u", text)
        self.assertNotIn("pipefail", text)

    def test_all_stages_fail_closed(self):
        for prefix in ("10_", "20_", "30_", "40_", "50_"):
            found = list(ROOT.glob(prefix + "*.sh"))
            self.assertEqual(len(found), 1)
            text = found[0].read_text()
            self.assertIn("rc=$?", text)
            self.assertIn('exit "$rc"', text)


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# v1.7.1 regression: selected-arm authority lives under policy_training_recipe
# ---------------------------------------------------------------------------

import importlib.util as _v171_importlib_util
from pathlib import Path as _V171Path
import sys as _v171_sys

import pytest as _v171_pytest


def _v171_load_upstream_verifier():
    root = _V171Path(__file__).resolve().parents[1]
    tools_root = root / "tools"
    path = tools_root / "verify_upstream_authorities.py"

    tools_root_text = str(tools_root)
    if tools_root_text not in _v171_sys.path:
        _v171_sys.path.insert(
            0,
            tools_root_text,
        )
    spec = _v171_importlib_util.spec_from_file_location(
        "v171_verify_upstream_authorities",
        path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = _v171_importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v171_selected_arms_binding_accepts_nested_recipe() -> None:
    module = _v171_load_upstream_verifier()

    module.validate_current_selected_arms(
        {
            "policy_training_recipe": {
                "selected_arm_ids": [
                    "T0",
                    "T2",
                ],
            },
        }
    )


def test_v171_selected_arms_binding_rejects_missing_recipe() -> None:
    module = _v171_load_upstream_verifier()

    with _v171_pytest.raises(
        module.ContractError,
        match="CURRENT_POLICY_TRAINING_RECIPE_MISSING",
    ):
        module.validate_current_selected_arms({})


def test_v171_selected_arms_binding_rejects_changed_nested_arms() -> None:
    module = _v171_load_upstream_verifier()

    with _v171_pytest.raises(
        module.ContractError,
        match="CURRENT_SELECTED_ARMS_CHANGED",
    ):
        module.validate_current_selected_arms(
            {
                "policy_training_recipe": {
                    "selected_arm_ids": [
                        "T0",
                        "T4",
                    ],
                },
            }
        )


# ---------------------------------------------------------------------------
# v1.7.2 regression:
# Current T2 sequence-length authority must come from the frozen current-T2
# census, never from the historical pi1 materialization recommendation.
# ---------------------------------------------------------------------------

import importlib.util as _v172_importlib_util
from pathlib import Path as _V172Path
import sys as _v172_sys

import pytest as _v172_pytest


_V172_EXPECTED_LENGTHS = [
    774,
    654,
    568,
    327,
    570,
    343,
    436,
    333,
    491,
    314,
    274,
    425,
]

_V172_EXPECTED_CEILING = 774


def _v172_load_materializer():
    root = _V172Path(__file__).resolve().parents[1]
    tools_root = root / "tools"
    path = tools_root / "materialize_current_t2_trainer_native.py"

    tools_root_text = str(tools_root)

    if tools_root_text not in _v172_sys.path:
        _v172_sys.path.insert(
            0,
            tools_root_text,
        )

    spec = _v172_importlib_util.spec_from_file_location(
        "v172_materialize_current_t2_trainer_native",
        path,
    )

    assert spec is not None
    assert spec.loader is not None

    module = _v172_importlib_util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def test_v172_current_t2_sequence_authority_is_exact_census() -> None:
    module = _v172_load_materializer()

    root = _V172Path(__file__).resolve().parents[1]

    lengths, ceiling = (
        module.load_current_t2_sequence_length_authority(
            root / "PACKAGE_METADATA.json"
        )
    )

    assert lengths == _V172_EXPECTED_LENGTHS
    assert ceiling == _V172_EXPECTED_CEILING


def test_v172_current_t2_sequence_authority_rejects_missing_metadata(
    tmp_path,
) -> None:
    module = _v172_load_materializer()

    path = tmp_path / "PACKAGE_METADATA.json"
    path.write_text(
        "{}\n",
        encoding="utf-8",
    )

    with _v172_pytest.raises(
        module.ContractError,
        match="CURRENT_T2_SEQUENCE_LENGTH_AUTHORITY_MISSING",
    ):
        module.load_current_t2_sequence_length_authority(
            path
        )


def test_v172_materializer_no_longer_inherits_historical_pi1_ceiling() -> None:
    root = _V172Path(__file__).resolve().parents[1]

    text = (
        root
        / "tools"
        / "materialize_current_t2_trainer_native.py"
    ).read_text(
        encoding="utf-8"
    )

    assert (
        "recommended_no_truncation_sequence_ceiling"
        not in text
    )
