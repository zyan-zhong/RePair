"""Execution-closed success-quality pilot registration."""

TASK13_LIVE_EXECUTION_ROLE="SECONDARY_NON_BLOCKING"
SUCCESS_EFFECT_LABELS=(
 "SUCCESS_PRESERVED_EFFICIENCY_GAIN",
 "SUCCESS_PRESERVED_NO_MEANINGFUL_GAIN",
 "SUCCESS_REGRESSION",
 "SUCCESS_EFFECT_UNCERTAIN",
)

def register_success_pilot(rows,max_candidates=12):
    data=list(rows)
    if len(data)>max_candidates:
        raise ValueError("success pilot exceeds preregistered candidate budget")
    ids=[x["candidate_sha256"] for x in data]
    if len(ids)!=len(set(ids)):
        raise ValueError("duplicate success candidate")
    games=[x["gamefile_sha256"] for x in data]
    if len(games)!=len(set(games)):
        raise ValueError("success pilot must use unique gamefiles")
    for row in data:
        if row.get("requires_environment_verification") is not True:
            raise ValueError("success candidate requires environment verification")
    return {
        "execution_role":TASK13_LIVE_EXECUTION_ROLE,
        "registered_candidate_sha256s":ids,
        "registered_gamefile_sha256s":games,
        "live_execution_authorized":False,
    }
