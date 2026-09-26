"""Compose existing clean-parent PEFT adapter with existing dual-view loader.

This is a Generic Training runtime adapter. It adds no optimizer implementation.
"""
from __future__ import annotations
import importlib.util
import importlib
import json
from pathlib import Path
import sys


def _module(ref, name):
    import hashlib
    path = Path(ref["path"])
    if not path.is_file() or path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != ref["sha256"]:
        raise ValueError("CLEAN_DUAL_SOURCE_BINDING_MISMATCH:" + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def _bootstrap_canonical(runtime):
    """The original clean adapter imports the pinned repository JSON reader."""
    import hashlib
    ref = runtime["canonical_source"]
    path = Path(ref["path"]).resolve()
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != ref["sha256"]:
        raise ValueError("CLEAN_CANONICAL_SOURCE_BINDING_MISMATCH")
    source_root = path.parents[2]
    if str(source_root) not in sys.path:
        sys.path.insert(0, str(source_root))
    module = importlib.import_module("pchsi.reference_loop.canonical")
    imported = Path(module.__file__).resolve()
    # H4.4 can already have loaded a byte-identical canonical helper from its
    # sealed native source capsule. Accept equal code bytes, never a different
    # implementation merely because it uses the same Python import name.
    if imported.is_symlink() or hashlib.sha256(imported.read_bytes()).hexdigest() != ref["sha256"]:
        raise ValueError("CLEAN_CANONICAL_IMPORT_SOURCE_CONFLICT")


def _delegate(context):
    contract = context.training_contract
    runtime = contract["clean_runtime"]
    _bootstrap_canonical(runtime)
    clean = _module(runtime["clean_adapter_source"], "_v17_existing_clean_adapter")
    dual = _module(runtime["dual_view_adapter_source"], "_v17_existing_dual_loader")
    # Verify the exact existing zero-step evidence before the original PEFT
    # adapter is allowed to interpret the new parent as trainable weights.
    receipt = clean.obj(clean.checked_ref(runtime["initialization_receipt_ref"]).read_bytes())
    plan = clean.obj(clean.checked_ref(runtime["plan_ref"]).read_bytes())
    clean.verify_seed_zero_receipt(receipt, plan, runtime)
    clean.need(contract["parent"]["pilot_adapter_reuse_allowed"] is False, "CURRENT_CLEAN_PILOT_ADAPTER_FORBIDDEN")
    continuation = runtime.get("accepted_parent_context")
    if continuation:
        from training_binding.accepted_output import read_accepted_output
        accepted = read_accepted_output(continuation)
        for key in ("adapter_path", "adapter_bundle_sha256", "final_trainable_parameter_sha256"):
            clean.need(contract["parent"][key] == accepted[key], "CURRENT_ACCEPTED_PARENT_" + key)
        clean.need(contract["parent"]["load_semantics"] == "PEFT_FROM_PRETRAINED_IS_TRAINABLE_TRUE", "CURRENT_CONTINUATION_LOAD_SEMANTICS")
    else:
        clean.need(contract["parent"]["policy_id"] == plan["parent_policy_id"], "CURRENT_CLEAN_PARENT_POLICY_ID")
        clean.need(contract["parent"]["final_trainable_parameter_sha256"] == receipt["initial_trainable_parameter_sha256"], "CURRENT_CLEAN_PARENT_INITIAL_HASH")
        clean.need(contract["parent"]["adapter_path"] == receipt["adapter_path"], "CURRENT_CLEAN_ONLY_ZERO_STEP_ADAPTER")
        clean.need(contract["budget"] == plan["policy_training_recipe"]["budget"], "CURRENT_CLEAN_RECIPE_BUDGET_DRIFT")
    delegate = clean._configured_legacy(context)
    delegate._load_records = dual._records_for_contract
    if continuation:
        # Keep original PEFT load/optimizer/schedule bodies. Correct only the
        # original clean wrapper's provenance labels for an accepted descendant.
        install = delegate._install_parent_adapter
        def install_continuation(parent, *, context):
            install(parent, context=context)
            builder = parent.build_formal_run_manifest
            def build_manifest(**kwargs):
                value = builder(**kwargs)
                value['parent_initialization'] = 'CONTINUE_ACCEPTED_PARENT_ADAPTER'
                value['parent_training_stage_receipt_sha256'] = accepted['terminal']['stage_receipt_sha256']
                return value
            parent.build_formal_run_manifest = build_manifest
        delegate._install_parent_adapter = install_continuation
        def continuation_refs(context):
            refs = clean.input_artifact_refs(context)
            for ref in refs:
                ref['logical_name'] = ref['logical_name'].replace('CLEAN_STEP_ZERO_', 'ACCEPTED_PARENT_')
                if ref['logical_name'] == 'CURRENT_PLANNER_PLAN':
                    ref['logical_name'] = 'ANCESTOR_INITIALIZATION_PLAN'
            for name, ref in continuation.items():
                if isinstance(ref, dict) and 'path' in ref and 'sha256' in ref:
                    path = clean.checked_ref(ref)
                    refs.append({'logical_name': 'ACCEPTED_PARENT_' + name.upper(), 'path': str(path),
                        'sha256': ref['sha256'], 'size_bytes': path.stat().st_size,
                        'retention_class': 'VALIDATED_SCIENTIFIC_ARTIFACT', 'schema_id': None})
            return refs
        delegate.input_artifact_refs = continuation_refs
    return delegate


def validate_profile_without_model_load(context):
    return _delegate(context).validate_profile_without_model_load(context)


def input_artifact_refs(context):
    return _delegate(context).input_artifact_refs(context)


def execute_training_stage(*, context, output_dir, runner_freeze_root_sha256):
    return _delegate(context).execute_training_stage(context=context, output_dir=output_dir,
        runner_freeze_root_sha256=runner_freeze_root_sha256)
