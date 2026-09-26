from copy import deepcopy
from pchsi.analyzer.crosscheck import finalize_crosscheck,apply_crosscheck_disposition
def test_crosscheck_is_immutable_sidecar():
 original={"group_result_sha256":"a"*64,"claims":["x"]}; before=deepcopy(original)
 side=finalize_crosscheck({"schema_id":"ANALYZER_CROSSCHECK_RESULT_V1",
  "schema_version":1,"target_artifact_sha256":"a"*64,"disposition":"DOWNGRADE_SCOPE",
  "supporting_evidence_sha256s":[],"contradiction_evidence_sha256s":["b"*64],
  "residual_case_ids":[],"current_evidence_sha256s":["b"*64],
  "historical_evidence_sha256s":[],"crosscheck_sha256":"0"*64})
 out=apply_crosscheck_disposition(original,side)
 assert original==before and out["effective_disposition"]=="DOWNGRADE_SCOPE"
