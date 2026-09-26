from stage0.generic_select_artifact_patch import (
    patch_action_trace_source,
    patch_episode_artifact_schema,
    patch_schema_models_source,
)


def test_action_trace_patch_generalizes_only_trained_branch() -> None:
    source = """
            elif (
                self.logical_condition_id
                == "P4-R1-Q2-BAD"
            ):
                if self.training_seed is None:
                    raise ValueError(
                        "SELECT pi1 trace requires training_seed"
                    )

                if (
                    self.model_name
                    != self.checkpoint_instance_id
                ):
                    raise ValueError(
                        "SELECT pi1 model/checkpoint mismatch"
                    )

            else:
                raise ValueError(
                    "unknown SELECT logical condition"
                )
"""
    patched = patch_action_trace_source(source)

    assert '== "P4-R1-Q2-BAD"' not in patched
    assert "unknown SELECT logical condition" not in patched
    assert "SELECT trained trace requires training_seed" in patched
    assert "SELECT trained model/checkpoint mismatch" in patched


def test_schema_models_patch_generalizes_trained_episode_branch() -> None:
    source = """
            elif (
                self.logical_condition_id
                == "P4-R1-Q2-BAD"
            ):
                if (
                    type(self.training_seed)
                    is not int
                    or self.training_seed < 0
                ):
                    raise ValueError(
                        "SELECT pi1 episode requires "
                        "non-negative training_seed"
                    )

            else:
                raise ValueError(
                    "unknown SELECT logical condition"
                )
"""
    patched = patch_schema_models_source(source)

    assert '== "P4-R1-Q2-BAD"' not in patched
    assert "unknown SELECT logical condition" not in patched
    assert "SELECT trained episode requires " in patched


def test_episode_artifact_schema_patch_replaces_closed_enum() -> None:
    value = {
        "properties": {
            "logical_condition_id": {
                "enum": [
                    "P4-R0-PI0",
                    "P4-R1-Q2-BAD",
                ],
                "type": "string",
            }
        }
    }

    patched = patch_episode_artifact_schema(value)

    logical = patched["properties"]["logical_condition_id"]
    assert "enum" not in logical
    assert logical["type"] == "string"
    assert logical["minLength"] == 1
    assert logical["pattern"] == (
        "^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
    )
