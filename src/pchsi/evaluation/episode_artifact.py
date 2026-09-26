"""Deterministic semantic and exact bytes for one E1/P1 attempt bundle."""
from __future__ import annotations
from collections.abc import Sequence
from dataclasses import dataclass, replace
from .action_trace import ActionTrace,ExecutionStatus
from .canonical_evidence import canonical_json_bytes,sha256_bytes
from .policy_call_evidence import PolicyCallEvidenceV1,semantic_policy_call_payload
from .schema_models import EpisodeArtifactV1,PublicTransitionRecordV1

_LEGACY_BUNDLE_FILE_ORDER=("attempt.json","action_traces.jsonl","public_transitions.jsonl","SHA256SUMS")
_P1_BUNDLE_FILE_ORDER=("attempt.json","action_traces.jsonl","policy_calls.jsonl","public_transitions.jsonl","SHA256SUMS")

@dataclass(frozen=True,slots=True)
class AttemptBundleBytes:
    attempt_json:bytes
    action_traces_jsonl:bytes
    public_transitions_jsonl:bytes
    checksums_text:bytes
    episode_semantic_sha256:str
    attempt_bundle_sha256:str
    policy_calls_jsonl:bytes|None=None
    def file_bytes(self):
        if self.policy_calls_jsonl is None:
            return (("attempt.json",self.attempt_json),("action_traces.jsonl",self.action_traces_jsonl),("public_transitions.jsonl",self.public_transitions_jsonl),("SHA256SUMS",self.checksums_text))
        return (("attempt.json",self.attempt_json),("action_traces.jsonl",self.action_traces_jsonl),("policy_calls.jsonl",self.policy_calls_jsonl),("public_transitions.jsonl",self.public_transitions_jsonl),("SHA256SUMS",self.checksums_text))

def _freeze_traces(traces):
    if isinstance(traces,(str,bytes,bytearray)): raise TypeError("traces must be sequence")
    f=tuple(traces)
    if any(not isinstance(x,ActionTrace) for x in f): raise TypeError("traces must contain ActionTrace")
    if tuple(x.model_call_index for x in f)!=tuple(range(len(f))): raise ValueError("traces must be ordered by contiguous model_call_index")
    return f

def _freeze_policy_calls(policy_calls):
    if policy_calls is None: return None
    if isinstance(policy_calls,(str,bytes,bytearray)): raise TypeError("policy_calls must be sequence")
    f=tuple(policy_calls)
    if any(not isinstance(x,PolicyCallEvidenceV1) for x in f): raise TypeError("policy_calls must contain PolicyCallEvidenceV1")
    if tuple(x.model_call_index for x in f)!=tuple(range(len(f))): raise ValueError("policy_calls must be ordered by contiguous model_call_index")
    return f

def _freeze_transitions(transitions):
    if isinstance(transitions,(str,bytes,bytearray)): raise TypeError("public_transitions must be sequence")
    f=tuple(transitions)
    if any(not isinstance(x,PublicTransitionRecordV1) for x in f): raise TypeError("public_transitions must contain PublicTransitionRecordV1")
    observed=tuple(x.environment_step_index for x in f)
    if observed!=tuple(sorted(observed)) or len(observed)!=len(set(observed)): raise ValueError("public transitions order/uniqueness invalid")
    return f

def _semantic_trace(trace):
    payload=trace.to_dict(); raw=payload["provenance"]; provenance=dict(raw.to_dict()) if hasattr(raw,"to_dict") else dict(raw)
    for key in ("provider_request_id","timestamp_utc","retry_count","episode_id"): provenance.pop(key,None)
    payload["provenance"]=provenance; return payload

def _semantic_episode(episode):
    p=episode.to_dict()
    for key in ("run_id","execution_attempt_id","attempt_ordinal","operational_finalization_status","episode_semantic_sha256","started_at_utc","completed_at_utc"): p.pop(key,None)
    return p

def _semantic_transition(transition):
    payload=transition.to_dict()
    payload.pop("execution_attempt_id",None)
    return payload

def _semantic_projection(*,episode,traces,policy_calls,transitions):
    transition_payloads=(
        [x.to_dict() for x in transitions]
        if policy_calls is None
        else [_semantic_transition(x) for x in transitions]
    )
    result={"episode":_semantic_episode(episode),"action_traces":[_semantic_trace(t) for t in traces],"public_transitions":transition_payloads}
    if policy_calls is not None: result["policy_calls"]=[semantic_policy_call_payload(x) for x in policy_calls]
    return result

def _validate_counts(*,episode,traces,policy_calls,transitions):
    if episode.trace_count!=len(traces): raise ValueError("episode trace_count does not match traces")
    if episode.public_transition_count!=len(transitions): raise ValueError("episode public_transition_count does not match transitions")
    if policy_calls is not None and len(policy_calls)!=len(traces): raise ValueError("policy call count must equal trace count")
    environment_calls=sum(t.execution_status in {ExecutionStatus.EXECUTED,ExecutionStatus.ENVIRONMENT_ERROR} for t in traces)
    if episode.environment_call_trace_count!=environment_calls: raise ValueError("episode environment_call_trace_count does not match traces")

def _jsonl_action_traces(items): return b"".join(x.to_json().encode("utf-8")+b"\n" for x in items)
def _jsonl_schema_models(items):
    return b"".join((x.to_json().rstrip("\n")+"\n").encode("utf-8") for x in items)
def _checksum_text(files): return "".join(f"{sha256_bytes(data)}  {name}\n" for name,data in files).encode("utf-8")
def _bundle_identity(files): return sha256_bytes(canonical_json_bytes([{"filename":name,"sha256":sha256_bytes(data)} for name,data in files]))

def build_attempt_bundle_bytes(*,episode_artifact:EpisodeArtifactV1,traces:Sequence[ActionTrace],public_transitions:Sequence[PublicTransitionRecordV1],policy_calls:Sequence[PolicyCallEvidenceV1]|None=None)->AttemptBundleBytes:
    if not isinstance(episode_artifact,EpisodeArtifactV1): raise TypeError("episode_artifact must be EpisodeArtifactV1")
    ft=_freeze_traces(traces); fp=_freeze_policy_calls(policy_calls); fr=_freeze_transitions(public_transitions)
    _validate_counts(episode=episode_artifact,traces=ft,policy_calls=fp,transitions=fr)
    semantic_bytes=canonical_json_bytes(_semantic_projection(episode=episode_artifact,traces=ft,policy_calls=fp,transitions=fr)); semantic_sha=sha256_bytes(semantic_bytes)
    corrected=replace(episode_artifact,episode_semantic_sha256=semantic_sha)
    attempt_json=corrected.to_json().encode("utf-8"); traces_jsonl=_jsonl_action_traces(ft); transitions_jsonl=_jsonl_schema_models(fr)
    if fp is None:
        policy_jsonl=None; payload=(("attempt.json",attempt_json),("action_traces.jsonl",traces_jsonl),("public_transitions.jsonl",transitions_jsonl))
    else:
        policy_jsonl=_jsonl_schema_models(fp); payload=(("attempt.json",attempt_json),("action_traces.jsonl",traces_jsonl),("policy_calls.jsonl",policy_jsonl),("public_transitions.jsonl",transitions_jsonl))
    checks=_checksum_text(payload); all_files=(*payload,("SHA256SUMS",checks)); bundle_sha=_bundle_identity(all_files)
    return AttemptBundleBytes(attempt_json,traces_jsonl,transitions_jsonl,checks,semantic_sha,bundle_sha,policy_jsonl)
