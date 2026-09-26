"""Reuse Stage4A's actual zero-step initializer for a current Strong plan.

Only its historical packet loader is adapted. The original smoke body performs
the GPU initialization, exact-zero-effect check, save, repeat-seed and reload.
No historical diagnostic plan, adapter, budget or approval token is promoted.
"""
from __future__ import annotations
import copy
from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any
from unittest.mock import patch

from .materializer import (
    NativeTraining, _order_manifest, _read_ref, _seal, _sha, _verify_seal,
    accept_recipe_decision, build_current_contract, canonical, digest,
)

TRAINER_REL = Path("scripts/engineering_snapshots/training_pipeline/round_generic_training_stage_v2_1_hardening_build")
PROFILE_REL = TRAINER_REL / "profiles/human_reference_t2/ROUND_LOCAL_TRAINING_CONTRACT_V1.json"


def derive_clean_parent_metadata(*, source_request: dict, runtime_bytes: bytes,
                                 native_repo_root: Path, profile_file_sha256: str) -> dict:
    """Use current rollout identity and the same code/model-only refs as Stage4A.

    The historical profile supplies its registered initializer code reference,
    immutable base-model manifest, and LoRA architecture reference. It supplies
    no dataset, seed, epoch, optimizer schedule, diagnostic flag, or approval.
    This is Stage3Y's documented architecture inheritance and Stage4A's existing
    clean-snapshot binding, now derived from the current native rollout request.
    """
    if hashlib.sha256(runtime_bytes).hexdigest() != source_request["policy_runtime_binding_sha256"]:
        raise ValueError("CURRENT_RUNTIME_FILE_BINDING_MISMATCH")
    runtime = json.loads(runtime_bytes)
    if runtime.get("schema_id") != "CLEAN_PI0_LIVE_RUNTIME_BINDING_V2":
        raise ValueError("CURRENT_CLEAN_RUNTIME_SCHEMA_UNSUPPORTED")
    if runtime["policy_runtime_manifest_sha256"] != source_request["parent_policy_artifact_sha256"]:
        raise ValueError("CURRENT_RUNTIME_PARENT_ARTIFACT_MISMATCH")
    path = Path(native_repo_root) / PROFILE_REL
    profile = json.loads(_read_ref({"path": str(path), "sha256": profile_file_sha256}))
    reference = profile["parent"]
    if runtime["tokenizer_revision"] != reference["base_model_revision"]:
        raise ValueError("CURRENT_BASE_MODEL_REVISION_REFERENCE_MISMATCH")
    parent = {k: reference[k] for k in ("base_model_artifact_manifest_path", "base_model_artifact_manifest_sha256",
        "base_model_repository", "base_model_revision", "formal_train_path", "formal_train_sha256")}
    parent.update(policy_id=source_request["parent_policy_id"], pilot_adapter_reuse_allowed=False,
                  base_model_local_path=runtime["base_model_local_path"])
    base = {"snapshot_path": runtime["base_model_local_path"], "manifest_path": reference["base_model_artifact_manifest_path"],
            "manifest_sha256": reference["base_model_artifact_manifest_sha256"], "repository_id": reference["base_model_repository"],
            "revision": reference["base_model_revision"]}
    # Only frozen runtime semantics are inherited; historical bad-node exclusions
    # are execution-attempt state and are deliberately not copied.
    execution = {k: v for k, v in profile["execution"].items() if k != "infrastructure_node_exclusions"}
    return {"parent": parent, "peft": copy.deepcopy(profile["peft"]), "execution": execution,
            "base_binding": base, "formal_source": {"path": reference["formal_train_path"], "sha256": reference["formal_train_sha256"]},
            "ordering_domain": "CURRENT_STRONG_PRIMARY_VERIFIED_DUAL_VIEW_ORDER_V1",
            "current_parent_binding_sha256": source_request["policy_runtime_binding_sha256"],
            "architecture_reference": {"path": str(path), "sha256": profile_file_sha256, "inherited_sections": ["peft", "execution_capabilities", "parent_code_and_base_manifest_only"]}}


