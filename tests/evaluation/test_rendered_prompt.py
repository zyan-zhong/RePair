from __future__ import annotations
from pchsi.evaluation.canonical_evidence import canonical_json_bytes, sha256_bytes, sha256_text
from pchsi.evaluation.rendered_prompt import LocalTokenizerPromptRenderer

class FakeTokenizer:
    chat_template="template-v1"
    def apply_chat_template(self,messages,*,tokenize,add_generation_prompt,continue_final_message):
        assert messages==[{"role":"user","content":"PROMPT"}]
        assert add_generation_prompt is True and continue_final_message is False
        return [11,12,13] if tokenize else "<user>PROMPT</user><assistant>"
class Factory:
    def __init__(self): self.calls=[]
    def load(self,**kwargs): self.calls.append(kwargs); return FakeTokenizer()

def test_renderer_uses_local_files_only_and_no_remote_code() -> None:
    factory=Factory()
    renderer=LocalTokenizerPromptRenderer(model_path="/models/qwen",revision="rev",chat_template_sha256=sha256_text("template-v1"),tokenizer_factory=factory)
    evidence=renderer.render(prompt_text="PROMPT")
    assert factory.calls==[{"model_path":"/models/qwen","revision":"rev","local_files_only":True,"trust_remote_code":False}]
    assert evidence.rendered_token_ids==(11,12,13)
    assert evidence.rendered_token_ids_sha256==sha256_bytes(canonical_json_bytes([11,12,13]))
