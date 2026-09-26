"""Exact audit and scientific semantic evidence for one completed policy call."""
from __future__ import annotations
import base64
from dataclasses import dataclass
from typing import Mapping,ClassVar
from .canonical_evidence import canonical_json_text,sha256_bytes,sha256_text,strict_json_loads
from .schema_contract import validate_payload_against_schema

_ALLOWED_HEADERS=("x-request-id","content-type","content-length")
_SECRET_HEADERS={"authorization","proxy-authorization","cookie","set-cookie"}

def allowlisted_response_headers(headers:Mapping[str,str])->dict[str,str|None]:
    normalized={str(k).casefold():str(v) for k,v in headers.items()}
    if _SECRET_HEADERS.intersection(normalized): raise ValueError("secret response header is forbidden")
    return {k:normalized.get(k) for k in _ALLOWED_HEADERS}

@dataclass(frozen=True,slots=True)
class PolicyCallTransportEvidenceV1:
    request_wire_bytes:bytes
    http_status:int
    response_headers_allowlisted:tuple[tuple[str,str|None],...]
    raw_response_body:bytes
    latency_ms:int
    def __post_init__(self):
        if not isinstance(self.request_wire_bytes,bytes) or not isinstance(self.raw_response_body,bytes): raise TypeError("transport bytes must be bytes")
        if type(self.http_status) is not int or not 100<=self.http_status<=599: raise ValueError("http_status invalid")
        if type(self.latency_ms) is not int or self.latency_ms<0: raise ValueError("latency_ms invalid")
        raw_keys=tuple(k.casefold() for k,_ in self.response_headers_allowlisted)
        keys=set(raw_keys)
        if len(raw_keys)!=len(keys): raise ValueError("response headers must be unique")
        if keys!=set(_ALLOWED_HEADERS): raise ValueError("response header evidence must use exact allowlist")
        if keys&_SECRET_HEADERS: raise ValueError("secret response header forbidden")
    def headers_dict(self): return dict(self.response_headers_allowlisted)

@dataclass(frozen=True,slots=True)
class PolicyCallResultV1:
    generation:object
    transport_evidence:PolicyCallTransportEvidenceV1

