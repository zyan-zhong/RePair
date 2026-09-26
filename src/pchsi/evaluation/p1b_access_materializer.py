"""Materialize TaskAccessManifestV1 from reviewed P1-B split proof."""
from __future__ import annotations
from collections.abc import Mapping, Sequence

from .distillation_access import (
    DistillationAccessClass, HistoricalAccessAuditV1, TaskAccessManifestV1, TaskAccessRecordV1,
)
from .distillation_governance import canonical_model_sha256
from .p1b_split import P1BSplitProofV1
from .task_manifest import FrozenTaskRecord


def materialize_task_access_manifest(*, records:Sequence[FrozenTaskRecord], audit:HistoricalAccessAuditV1, split_proof:P1BSplitProofV1, gamefile_sha256_by_task_id:Mapping[str,str], manifest_id:str='P1_B_TASK_ACCESS_MANIFEST_V1')->TaskAccessManifestV1:
    frozen=tuple(records)
    if not frozen or any(not isinstance(r,FrozenTaskRecord) for r in frozen): raise TypeError("records must contain FrozenTaskRecord")
    if not isinstance(audit,HistoricalAccessAuditV1): raise TypeError("audit must be HistoricalAccessAuditV1")
    if not isinstance(split_proof,P1BSplitProofV1): raise TypeError("split_proof must be P1BSplitProofV1")
    if split_proof.historical_access_audit_sha256!=canonical_model_sha256(audit): raise ValueError("split proof historical audit hash mismatch")
    amap={r.task_id:r for r in audit.records}
    if set(amap)!={r.task_id for r in frozen}: raise ValueError("audit coverage mismatch")
    if split_proof.record_count!=len(frozen): raise ValueError("split proof count mismatch")
    out=[]
    for r,proof in zip(frozen,split_proof.records,strict=True):
        a=amap[r.task_id]
        if proof.manifest_index!=r.index or proof.task_id!=r.task_id or proof.gamefile_sha1!=r.gamefile_sha1: raise ValueError("split proof/current identity mismatch")
        if proof.historical_access_flags!=a.access_flags: raise ValueError("split proof/audit historical flags mismatch")
        sha256=gamefile_sha256_by_task_id.get(r.task_id)
        if not isinstance(sha256,str) or len(sha256)!=64 or any(c not in '0123456789abcdef' for c in sha256): raise ValueError(f"gamefile SHA-256 missing/invalid for {r.task_id}")
        if proof.final_access_class is DistillationAccessClass.DEV_VISIBLE:
            permissions=(True,True,False,False)
        elif proof.final_access_class is DistillationAccessClass.SELECT_SUMMARY_ONLY:
            permissions=(False,False,True,False)
        else:
            raise ValueError("P1-B split proof may materialize DEV or SELECT only")
        proof_sha=canonical_model_sha256(split_proof)
        provenance=(*a.evidence_sources,f"p1b-split-proof:{proof_sha}")
        out.append(TaskAccessRecordV1(r.index,r.task_id,r.split,r.task_type,r.gamefile,r.gamefile_sha1,sha256,a.access_flags,proof.final_access_class,*permissions,provenance))
    return TaskAccessManifestV1(TaskAccessManifestV1.SCHEMA_ID,1,manifest_id,audit.dataset_version,canonical_model_sha256(audit),len(out),tuple(out))
