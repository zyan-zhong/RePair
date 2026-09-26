import pytest
from pchsi.analyzer.repair_decomposition import (
    register_decomposition,interpret_decomposition,
)
from pchsi.analyzer.experiment_registry import validate_registry
from pchsi.analyzer.success_optimization import register_success_pilot

def test_decomposition_missing_d4_is_not_silently_history_dependent():
    trace=register_decomposition("a"*64)
    with pytest.raises(ValueError,match="D4"):
        interpret_decomposition(trace,{
            "D0":"Failure","D1":"Benefit","D3":"Neutral","prefix_results":[]
        })

def test_decomposition_uncertain_is_unresolved():
    trace=register_decomposition("a"*64)
    out=interpret_decomposition(trace,{
        "D0":"Failure","D1":"Benefit","D3":"Neutral","D4":"Uncertain",
        "prefix_results":[{"prefix_length":1,"effect_label":"Neutral"}],
    })
    assert out["mechanism_label"]=="UNRESOLVED_MULTI_CHANNEL_EFFECT"

def _registry():
    base={
        "conditions":["A0","A1","A2","A3"],
        "registered_unit_ids":["u1"],
        "max_formal_candidate_count_per_unit":1,
        "common_repair_budget":{
            "max_candidate_count_per_unit":1,"max_option_actions":4,
            "analyzer_prose_in_policy_prompt":False,
            "all_intervention_actions_count_against_environment_budget":True,
        },
        "unit_condition_rows":[
            {"unit_id":"u1","condition_id":c,"candidate_count":0,"abstained":True}
            for c in ("A0","A1","A2","A3")
        ],
    }
    for c in ("A0","A1","A2","A3"):
        base[c]={
            "registered_universe_sha256":"1"*64,
            "common_evidence_pack_sha256s":["2"*64],
            "local_result_sha256s":["3"*64] if c!="A0" else [],
            "memory_pack_sha256":"4"*64 if c=="A3" else None,
        }
    return base

def test_registry_requires_complete_cartesian_and_all_condition_evidence_identity():
    r=_registry()
    assert validate_registry(r)
    bad=_registry(); bad["unit_condition_rows"].pop()
    with pytest.raises(ValueError,match="incomplete"):
        validate_registry(bad)
    bad=_registry(); bad["A0"]["common_evidence_pack_sha256s"]=["9"*64]
    with pytest.raises(ValueError,match="common evidence"):
        validate_registry(bad)

def test_success_pilot_rejects_duplicate_gamefiles():
    with pytest.raises(ValueError,match="unique gamefiles"):
        register_success_pilot([
            {"candidate_sha256":"a"*64,"gamefile_sha256":"c"*64,
             "requires_environment_verification":True},
            {"candidate_sha256":"b"*64,"gamefile_sha256":"c"*64,
             "requires_environment_verification":True},
        ])
