"""Frozen P1-B family-stratified task split with forced-DEV evidence."""
from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import ClassVar, Mapping, Sequence

from .canonical_evidence import canonical_json_bytes, canonical_json_text, sha256_bytes
from .distillation_access import (
    DistillationAccessClass, HistoricalAccessAuditV1, HistoricalAccessFlag,
)
from .distillation_governance import canonical_model_sha256
from .schema_contract import validate_payload_against_schema
from .task_manifest import FrozenTaskRecord

P1_B_SPLIT_SALT = "P1_B_ACCESS_SPLIT_V1|effb7c0b25002321a7c123376c53890731ee19a9"
_FORCED_FLAGS=(HistoricalAccessFlag.TRAJECTORY_INSPECTED,HistoricalAccessFlag.USED_FOR_METHOD_DESIGN)

class P1BSplitInfeasibleError(ValueError):
    pass

@dataclass(frozen=True, slots=True)
class P1BSplitContractV1:
    SCHEMA_ID: ClassVar[str]="P1_B_SPLIT_CONTRACT_V1"
    schema_id: str="P1_B_SPLIT_CONTRACT_V1"
    schema_version: int=1
    split_contract_id: str="P1_B_SPLIT_CONTRACT_V1"
    salt: str=P1_B_SPLIT_SALT
    family_rule: str="E_f=N_f-F_f; require E_f>0; SELECT_TARGET=max(1,floor(E_f/3))"
    sort_rule: str="split_key_sha256_then_manifest_index"
    forced_dev_flags: tuple[str,str]=("TRAJECTORY_INSPECTED","USED_FOR_METHOD_DESIGN")

    def __post_init__(self):
        if self.forced_dev_flags!=("TRAJECTORY_INSPECTED","USED_FOR_METHOD_DESIGN"):
            raise ValueError("forced_dev_flags must match frozen order")
        validate_payload_against_schema(schema_id=self.SCHEMA_ID,payload=self.to_dict())
    def to_dict(self):
        return {"schema_id":self.schema_id,"schema_version":self.schema_version,"split_contract_id":self.split_contract_id,"salt":self.salt,"family_rule":self.family_rule,"sort_rule":self.sort_rule,"forced_dev_flags":list(self.forced_dev_flags)}
    def to_json(self): return canonical_json_text(self.to_dict())

@dataclass(frozen=True, slots=True)
class P1BSplitAssignmentV1:
    manifest_index:int
    task_id:str
    task_type:str
    gamefile_sha1:str
    historical_access_flags:tuple[HistoricalAccessFlag,...]
    historical_evidence_sources:tuple[str,...]
    forced_dev:bool
    forced_dev_reason:str|None
    forced_dev_evidence_sources:tuple[str,...]
    split_key_sha256:str|None
    family_select_target:int
    family_rank:int|None
    final_access_class:DistillationAccessClass

    def to_dict(self):
        return {
            "manifest_index":self.manifest_index,"task_id":self.task_id,"task_type":self.task_type,"gamefile_sha1":self.gamefile_sha1,
            "historical_access_flags":[x.value for x in self.historical_access_flags],"historical_evidence_sources":list(self.historical_evidence_sources),
            "forced_dev":self.forced_dev,"forced_dev_reason":self.forced_dev_reason,"forced_dev_evidence_sources":list(self.forced_dev_evidence_sources),
            "split_key_sha256":self.split_key_sha256,"family_select_target":self.family_select_target,"family_rank":self.family_rank,"final_access_class":self.final_access_class.value,
        }

@dataclass(frozen=True, slots=True)
class P1BSplitProofV1:
    SCHEMA_ID: ClassVar[str]="P1_B_SPLIT_PROOF_V1"
    schema_id:str
    schema_version:int
    split_contract_sha256:str
    historical_access_audit_sha256:str
    record_count:int
    records:tuple[P1BSplitAssignmentV1,...]

    def __post_init__(self):
        if self.schema_id!=self.SCHEMA_ID or self.schema_version!=1: raise ValueError("split proof schema mismatch")
        if self.record_count!=len(self.records) or not self.records: raise ValueError("record_count mismatch")
        indices=[x.manifest_index for x in self.records]
        if indices!=list(range(len(self.records))): raise ValueError("split proof must preserve manifest order")
        validate_payload_against_schema(schema_id=self.SCHEMA_ID,payload=self.to_dict())
    def to_dict(self):
        return {"schema_id":self.schema_id,"schema_version":self.schema_version,"split_contract_sha256":self.split_contract_sha256,"historical_access_audit_sha256":self.historical_access_audit_sha256,"record_count":self.record_count,"records":[x.to_dict() for x in self.records]}
    def to_json(self): return canonical_json_text(self.to_dict())
    def assignment_for(self,index:int): return self.records[index]


