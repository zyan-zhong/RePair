from __future__ import annotations
from collections.abc import Mapping
from pathlib import Path
from pchsi.reference_loop.canonical import domain_hash, write_new_json
from .schema_registry import validate_artifact

FORBIDDEN_KEYS={"current_f0f1_outcomes","human_pre_record","api_shadow_output",
                "sealed_test_trajectory","future_pi2_evaluation"}


def freeze_round_evidence_package(value: Mapping[str,object], output: Path) -> dict[str,object]:
    if FORBIDDEN_KEYS & set(value):
        raise ValueError("round evidence contains forbidden future/sealed fields")
    out={"schema_id":"ROUND_EVIDENCE_PACKAGE_V1","schema_version":1,**dict(value),
         "forbidden_future_outcomes_absent":True,"sealed_test_details_absent":True,
         "round_evidence_package_sha256":"0"*64}
    out["round_evidence_package_sha256"]=domain_hash("ROUND_EVIDENCE_PACKAGE_V1",out,
        excluded_field="round_evidence_package_sha256")
    validate_artifact("ROUND_EVIDENCE_PACKAGE_V1",out)
    write_new_json(output,out); return out
