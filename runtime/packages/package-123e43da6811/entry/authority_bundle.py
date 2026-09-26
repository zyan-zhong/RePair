"""Validate captured Formal authority through existing native domain contracts.

This validates the scientific startup authority, not executable stage closure.
Current hashes/paths/model/round limits are read from authority files, not source
constants. Archive byte identity is checked separately by the package inventory.
"""
from __future__ import annotations
from dataclasses import dataclass, fields
import hashlib
from pathlib import Path
from typing import Any

from pchsi.reference_loop.canonical import strict_json_loads, domain_hash
from pchsi.round_control.campaign_authority import CampaignStartupAuthorityV1
from pchsi.round_control.rollout_collection import RoundRolloutCollectionRequestV1, RoundRolloutExecutionBindingV1
from pchsi.round_control.formal_campaign_startup import freeze_formal_max10_campaign_startup_receipt
from pchsi.round_control.scientific_round_governance import new_scientific_round_governance


def _obj(root: Path, name: str) -> dict:
    path = root / name
    if path.is_symlink() or not path.is_file():
        raise ValueError('AUTHORITY_FILE_NOT_REGULAR:' + name)
    value = strict_json_loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError('AUTHORITY_OBJECT_REQUIRED:' + name)
    return value


def _domain(value: dict, field: str, schema: str):
    if value.get('schema_id') != schema or value.get('schema_version') != 1:
        raise ValueError('AUTHORITY_SCHEMA_MISMATCH:' + schema)
    if value.get(field) != domain_hash(schema, value, excluded_field=field):
        raise ValueError('AUTHORITY_DOMAIN_SHA_MISMATCH:' + schema)


def _equals(value: Any, expected: Any, label: str):
    if type(value) is not type(expected) or value != expected:
        raise ValueError('AUTHORITY_CROSS_REFERENCE_MISMATCH:' + label)


@dataclass(frozen=True)
class FormalAuthorityBundle:
    campaign: CampaignStartupAuthorityV1
    request: RoundRolloutCollectionRequestV1
    rollout_binding: RoundRolloutExecutionBindingV1
    startup: Any
    prelaunch: dict
    telemetry: dict
    provenance: dict
    initial: dict


