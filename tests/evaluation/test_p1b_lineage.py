from pchsi.evaluation.p1b_lineage import CurrentPilotDataLineageV1,build_p1_dev_policy_condition

def test_lineage_excludes_legacy_and_seed17_is_dev_only():
    x=CurrentPilotDataLineageV1(); assert x.p1_dev_seed==17 and x.legacy_reference_only and "OLD_GPT_TRAJECTORY" in x.prohibited_legacy_data_classes

def test_pi0_uses_frozen_e1_service_name():
    p=build_p1_dev_policy_condition(policy_runtime_manifest_sha256="a"*64,tokenizer_identity_manifest_sha256="b"*64,chat_template_sha256="c"*64,raw_protocol_sha256="d"*64,runtime_core_commit="e"*40,evaluator_commit="f"*40)
    assert p.policy_condition_id=="P4-R0-PI0" and p.served_model_name=="Qwen2.5-3B-Instruct-E1"
