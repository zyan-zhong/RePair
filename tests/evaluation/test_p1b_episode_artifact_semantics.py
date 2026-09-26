from pchsi.evaluation.episode_artifact import AttemptBundleBytes


def test_attempt_bundle_has_policy_calls_jsonl_field() -> None:
    assert "policy_calls_jsonl" in AttemptBundleBytes.__dataclass_fields__
