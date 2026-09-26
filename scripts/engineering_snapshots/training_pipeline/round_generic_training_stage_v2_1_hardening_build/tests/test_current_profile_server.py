import importlib.util
from pathlib import Path
from round_training.contracts import load_stage_context
ROOT=Path(__file__).resolve().parents[1]
def load(p):
 s=importlib.util.spec_from_file_location('a',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def test_current_profile_server_assets():
 c=load_stage_context(ROOT/'profiles/human_reference_t2/ROUND_TRAINING_STAGE_BINDING_V1.json');x=load(c.runtime_adapter_path).validate_profile_without_model_load(c);assert x['record_count']==12 and x['optimizer_group_target_loss_tokens']==[43,53,55]
def test_trainable_parent_loader_static():
 t=(ROOT/'round_training/adapters/frozen_formal_train_peft.py').read_text();assert 'PeftModel.from_pretrained' in t and 'is_trainable=True' in t and 'get_peft_model' not in t and 'resume_from_checkpoint(' not in t


def test_current_profile_direct_input_artifacts_are_indexable() -> None:
    context = load_stage_context(
        ROOT
        / "profiles/human_reference_t2/"
        "ROUND_TRAINING_STAGE_BINDING_V1.json"
    )
    adapter = load(context.runtime_adapter_path)
    refs = adapter.input_artifact_refs(context)
    logical_names = {row["logical_name"] for row in refs}
    assert {
        "PARENT_FORMAL_TRAIN_SOURCE",
        "PARENT_TRAINING_CONFIG",
        "PARENT_ADAPTER_ARTIFACT_MANIFEST",
        "PARENT_ADAPTER_CONFIG",
        "PARENT_ADAPTER_MODEL",
        "BASE_MODEL_ARTIFACT_MANIFEST",
        "TRAINER_NATIVE_DATASET",
        "TRAINER_NATIVE_DATASET_MANIFEST",
    }.issubset(logical_names)
