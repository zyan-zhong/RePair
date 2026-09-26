from __future__ import annotations
import importlib.util
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

EXECUTION_VIEW='I1_EXECUTION_ACTION'
STRATEGY_VIEW='STRATEGY_AUXILIARY'
SCHEMA='POLICY_STRATEGY_DUAL_VIEW_NATIVE_ROW_V1'


def _sha(value: object, label: str) -> str:
    if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError(label+'_INVALID_SHA256')
    return value


def load_dual_view_records(path: Path, *, prompt_label_value: int=-100) -> tuple[dict[str,Any],...]:
    rows=[]
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if line.strip():
            value=json.loads(line)
            if not isinstance(value,dict): raise ValueError('DUAL_VIEW_ROW_NOT_OBJECT')
            rows.append(value)
    if not rows: raise ValueError('DUAL_VIEW_DATASET_EMPTY')
    examples=set(); row_shas=set(); by_state=defaultdict(list); records=[]
    for ordinal,row in enumerate(rows):
        if row.get('schema_id')!=SCHEMA or row.get('schema_version')!=1: raise ValueError('DUAL_VIEW_ROW_SCHEMA_CHANGED')
        if row.get('ordinal')!=ordinal: raise ValueError('DUAL_VIEW_ROW_ORDINAL_CHANGED')
        view=row.get('view_kind')
        if view not in {EXECUTION_VIEW,STRATEGY_VIEW}: raise ValueError('DUAL_VIEW_KIND_INVALID')
        identity=row.get('source_identity')
        if not isinstance(identity,dict): raise ValueError('DUAL_VIEW_SOURCE_IDENTITY_MISSING')
        state=_sha(identity.get('source_state_sha256'),'SOURCE_STATE')
        example=_sha(identity.get('source_example_sha256'),'SOURCE_EXAMPLE')
        if example in examples: raise ValueError('SOURCE_EXAMPLE_DUPLICATE:'+example)
        examples.add(example)
        row_sha=_sha(row.get('trainer_native_row_sha256'),'TRAINER_NATIVE_ROW')
        if row_sha in row_shas: raise ValueError('TRAINER_NATIVE_ROW_DUPLICATE:'+row_sha)
        row_shas.add(row_sha)
        tok=row.get('tokenization')
        if not isinstance(tok,dict): raise ValueError('DUAL_VIEW_TOKENIZATION_MISSING')
        input_ids=tok.get('input_ids'); labels=tok.get('labels')
        if not isinstance(input_ids,list) or not isinstance(labels,list) or len(input_ids)!=len(labels) or not input_ids:
            raise ValueError('DUAL_VIEW_TOKEN_ARRAYS_INVALID')
        target_count=sum(x!=prompt_label_value for x in labels[1:])
        if target_count!=tok.get('completion_loss_token_count') or target_count<=0:
            raise ValueError('DUAL_VIEW_TARGET_COUNT_INVALID')
        if view==EXECUTION_VIEW:
            if row.get('deployment_i1_execution_view') is not True or row.get('training_auxiliary_strategy_view') is not False:
                raise ValueError('EXECUTION_VIEW_FLAGS_INVALID')
        else:
            if row.get('deployment_i1_execution_view') is not False or row.get('training_auxiliary_strategy_view') is not True:
                raise ValueError('STRATEGY_VIEW_FLAGS_INVALID')
        if row.get('promotion_eligible') is not False: raise ValueError('DUAL_VIEW_ROW_MUST_NOT_SELF_PROMOTE')
        by_state[state].append(view)
        records.append({'case_id':row_sha,'ordinal':ordinal,'source_state_sha256':state,'source_example_sha256':example,'view_kind':view,'tokenization':tok,'trainer_native_row_sha256':row_sha})
    for state,views in by_state.items():
        if sorted(views)!=sorted([EXECUTION_VIEW,STRATEGY_VIEW]):
            raise ValueError('DUAL_VIEW_PAIR_INCOMPLETE:'+state)
    return tuple(records)


def validate_dual_view_census(census: dict[str,Any]) -> dict[str,object]:
    positive=('STRATEGY_ROW_COUNT','VERIFIED_BENEFIT_ROW_COUNT','STRATEGY_TARGET_TOKEN_COUNT','STRATEGY_LOSS_BEARING_TOKEN_COUNT','ACTION_TARGET_TOKEN_COUNT','ACTION_LOSS_BEARING_TOKEN_COUNT','PROMPT_MASKED_TOKEN_COUNT','TOTAL_LOSS_BEARING_TOKEN_COUNT')
    for key in positive:
        if type(census.get(key)) is not int or census[key]<=0: raise ValueError(key+'_MUST_BE_POSITIVE')
    if census['VERIFIED_BENEFIT_ROW_COUNT']!=census['STRATEGY_ROW_COUNT']: raise ValueError('VERIFIED_BENEFIT_ROW_COUNT_MISMATCH')
    for key in ('ACTION_ONLY_STRATEGY_ROW_COUNT','NON_VERIFIED_STRATEGY_ROW_COUNT'):
        if census.get(key)!=0: raise ValueError(key+'_MUST_BE_ZERO')
    return {'authorized':True,'strategy_loss_bearing_tokens':census['STRATEGY_LOSS_BEARING_TOKEN_COUNT'],'action_loss_bearing_tokens':census['ACTION_LOSS_BEARING_TOKEN_COUNT']}


def _fixed_original_adapter_path() -> Path:
    repo=os.environ.get('PCHSI_FIXED_REPO_ROOT')
    if not repo: raise ValueError('PCHSI_FIXED_REPO_ROOT_REQUIRED')
    return Path(repo).resolve()/('scripts/engineering_snapshots/training_pipeline/'
        'round_generic_training_stage_v2_1_hardening_build/round_training/adapters/frozen_formal_train_peft.py')


def _load_original_adapter():
    path=_fixed_original_adapter_path()
    if not path.is_file() or path.is_symlink(): raise ValueError('ORIGINAL_GENERIC_TRAINING_ADAPTER_MISSING')
    spec=importlib.util.spec_from_file_location('pchsi_frozen_formal_train_peft_dual_view_delegate',path)
    if spec is None or spec.loader is None: raise ValueError('ORIGINAL_GENERIC_TRAINING_ADAPTER_IMPORT_FAILED')
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def _records_for_contract(contract: dict[str,Any]) -> tuple[dict[str,Any],...]:
    dataset=contract['dataset']; path=Path(dataset['path'])
    records=load_dual_view_records(path,prompt_label_value=dataset['prompt_label_value'])
    if len(records)!=dataset['row_count']: raise ValueError('ROUND_TRAINING_ROW_COUNT_CHANGED')
    lengths=dataset['sequence_lengths']
    if [len(r['tokenization']['input_ids']) for r in records]!=lengths: raise ValueError('ROUND_TRAINING_SEQUENCE_LENGTH_CHANGED')
    total=sum(r['tokenization']['completion_loss_token_count'] for r in records)
    if total!=dataset['one_pass_target_loss_token_count']: raise ValueError('ROUND_TRAINING_TARGET_TOKEN_TOTAL_CHANGED')
    return records


def _delegate(context):
    original=_load_original_adapter()
    original._load_records=_records_for_contract
    return original


def validate_profile_without_model_load(context):
    return _delegate(context).validate_profile_without_model_load(context)


def input_artifact_refs(context):
    return _delegate(context).input_artifact_refs(context)


def execute_training_stage(*,context,output_dir:Path,runner_freeze_root_sha256:str):
    return _delegate(context).execute_training_stage(context=context,output_dir=output_dir,runner_freeze_root_sha256=runner_freeze_root_sha256)
