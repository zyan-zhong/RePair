from __future__ import annotations
import copy,json
from pathlib import Path
import pytest
from round_training.common import ContractError
from round_training.contracts import validate_training_contract
ROOT=Path(__file__).resolve().parents[1]
def cur():
 return json.loads((ROOT/'profiles/human_reference_t2/ROUND_LOCAL_TRAINING_CONTRACT_V1.json').read_text()),json.loads((ROOT/'profiles/human_reference_t2/ROUND_SAMPLE_ORDER_MANIFEST_V1.json').read_text())
def test_current_profile_contract_is_valid(): validate_training_contract(*cur())
def test_optimizer_steps_are_derived():
 c,o=cur();x=copy.deepcopy(c);x['budget']['optimizer_steps']=4
 with pytest.raises(ContractError,match='OPTIMIZER_STEP_DERIVATION_MISMATCH'): validate_training_contract(x,o)
def test_two_rounds_same_validator():
 for rid,n,e,tokens_per_pass in [('R7',8,1,20),('R8',12,2,30)]:
  effective_batch=4
  steps=n//effective_batch*e
  lengths=list(range(100,100+n))
  orders=[list(range(n)) for _ in range(e)]
  ordered_rows=[]
  ordered_states=[]
  groups=[]
  remaining=tokens_per_pass*e
  global_step=0
  for pass_index,order in enumerate(orders):
   for step_in_pass,start in enumerate(range(0,n,effective_batch),start=1):
    global_step+=1
    ordinals=order[start:start+effective_batch]
    row_shas=[f"{index+1:064x}" for index in ordinals]
    state_shas=[f"{index+1001:064x}" for index in ordinals]
    ordered_rows.extend(row_shas)
    ordered_states.extend(state_shas)
    steps_left=steps-global_step+1
    token_count=remaining//steps_left
    remaining-=token_count
    groups.append({
     'global_step':global_step,
     'pass_index':pass_index,
     'step_in_pass':step_in_pass,
     'ordinals':ordinals,
     'row_sha256s':row_shas,
     'source_state_sha256s':state_shas,
     'target_loss_tokens':token_count,
    })
  c={
   'schema_id':'ROUND_LOCAL_TRAINING_CONTRACT_V1',
   'training_execution_authorized':False,
   'training_execution_count':0,
   'dataset':{
    'row_count':n,
    'sequence_lengths':lengths,
    'max_sequence_length':max(lengths),
    'truncation':False,
    'retokenization':False,
    'reapply_chat_template':False,
    'one_pass_target_loss_token_count':tokens_per_pass,
   },
   'budget':{
    'epochs':e,
    'micro_batch_size':1,
    'gradient_accumulation_steps':4,
    'effective_batch_size':4,
    'partial_final_accumulation_group':False,
    'optimizer_steps':steps,
    'target_loss_token_budget':tokens_per_pass*e,
    'training_seed':31,
    'data_seed':31,
   },
   'optimization':{
    'optimizer':'adamw_torch',
    'learning_rate':1e-4,
    'adam_beta1':0.9,
    'adam_beta2':0.999,
    'adam_epsilon':1e-8,
    'weight_decay':0.0,
    'max_grad_norm':1.0,
    'lr_scheduler':'linear',
    'resume_from_checkpoint':False,
    'fresh_optimizer':True,
    'fresh_scheduler':True,
    'warmup_steps':0,
   },
   'execution':{},
   'round_id':rid,
  }
  o={
   'schema_id':'ROUND_SAMPLE_ORDER_MANIFEST_V1',
   'row_count':n,
   'dataset_passes':e,
   'training_seed':31,
   'data_seed':31,
   'shuffle_during_training':False,
   'pass_orders':orders,
   'ordered_row_sha256s':ordered_rows,
   'ordered_source_state_sha256s':ordered_states,
   'optimizer_groups':groups,
  }
  validate_training_contract(c,o)


def test_optimizer_groups_must_follow_pass_orders() -> None:
    contract, order = cur()
    changed = copy.deepcopy(order)
    changed["optimizer_groups"][0]["ordinals"] = [
        6,
        8,
        9,
        7,
    ]
    with pytest.raises(
        ContractError,
        match="OPTIMIZER_GROUP_ORDINALS_MISMATCH",
    ):
        validate_training_contract(contract, changed)


def test_optimizer_group_lineage_must_match_flat_order() -> None:
    contract, order = cur()
    changed = copy.deepcopy(order)
    changed["optimizer_groups"][0]["row_sha256s"][0] = "0" * 64
    with pytest.raises(
        ContractError,
        match="OPTIMIZER_GROUP_ROW_SHA_MISMATCH",
    ):
        validate_training_contract(contract, changed)


@pytest.mark.parametrize(
    ("section", "key", "value", "message"),
    [
        ("optimization", "learning_rate", 0.0, "LEARNING_RATE_INVALID"),
        ("optimization", "weight_decay", -0.1, "WEIGHT_DECAY_INVALID"),
        ("optimization", "max_grad_norm", 0.0, "MAX_GRAD_NORM_INVALID"),
        ("optimization", "adam_beta1", 1.0, "ADAM_BETA1_INVALID"),
        ("optimization", "adam_beta2", -0.1, "ADAM_BETA2_INVALID"),
        ("optimization", "adam_epsilon", 0.0, "ADAM_EPSILON_INVALID"),
        ("peft", "r", 0, "LORA_R_INVALID"),
        ("peft", "lora_alpha", 0, "LORA_ALPHA_INVALID"),
        ("peft", "lora_dropout", 1.0, "LORA_DROPOUT_INVALID"),
    ],
)
def test_numeric_training_contract_fields_are_validated(
    section,
    key,
    value,
    message,
) -> None:
    contract, order = cur()
    changed = copy.deepcopy(contract)
    changed[section][key] = value
    with pytest.raises(ContractError, match=message):
        validate_training_contract(changed, order)
