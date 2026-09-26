"""Fail-closed projection of validated source-conditioned candidate bytes."""

from __future__ import annotations
from collections.abc import Mapping
from pchsi.reference_loop.canonical import domain_hash
from .authorities import CrosscheckDisposition
from .schema_contract import validate_payload_against_schema, verify_domain_hash

SCHEMA_BY_KIND={
 "FAILURE_REPAIR":"ANALYZER_REPAIR_CANDIDATE_V1",
 "SUCCESS_OPTIMIZATION":"ANALYZER_SUCCESS_OPTIMIZATION_CANDIDATE_V1",
 "SUCCESS_WORKFLOW_REFERENCE":"ANALYZER_SUCCESS_WORKFLOW_REFERENCE_V1",
 "REGRESSION_GUARD":"ANALYZER_REGRESSION_GUARD_V1",
}


def _validate_proposal(proposal: Mapping[str,object]) -> None:
    validate_payload_against_schema(
        schema_id="ANALYZER_SOURCE_CONDITIONED_PROPOSAL_V1",payload=proposal
    )
    verify_domain_hash(
        payload=proposal,domain="ANALYZER_SOURCE_CONDITIONED_PROPOSAL_V1",
        hash_field="source_proposal_sha256",
    )
    exact=proposal["exact_action"]
    option=proposal["option_actions"]
    termination=proposal["termination_condition"]
    if exact is not None:
        if not isinstance(exact,str) or not exact or option or termination is not None:
            raise ValueError("source proposal exact-action fields invalid")
    else:
        if not isinstance(option,list) or not 1<=len(option)<=4:
            raise ValueError("source proposal short option invalid")
        if not isinstance(termination,str) or not termination:
            raise ValueError("source proposal short option lacks termination")


def project_candidate(
    proposal: Mapping[str,object]|None,
    source_state: Mapping[str,object],
    *,
    candidate_kind: str,
    crosscheck_disposition: str="ACCEPT",
)->dict[str,object]:
    sid=SCHEMA_BY_KIND[candidate_kind]
    disposition=CrosscheckDisposition(crosscheck_disposition)
    base={
        "schema_id":sid,"schema_version":1,"candidate_kind":candidate_kind,
        "source_state_sha256":source_state["source_state_sha256"],
        "menu_sha256":source_state["menu_sha256"],
        "source_proposal_sha256":"0"*64 if proposal is None else proposal["source_proposal_sha256"],
        "candidate_status":"ABSTAIN",
        "exact_action":None,"option_actions":[],"termination_condition":None,
        "requires_environment_verification":True,
        "live_menu_revalidation_required":True,
        "all_intervention_actions_count_against_environment_budget":True,
        "candidate_sha256":"0"*64,
    }
    if proposal is not None:
        _validate_proposal(proposal)
        if disposition in {
            CrosscheckDisposition.REQUIRE_ABSTENTION,
            CrosscheckDisposition.REJECT,
        }:
            base["candidate_status"]="REJECTED_CROSSCHECK"
        elif (
            proposal["source_state_sha256"]!=source_state["source_state_sha256"]
            or proposal["menu_sha256"]!=source_state["menu_sha256"]
        ):
            base["candidate_status"]="REJECTED_SOURCE_BINDING"
        else:
            menu=source_state["admissible_commands"]
            if not isinstance(menu,list):
                raise ValueError("source admissible menu must be array")
            exact=proposal["exact_action"]
            option=proposal["option_actions"]
            if exact is not None:
                if exact not in menu:
                    base["candidate_status"]="REJECTED_SOURCE_BINDING"
                else:
                    base["candidate_status"]="EXECUTABLE_EXACT_ACTION"
                    base["exact_action"]=exact
            else:
                # Only the first option action is executable at the source state.
                # Every later action must be revalidated against the live menu by F1.
                if option[0] not in menu:
                    base["candidate_status"]="REJECTED_SOURCE_BINDING"
                else:
                    base["candidate_status"]="EXECUTABLE_SHORT_OPTION"
                    base["option_actions"]=list(option)
                    base["termination_condition"]=proposal["termination_condition"]
    base["candidate_sha256"]=domain_hash(
        sid,base,excluded_field="candidate_sha256"
    )
    validate_payload_against_schema(schema_id=sid,payload=base)
    return base
