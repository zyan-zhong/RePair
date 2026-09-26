from pchsi.evaluation.rendered_prompt import RenderedPromptEvidence
from pchsi.evaluation.canonical_evidence import canonical_json_bytes,sha256_bytes,sha256_text

def test_rendered_prompt_text_is_bound_to_hash():
    r=RenderedPromptEvidence("a"*64,"b"*64,sha256_text("rendered"),(1,2),sha256_bytes(canonical_json_bytes([1,2])),2,"rendered")
    assert r.rendered_prompt_text=="rendered"
