from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "tools" / "master.py"
spec = importlib.util.spec_from_file_location("boundary_master", PATH)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules["boundary_master"] = mod
spec.loader.exec_module(mod)


def test_pair_suffix_and_pair_id():
    arm, suffix = mod.pair_suffix("FORMAL_PI1_MAIN_L_A1_12_deadbeef")
    assert arm == "1"
    assert suffix == "12_deadbeef"
    assert mod.paired_local_id(suffix) == "FORMAL_PI1_MAIN_LOCAL_12_deadbeef"


def test_execution_semantics_exact():
    row = {
        "candidate_status": "EXECUTABLE_EXACT_ACTION",
        "source_state_sha256": "a" * 64,
        "exact_action": "open fridge 1",
    }
    assert mod.execution_semantics(row) == (
        "a" * 64,
        "EXACT",
        "open fridge 1",
    )


def test_execution_semantics_short_option():
    row = {
        "candidate_status": "EXECUTABLE_SHORT_OPTION",
        "source_state_sha256": "b" * 64,
        "option_actions": ["open fridge 1", "take apple 1 from fridge 1"],
        "termination_condition": "apple acquired",
    }
    assert mod.execution_semantics(row) == (
        "b" * 64,
        "OPTION",
        ("open fridge 1", "take apple 1 from fridge 1"),
        "apple acquired",
    )


def test_non_executable_has_no_semantics():
    assert mod.execution_semantics(
        {
            "candidate_status": "REJECTED_CROSSCHECK",
            "source_state_sha256": "c" * 64,
        }
    ) is None


class _FakeAPI:
    @staticmethod
    def validate_task_access(record, *, live_call=True):
        assert live_call is True
        if record.get("teacher_call_permitted") is not True:
            raise ValueError("teacher_call_permitted=false")
        for key in (
            "task_id",
            "gamefile_sha256",
            "access_class",
            "dataset_split",
            "training_permitted",
            "select_evaluation_permitted",
            "confirmatory_permitted",
        ):
            assert key in record


def test_analyzer_live_access_does_not_require_confirmatory():
    access = {
        "task_id": "task-1",
        "gamefile_sha256": "a" * 64,
        "access_class": "DEV_VISIBLE",
        "dataset_split": "train",
        "teacher_call_permitted": True,
        "training_permitted": True,
        "select_evaluation_permitted": False,
        "confirmatory_permitted": False,
    }
    membership = {
        "task_id": "task-1",
        "gamefile_sha256": "a" * 64,
    }
    mod.validate_analyzer_member_access(
        _FakeAPI(),
        access,
        membership,
        group_manifest_sha256="b" * 64,
        local_result_sha256="c" * 64,
    )


def test_analyzer_live_access_still_rejects_teacher_forbidden():
    access = {
        "task_id": "task-1",
        "gamefile_sha256": "a" * 64,
        "access_class": "SELECT_SUMMARY_ONLY",
        "dataset_split": "valid_unseen",
        "teacher_call_permitted": False,
        "training_permitted": False,
        "select_evaluation_permitted": True,
        "confirmatory_permitted": False,
    }
    membership = {
        "task_id": "task-1",
        "gamefile_sha256": "a" * 64,
    }
    import pytest
    with pytest.raises(ValueError, match="teacher_call_permitted"):
        mod.validate_analyzer_member_access(
            _FakeAPI(),
            access,
            membership,
            group_manifest_sha256="b" * 64,
            local_result_sha256="c" * 64,
        )
