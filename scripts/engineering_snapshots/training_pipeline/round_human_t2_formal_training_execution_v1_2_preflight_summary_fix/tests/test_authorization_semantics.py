from formal_exec.common import (
    domain_sha256,
    require_domain_sha,
)


def test_authorization_domain_hash_round_trip() -> None:
    value = {
        "schema_id": "ROUND_TRAINING_EXECUTION_AUTHORIZATION_V1",
        "schema_version": 1,
        "authorization_status": "APPROVED",
        "round_id": "R",
        "authorization_sha256": "",
    }
    value["authorization_sha256"] = domain_sha256(
        value["schema_id"],
        value,
        sha_field="authorization_sha256",
    )
    require_domain_sha(
        value,
        schema_id=value["schema_id"],
        sha_field="authorization_sha256",
    )
