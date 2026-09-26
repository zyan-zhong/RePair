from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys
import zipfile
import pytest

WORK = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(WORK / "v17"))
REPO = WORK / "v17/native_bba_full"
CLEAN = REPO / "scripts/engineering_snapshots/clean_human_r1_tail_v1/STAGE4A_EXISTING_TRAINER_CLEAN_INIT_V1"


def _module():
    assert (WORK / "v17/training_binding/clean_base.py").is_file(), "clean-base producer missing"
    from training_binding import clean_base
    return clean_base


def test_clean_parent_metadata_comes_from_exact_current_runtime_and_registered_code():
    module = _module()
    profile_path = REPO / module.PROFILE_REL
    raw = json.dumps({"schema_id": "CLEAN_PI0_LIVE_RUNTIME_BINDING_V2", "base_model_local_path": "/current/clean-base/aa8e72537993ba99e69dfaafa59ed015b17504d1",
        "tokenizer_revision": "aa8e72537993ba99e69dfaafa59ed015b17504d1", "policy_runtime_manifest_sha256": "a" * 64}).encode()
    request = {"parent_policy_id": "CURRENT-BASE", "parent_policy_artifact_sha256": "a" * 64, "policy_runtime_binding_sha256": hashlib.sha256(raw).hexdigest()}
    result = module.derive_clean_parent_metadata(source_request=request, runtime_bytes=raw,
        native_repo_root=REPO, profile_file_sha256=hashlib.sha256(profile_path.read_bytes()).hexdigest())
    assert result["parent"]["policy_id"] == "CURRENT-BASE"
    assert result["base_binding"]["snapshot_path"].startswith("/current/")
    assert "adapter_path" not in result["parent"]
    assert "budget" not in result
    assert "training_seed" not in result
    assert "diagnostic_only" not in result
    request["parent_policy_artifact_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="CURRENT_RUNTIME_PARENT_ARTIFACT"):
        module.derive_clean_parent_metadata(source_request=request, runtime_bytes=raw,
            native_repo_root=REPO, profile_file_sha256=hashlib.sha256(profile_path.read_bytes()).hexdigest())


def test_native_clean_mechanical_source_is_reused_without_diagnostic_packet_entry():
    module = _module()
    hashes = {name: hashlib.sha256((CLEAN / name).read_bytes()).hexdigest() for name in ("clean_adapter.py", "run_stage.py")}
    clean = module.NativeClean.load(CLEAN, hashes)
    assert Path(clean.runner.smoke.__code__.co_filename).resolve() == (CLEAN / "run_stage.py").resolve()
    assert Path(clean.adapter.load_clean_formal.__code__.co_filename).resolve() == (CLEAN / "clean_adapter.py").resolve()
    assert clean.runner.load_source is not None  # Original historical parser is left intact outside calls.


def test_clean_wrapper_requires_valid_source_seal():
    module = _module()
    with pytest.raises(ValueError, match="INPUT_REF_SHA_MISMATCH"):
        module.NativeClean.load(CLEAN, {"clean_adapter.py": "0" * 64, "run_stage.py": "0" * 64})


def _prepared(tmp_path):
    from test_materializer import _fixture
    module = _module()
    m, native, projection, decision = _fixture(tmp_path)
    clean = module.NativeClean.load(CLEAN, {name: hashlib.sha256((CLEAN / name).read_bytes()).hexdigest()
        for name in ("clean_adapter.py", "run_stage.py")})
    parent = projection["current"]["parent"]
    base = {"snapshot_path": str(tmp_path / "base"), "manifest_path": parent["base_model_artifact_manifest_path"],
        "manifest_sha256": parent["base_model_artifact_manifest_sha256"], "repository_id": "SYNTHETIC", "revision": "synthetic-revision"}
    sources = {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (WORK / "v17/training_binding").glob("*.py")}
    result = clean.prepare(native=native, projection=projection, decision=decision, base_binding=base,
        formal_source={"path": parent["formal_train_path"], "sha256": parent["formal_train_sha256"]},
        output_root=tmp_path / "initialization", binding_source_sha256s=sources)
    return m, native, clean, Path(result["request_path"])


def test_current_clean_preparation_uses_native_contract_and_never_trains(tmp_path):
    m, native, clean, request_path = _prepared(tmp_path)
    root = request_path.parent
    request = json.loads(request_path.read_bytes())
    contract = json.loads((root / "CURRENT_INITIALIZATION_CONTRACT.json").read_bytes())
    order = json.loads((root / "CURRENT_INITIALIZATION_ORDER.json").read_bytes())
    native.contracts.validate_training_contract(contract, order)
    assert request["authorization_scope"] == "INITIALIZATION_ONLY_NO_OPTIMIZER"
    assert contract["budget"]["optimizer_steps"] == 2
    assert contract["clean_runtime"]["canonical_source"]["path"] == str(REPO / "src/pchsi/reference_loop/canonical.py")
    assert not (root / "INITIALIZATION_RECEIPT.json").exists()


def test_current_clean_execute_reaches_original_cuda_gate_without_training(tmp_path, monkeypatch):
    m, native, clean, request_path = _prepared(tmp_path)
    import torch
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(ValueError, match="ONE_CUDA_DEVICE_REQUIRED"):
        clean.execute(native=native, request_path=request_path)
    lock = json.loads((request_path.parent / "SMOKE_EXECUTION_STARTED.json").read_bytes())
    assert lock["optimizer_step_count"] == 0
    assert not (request_path.parent / "INITIALIZATION_RECEIPT.json").exists()
    with pytest.raises(ValueError, match="SMOKE_ATTEMPT_ALREADY_STARTED_NO_AUTOMATIC_RETRY"):
        clean.execute(native=native, request_path=request_path)


def test_current_clean_execute_rejects_scientific_contract_change(tmp_path):
    m, native, clean, request_path = _prepared(tmp_path)
    contract_path = request_path.parent / "CURRENT_INITIALIZATION_CONTRACT.json"
    contract = json.loads(contract_path.read_bytes())
    contract["budget"]["epochs"] += 1
    contract_path.write_bytes(m.canonical(contract))
    with pytest.raises(ValueError, match="CLEAN_INITIALIZATION_SCIENTIFIC_CONTRACT_CHANGED"):
        clean.execute(native=native, request_path=request_path)
    assert not (request_path.parent / "SMOKE_EXECUTION_STARTED.json").exists()


def test_training_adoption_without_initialization_receipt_never_runs_smoke(tmp_path, monkeypatch):
    m, native, clean, request_path = _prepared(tmp_path)
    def forbidden(path):
        pytest.fail('training phase must never invoke the smoke execution body')
    monkeypatch.setattr(clean.runner, 'smoke', forbidden)
    with pytest.raises(ValueError, match='SEPARATE_INITIALIZATION_RECEIPT_REQUIRED'):
        clean.execute(native=native, request_path=request_path, adopt_only=True)
    assert not (request_path.parent / 'SMOKE_EXECUTION_STARTED.json').exists()


def test_training_adopts_existing_native_zero_step_receipt_without_smoke(tmp_path, monkeypatch):
    m, native, clean, request_path = _prepared(tmp_path)
    request = json.loads(request_path.read_bytes())
    contract = json.loads((request_path.parent / 'CURRENT_INITIALIZATION_CONTRACT.json').read_bytes())
    parent = contract['parent']
    receipt = {'schema_id': 'CLEAN_SEEDED_LORA_INITIALIZATION_RECEIPT_V1', 'schema_version': 1,
        'status': 'PASS', 'training_executed': False, 'optimizer_step_count': 0,
        'training_plan_sha256': request['plan_sha256'], 'seed': contract['budget']['training_seed'],
        'base_binding': request['runtime']['base_binding'],
        'source_code_root_sha256': request['runtime']['source_code_root_sha256'],
        'lora_a_nonzero': True, 'lora_b_all_zero': True, 'base_parameters_frozen': True,
        'repeat_seed_parameter_hash_equal': True, 'saved_adapter_reload_hash_equal': True,
        'enabled_vs_disabled_logits_exact_equal': True, 'logits_finite': True,
        'initial_trainable_parameter_sha256': 'b' * 64, 'repeat_initial_trainable_parameter_sha256': 'b' * 64,
        'reloaded_trainable_parameter_sha256': 'b' * 64, 'adapter_path': parent['adapter_path'],
        'adapter_manifest_path': parent['adapter_artifact_manifest_path'],
        'adapter_manifest_sha256': parent['adapter_artifact_manifest_sha256'],
        'adapter_bundle_sha256': parent['adapter_bundle_sha256'], 'software_fixture_only': True}
    receipt['initialization_receipt_sha256'] = native.common.domain_sha256(receipt['schema_id'], receipt, sha_field='initialization_receipt_sha256')
    (request_path.parent / 'INITIALIZATION_RECEIPT.json').write_bytes(m.canonical(receipt))
    def forbidden(path):
        pytest.fail('adoption must never call original smoke or initialize a model')
    monkeypatch.setattr(clean.runner, 'smoke', forbidden)
    result = clean.execute(native=native, request_path=request_path, adopt_only=True)
    assert result['training_execution_count'] == 0 and result['optimizer_executed'] is False
    assert result['projection']['current']['parent']['adapter_path'] == parent['adapter_path']
    assert not (request_path.parent / 'SMOKE_EXECUTION_STARTED.json').exists()


def test_captured_current_pi0_runtime_derives_context_without_recipe_fallback():
    module = _module()
    request = json.loads((WORK / "v14_live_export/current_v14/authority/ROUND_ROLLOUT_COLLECTION_REQUEST_V1.json").read_bytes())
    capsule = WORK / "v16/reference/PCHSI_CAMPAIGN_AUTHORITY_DRIVEN_FRESH_MEMORY_AWARE_TRAIN_UPDATE_ROLLOUT_V1_23_2/V123133_MEMORY_AWARE_GENERIC_ROLLOUT_LIVE_SOURCE_CAPSULE.zip"
    with zipfile.ZipFile(capsule) as archive:
        raw = archive.read("CLEAN_PI0_LIVE_RUNTIME_BINDING_V2.json")
    profile = REPO / module.PROFILE_REL
    result = module.derive_clean_parent_metadata(source_request=request, runtime_bytes=raw, native_repo_root=REPO,
        profile_file_sha256=hashlib.sha256(profile.read_bytes()).hexdigest())
    assert result["parent"]["policy_id"] == request["parent_policy_id"] == "PI0_CLEAN"
    assert result["current_parent_binding_sha256"] == request["policy_runtime_binding_sha256"]
    assert result["base_binding"]["snapshot_path"] == json.loads(raw)["base_model_local_path"]
    assert "training_seed" not in result and "budget" not in result
    assert result["peft"]["r"] == 16
