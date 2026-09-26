from __future__ import annotations

from collections.abc import Mapping

from pchsi.reference_loop.canonical import domain_hash
from .schema_registry import validate_artifact

LOCAL_CONDITIONS = ("A0", "A1")
GROUP_CONDITIONS = ("A2", "A3")


def validate_formal_dag_v2(value: Mapping[str, object]) -> None:
    """Validate the hierarchical Formal Analyzer registry.

    Local conditions are registered over the pre-registered episode-level U_reg.
    Group conditions are registered only after Formal A1 bytes deterministically
    materialize group membership.
    """
    validate_artifact("FORMAL_ANALYZER_DAG_REGISTRY_V2", value)

    observed_sha = domain_hash(
        "FORMAL_ANALYZER_DAG_REGISTRY_V2",
        value,
        excluded_field="formal_dag_sha256",
    )
    if value["formal_dag_sha256"] != observed_sha:
        raise ValueError("formal DAG V2 SHA mismatch")

    local_units = list(value["registered_local_unit_ids"])
    if len(local_units) != len(set(local_units)):
        raise ValueError("duplicate registered local unit")
    local_unit_set = set(local_units)

    local_rows = list(value["local_condition_rows"])
    local_observed: set[tuple[str, str]] = set()
    local_by_unit = {unit: {} for unit in local_units}

    for row in local_rows:
        source = row["source_unit_id"]
        condition = row["condition_id"]
        key = (source, condition)
        if key in local_observed:
            raise ValueError("duplicate local unit-condition row")
        local_observed.add(key)
        if source not in local_by_unit:
            raise ValueError("local condition row outside registered U_reg")
        local_by_unit[source][condition] = row

    expected_local = {
        (unit, condition)
        for unit in local_units
        for condition in LOCAL_CONDITIONS
    }
    if local_observed != expected_local:
        raise ValueError("formal DAG V2 local registry is not U_reg x A0-A1")

    a1_sha_by_unit: dict[str, str] = {}
    for unit, conditions in local_by_unit.items():
        a0 = conditions["A0"]
        a1 = conditions["A1"]

        if (
            a0["common_evidence_pack_sha256"]
            != a1["common_evidence_pack_sha256"]
        ):
            raise ValueError("A0/A1 common evidence differs")

        if a0["memory_pack_sha256"] is not None:
            raise ValueError("A0 cannot receive Memory")
        if a1["memory_pack_sha256"] is not None:
            raise ValueError("A1 cannot receive Memory")

        if a0["a1_local_result_sha256"] is not None:
            raise ValueError("A0 cannot bind A1 result")

        a1_sha = a1["a1_local_result_sha256"]
        if not isinstance(a1_sha, str):
            raise ValueError("A1 must bind its exact Formal local-result SHA")
        a1_sha_by_unit[unit] = a1_sha

    group_manifests = list(value["registered_group_manifest_sha256s"])
    if len(group_manifests) != len(set(group_manifests)):
        raise ValueError("duplicate registered group manifest")
    group_manifest_set = set(group_manifests)

    group_rows = list(value["group_condition_rows"])
    group_observed: set[tuple[str, str]] = set()
    group_by_manifest = {manifest: {} for manifest in group_manifests}

    for row in group_rows:
        manifest = row["group_manifest_sha256"]
        condition = row["condition_id"]
        key = (manifest, condition)
        if key in group_observed:
            raise ValueError("duplicate group-condition row")
        group_observed.add(key)
        if manifest not in group_by_manifest:
            raise ValueError("group condition row outside registered groups")
        group_by_manifest[manifest][condition] = row

    expected_group = {
        (manifest, condition)
        for manifest in group_manifests
        for condition in GROUP_CONDITIONS
    }
    if group_observed != expected_group:
        raise ValueError("formal DAG V2 group registry is not groups x A2-A3")

    if group_manifests:
        if value["group_runtime_input_registry_sha256"] is None:
            raise ValueError("group runtime registry SHA required when groups exist")
    elif value["group_runtime_input_registry_sha256"] is not None:
        raise ValueError("group runtime registry SHA must be null before groups exist")

    for manifest, conditions in group_by_manifest.items():
        a2 = conditions["A2"]
        a3 = conditions["A3"]

        for field in (
            "group_id",
            "group_manifest_sha256",
            "member_bindings",
            "a1_local_result_sha256s",
            "current_evidence_sha256s",
        ):
            if a2[field] != a3[field]:
                raise ValueError(f"A2/A3 grouped evidence drift: {field}")

        if a2["memory_pack_sha256"] is not None:
            raise ValueError("A2 cannot receive Memory")
        if a3["memory_pack_sha256"] is None:
            raise ValueError("A3 requires exactly one frozen Memory identity")

        bindings = list(a2["member_bindings"])
        binding_keys: set[tuple[str, str]] = set()
        observed_a1 = set()

        for binding in bindings:
            source = binding["source_unit_id"]
            error_id = binding["error_instance_id"]
            key = (source, error_id)
            if key in binding_keys:
                raise ValueError("duplicate group member binding")
            binding_keys.add(key)

            if source not in local_unit_set:
                raise ValueError("group member outside Formal local U_reg")

            expected_a1_sha = a1_sha_by_unit[source]
            if binding["a1_local_result_sha256"] != expected_a1_sha:
                raise ValueError("group member does not byte-reuse Formal A1 result")
            observed_a1.add(expected_a1_sha)

        declared_a1 = list(a2["a1_local_result_sha256s"])
        if declared_a1 != sorted(set(declared_a1)):
            raise ValueError("group A1 SHA identities must be sorted unique")
        if set(declared_a1) != observed_a1:
            raise ValueError("group plural A1 SHA identities mismatch member bindings")

        current = list(a2["current_evidence_sha256s"])
        if current != sorted(set(current)):
            raise ValueError("group current evidence SHA identities must be sorted unique")