@dataclass(frozen=True,slots=True)
class PolicyCallEvidenceV1:
    SCHEMA_ID:ClassVar[str]="POLICY_CALL_EVIDENCE_V1"
    schema_id:str; schema_version:int; model_call_index:int; environment_step_count_before:int; client_request_id:str; provider_request_id:str
    prompt_text:str; prompt_sha256:str; rendered_prompt_text:str; rendered_prompt_sha256:str; rendered_prompt_token_ids:tuple[int,...]; rendered_prompt_token_count:int
    request_semantics_json:str; request_semantics_sha256:str
    request_wire_bytes_base64:str; request_wire_sha256:str; http_status:int; response_headers_allowlisted:tuple[tuple[str,str|None],...]
    raw_response_body_base64:str; raw_response_body_sha256:str; raw_response_text:str; raw_response_text_sha256:str; finish_reason:str; prompt_tokens:int; completion_tokens:int; prompt_token_ids:tuple[int,...]; completion_token_ids:tuple[int,...]|None; latency_ms:int
    public_task_goal:str; public_task_goal_sha256:str; observation:str; observation_sha256:str; admissible_commands:tuple[str,...]; admissible_commands_sequence_sha256:str
    executed_history:tuple[tuple[str,str],...]; executed_history_sha256:str; interface_feedback_before:str|None; budget_before:tuple[tuple[str,int],...]
    def __post_init__(self):
        if self.schema_id!=self.SCHEMA_ID or self.schema_version!=1: raise ValueError("policy-call schema mismatch")
        if self.prompt_sha256!=sha256_text(self.prompt_text): raise ValueError("prompt hash mismatch")
        if self.rendered_prompt_sha256!=sha256_text(self.rendered_prompt_text): raise ValueError("rendered prompt hash mismatch")
        if self.rendered_prompt_token_count!=len(self.rendered_prompt_token_ids): raise ValueError("rendered token count mismatch")
        if self.request_semantics_sha256!=sha256_text(self.request_semantics_json): raise ValueError("request semantics hash mismatch")
        req=base64.b64decode(self.request_wire_bytes_base64.encode("ascii"),validate=True); resp=base64.b64decode(self.raw_response_body_base64.encode("ascii"),validate=True)
        if self.request_wire_sha256!=sha256_bytes(req): raise ValueError("request wire hash mismatch")
        wire_payload=strict_json_loads(req)
        if not isinstance(wire_payload,dict): raise ValueError("request wire must be JSON object")
        semantic_wire=dict(wire_payload)
        semantic_wire.pop("request_id",None)
        if canonical_json_text(semantic_wire)!=self.request_semantics_json:
            raise ValueError("request semantics do not match exact request bytes")
        if self.raw_response_body_sha256!=sha256_bytes(resp): raise ValueError("raw response body hash mismatch")
        if self.raw_response_text_sha256!=sha256_text(self.raw_response_text): raise ValueError("raw response text hash mismatch")
        response_payload=strict_json_loads(resp)
        if not isinstance(response_payload,dict): raise ValueError("raw response body must be JSON object")
        choices=response_payload.get("choices")
        if not isinstance(choices,list) or len(choices)!=1 or not isinstance(choices[0],dict): raise ValueError("raw response choices mismatch")
        choice=choices[0]
        message=choice.get("message")
        if not isinstance(message,dict) or message.get("content")!=self.raw_response_text: raise ValueError("raw response content mismatch")
        if choice.get("finish_reason")!=self.finish_reason: raise ValueError("finish_reason mismatch")
        usage=response_payload.get("usage")
        if not isinstance(usage,dict) or usage.get("prompt_tokens")!=self.prompt_tokens or usage.get("completion_tokens")!=self.completion_tokens:
            raise ValueError("usage mismatch")
        if tuple(response_payload.get("prompt_token_ids",()))!=self.prompt_token_ids: raise ValueError("prompt token IDs mismatch")
        observed_completion=choice.get("token_ids")
        if observed_completion is None:
            if self.completion_token_ids is not None: raise ValueError("completion token IDs mismatch")
        elif tuple(observed_completion)!=self.completion_token_ids:
            raise ValueError("completion token IDs mismatch")
        if self.public_task_goal_sha256!=sha256_text(self.public_task_goal): raise ValueError("public task goal hash mismatch")
        if self.observation_sha256!=sha256_text(self.observation): raise ValueError("observation hash mismatch")
        from .action_trace import sha256_string_sequence
        if self.admissible_commands_sequence_sha256!=sha256_string_sequence(self.admissible_commands): raise ValueError("admissible command hash mismatch")
        from .raw_policy_prompt import ExecutedTransition,sha256_executed_transitions
        hist=tuple(ExecutedTransition(a,o) for a,o in self.executed_history)
        if self.executed_history_sha256!=sha256_executed_transitions(hist): raise ValueError("executed history hash mismatch")
        raw_header_keys=tuple(k.casefold() for k,_ in self.response_headers_allowlisted)
        headers=dict(self.response_headers_allowlisted)
        if len(raw_header_keys)!=len(set(raw_header_keys)) or set(headers)!=set(_ALLOWED_HEADERS): raise ValueError("response header allowlist fields mismatch")
        if _SECRET_HEADERS.intersection(k.casefold() for k in headers): raise ValueError("secret header forbidden")
        response_id=response_payload.get("id")
        header_request_id=headers.get("x-request-id")
        expected_provider=header_request_id or response_id
        if expected_provider!=self.provider_request_id: raise ValueError("provider request ID mismatch")
        budget_keys=tuple(k for k,_ in self.budget_before)
        expected_budget=("policy_attempt_count","environment_step_count","protocol_failure_count","inadmissible_action_count","consecutive_nonexecuted_attempt_count")
        if budget_keys!=expected_budget: raise ValueError("budget_before keys/order mismatch")
        validate_payload_against_schema(schema_id=self.SCHEMA_ID,payload=self.to_dict())
    @property
    def request_wire_bytes(self): return base64.b64decode(self.request_wire_bytes_base64)
    @property
    def raw_response_body(self): return base64.b64decode(self.raw_response_body_base64)
    def to_dict(self):
        return {
        "schema_id":self.schema_id,"schema_version":self.schema_version,"model_call_index":self.model_call_index,"environment_step_count_before":self.environment_step_count_before,"client_request_id":self.client_request_id,"provider_request_id":self.provider_request_id,
        "prompt_text":self.prompt_text,"prompt_sha256":self.prompt_sha256,"rendered_prompt_text":self.rendered_prompt_text,"rendered_prompt_sha256":self.rendered_prompt_sha256,"rendered_prompt_token_ids":list(self.rendered_prompt_token_ids),"rendered_prompt_token_count":self.rendered_prompt_token_count,
        "request_semantics_json":self.request_semantics_json,"request_semantics_sha256":self.request_semantics_sha256,
        "request_wire_bytes_base64":self.request_wire_bytes_base64,"request_wire_sha256":self.request_wire_sha256,"http_status":self.http_status,"response_headers_allowlisted":dict(self.response_headers_allowlisted),
        "raw_response_body_base64":self.raw_response_body_base64,"raw_response_body_sha256":self.raw_response_body_sha256,"raw_response_text":self.raw_response_text,"raw_response_text_sha256":self.raw_response_text_sha256,"finish_reason":self.finish_reason,"prompt_tokens":self.prompt_tokens,"completion_tokens":self.completion_tokens,"prompt_token_ids":list(self.prompt_token_ids),"completion_token_ids":None if self.completion_token_ids is None else list(self.completion_token_ids),"latency_ms":self.latency_ms,
        "public_task_goal":self.public_task_goal,"public_task_goal_sha256":self.public_task_goal_sha256,"observation":self.observation,"observation_sha256":self.observation_sha256,"admissible_commands":list(self.admissible_commands),"admissible_commands_sequence_sha256":self.admissible_commands_sequence_sha256,
        "executed_history":[{"action":a,"resulting_observation":o} for a,o in self.executed_history],"executed_history_sha256":self.executed_history_sha256,"interface_feedback_before":self.interface_feedback_before,"budget_before":dict(self.budget_before)}
    def to_json(self): return canonical_json_text(self.to_dict())
    @classmethod
    def from_dict(cls,value:object):
        if not isinstance(value,dict): raise TypeError("policy call wire value must be object")
        validate_payload_against_schema(schema_id=cls.SCHEMA_ID,payload=value)
        history=value["executed_history"]
        budget=value["budget_before"]
        headers=value["response_headers_allowlisted"]
        return cls(
            value["schema_id"],value["schema_version"],value["model_call_index"],value["environment_step_count_before"],value["client_request_id"],value["provider_request_id"],
            value["prompt_text"],value["prompt_sha256"],value["rendered_prompt_text"],value["rendered_prompt_sha256"],tuple(value["rendered_prompt_token_ids"]),value["rendered_prompt_token_count"],
            value["request_semantics_json"],value["request_semantics_sha256"],
            value["request_wire_bytes_base64"],value["request_wire_sha256"],value["http_status"],tuple((k,headers[k]) for k in _ALLOWED_HEADERS),
            value["raw_response_body_base64"],value["raw_response_body_sha256"],value["raw_response_text"],value["raw_response_text_sha256"],value["finish_reason"],value["prompt_tokens"],value["completion_tokens"],tuple(value["prompt_token_ids"]),None if value["completion_token_ids"] is None else tuple(value["completion_token_ids"]),value["latency_ms"],
            value["public_task_goal"],value["public_task_goal_sha256"],value["observation"],value["observation_sha256"],tuple(value["admissible_commands"]),value["admissible_commands_sequence_sha256"],
            tuple((item["action"],item["resulting_observation"]) for item in history),value["executed_history_sha256"],value["interface_feedback_before"],tuple((k,budget[k]) for k in ("policy_attempt_count","environment_step_count","protocol_failure_count","inadmissible_action_count","consecutive_nonexecuted_attempt_count")),
        )
    @classmethod
    def from_json(cls,value:str|bytes):
        return cls.from_dict(strict_json_loads(value))

