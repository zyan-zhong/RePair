from stage0.twin_contract import (
    audit_runtime_binding_documents,
    audit_twin_documents,
)


def _documents() -> dict[str, dict]:
    return {
        "review": {
            "review_status": "READY_FOR_OFFOFF_EXECUTION_AUTHORIZATION_REVIEW",
            "select_task_count": 17,
            "replicate_seeds": [17, 31, 47, 73, 101],
            "paired_cell_count": 85,
            "total_condition_cell_count": 170,
            "evaluation_execution_authorized": False,
            "evaluation_execution_count": 0,
            "next_gate": "OFFOFF_EXECUTION_AUTHORIZATION_AND_RUNTIME_READINESS",
        },
        "protocol": {
            "status": "PASS",
            "selected_task_count": 17,
            "replicate_seeds": [17, 31, 47, 73, 101],
            "paired_cell_count": 85,
            "total_condition_cell_count": 170,
            "grid_equal": True,
            "memory_state": "OFF",
            "harness_state": "OFF",
            "protocol_equality_sha256": (
                "d831c966daf214955683541d4a0434b85"
                "feb6ee696eb854bec301a334297ebca"
            ),
        },
        "handoff": {
            "status": "READY_FOR_OFFOFF_EXECUTION_AUTHORIZATION_REVIEW",
            "select_task_count": 17,
            "replicate_seeds": [17, 31, 47, 73, 101],
            "paired_cell_count": 85,
            "total_condition_cell_count": 170,
            "memory_off": True,
            "harness_off": True,
            "evaluation_execution_authorized": False,
            "evaluation_execution_count": 0,
            "promotion_decision_authorized": False,
            "promotion_eligible": False,
            "handoff_sha256": (
                "22c9ad08bc0a74f315d03170bd5cffc6"
                "45f113c06603c5dff161778cf70e211a"
            ),
            "next_gate": "OFFOFF_EXECUTION_AUTHORIZATION_AND_RUNTIME_READINESS",
        },
    }


def test_twin_contract_accepts_exact_engineering_pilot_boundary() -> None:
    result = audit_twin_documents(_documents())
    assert result["select_task_count"] == 17
    assert result["paired_cell_count"] == 85
    assert result["total_condition_cell_count"] == 170
    assert result["paper_efficacy_evidence"] is False
    assert result["promotion_eligible"] is False


def test_twin_contract_rejects_promotion_or_paper_claim() -> None:
    docs = _documents()
    docs["handoff"]["promotion_eligible"] = True
    try:
        audit_twin_documents(docs)
    except ValueError as exc:
        assert "promotion" in str(exc).lower()
    else:
        raise AssertionError("promotion boundary was not rejected")



def test_runtime_binding_rejects_wrong_adapter_path() -> None:
    server = {
        "static_lora_registry": [
            {
                "served_model_name": "P4-R1-Q2-BAD-TRAIN17",
                "adapter_path": "/wrong-parent",
                "adapter_bundle_sha256": (
                    "b296f2254b1fa1f2e141dffd3f6b5af"
                    "903f839df4790ffcb245fd8dd57773ace"
                ),
            },
            {
                "served_model_name":
                    "P4-R2-HUMAN-T2-DIAGNOSTIC-TRAIN17",
                "adapter_path": "/wrong-candidate",
                "adapter_bundle_sha256": (
                    "908acf081e80008800284653c3340c39"
                    "7353eef0de08ee044f06810cab2a251e"
                ),
            },
        ],
        "max_loras": 1,
        "max_cpu_loras": 2,
    }
    parent_runtime = {
        "checkpoint_instance_id": "P4-R1-Q2-BAD-TRAIN17",
        "adapter_path": "/wrong-parent",
        "adapter_bundle_sha256": (
            "b296f2254b1fa1f2e141dffd3f6b5af"
            "903f839df4790ffcb245fd8dd57773ace"
        ),
    }
    candidate_runtime = {
        "checkpoint_instance_id":
            "P4-R2-HUMAN-T2-DIAGNOSTIC-TRAIN17",
        "adapter_path": "/wrong-candidate",
        "adapter_bundle_sha256": (
            "908acf081e80008800284653c3340c39"
            "7353eef0de08ee044f06810cab2a251e"
        ),
    }
    parent_condition = {
        "checkpoint_sha256": parent_runtime[
            "adapter_bundle_sha256"
        ],
    }
    candidate_condition = {
        "checkpoint_sha256": candidate_runtime[
            "adapter_bundle_sha256"
        ],
    }

    try:
        audit_runtime_binding_documents(
            server=server,
            parent_runtime=parent_runtime,
            candidate_runtime=candidate_runtime,
            parent_condition=parent_condition,
            candidate_condition=candidate_condition,
        )
    except Exception as exc:
        assert "PATH" in str(exc).upper()
    else:
        raise AssertionError("wrong adapter paths were accepted")
