from pathlib import Path
import json
from round_training.contracts import load_stage_context
from round_training.receipts import build_input_artifact_index,build_output_artifact_index,build_stage_receipt
ROOT=Path(__file__).resolve().parents[1]
def test_core_has_no_current_identity():
 fs=[ROOT/'round_training/contracts.py',ROOT/'round_training/receipts.py',ROOT/'round_training/stage_runner.py',ROOT/'round_training/adapters/frozen_formal_train_peft.py']
 for p in fs:
  t=p.read_text()
  for x in ('HUMAN_T2','PILOT_DISTILLED_PI1','HUMAN_REFERENCE_ROUND_PI1_PI2_V1'): assert x not in t
def test_profile_via_binding():
 c=load_stage_context(ROOT/'profiles/human_reference_t2/ROUND_TRAINING_STAGE_BINDING_V1.json');assert c.training_contract['budget']['optimizer_steps']==3
def test_receipt_chain():
 i=build_input_artifact_index(round_id='R7',stage_id='TRAINING_EXECUTION',refs=[]);s=build_stage_receipt(round_id='R7',stage_id='TRAINING_EXECUTION',stage_attempt_id='a',input_artifact_index_sha256=i['artifact_index_sha256'],output_artifact_index_sha256=None,runner_freeze_root_sha256='1'*64,authorization_sha256='2'*64,started_from_receipt_sha256=None,previous_stage_receipt_sha256='3'*64,terminal_status='STARTED',scientific_missingness_class=None,model_training_executed=False,model_training_execution_status='NOT_STARTED',failure_summary=None);o=build_output_artifact_index(round_id='R7',stage_id='TRAINING_EXECUTION',artifacts=[]);t=build_stage_receipt(round_id='R7',stage_id='TRAINING_EXECUTION',stage_attempt_id='a',input_artifact_index_sha256=i['artifact_index_sha256'],output_artifact_index_sha256=o['artifact_index_sha256'],runner_freeze_root_sha256='1'*64,authorization_sha256='2'*64,started_from_receipt_sha256=s['stage_receipt_sha256'],previous_stage_receipt_sha256='3'*64,terminal_status='ACCEPTED',scientific_missingness_class=None,model_training_executed=True,model_training_execution_status='COMPLETED',failure_summary=None);assert t['started_from_receipt_sha256']==s['stage_receipt_sha256']
def test_no_approval():
 v=json.loads((ROOT/'profiles/human_reference_t2/ROUND_TRAINING_EXECUTION_AUTHORIZATION_TEMPLATE_V1.json').read_text());assert v['authorization_status']=='NOT_AUTHORIZED' and v['execution_attempt_id'] is None

def test_review_freeze_excludes_runtime_logs() -> None:
    text = (ROOT / "build_review.py").read_text(encoding="utf-8")
    assert 'path.suffix != ".log"' in text


def test_current_binding_has_round_derived_output_policy() -> None:
    context = load_stage_context(ROOT / "profiles/human_reference_t2/ROUND_TRAINING_STAGE_BINDING_V1.json")
    policy = context.binding["output_policy"]
    assert policy["require_direct_child"] is True
    assert policy["require_basename_equals_execution_attempt_id"] is True


def test_trainer_role_binding_schema_bundle_matches_round_contract() -> None:
    profile_root = ROOT / "profiles/human_reference_t2"
    role_binding = json.loads(
        (profile_root / "TRAINER_ROLE_BINDING_V1.json").read_text(
            encoding="utf-8"
        )
    )
    contract_path = profile_root / "ROUND_LOCAL_TRAINING_CONTRACT_V1.json"

    import hashlib

    observed = hashlib.sha256(contract_path.read_bytes()).hexdigest()
    assert role_binding["schema_bundle_sha256"] == observed