def select_target_for_eligible(eligible_count:int)->int:
    if type(eligible_count) is not int:
        raise TypeError("eligible_count must be int")
    if eligible_count<=0:
        raise P1BSplitInfeasibleError(
            "P1_B_SPLIT_INFEASIBLE_NO_ELIGIBLE_SELECT"
        )
    return max(1,floor(eligible_count/3))


def select_target(n:int)->int:
    return select_target_for_eligible(n)


def split_key_sha256(record:FrozenTaskRecord)->str:
    if not isinstance(record,FrozenTaskRecord): raise TypeError("record must be FrozenTaskRecord")
    return sha256_bytes(canonical_json_bytes({"schema_id":"P1_B_TASK_SPLIT_KEY_V1","salt":P1_B_SPLIT_SALT,"task_type":record.task_type,"task_id":record.task_id,"gamefile_sha1":record.gamefile_sha1}))


def _forced_reason(flags:tuple[HistoricalAccessFlag,...])->str|None:
    has_t=HistoricalAccessFlag.TRAJECTORY_INSPECTED in flags
    has_m=HistoricalAccessFlag.USED_FOR_METHOD_DESIGN in flags
    if has_t and has_m: return "TRAJECTORY_INSPECTED+USED_FOR_METHOD_DESIGN"
    if has_t: return "TRAJECTORY_INSPECTED"
    if has_m: return "USED_FOR_METHOD_DESIGN"
    return None


def assign_p1b_access(*, records:Sequence[FrozenTaskRecord], audit:HistoricalAccessAuditV1, forced_dev_evidence:Mapping[str,Sequence[str]])->P1BSplitProofV1:
    frozen=tuple(records)
    if not frozen: raise ValueError("records must not be empty")
    if any(not isinstance(r,FrozenTaskRecord) for r in frozen): raise TypeError("records must contain FrozenTaskRecord")
    if [r.index for r in frozen]!=list(range(len(frozen))): raise ValueError("records must preserve manifest order")
    if not isinstance(audit,HistoricalAccessAuditV1): raise TypeError("audit must be HistoricalAccessAuditV1")
    audit_map={r.task_id:r for r in audit.records}
    current_ids={r.task_id for r in frozen}
    if set(audit_map)!=current_ids: raise ValueError("audit/current task coverage mismatch")
    extra_evidence=set(forced_dev_evidence)-current_ids
    if extra_evidence: raise ValueError(f"forced DEV evidence contains unknown tasks: {sorted(extra_evidence)}")
    for r in frozen:
        a=audit_map[r.task_id]
        if a.gamefile!=r.gamefile or a.dataset_split!=r.split: raise ValueError(f"audit identity mismatch for {r.task_id}")

    family_members={}
    for r in frozen: family_members.setdefault(r.task_type,[]).append(r)
    outputs=[None]*len(frozen)
    contract=P1BSplitContractV1()

    for family,members in family_members.items():
        nonforced=[]
        forced=[]
        for r in members:
            a=audit_map[r.task_id]
            reason=_forced_reason(a.access_flags)
            if reason is not None:
                sources=tuple(forced_dev_evidence.get(r.task_id,()))
                if not sources: raise ValueError(f"forced DEV evidence missing for {r.task_id}")
                if any(not isinstance(s,str) or not s for s in sources): raise ValueError("forced DEV evidence source must be non-empty str")
                if len(set(sources))!=len(sources): raise ValueError("forced DEV evidence sources must be unique")
                if not set(sources).issubset(set(a.evidence_sources)):
                    raise ValueError(f"forced DEV evidence sources must come from reviewed audit for {r.task_id}")
                forced.append((r,a,reason,sources))
            else:
                if r.task_id in forced_dev_evidence:
                    raise ValueError(f"forced DEV evidence supplied for non-forced task {r.task_id}")
                nonforced.append((split_key_sha256(r),r,a))

        target=select_target_for_eligible(len(nonforced))
        nonforced.sort(key=lambda x:(x[0],x[1].index))
        select_ids={r.task_id for _,r,_ in nonforced[:target]}
        rank={r.task_id:i for i,(_,r,_) in enumerate(nonforced)}
        for r,a,reason,sources in forced:
            outputs[r.index]=P1BSplitAssignmentV1(r.index,r.task_id,r.task_type,r.gamefile_sha1,a.access_flags,a.evidence_sources,True,reason,sources,None,target,None,DistillationAccessClass.DEV_VISIBLE)
        for key,r,a in nonforced:
            cls=DistillationAccessClass.SELECT_SUMMARY_ONLY if r.task_id in select_ids else DistillationAccessClass.DEV_VISIBLE
            outputs[r.index]=P1BSplitAssignmentV1(r.index,r.task_id,r.task_type,r.gamefile_sha1,a.access_flags,a.evidence_sources,False,None,(),key,target,rank[r.task_id],cls)

    proof=P1BSplitProofV1("P1_B_SPLIT_PROOF_V1",1,canonical_model_sha256(contract),canonical_model_sha256(audit),len(frozen),tuple(outputs))
    return proof
