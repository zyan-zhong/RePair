from handoff.common import domain_sha256, require_domain_sha


def test_domain_sha_round_trip() -> None:
    value = {
        "schema_id": "TEST_SCHEMA_V1",
        "schema_version": 1,
        "payload": {"x": 1},
        "value_sha256": "",
    }
    value["value_sha256"] = domain_sha256(
        value["schema_id"],
        value,
        sha_field="value_sha256",
    )
    require_domain_sha(
        value,
        schema_id="TEST_SCHEMA_V1",
        sha_field="value_sha256",
    )