def exact_policy_call_payload(evidence:PolicyCallEvidenceV1)->dict[str,object]: return evidence.to_dict()

def semantic_policy_call_payload(evidence:PolicyCallEvidenceV1)->dict[str,object]:
    p=evidence.to_dict()
    for k in ("client_request_id","provider_request_id","request_wire_bytes_base64","request_wire_sha256","http_status","response_headers_allowlisted","raw_response_body_base64","raw_response_body_sha256","latency_ms"):
        p.pop(k,None)
    return p


def build_policy_call_evidence(*,model_call_index:int,public_task_goal:str,observation:str,admissible_commands,executed_history,interface_feedback_before,budget_before,request,expected_prompt,generation,transport_evidence:PolicyCallTransportEvidenceV1):
    from .action_trace import sha256_string_sequence
    from .raw_policy_prompt import canonical_executed_transitions_json,sha256_executed_transitions
    if expected_prompt.rendered_prompt_text is None:
        raise ValueError("rendered prompt text is required for P1 complete evidence")
    history_pairs=tuple((x.action,x.resulting_observation) for x in executed_history)
    history_hash=sha256_executed_transitions(executed_history)
    feedback=None if interface_feedback_before is None else interface_feedback_before.value
    semantic_request=request.to_wire_dict()
    semantic_request=dict(semantic_request)
    semantic_request.pop("request_id",None)
    from .canonical_evidence import canonical_json_text
    request_semantics_json=canonical_json_text(semantic_request)
    budget_pairs=tuple((name,getattr(budget_before,name)) for name in ("policy_attempt_count","environment_step_count","protocol_failure_count","inadmissible_action_count","consecutive_nonexecuted_attempt_count"))
    return PolicyCallEvidenceV1(
        "POLICY_CALL_EVIDENCE_V1",1,model_call_index,budget_before.environment_step_count,request.request_id,generation.provider_request_id,
        request.prompt_text,sha256_text(request.prompt_text),expected_prompt.rendered_prompt_text,expected_prompt.rendered_prompt_text_sha256,expected_prompt.rendered_token_ids,expected_prompt.prompt_token_count,
        request_semantics_json,sha256_text(request_semantics_json),
        base64.b64encode(transport_evidence.request_wire_bytes).decode("ascii"),sha256_bytes(transport_evidence.request_wire_bytes),transport_evidence.http_status,transport_evidence.response_headers_allowlisted,
        base64.b64encode(transport_evidence.raw_response_body).decode("ascii"),sha256_bytes(transport_evidence.raw_response_body),generation.raw_response_text,sha256_text(generation.raw_response_text),generation.finish_reason,generation.prompt_tokens,generation.completion_tokens,generation.prompt_token_ids,generation.token_ids,generation.latency_ms,
        public_task_goal,sha256_text(public_task_goal),observation,sha256_text(observation),tuple(admissible_commands),sha256_string_sequence(tuple(admissible_commands)),history_pairs,history_hash,feedback,budget_pairs,
    )
