from pchsi.analyzer.grouping import build_group_manifests


def _result(statement="first"):
    return {"local_result_sha256":"a"*64,"task_id":"t","gamefile_sha256":"b"*64,
            "error_instances":[
                {"error_instance_id":"e1","resolution_status":"RESOLVED",
                 "terminal_footprint":"BUDGET_ONLY_IMPACT",
                 "mechanism_hypotheses":[{"statement":statement}]},
                {"error_instance_id":"e2","resolution_status":"ACTIVE",
                 "terminal_footprint":"DIRECT_TERMINAL_IMPACT",
                 "mechanism_hypotheses":[{"statement":"other"}]},
            ]}


def test_episode_can_join_multiple_groups_and_prose_is_not_key() -> None:
    sig={
      ("a"*64,"e1"):{"task_family":"f","mechanical_signature_sha256":"1"*64,
                     "progress_signature_sha256":"2"*64},
      ("a"*64,"e2"):{"task_family":"f","mechanical_signature_sha256":"3"*64,
                     "progress_signature_sha256":"4"*64},
    }
    first=build_group_manifests([_result("x")],sig)
    second=build_group_manifests([_result("changed prose")],sig)
    assert {x["group_id"] for x in first}=={x["group_id"] for x in second}
    assert sum(len(x["membership_records"]) for x in first)==2
    assert {x["inference_cluster_unit"] for x in first}=={"TASK_GAMEFILE"}
