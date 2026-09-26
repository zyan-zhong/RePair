"""Fail-closed A0-A3 experiment registry and execution-dedup validation."""

CONDITIONS=("A0","A1","A2","A3")

def validate_registry(r):
    if set(r["conditions"])!=set(CONDITIONS):
        raise ValueError("registry conditions must be exactly A0-A3")
    ids=[r[x]["registered_universe_sha256"] for x in CONDITIONS]
    if len(set(ids))!=1:
        raise ValueError("A0-A3 U_reg mismatch")
    evidence=[tuple(r[x]["common_evidence_pack_sha256s"]) for x in CONDITIONS]
    if len(set(evidence))!=1:
        raise ValueError("A0-A3 common evidence pack mismatch")
    if r["A2"]["local_result_sha256s"]!=r["A1"]["local_result_sha256s"]:
        raise ValueError("A2 does not byte-reuse A1 local results")
    if r["A3"]["local_result_sha256s"]!=r["A1"]["local_result_sha256s"]:
        raise ValueError("A3 does not byte-reuse A1 local results")
    if r["A0"].get("memory_pack_sha256") is not None or r["A1"].get("memory_pack_sha256") is not None or r["A2"].get("memory_pack_sha256") is not None:
        raise ValueError("Memory may not attach to A0-A2")
    if not r["A3"].get("memory_pack_sha256"):
        raise ValueError("A3 requires frozen higher-level Memory packet")
    budget=r["common_repair_budget"]
    if budget != {
        "max_candidate_count_per_unit":1,
        "max_option_actions":4,
        "analyzer_prose_in_policy_prompt":False,
        "all_intervention_actions_count_against_environment_budget":True,
    }:
        raise ValueError("common repair budget mismatch")
    units=list(r["registered_unit_ids"])
    if len(units)!=len(set(units)):
        raise ValueError("duplicate registered unit")
    expected={(u,c) for u in units for c in CONDITIONS}
    observed=set()
    for row in r["unit_condition_rows"]:
        key=(row["unit_id"],row["condition_id"])
        if key in observed:
            raise ValueError("duplicate unit-condition row")
        observed.add(key)
        if row["candidate_count"] not in (0,1):
            raise ValueError("K=1 violation")
        if (row["candidate_count"]==0) != (row["abstained"] is True):
            raise ValueError("candidate/ABSTAIN exclusivity violation")
    if observed!=expected:
        raise ValueError("incomplete U_reg x A0-A3 registry")
    return r


def build_execution_dedup_map(rows):
    result={}
    for row in rows:
        key=(
            row["source_state_sha256"],
            row["candidate_sha256"],
            row["termination_condition_sha256"],
        )
        result.setdefault(key,":".join(key))
    return result
