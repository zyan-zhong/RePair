from pathlib import Path
import pytest
from pchsi.cognitive_runtime.researcher import finalize_human_pre
from pchsi.cognitive_runtime.round_evidence import freeze_round_evidence_package

def _candidate(status="SELECTED"):
 return {"candidate_id":"c","observed_facts":["f"],"uncertainties":["u"],
 "evidence_sha256s":["a"*64],"counterevidence_sha256s":[],
 "expected_value_class":"MEDIUM","expected_value_basis":"basis",
 "expected_environment_steps":1,"expected_model_logical_calls":1,
 "expected_transport_attempts":1,"expected_gpu_hours":0.0,
 "expected_api_cost_usd":0.1,"risk_class":"LOW","risk_basis":"basis",
 "status":status,"disposition_reason":"reason"}

def test_human_pre_has_one_selected_bottleneck():
 v={"round_id":"r","policy_version":"p","evidence_cutoff":"cut",
 "round_evidence_package_sha256":"b"*64,"observed_facts":["f"],
 "uncertainties":["u"],"candidate_bottlenecks":[_candidate()],
 "selected_bottleneck_id":"c","selection_rationale":"why",
 "single_falsifiable_hypothesis":"h","single_principal_change":"change",
 "baseline":"b","intervention":"i","fixed_variables":["x"],
 "sample_definition":"s","verification_budget":1,
 "model_logical_call_budget":1,"environment_budget":1,"gpu_budget_hours":0.0,
 "primary_endpoint":"EVRY","secondary_diagnostics":["Harm"],
 "support_criterion":"support","refutation_criterion":"refute",
 "stop_condition":"stop"}
 assert finalize_human_pre(v)["selected_bottleneck_id"]=="c"

def test_round_evidence_rejects_future_outcomes(tmp_path: Path):
 with pytest.raises(ValueError,match="forbidden"):
  freeze_round_evidence_package({"current_f0f1_outcomes":"x"},tmp_path/"x.json")
