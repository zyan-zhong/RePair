from __future__ import annotations
from collections.abc import Mapping
from pchsi.reference_loop.canonical import domain_hash
from .schema_registry import validate_artifact


def _finalize(domain: str, field: str, value: Mapping[str,object], schema_id: str):
    out=dict(value); out[field]="0"*64
    out[field]=domain_hash(domain,out,excluded_field=field)
    validate_artifact(schema_id,out)
    return out


def build_scientific_unit_identity(**kwargs):
    value={"schema_id":"SCIENTIFIC_UNIT_IDENTITY_V1","schema_version":1,
           **kwargs,"identity_sha256":"0"*64}
    return _finalize("SCIENTIFIC_UNIT_IDENTITY_V1","identity_sha256",value,
                     "SCIENTIFIC_UNIT_IDENTITY_V1")


def build_logical_call_record(**kwargs):
    value={"schema_id":"LOGICAL_CALL_RECORD_V1","schema_version":1,
           **kwargs,"logical_call_sha256":"0"*64}
    return _finalize("LOGICAL_CALL_RECORD_V1","logical_call_sha256",value,
                     "LOGICAL_CALL_RECORD_V1")


def build_transport_attempt_record(**kwargs):
    value={"schema_id":"TRANSPORT_ATTEMPT_RECORD_V1","schema_version":1,
           **kwargs,"attempt_sha256":"0"*64}
    return _finalize("TRANSPORT_ATTEMPT_RECORD_V1","attempt_sha256",value,
                     "TRANSPORT_ATTEMPT_RECORD_V1")
