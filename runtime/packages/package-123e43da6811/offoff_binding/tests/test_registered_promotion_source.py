"""Exercise the actual V1.8 runtime delta, locally and in packaged fixtures."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types

import pytest


def _ref(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf8")
    return _ref(path)


def _load(name, path, monkeypatch):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def runtime(monkeypatch):
    here = Path(__file__).resolve()
    if here.parent.name == "promotion_rule_work":
        project = here.parents[3]
        runtime_root = project / "work/v18/runtime"
        dependencies = project / "work/v17"
    else:
        runtime_root = here.parents[2]
        dependencies = runtime_root
    monkeypatch.syspath_prepend(str(dependencies / "native_bba_full/src"))
    monkeypatch.syspath_prepend(str(dependencies))
    package = types.ModuleType("offoff_binding")
    package.__path__ = [str(runtime_root / "offoff_binding"), str(dependencies / "offoff_binding")]
    monkeypatch.setitem(sys.modules, "offoff_binding", package)
    execute = _load("offoff_binding.execute", runtime_root / "offoff_binding/execute.py", monkeypatch)
    _load("offoff_binding.promotion_rule", runtime_root / "offoff_binding/promotion_rule.py", monkeypatch)
    entry = types.ModuleType("_promotion_source_test_entry")
    entry.__path__ = [str(runtime_root / "entry")]
    monkeypatch.setitem(sys.modules, entry.__name__, entry)
    preflight = _load(entry.__name__ + ".preflight", runtime_root / "entry/preflight.py", monkeypatch)
    registration = _load(entry.__name__ + ".registration", runtime_root / "entry/registration.py", monkeypatch)
    assert Path(execute.__file__).resolve() == runtime_root / "offoff_binding/execute.py"
    return types.SimpleNamespace(root=runtime_root, execute=execute, preflight=preflight, registration=registration)


def _rule(runtime):
    source = _ref(runtime.root / "offoff_binding/promotion_rule.py")
    return {
        "schema_id": "FROZEN_TRAIN_SELECT_PROMOTION_RULE_V1", "frozen_before_outcomes": True,
        "evidence_access_class": "TRAIN_SELECT", "decision_rule_id": "fixture-success-count",
        "primary_metric": "total_success_cells", "comparison": "strictly_greater",
        "secondary_metrics_role": "explanation_only", "expected_task_count": 2,
        "replicate_seeds": [7, 19], "registered_select_task_access_sha256": "a" * 64,
        "decision_producer": {"source_member": "offoff_binding/promotion_rule.py",
                              "sha256": source["sha256"], "entrypoint": "decide"},
    }


def test_package_source_resolves_and_loads_registered_function(runtime):
    rule = _rule(runtime)
    expected = _ref(runtime.root / "offoff_binding/promotion_rule.py")
    assert runtime.execute.registered_decision_source(rule) == expected
    native = types.SimpleNamespace(sources={expected["path"]: expected})
    decider = runtime.execute._registered_decider(native, rule)
    # Frozen config validation happens before receiving any outcome.
    assert callable(decider)
    rule["comparison"] = "greater_or_equal"
    with pytest.raises(ValueError, match="comparison"):
        runtime.execute._registered_decider(native, rule)


@pytest.mark.parametrize("member", ["../escape.py", "/escape.py", "offoff_binding\\escape.py",
                                    "C:/escape.py", "C:escape.py", "", "offoff_binding"])
def test_package_source_rejects_path_escape_and_nonfiles(runtime, member):
    rule = _rule(runtime)
    rule["decision_producer"]["source_member"] = member
    with pytest.raises(ValueError, match="PROMOTION_SOURCE_MEMBER_INVALID"):
        runtime.execute.registered_decision_source(rule)


def test_ambiguous_source_cannot_choose_between_member_and_reference(runtime):
    rule = _rule(runtime)
    rule["decision_producer"]["source_ref"] = _ref(runtime.root / "offoff_binding/promotion_rule.py")
    with pytest.raises(ValueError, match="AMBIGUOUS_PROMOTION_SOURCE"):
        runtime.execute.registered_decision_source(rule)


def test_missing_producer_retains_existing_continuity_error(runtime):
    with pytest.raises(runtime.execute.ContinuityError, match="FROZEN_PROMOTION_DECISION_PRODUCER_REQUIRED"):
        runtime.execute._registered_decider(types.SimpleNamespace(sources={}), {"decision_rule_id": "fixture"})


@pytest.mark.parametrize("wrong_sha", [False, True])
def test_package_producer_must_match_exact_native_registration(runtime, wrong_sha):
    rule = _rule(runtime)
    source = runtime.execute.registered_decision_source(rule)
    sources = {source["path"]: {**source, "sha256": "0" * 64}} if wrong_sha else {}
    with pytest.raises(ValueError, match="PROMOTION_PRODUCER_NOT_REGISTERED"):
        runtime.execute._registered_decider(types.SimpleNamespace(sources=sources), rule)


def test_legacy_exact_source_reference_still_executes_and_checks_bytes(runtime, tmp_path):
    source_path = tmp_path / "legacy_fixture_decider.py"
    source_path.write_text('def decide(*, frozen_rule, aggregate):\n'
                           '    return {"decision": "ROLLBACK", "decision_rule_id": frozen_rule["decision_rule_id"]}\n',
                           encoding="utf8")
    source = _ref(source_path)
    rule = {"decision_rule_id": "legacy-fixture", "decision_producer": {"source_ref": source, "entrypoint": "decide"}}
    native = types.SimpleNamespace(sources={source["path"]: source})
    assert runtime.execute._registered_decider(native, rule)(frozen_rule=rule, aggregate={}) == {
        "decision": "ROLLBACK", "decision_rule_id": "legacy-fixture",
    }
    source_path.write_text('raise RuntimeError("unregistered source")\n', encoding="utf8")
    with pytest.raises(ValueError, match="FILE_SHA_MISMATCH"):
        runtime.execute._registered_decider(native, rule)


@pytest.fixture
def deployment(runtime, tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    marker = _json(bundle / "marker.json", {"fixture": True})
    (bundle / "PACKAGE_FILES.sha256").write_text(marker["sha256"] + "  marker.json\n", encoding="utf8")
    manifest_sha = _ref(bundle / "PACKAGE_FILES.sha256")["sha256"]
    task_access = _json(tmp_path / "task_access.json", {"fixture_tasks": ["a", "b"]})
    protocol = _json(tmp_path / "protocol.json", {"grid": {"task_count": 2, "replicate_seeds": [7, 19]}})
    rule = _rule(runtime)
    rule["registered_select_task_access_sha256"] = task_access["sha256"]
    rule_ref = _json(tmp_path / "rule.json", rule)
    source = runtime.execute.registered_decision_source(rule)
    value = {
        "entry_source_sha256": manifest_sha, "formal_files": {},
        "scientific_repo_root": str(tmp_path / "native"), "promotion_rule_ref": rule_ref,
        "training_source_registration": {"repo_head": "f" * 40, "source_files": {},
            "dual_adapter": marker, "operational_request_ref": marker, "binding_source_files": {}},
        "offoff_source_registration": {"source_refs": [source], "promotion_rule_ref": rule_ref,
            "assets": {"historical_protocol": protocol, "task_access": task_access}, "code_source_ref": marker},
    }
    return value, {"formal_root": tmp_path / "formal", "bundle_root": bundle}, rule


def test_preflight_accepts_the_registered_frozen_grid_without_outcomes(runtime, deployment):
    value, locations, _ = deployment
    result = runtime.preflight.validate_deployment(value, **locations)
    assert result == {"package_file_count": 1, "entry_source_sha256": value["entry_source_sha256"],
                      "scientific_execution_started": False}


@pytest.mark.parametrize("field,other", [("expected_task_count", 3), ("replicate_seeds", [7, 23]),
                                        ("registered_select_task_access_sha256", "0" * 64)])
def test_preflight_rejects_rule_bound_to_a_different_registered_grid(runtime, deployment, field, other):
    value, locations, rule = deployment
    rule[field] = other
    changed_ref = _json(Path(value["promotion_rule_ref"]["path"]), rule)
    value["promotion_rule_ref"] = changed_ref
    value["offoff_source_registration"]["promotion_rule_ref"] = changed_ref
    with pytest.raises(ValueError, match="PROMOTION_RULE_REGISTERED_SELECT_GRID_CHANGED"):
        runtime.preflight.validate_deployment(value, **locations)


def test_preflight_rule_must_be_the_actual_execution_rule(runtime, deployment):
    value, locations, _ = deployment
    value["offoff_source_registration"]["promotion_rule_ref"] = value["offoff_source_registration"]["code_source_ref"]
    with pytest.raises(ValueError, match="PREFLIGHT_EXECUTION_RULE_MISMATCH"):
        runtime.preflight.validate_deployment(value, **locations)


def test_preflight_rejects_unregistered_package_producer(runtime, deployment):
    value, locations, _ = deployment
    value["offoff_source_registration"]["source_refs"] = []
    with pytest.raises(ValueError, match="FORMAL_PROMOTION_PRODUCER_NOT_REGISTERED"):
        runtime.preflight.validate_deployment(value, **locations)


def test_preflight_legacy_source_reference_remains_supported(runtime, deployment, tmp_path):
    value, locations, rule = deployment
    path = tmp_path / "legacy.py"
    path.write_text('def decide(**kwargs): return {}\n', encoding="utf8")
    source = _ref(path)
    rule["decision_producer"] = {"source_ref": source, "entrypoint": "decide"}
    changed_ref = _json(Path(value["promotion_rule_ref"]["path"]), rule)
    value["promotion_rule_ref"] = changed_ref
    value["offoff_source_registration"].update(promotion_rule_ref=changed_ref, source_refs=[source])
    assert runtime.preflight.validate_deployment(value, **locations)["scientific_execution_started"] is False


@pytest.fixture
def registry_bundle(tmp_path):
    root = tmp_path / "registry_bundle"
    root.mkdir()
    formal = str(tmp_path / "formal")
    repo = str(tmp_path / "native")

    def member(name, data):
        ref = _json(root / name, data)
        return {"member": name, "sha256": ref["sha256"]}

    source = member("offoff_binding/promotion_rule.py", {"fixture_source": True})
    rule = member("rule.json", {"fixture_rule": True})
    adapter = member("adapter.py", {"fixture_adapter": True})
    template = {
        "schema_id": "FORMAL_REGISTERED_EXECUTION_SOURCE_REGISTRY_V1", "native_commit": "f" * 40,
        "capture": member("capture.json", {"formal_state_root": formal, "repo": {"head": "f" * 40}}),
        "source_plan": member("plan.json", {"protected_roots": [formal]}),
        "ready": member("ready.json", {"settings": {}, "capsule_path": repo + "/capsule", "capsule_sha256": "a" * 64}),
        "gate2": member("gate2.json", {"manifest": [{"kind": "git_relevant_sources_archive", "source_path": repo}]}),
        "authority_members": member("authority.json", {"files": []}),
        "training": {"dual_adapter_member": adapter, "operational_request_relative": "request.json",
                     "source_files": {"request.json": "c" * 64}, "binding_members": []},
        "offoff": {"native_sources": [], "binding_members": [source], "code_source_member": adapter, "assets": {}},
        "promotion_rule": rule,
    }
    _json(root / "EXECUTION_SOURCE_REGISTRY.json", template)
    return root, template


def test_registration_installs_package_producer_and_one_shared_rule_reference(runtime, registry_bundle):
    root, _ = registry_bundle
    value = runtime.registration.build_deployment(root, entry_source_sha256="e" * 64)
    offoff = value["offoff_source_registration"]
    assert offoff["source_refs"] == [_ref(root / "offoff_binding/promotion_rule.py")]
    assert offoff["promotion_rule_ref"] == value["promotion_rule_ref"] == _ref(root / "rule.json")


@pytest.mark.parametrize("member", ["../escape.py", "/escape.py", "offoff_binding\\escape.py", "C:/escape.py", "C:escape.py"])
def test_registration_rejects_escaped_package_producer_before_file_access(runtime, registry_bundle, member):
    root, template = registry_bundle
    template["offoff"]["binding_members"][0]["member"] = member
    _json(root / "EXECUTION_SOURCE_REGISTRY.json", template)
    with pytest.raises(ValueError, match="REGISTERED_PACKAGE_MEMBER_INVALID"):
        runtime.registration.build_deployment(root, entry_source_sha256="e" * 64)
