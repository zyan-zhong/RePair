from __future__ import annotations
import json
from pathlib import Path
import pytest

from no_training_recovery import (
    build_no_training_update,
    recoverable_v110_post_without_gap,
)


def _fake_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    pkg = repo / "src/pchsi/round_control"
    pkg.mkdir(parents=True)
    for p in [repo/'src/pchsi/__init__.py', repo/'src/pchsi/round_control/__init__.py']:
        p.write_text('', encoding='utf-8')
    (pkg/'no_training_update.py').write_text('''\nclass V:\n    def __init__(self, kw): self.kw=kw\n    def to_dict(self):\n        return {"schema_id":"NO_TRAINING_UPDATE_V1","schema_version":1, **self.kw,\n        "scientific_attempt_consumed":True,"candidate_policy_created":False,\n        "training_execution_count":0,"parent_policy_retained":True,\n        "reason":"NO_VERIFIED_BENEFIT","disposition_sha256":"d"*64}\ndef freeze_no_training_update(**kw):\n    required={"round_id","parent_policy_id","post_plan_sha256","verifier_result_sha256",\n    "verified_benefit_count","verified_harm_count","verified_neutral_count",\n    "verified_uncertain_count","scientifically_valid_round"}\n    assert set(kw)==required\n    assert kw["verified_benefit_count"]==0\n    assert kw["scientifically_valid_round"] is True\n    return V(kw)\n''', encoding='utf-8')
    return repo


def _post(tmp_path: Path) -> dict:
    call = tmp_path/'call'; call.mkdir()
    artifact={"schema_id":"API_RESEARCHER_POST_PRIMARY_V1","schema_version":1,"primary_record_sha256":"a"*64}
    (call/'validated_artifact.json').write_text(json.dumps(artifact), encoding='utf-8')
    return {"schema_id":"STRONG_PRIMARY_R1_HYDRATED_PLANNER_POST_ACCEPTED_V1","schema_version":1,
            "round_id":"R1","call_dir":str(call),"result_package_sha256":"b"*64,
            "route":"NO_TRAINING_UPDATE","verified_benefit_count":0}


def test_exact_current_fixed_head_no_train_signature(tmp_path: Path):
    repo=_fake_repo(tmp_path); post=_post(tmp_path)
    verifier={"round_id":"R1","parent_policy_id":"PI0","result_package_sha256":"b"*64,
              "stable_effect_counts":{"BENEFIT":0,"HARM":2,"NEUTRAL":3,"UNCERTAIN":1},
              "scientific_attempt_consumed":True}
    out=build_no_training_update(repo=repo,post_receipt=post,verifier_gate=verifier)
    assert out["post_plan_sha256"]=="a"*64
    assert out["verifier_result_sha256"]=="b"*64
    assert out["verified_harm_count"]==2
    assert out["verified_neutral_count"]==3
    assert out["verified_uncertain_count"]==1
    assert out["scientifically_valid_round"] is True


def test_post_only_zero_benefit_is_recoverable_without_gap(tmp_path: Path):
    post=_post(tmp_path)
    verifier={"round_id":"R1","result_package_sha256":"b"*64,
              "stable_effect_counts":{"BENEFIT":0,"HARM":0,"NEUTRAL":1,"UNCERTAIN":0},
              "scientific_attempt_consumed":True}
    x=recoverable_v110_post_without_gap(post_receipt=post,verifier_gate=verifier,gap_present=False)
    assert x["recoverable"] is True and x["route"]=="NO_TRAINING_UPDATE"


def test_post_only_positive_benefit_never_fabricates_gap(tmp_path: Path):
    post=_post(tmp_path); post["route"]="VERIFIED_BENEFIT_TRAINING"; post["verified_benefit_count"]=1
    verifier={"round_id":"R1","result_package_sha256":"b"*64,
              "stable_effect_counts":{"BENEFIT":1,"HARM":0,"NEUTRAL":0,"UNCERTAIN":0},
              "scientific_attempt_consumed":True}
    with pytest.raises(ValueError,match="POSITIVE_BENEFIT_REQUIRES_V110_GAP"):
        recoverable_v110_post_without_gap(post_receipt=post,verifier_gate=verifier,gap_present=False)
