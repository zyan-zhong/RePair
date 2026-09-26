"""Narrow policy-attempt adapters for the existing episode evaluator.

The evaluator remains owner of environment execution, traces, policy-call
artifacts and attempt publication.  This module only prepares a policy prompt
and consumes one generation through already-frozen Runtime Core / Memory APIs.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Protocol, Sequence

from pchsi.evaluation.budget import BudgetLimits, BudgetState
from pchsi.evaluation.canonical_evidence import canonical_json_bytes, strict_json_loads
from pchsi.evaluation.raw_policy_prompt import ExecutedTransition, InterfaceFeedbackCode, build_raw_policy_prompt, sha256_executed_transitions
from pchsi.evaluation.runtime_core import ProtocolPreconditionResult, RuntimeDecision, process_completed_generation, validate_runtime_preconditions
from pchsi.memory.consumer_views import MemoryConsumerQueryV1, build_policy_memory_view_v1
from pchsi.memory.dev_snapshot_loader import LoadedDevSnapshotV2, load_calibrated_dev_snapshot_v2
from pchsi.memory.formal_b_retrieval import FormalBRetrieverConfigV1
from pchsi.memory.memory_runtime_bridge import PreparedMemoryPolicyAttemptV1, prepare_memory_policy_attempt_v1, process_memory_policy_generation_v1
from pchsi.memory.policy_projection import build_failure_memory_policy_projection_v1
from pchsi.memory.projection_common import ProjectionClassV1


@dataclass(frozen=True, slots=True)
class PreparedPolicyAttemptV1:
    precondition: ProtocolPreconditionResult
    prompt_text: str | None
    memory_version: str
    memory_state_sha256: str
    adapter_state: object


class PolicyAttemptAdapterV1(Protocol):
    def prepare(self, *, public_task_goal: str, observation: str,
                executed_transitions: tuple[ExecutedTransition, ...],
                policy_visible_commands: Sequence[str],
                harness_visible_commands: Sequence[str],
                environment_commands: Sequence[str],
                interface_feedback: InterfaceFeedbackCode | None,
                budget_state: BudgetState,
                budget_limits: BudgetLimits) -> PreparedPolicyAttemptV1: ...

    def process(self, *, raw_response: str,
                visible_admissible_commands: Sequence[str],
                prepared: PreparedPolicyAttemptV1,
                budget_limits: BudgetLimits) -> RuntimeDecision: ...


@dataclass(frozen=True, slots=True)
class BoundI1PolicyExecutionProfileV1:
    """I1 serialization with the current bound service alias, not the legacy pi0 alias."""
    served_model_name: str
    continuation_request_contract: dict[str, object]
    policy_version: str
    profile_id: str = "ROUND_BOUND_I1_EXECUTION_PROFILE_V1"
    arm_id: str = "I1_STRUCTURED_SERIALIZATION_CONSTRAINT_V1"
    request_kind: str = "I1"
    requires_diagnostic_policy_call_evidence: bool = True
    requires_current_admissible_commands: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.served_model_name, str) or not self.served_model_name:
            raise ValueError("served_model_name must be non-empty")
        if not isinstance(self.policy_version, str) or not self.policy_version:
            raise ValueError("policy_version must be non-empty")
        from pchsi.research_intelligence.human_f0f1_runtime import continuation_request_contract_v1
        expected=continuation_request_contract_v1("I1_EXECUTION_PROFILE_V1")
        if self.continuation_request_contract != expected:
            raise ValueError("bound I1 continuation contract changed")

    def build_request(self, *, prompt_text: str, seed: int, request_id: str, admissible_commands=None):
        if admissible_commands is not None:
            raise ValueError("bound I1 does not accept dynamic action enum")
        from pchsi.research_intelligence.human_f0f1_runtime import build_bound_continuation_request_v1
        return build_bound_continuation_request_v1(
            runtime={
                "served_model_name": self.served_model_name,
                "continuation_request_contract": self.continuation_request_contract,
            },
            prompt_text=prompt_text, seed=seed, request_id=request_id,
        )


class RawPolicyAttemptAdapterV1:
    def prepare(self, *, public_task_goal, observation, executed_transitions,
                policy_visible_commands, harness_visible_commands,
                environment_commands, interface_feedback, budget_state,
                budget_limits):
        pre = validate_runtime_preconditions(
            policy_visible_commands=policy_visible_commands,
            harness_visible_commands=harness_visible_commands,
            environment_commands=environment_commands,
            budget_state=budget_state,
            budget_limits=budget_limits,
        )
        prompt = None
        if pre.should_call_policy:
            prompt = build_raw_policy_prompt(
                public_task_goal=public_task_goal,
                observation=observation,
                executed_transitions=executed_transitions,
                admissible_commands=policy_visible_commands,
                interface_feedback=interface_feedback,
            )
        return PreparedPolicyAttemptV1(
            precondition=pre,
            prompt_text=prompt,
            memory_version="MEMORY_M0_V1",
            memory_state_sha256=sha256_executed_transitions(executed_transitions),
            adapter_state=pre,
        )

    def process(self, *, raw_response, visible_admissible_commands, prepared, budget_limits):
        if not isinstance(prepared.adapter_state, ProtocolPreconditionResult):
            raise TypeError("raw adapter state mismatch")
        return process_completed_generation(
            raw_response=raw_response,
            visible_admissible_commands=visible_admissible_commands,
            precondition_result=prepared.adapter_state,
            budget_limits=budget_limits,
        )


RAW_POLICY_ATTEMPT_ADAPTER_V1 = RawPolicyAttemptAdapterV1()


def _canonical_object(path: Path) -> dict[str, object]:
    raw=Path(path).read_bytes(); value=strict_json_loads(raw)
    if not isinstance(value,dict) or canonical_json_bytes(value)!=raw:
        raise ValueError("bound object is not canonical JSON: "+str(path))
    return value


class _HFTokenCounter:
    def __init__(self, *, model_path: str, revision: str):
        from transformers import AutoTokenizer
        self.tokenizer_id=model_path; self.tokenizer_revision=revision
        self._tokenizer=AutoTokenizer.from_pretrained(
            model_path, revision=revision, local_files_only=True, trust_remote_code=False
        )
    def count_tokens(self,text: str)->int:
        return len(self._tokenizer.encode(text,add_special_tokens=False))


class RoundMemoryPolicyAttemptAdapterV1:
    """Governed round-start Memory view, adapted from the audited live Memory runner."""
    def __init__(self, *, runtime_identity_path: Path, expected_runtime_identity_file_sha256: str):
        path=Path(runtime_identity_path).resolve()
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest()!=expected_runtime_identity_file_sha256:
            raise ValueError("Memory runtime identity file SHA mismatch")
        outer=_canonical_object(path)
        if outer.get("schema_id")!="FAILURE_MEMORY_FINAL_RUNTIME_IDENTITY_V1":
            raise ValueError("Memory runtime identity schema mismatch")
        self._runtime=outer
        self._snapshot=load_calibrated_dev_snapshot_v2(
            snapshot_directory=Path(str(outer["active_snapshot_directory"])),
            expected_snapshot_sha256=str(outer["active_snapshot_sha256"]),
            token_budget_contract_path=Path(str(outer["token_budget_contract_path"])),
            expected_token_budget_contract_sha256=str(outer["token_budget_contract_sha256"]),
        )
        b=_canonical_object(Path(str(outer["formal_b_result_path"])))
        self._retriever=FormalBRetrieverConfigV1(threshold_pct=int(b["selected_threshold_pct"]))
        source=_canonical_object(Path(str(outer["source_runtime_binding_path"])))
        self._token_counter=_HFTokenCounter(
            model_path=str(source["base_model_local_path"]),
            revision=str(source["base_model_revision"]),
        )

    @property
    def snapshot_sha256(self)->str:
        return str(self._runtime["active_snapshot_sha256"])

    def _payload(self, query: MemoryConsumerQueryV1):
        view=build_policy_memory_view_v1(query=query,snapshot=self._snapshot,config=self._retriever)
        if view.policy_prompt_fragment() is None:
            return (),"M0",None,None,None,0
        lineage=view.selected_memory_lineage_id
        members=[m for m in self._snapshot.members if m.record.memory_lineage_id==lineage]
        if len(members)!=1: raise ValueError("selected Memory member is not unique")
        member=members[0]
        projection=build_failure_memory_policy_projection_v1(
            record=member.record, projection_class=ProjectionClassV1.FM3,
            tokenizer=self._token_counter,
            hard_ceiling=int(self._snapshot.token_budget_contract.single_record_hard_ceiling),
        )
        representation="M3"
        if projection.policy_visible_payload is None:
            projection=member.fm2; representation="M2"
        if projection.policy_visible_payload is None:
            return (),"M0",None,None,None,0
        count=0 if projection.token_count is None else projection.token_count.policy_visible_token_count
        return (
            (projection.policy_visible_payload.to_dict(),), representation, lineage,
            member.record.record_version, projection.policy_visible_payload_sha256, count,
        )

    def prepare(self, *, public_task_goal, observation, executed_transitions,
                policy_visible_commands, harness_visible_commands,
                environment_commands, interface_feedback, budget_state,
                budget_limits):
        query=MemoryConsumerQueryV1(
            observation=observation,
            executed_transitions=executed_transitions,
            admissible_commands=tuple(policy_visible_commands),
            interface_feedback=interface_feedback,
            public_task_goal=public_task_goal,
        )
        payloads,representation,lineage,version,projection_sha,packed=self._payload(query)
        prepared=prepare_memory_policy_attempt_v1(
            public_task_goal=public_task_goal, observation=observation,
            executed_transitions=executed_transitions, memory_payloads=payloads,
            policy_visible_commands=policy_visible_commands,
            harness_visible_commands=harness_visible_commands,
            environment_commands=environment_commands,
            interface_feedback=interface_feedback, budget_state=budget_state,
            snapshot_sha256=self.snapshot_sha256,
            token_budget_contract_sha256=str(self._runtime["token_budget_contract_sha256"]),
            retrieval_mode="NO_RETRIEVAL" if representation=="M0" else "FROZEN_JACCARD_POLICY_GATE_V1",
            branch_role="ROUND_ACTIVE", representation_class=representation,
            memory_lineage_id=lineage, record_version=version,
            projection_artifact_sha256=projection_sha,
            packed_token_count=packed, budget_limits=budget_limits,
        )
        return PreparedPolicyAttemptV1(
            precondition=prepared.precondition,
            prompt_text=prepared.prompt,
            memory_version="PERSISTENT_FAILURE_EXPERIENCE_V1",
            memory_state_sha256=self.snapshot_sha256,
            adapter_state=prepared,
        )

    def process(self, *, raw_response, visible_admissible_commands, prepared, budget_limits):
        if not isinstance(prepared.adapter_state, PreparedMemoryPolicyAttemptV1):
            raise TypeError("Memory adapter state mismatch")
        return process_memory_policy_generation_v1(
            raw_response=raw_response,
            visible_admissible_commands=visible_admissible_commands,
            prepared=prepared.adapter_state,
            budget_limits=budget_limits,
        )