@dataclass(frozen=True)
class NativeClean:
    root: Path
    source_sha256s: dict[str, str]
    adapter: Any
    runner: Any

    @classmethod
    def load(cls, root: Path, source_sha256s: dict[str, str]):
        root = Path(root).resolve()
        modules = {}
        previous = sys.modules.get("clean_adapter")
        try:
            for name in ("clean_adapter", "run_stage"):
                path = root / (name + ".py")
                _read_ref({"path": str(path), "sha256": source_sha256s.get(path.name)})
                spec = importlib.util.spec_from_file_location(name, path)
                value = importlib.util.module_from_spec(spec)
                if name == "clean_adapter": sys.modules[name] = value
                spec.loader.exec_module(value)
                modules[name] = value
        finally:
            if previous is None: sys.modules.pop("clean_adapter", None)
            else: sys.modules["clean_adapter"] = previous
        return cls(root, dict(source_sha256s), modules["clean_adapter"], modules["run_stage"])

    def prepare(self, *, native: NativeTraining, projection: dict, decision: dict,
                base_binding: dict, formal_source: dict, output_root: Path,
                binding_source_sha256s: dict[str, str]) -> dict:
        """Freeze current recipe inputs and a zero-optimizer initialization request."""
        contract, rows, _ = build_current_contract(native=native, projection=projection, decision=decision)
        root = Path(output_root).resolve()
        native.adapter.validate_runtime_capabilities(contract)
        _read_ref(formal_source)
        sources = dict(native.source_sha256s)
        sources.update({str(self.root / name): value for name, value in self.source_sha256s.items()})
        sources.update(binding_source_sha256s)
        sources[formal_source["path"]] = formal_source["sha256"]
        canonical_path = native.root.parents[3] / "src/pchsi/reference_loop/canonical.py"
        for relative in ("src/pchsi/__init__.py", "src/pchsi/reference_loop/__init__.py", "src/pchsi/reference_loop/canonical.py"):
            source = native.root.parents[3] / relative
            sources[str(source)] = hashlib.sha256(source.read_bytes()).hexdigest()
        required_binding_files = (Path(__file__).resolve(), Path(__file__).with_name("clean_dual_runtime.py").resolve(), Path(__file__).with_name("materializer.py").resolve())
        for path in required_binding_files:
            if str(path) not in binding_source_sha256s:
                raise ValueError("CLEAN_BINDING_SOURCE_SEAL_MISSING:" + str(path))
        for path, expected in sources.items(): _read_ref({"path": path, "sha256": expected})
        runtime = {"base_binding": copy.deepcopy(base_binding), "formal_source": copy.deepcopy(formal_source),
            "canonical_source": {"path": str(canonical_path), "sha256": sources[str(canonical_path)]},
            "legacy_adapter_source": {"path": str(native.root / "round_training/adapters/frozen_formal_train_peft.py"), "sha256": native.source_sha256s[str(native.root / "round_training/adapters/frozen_formal_train_peft.py")]},
            "clean_adapter_source": {"path": str(self.root / "clean_adapter.py"), "sha256": self.source_sha256s["clean_adapter.py"]},
            "dual_view_adapter_source": {"path": str(native.dual_path), "sha256": native.source_sha256s[str(native.dual_path)]},
            "source_code_files": sources, "source_code_root_sha256": digest(sources)}
        contract["clean_runtime"] = runtime
        parent = self.adapter.load_clean_formal(contract, {"ordering_domain": projection["current"]["ordering_domain"]})
        recipe = decision["recipe"]
        orders = [list(x) for x in parent.build_training_orders(example_count=len(rows), seed=recipe["data_seed"], passes=recipe["epochs"])]
        order = _order_manifest(rows, recipe, orders, projection["current"]["ordering_domain"])
        native.contracts.validate_training_contract(contract, order)
        plan = {"schema_id": "CURRENT_STRONG_POST_INITIALIZATION_PLAN_V1", "schema_version": 1,
            "round_id": contract["round_id"], "parent_policy_id": contract["parent"]["policy_id"],
            "source_recipe_decision_sha256": decision["decision_sha256"],
            "post_primary_record_sha256": projection["accepted_post"]["primary_record_sha256"],
            "policy_training_recipe": {"budget": copy.deepcopy(contract["budget"]), "recipe": copy.deepcopy(recipe)},
            "peft": copy.deepcopy(contract["peft"]), "training_execution_authorized": False}
        plan["training_plan_sha256"] = native.common.domain_sha256(plan["schema_id"], plan, sha_field="training_plan_sha256")
        runtime["plan_ref"] = {"path": str(root / "CURRENT_STRONG_POST_INITIALIZATION_PLAN_V1.json"), "sha256": hashlib.sha256(canonical(plan)).hexdigest()}
        request = {"schema_id": "CURRENT_STRONG_CLEAN_INITIALIZATION_REQUEST_V1", "schema_version": 1,
            "round_id": contract["round_id"], "projection_sha256": projection["projection_sha256"],
            "decision_sha256": decision["decision_sha256"], "runtime": runtime, "output_root": str(root),
            "request": {"current_strong_recipe": True}, "plan_sha256": plan["training_plan_sha256"],
            "authorization_scope": "INITIALIZATION_ONLY_NO_OPTIMIZER", "training_authorized": False}
        request["request_sha256"] = native.common.domain_sha256(request["schema_id"], request, sha_field="request_sha256")
        authorization = {"schema_id": "CURRENT_STRONG_CLEAN_INITIALIZATION_AUTHORIZATION_V1",
            "request_sha256": request["request_sha256"], "authorization_scope": "INITIALIZATION_ONLY_NO_OPTIMIZER",
            "same_call_recipe_receipt_sha256": decision["same_call_recipe_receipt"]["recipe_receipt_sha256"],
            "authorized_optimizer_steps": 0, "training_execution_authorized": False}
        values = {"CURRENT_STRONG_POST_INITIALIZATION_PLAN_V1.json": plan,
            "INITIALIZATION_REQUEST.json": request, "SMOKE_AUTHORIZATION.json": authorization,
            "CURRENT_INITIALIZATION_CONTRACT.json": contract, "CURRENT_INITIALIZATION_ORDER.json": order,
            "CURRENT_TRAINING_INPUT_V1.json": projection, "CURRENT_STRONG_POST_TRAINING_RECIPE_V1.json": decision}
        for name, value in values.items():
            path = root / name
            if path.exists() and (path.is_symlink() or path.read_bytes() != canonical(value)):
                raise ValueError("CLEAN_INITIALIZATION_INPUT_CONFLICT:" + name)
        root.mkdir(parents=True, exist_ok=True)
        for name, value in values.items(): self.runner.put(root / name, value)
        return {"request_path": str(root / "INITIALIZATION_REQUEST.json"), "request_sha256": request["request_sha256"],
                "optimizer_executed": False, "initialization_executed": False}

    def execute(self, *, native: NativeTraining, request_path: Path, adopt_only: bool = False) -> dict:
        """Execute original native zero-step smoke. Never submit Slurm or train."""
        path = Path(request_path).resolve()
        root = path.parent
        read = lambda name: json.loads((root / name).read_bytes())
        request = read(path.name)
        native.common.require_domain_sha(request, schema_id="CURRENT_STRONG_CLEAN_INITIALIZATION_REQUEST_V1", sha_field="request_sha256")
        if Path(request["output_root"]).resolve() != root:
            raise ValueError("CLEAN_INITIALIZATION_OUTPUT_ROOT_MISMATCH")
        for source, expected in request["runtime"]["source_code_files"].items(): _read_ref({"path": source, "sha256": expected})
        if digest(request["runtime"]["source_code_files"]) != request["runtime"]["source_code_root_sha256"]:
            raise ValueError("CLEAN_INITIALIZATION_SOURCE_ROOT_MISMATCH")
        projection, decision = read("CURRENT_TRAINING_INPUT_V1.json"), read("CURRENT_STRONG_POST_TRAINING_RECIPE_V1.json")
        _verify_seal(projection, "projection_sha256"); _verify_seal(decision, "decision_sha256")
        if request["projection_sha256"] != projection["projection_sha256"] or request["decision_sha256"] != decision["decision_sha256"]:
            raise ValueError("CLEAN_INITIALIZATION_CURRENT_INPUT_IDENTITY_MISMATCH")
        expected_contract, records, _ = build_current_contract(native=native, projection=projection, decision=decision)
        contract, order = read("CURRENT_INITIALIZATION_CONTRACT.json"), read("CURRENT_INITIALIZATION_ORDER.json")
        runtime = request["runtime"]
        if {k: v for k, v in contract.items() if k != "clean_runtime"} != expected_contract or contract["clean_runtime"] != runtime:
            raise ValueError("CLEAN_INITIALIZATION_SCIENTIFIC_CONTRACT_CHANGED")
        native.contracts.validate_training_contract(contract, order)
        plan = json.loads(_read_ref(runtime["plan_ref"]))
        native.common.require_domain_sha(plan, schema_id=plan["schema_id"], sha_field="training_plan_sha256")
        if plan["training_plan_sha256"] != request["plan_sha256"] or plan["source_recipe_decision_sha256"] != decision["decision_sha256"]:
            raise ValueError("CLEAN_INITIALIZATION_PLAN_IDENTITY_MISMATCH")
        data = {"contract": contract, "order": order, "native": records, "plan": plan}
        from .clean_dual_runtime import _bootstrap_canonical
        _bootstrap_canonical(runtime)
        def validate_receipt(_request, receipt):
            self.adapter.verify_seed_zero_receipt(receipt, plan, runtime)
            return receipt
        # These three adapters replace only historical packet/Git discovery and
        # old diagnostic binding compilation. Native smoke/model code is intact.
        if adopt_only:
            # Equivalent to the original smoke's existing-receipt branch, but
            # structurally cannot fall through into initialization on a GPU.
            if not (root / "INITIALIZATION_RECEIPT.json").is_file():
                raise ValueError("SEPARATE_INITIALIZATION_RECEIPT_REQUIRED_NO_SMOKE_REEXECUTION")
        else:
            with patch.object(self.runner, "checked_request", lambda _path: request), \
                 patch.object(self.runner, "load_source", lambda _request: data), \
                 patch.object(self.runner, "compile_binding", validate_receipt):
                self.runner.smoke(path)
        receipt = read("INITIALIZATION_RECEIPT.json")
        validate_receipt(request, receipt)
        current = copy.deepcopy(projection["current"])
        current["parent"].update(formal_train_path=runtime["formal_source"]["path"], formal_train_sha256=runtime["formal_source"]["sha256"],
            adapter_path=receipt["adapter_path"], adapter_artifact_manifest_path=receipt["adapter_manifest_path"],
            adapter_artifact_manifest_sha256=receipt["adapter_manifest_sha256"], adapter_bundle_sha256=receipt["adapter_bundle_sha256"],
            final_trainable_parameter_sha256=receipt["initial_trainable_parameter_sha256"],
            load_semantics="PEFT_LOAD_FRESH_SEEDED_STEP_ZERO_ADAPTER_IS_TRAINABLE_TRUE", pilot_adapter_reuse_allowed=False)
        current["clean_runtime"] = copy.deepcopy(runtime)
        current["clean_runtime"].update(initialization_receipt_ref={"path": str(root / "INITIALIZATION_RECEIPT.json"), "sha256": hashlib.sha256((root / "INITIALIZATION_RECEIPT.json").read_bytes()).hexdigest()},
            initialization_receipt_sha256=receipt["initialization_receipt_sha256"])
        current["runner_freeze_root_sha256"] = runtime["source_code_root_sha256"]
        new_projection = _seal({**projection, "current": current}, "projection_sha256")
        new_decision = accept_recipe_decision(decision["same_call_recipe_receipt"], projection=new_projection)
        return {"projection": new_projection, "decision": new_decision,
                "initialization_receipt_sha256": receipt["initialization_receipt_sha256"],
                "initialization_executed": True, "optimizer_executed": False, "training_execution_count": 0}
