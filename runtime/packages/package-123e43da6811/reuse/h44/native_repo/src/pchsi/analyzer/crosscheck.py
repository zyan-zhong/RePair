"""Immutable, validated cross-check sidecars."""

from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
from pchsi.reference_loop.canonical import domain_hash
from .schema_contract import validate_payload_against_schema, verify_domain_hash
from .authorities import CrosscheckDisposition


def _validate_source_balance(out: Mapping[str,object]) -> None:
    current=list(out["current_evidence_sha256s"])
    historical=list(out["historical_evidence_sha256s"])
    if historical and not current and out["disposition"]=="ACCEPT":
        raise ValueError("historical-only claim cannot be ACCEPTed without current evidence")


def finalize_crosscheck(value: Mapping[str,object])->dict[str,object]:
    out=deepcopy(dict(value))
    CrosscheckDisposition(out["disposition"])
    _validate_source_balance(out)
    out["crosscheck_sha256"]="0"*64
    out["crosscheck_sha256"]=domain_hash(
        "ANALYZER_CROSSCHECK_RESULT_V1",out,excluded_field="crosscheck_sha256"
    )
    validate_payload_against_schema(
        schema_id="ANALYZER_CROSSCHECK_RESULT_V1",payload=out
    )
    return out


def validate_crosscheck(sidecar: Mapping[str,object]) -> None:
    validate_payload_against_schema(
        schema_id="ANALYZER_CROSSCHECK_RESULT_V1",payload=sidecar
    )
    verify_domain_hash(
        payload=sidecar,domain="ANALYZER_CROSSCHECK_RESULT_V1",
        hash_field="crosscheck_sha256",
    )
    CrosscheckDisposition(sidecar["disposition"])
    _validate_source_balance(sidecar)


def apply_crosscheck_disposition(
    original: Mapping[str,object],sidecar: Mapping[str,object]
)->dict[str,object]:
    validate_crosscheck(sidecar)
    target=sidecar["target_artifact_sha256"]
    known={
        original.get("local_result_sha256"),original.get("group_result_sha256"),
        original.get("profile_sha256"),original.get("policy_profile_sha256"),
    }
    if target not in known:
        raise ValueError("crosscheck target mismatch")
    return {
        "target_artifact":deepcopy(dict(original)),
        "crosscheck_sidecar":deepcopy(dict(sidecar)),
        "effective_disposition":sidecar["disposition"],
    }
