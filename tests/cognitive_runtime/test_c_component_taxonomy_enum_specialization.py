from pchsi.analyzer.component_attribution import load_taxonomy
from pchsi.analyzer.schema_contract import load_schema
from pchsi.cognitive_runtime.request_renderer import (
    _specialize_component_taxonomy_enums,
)
import inspect
from pchsi.cognitive_runtime import request_renderer


def test_c_component_taxonomy_specialization_uses_canonical_taxonomy():
    schema = load_schema("ANALYZER_COMPONENT_ATTRIBUTION_V1")
    taxonomy = list(load_taxonomy())

    specialized = _specialize_component_taxonomy_enums(schema)

    properties = specialized["properties"]
    assert properties["principal_component"]["enum"] == taxonomy
    assert (
        properties["secondary_components"]["items"]["enum"]
        == taxonomy
    )


def test_c_component_taxonomy_specialization_does_not_mutate_static_schema():
    schema = load_schema("ANALYZER_COMPONENT_ATTRIBUTION_V1")
    assert "enum" not in schema["properties"]["principal_component"]
    assert (
        "enum"
        not in schema["properties"]["secondary_components"]["items"]
    )

    _specialize_component_taxonomy_enums(schema)

    assert "enum" not in schema["properties"]["principal_component"]
    assert (
        "enum"
        not in schema["properties"]["secondary_components"]["items"]
    )


def test_c_renderer_has_generation_time_taxonomy_specialization_hook():
    source = inspect.getsource(request_renderer.render_stage_request)
    assert 'if stage_id == "C":' in source
    assert "_specialize_component_taxonomy_enums(schema)" in source