def load_formal_authority(root: Path) -> FormalAuthorityBundle:
    root = Path(root)
    campaign = CampaignStartupAuthorityV1.from_dict(_obj(root,'CAMPAIGN_STARTUP_AUTHORITY_V1.json'))
    raw_request = _obj(root,'ROUND_ROLLOUT_COLLECTION_REQUEST_V1.json')
    request = RoundRolloutCollectionRequestV1(**{f.name:raw_request[f.name] for f in fields(RoundRolloutCollectionRequestV1)})
    _equals(request.to_dict(),raw_request,'request_exact_native_serialization')
    raw_binding = _obj(root,'ROUND_ROLLOUT_EXECUTION_BINDING_V1.json')
    binding = RoundRolloutExecutionBindingV1(**{f.name:raw_binding[f.name] for f in fields(RoundRolloutExecutionBindingV1)})
    _equals(binding.to_dict(),raw_binding,'binding_exact_native_serialization')
    execution = _obj(root,'FORMAL_MAX10_FIRST_ROUND_EXECUTION_BINDING_V1.json')
    _domain(execution,'binding_sha256','FORMAL_MAX10_FIRST_ROUND_EXECUTION_BINDING_V1')
    provenance = _obj(root,'FORMAL_MAX10_CANARY_PROVENANCE_REFERENCE_V1.json')
    if provenance.get('schema_id') != 'FORMAL_MAX10_CANARY_PROVENANCE_REFERENCE_V1' or provenance.get('schema_version') != 1:
        raise ValueError('CANARY_PROVENANCE_SCHEMA_MISMATCH')
    if type(provenance.get('formal_denominator_contribution')) is not int or provenance['formal_denominator_contribution'] != 0 or provenance.get('formal_round_adoption') is not False:
        raise ValueError('CANARY_FORMAL_DENOMINATOR_ISOLATION_FAILED')
    for stem in ('request','binding','handoff'):
        _equals(execution.get('source_canary_'+stem+'_file_sha256'),provenance.get(stem+'_file_sha256'),'canary_'+stem)
    execution_equals = {
        'round_id':request.round_id,
        'parent_policy_id':request.parent_policy_id,
        'parent_policy_artifact_sha256':request.parent_policy_artifact_sha256,
        'formal_rollout_request_sha256':request.request_sha256,
        'formal_rollout_execution_binding_sha256':binding.binding_sha256,
        'policy_runtime_adapter_sha256':binding.policy_runtime_adapter_sha256,
        'train_update_manifest_sha256':request.train_update_manifest_sha256,
        'round_memory_runtime_authority_sha256':request.round_memory_runtime_authority_sha256,
        'round_start_memory_snapshot_sha256':request.round_start_memory_snapshot_sha256,
        'token_budget_contract_sha256':request.token_budget_contract_sha256,
        'rollout_seed':request.rollout_seed,
        'benchmark_feedback_authorized':False,
        'invalid_attempt_adaptive_evidence_reuse_authorized':False,
        'human_runtime_selection_required':False,
        'routine_human_scientific_decision_required':False,
        'canary_round_adopted_as_formal_round':False,
        'scientific_execution_authorized':True,
    }
    for key,expected in execution_equals.items():
        _equals(execution.get(key),expected,'first_round.'+key)
    startup = freeze_formal_max10_campaign_startup_receipt(
        campaign_authority=campaign,
        integration_commit_oid=execution['integration_commit_oid'],
        rollout_request=request, rollout_execution_binding=binding,
        first_round_execution_binding_sha256=execution['binding_sha256'],
        controlled_campaign_startup_authorized=True,
        single_operator_launch_only=True,
        routine_human_scientific_decision_count=0,
        canary_round_adopted_as_formal_round=False,
        scientific_execution_started=False,
    )
    _equals(startup.to_dict(),_obj(root,'FORMAL_MAX10_CAMPAIGN_STARTUP_RECEIPT_V1.json'),'startup_receipt')
    _equals(new_scientific_round_governance(authority=campaign).to_dict(),_obj(root,'SCIENTIFIC_ROUND_GOVERNANCE_V1.json'),'initial_governance')
    telemetry = _obj(root,'FORMAL_MAX10_PAPER_TELEMETRY_BINDING_V1.json')
    _domain(telemetry,'binding_sha256','FORMAL_MAX10_PAPER_TELEMETRY_BINDING_V1')
    contract = _obj(root,'PCHSI_PAPER_ROUND_EXPORT_CONTRACT_V1.json')
    _equals(hashlib.sha256((root/'PCHSI_PAPER_ROUND_EXPORT_CONTRACT_V1.json').read_bytes()).hexdigest(),telemetry['paper_export_contract_file_sha256'],'paper_contract_raw_file_SHA')
    _equals(contract['contract_sha256'],telemetry['paper_export_contract_sha256'],'paper_contract_semantic_SHA')
    for key,expected in {
        'campaign_id':campaign.campaign_id,'campaign_authority_sha256':campaign.authority_sha256,
        'formal_round_id':request.round_id,'formal_rollout_request_sha256':request.request_sha256,
        'live_capture_required':True,'missing_fields_may_be_fabricated':False,
        'primary_independent_unit':'UNIQUE_TASK_OR_SOURCE_STATE',
        'branch_runs_increase_independent_n':False,
        'paired_f0f1_repetitions_are_independent_samples':False,
        'telemetry_is_scientific_authority':False,
    }.items():
        _equals(telemetry.get(key),expected,'telemetry.'+key)
    for lane,definition in contract['lanes'].items():
        _equals(telemetry.get(lane),definition['required_fields'],'telemetry_lane.'+lane)
    prelaunch = _obj(root,'FORMAL_MAX10_PRELAUNCH_AUTHORITY_V1.json')
    _domain(prelaunch,'authority_sha256','FORMAL_MAX10_PRELAUNCH_AUTHORITY_V1')
    for key,expected in {
        'campaign_id':campaign.campaign_id,
        'campaign_authority_sha256':campaign.authority_sha256,
        'integration_commit_oid':startup.integration_commit_oid,
        'first_round_id':request.round_id,
        'first_round_request_sha256':request.request_sha256,
        'first_round_rollout_binding_sha256':binding.binding_sha256,
        'first_round_execution_binding_sha256':execution['binding_sha256'],
        'startup_receipt_sha256':startup.startup_receipt_sha256,
        'paper_telemetry_binding_sha256':telemetry['binding_sha256'],
        'requested_max_valid_rounds':campaign.requested_max_valid_rounds,
        'no_promotion_patience':campaign.no_promotion_patience,
        'max_infrastructure_attempt_restarts':campaign.max_infrastructure_attempt_restarts,
        'force_run_all_rounds':campaign.force_run_all_rounds,
        'valid_rounds_consumed':0,'invalid_attempt_count':0,
        'routine_human_scientific_decision_count':0,
        'canary_round_adopted_as_formal_round':False,
        'formal_max10_startup_authorized':True,
        'scientific_execution_started':False,
    }.items():
        _equals(prelaunch.get(key),expected,'prelaunch.'+key)
    initial = request.to_dict()
    return FormalAuthorityBundle(campaign,request,binding,startup,prelaunch,telemetry,provenance,initial)
