from dataclasses import replace
import os

import pytest

from pchsi.evaluation.distillation_governance import (
    canonical_model_sha256,
    freeze_governance_inputs,
)
from test_distillation_governance import parts


def test_freeze_writes_canonical_no_clobber_bundle(tmp_path):
    audit, access, policy, schedule = parts()
    output = tmp_path / "frozen"
    result = freeze_governance_inputs(
        historical_access_audit=audit,
        task_access_manifest=access,
        policy_condition=policy,
        schedule=schedule,
        output_dir=output,
    )
    assert result.output_dir == output
    assert (
        output / "historical_access_audit.json"
    ).read_text(encoding="utf-8") == audit.to_json()
    assert (
        output / "task_access_manifest.sha256"
    ).read_text(encoding="ascii").strip() == (
        canonical_model_sha256(access)
    )
    assert len(list(output.iterdir())) == 10


def test_freeze_refuses_existing_output(tmp_path):
    audit, access, policy, schedule = parts()
    output = tmp_path / "frozen"
    output.mkdir()
    with pytest.raises(FileExistsError):
        freeze_governance_inputs(
            historical_access_audit=audit,
            task_access_manifest=access,
            policy_condition=policy,
            schedule=schedule,
            output_dir=output,
        )


def test_invalid_binding_fails_before_output_creation(tmp_path):
    audit, access, policy, schedule = parts()
    bad = replace(
        access,
        historical_access_audit_sha256="0" * 64,
    )
    output = tmp_path / "frozen"
    with pytest.raises(ValueError):
        freeze_governance_inputs(
            historical_access_audit=audit,
            task_access_manifest=bad,
            policy_condition=policy,
            schedule=schedule,
            output_dir=output,
        )
    assert not os.path.lexists(output)


def test_symlink_output_is_rejected(tmp_path):
    audit, access, policy, schedule = parts()
    target = tmp_path / "target"
    target.mkdir()
    output = tmp_path / "frozen"
    output.symlink_to(target, target_is_directory=True)
    with pytest.raises(FileExistsError):
        freeze_governance_inputs(
            historical_access_audit=audit,
            task_access_manifest=access,
            policy_condition=policy,
            schedule=schedule,
            output_dir=output,
        )


def test_freeze_index_has_no_timestamp(tmp_path):
    audit, access, policy, schedule = parts()
    output = tmp_path / "frozen"
    freeze_governance_inputs(
        historical_access_audit=audit,
        task_access_manifest=access,
        policy_condition=policy,
        schedule=schedule,
        output_dir=output,
    )
    text = (
        output / "governance_freeze_index.json"
    ).read_text(encoding="utf-8")
    assert "timestamp" not in text.lower()
    assert "created_at" not in text.lower()
