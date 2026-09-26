"""Local-only tokenizer rendering evidence for E1 policy requests."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol
from .canonical_evidence import canonical_json_bytes, require_lower_sha256, require_nonnegative_int, sha256_bytes, sha256_text

@dataclass(frozen=True, slots=True)
class RenderedPromptEvidence:
    raw_policy_prompt_sha256:str
    chat_template_sha256:str
    rendered_prompt_text_sha256:str
    rendered_token_ids:tuple[int,...]
    rendered_token_ids_sha256:str
    prompt_token_count:int
    rendered_prompt_text:str|None=None
    def __post_init__(self):
        for name in ("raw_policy_prompt_sha256","chat_template_sha256","rendered_prompt_text_sha256","rendered_token_ids_sha256"): require_lower_sha256(name,getattr(self,name))
        require_nonnegative_int("prompt_token_count",self.prompt_token_count)
        if self.prompt_token_count!=len(self.rendered_token_ids): raise ValueError("prompt_token_count mismatch")
        for i,item in enumerate(self.rendered_token_ids): require_nonnegative_int(f"rendered_token_ids[{i}]",item)
        if self.rendered_prompt_text is not None:
            if not isinstance(self.rendered_prompt_text,str): raise TypeError("rendered_prompt_text must be str or None")
            if sha256_text(self.rendered_prompt_text)!=self.rendered_prompt_text_sha256: raise ValueError("rendered_prompt_text SHA-256 mismatch")
class PromptRenderer(Protocol):
    def render(self,*,prompt_text:str)->RenderedPromptEvidence: ...
class HuggingFaceTokenizerFactory:
    def load(self,**kwargs):
        from transformers import AutoTokenizer
        model_path=kwargs.pop("model_path")
        return AutoTokenizer.from_pretrained(model_path,**kwargs)
class LocalTokenizerPromptRenderer:
    def __init__(self,*,model_path:str,revision:str,chat_template_sha256:str,tokenizer_factory):
        if not model_path or not revision: raise ValueError("model_path and revision must be non-empty")
        require_lower_sha256("chat_template_sha256",chat_template_sha256)
        self._model_path=model_path; self._revision=revision; self._template=chat_template_sha256; self._factory=tokenizer_factory
    def render(self,*,prompt_text:str)->RenderedPromptEvidence:
        tokenizer=self._factory.load(model_path=self._model_path,revision=self._revision,local_files_only=True,trust_remote_code=False)
        template=getattr(tokenizer,"chat_template",None)
        if not isinstance(template,str) or not template: raise ValueError("tokenizer chat_template must be non-empty")
        observed=sha256_text(template)
        if observed!=self._template: raise ValueError("chat template SHA-256 mismatch")
        messages=[{"role":"user","content":prompt_text}]
        rendered=tokenizer.apply_chat_template(messages,tokenize=False,add_generation_prompt=True,continue_final_message=False)
        raw_ids=tokenizer.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,continue_final_message=False)
        if not isinstance(rendered,str) or not isinstance(raw_ids,(list,tuple)): raise TypeError("invalid tokenizer rendering")
        ids=tuple(require_nonnegative_int(f"token[{i}]",item) for i,item in enumerate(raw_ids))
        return RenderedPromptEvidence(sha256_text(prompt_text),observed,sha256_text(rendered),ids,sha256_bytes(canonical_json_bytes(list(ids))),len(ids),rendered)
