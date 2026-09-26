"""Tests for isolation and one-admission behavior; no remote/provider execution."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest

from one_validation import (ValidationError, run_validation, memory_reuse_context,
                            export_validation, write_once, read_ref, validation_lock, _stage)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    path.write_bytes(raw)
    return {"path": str(path.absolute()), "sha256": hashlib.sha256(raw).hexdigest()}


class NativeFixture:
    """GPU/provider boundaries are unavailable locally; receipts remain real files."""
    def __init__(self, outcome="NO_TRAINING_UPDATE"):
        self.outcome = outcome

    def validate_start(self, binding, values):
        assert binding["round_id"] == values["request"]["round_id"]

    def evidence(self, analyzer_root):
        return {k: save(Path(analyzer_root) / (k + ".json"), v) for k, v in {
            "execution_plan": {"plan_sha256": "b" * 64, "source_request": self.start},
            "verifier": {"schema_id": "CURRENT_ROUND_INDEPENDENT_VERIFIER_RESULT_V1",
                         "stable_effect_counts": {"BENEFIT": int(self.outcome != "NO_TRAINING_UPDATE")},
                         "state_results": [], "branch_records": []}}.items()}

    def post(self, *, start, evidence_refs):
        read_ref(evidence_refs["execution_plan"])
        return ({"researcher_training_recommendation":
                 "NO_TRAIN" if self.outcome == "NO_TRAINING_UPDATE" else "TRAIN"}, {})

    def replay(self, result):
        assert read_ref(result["stage_evidence_refs"]["execution_plan"])["plan_sha256"] == "b" * 64

    def train(self, **kw):
        return {"training_ref": save(Path(kw["output_root"]) / "TRAINED.json",
                                    {"round_id": kw["start"]["round_id"], "training_execution_count": 1})}

    def offoff(self, **kw):
        assert read_ref(kw["trained"]["training_ref"])["training_execution_count"] == 1
        return {"terminal_ref": save(Path(kw["output_root"]) / "TERMINAL.json", {"outcome": self.outcome}),
                "next_policy_input_refs": {"runtime": {"path": "/candidate", "sha256": "c" * 64}},
                "current_parent_context": {"candidate": True}}

    def close(self, *, reuse, **kw):
        training = kw["training_result_ref"]
        if self.outcome == "NO_TRAINING_UPDATE":
            assert training is None and kw["next_policy_input_refs"] is None
        else:
            assert read_ref(training)["outcome"] == self.outcome
            assert (kw["next_policy_input_refs"] is not None) == (self.outcome == "PROMOTED")
        root = Path(kw["attempt_root"])
        memory = save(root / "tail/MEMORY.json", {"request_sha256": kw["start"]["request_sha256"]})
        start = kw["start"]
        return {**start, "schema_id": "FORMAL_NATIVE_ROUND_RESULT_V1", "outcome": self.outcome,
                "next_parent_policy_id": "new" if self.outcome == "PROMOTED" else start["parent_policy_id"],
                "next_parent_policy_artifact_sha256": "c" * 64 if self.outcome == "PROMOTED" else start["parent_policy_artifact_sha256"],
                "next_request": None, "human_scientific_decision_count": 0, "benchmark_feedback_used": False,
                "terminal_ref": save(root / "tail/TERMINAL.json", {"outcome": self.outcome}),
                "stage_evidence_refs": {**kw["stage_evidence_refs"], "memory_materialization": memory}}

    def validate_result(self, *, start, result, authority):
        assert result["round_id"] == start["round_id"] and result["next_request"] is None
        read_ref(result["stage_evidence_refs"]["memory_materialization"])

    def export(self, *, start, result, authority, experiment_root):
        return save(Path(experiment_root) / "export/INDEX.json", {
            "experiment_id": authority["experiment_id"], "formal_valid_round_contribution": 0,
            "independent_new_source_sample_count": 0, "outcome": result["outcome"]})


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).absolute()
        self.source = self.root / "source"
        self.run = self.root / "validation"
        self.start = {"round_id": "FORMAL-R5", "request_sha256": "1" * 64,
                      "execution_attempt_id": "2" * 64, "parent_policy_id": "parent",
                      "parent_policy_artifact_sha256": "3" * 64,
                      "round_start_memory_snapshot_sha256": "4" * 64}
        request = save(self.source / "REQUEST.json", self.start)
        current = save(self.source / "CURRENT_INPUTS.json", {"request_sha256": self.start["request_sha256"]})
        execution = save(self.source / "EXECUTION.json", {"request_sha256": self.start["request_sha256"]})
        memory = save(self.source / "MEMORY_STATE.json", {"round_id": "FORMAL-R5"})
        old_plan = save(self.source / "OLD_PLAN.json", {"plan_sha256": "a" * 64})
        result = {**self.start, "outcome": "NO_TRAINING_UPDATE",
                  "next_parent_policy_id": "parent", "next_parent_policy_artifact_sha256": "3" * 64,
                  "current_parent_context": {"native": True}, "stage_evidence_refs": {
                      "current_inputs": current, "rollout_execution_binding": execution,
                      "memory_state": memory, "execution_plan": old_plan}}
        files = {}
        for role, relative, value in [
            ("census", "local/GROUP_PREPARATION_CENSUS.json", {"round_id": "FORMAL-R5", "sources": {}}),
            ("tail", "group/V1232U_STRONG_ANALYZER_TAIL_TERMINAL_V1.json", {"round_id": "FORMAL-R5"}),
            ("universe", "group/V1232U_DYNAMIC_PLANNER_PAIR_UNIVERSE_V1.json", {"round_id": "FORMAL-R5", "parent_policy_id": "parent", "pair_table": []}),
            ("execution", "local/strong_local_runtime/execution_manifest.json", {"round_id": "FORMAL-R5"}),
            ("source_units", "local/SOURCE_UNITS.json", {"rows": []})]:
            files[role] = save(self.source / relative, value)
        self.authority = {"schema_id": "PCHSI_REUSED_INPUT_SINGLE_VALIDATION_AUTHORITY_V1",
            "experiment_id": "strategy-v207-test", "max_validation_runs": 1,
            "implementation_sha256": "5" * 64, "source_request_ref": request,
            "source_result_ref": save(self.source / "RESULT.json", result),
            "live_parent_ref": save(self.root / "LIVE_PARENT.json", {"policy_id": "parent", "artifact_sha256": "3" * 64}),
            "source_analyzer_root": str(self.source), "source_files": files,
            "source_pre_logical_call_id": "6" * 64,
            "current_inputs_ref": current, "current_execution_binding_ref": execution,
            "current_memory_state_ref": memory, "current_parent_context": {"native": True},
            "round_index": 5, "deployment": {}}
        self.binding = {"round_id": "FORMAL-R5", "parent_policy_id": "parent", "refs": {"request": request}}
        self.values = {"request": self.start}

    def execute(self, native=None, pre=None, recover=None):
        native = native or NativeFixture()
        native.start = self.start
        def accepted(*args):
            output = Path(args[-1])
            save(output / "PRE_SENT.json", {"request": "new"})
            return ({"accepted_pre_logical_call_id": "7" * 64}, {"selected_states": [{}]})
        def capture(*args):
            return save(Path(args[-1]) / "CAPTURE.json", {"pre": args[4]})
        def h44(*args, **kw):
            return save(Path(args[2]) / "H44.json", {"environment_execution_count": 1})
        return run_validation(binding=self.binding, values=self.values, core=object(),
            authority=self.authority, experiment_root=self.run,
            pre_callable=pre or accepted, capture_callable=capture, h44_callable=h44,
            native=native, recover_callable=recover)

    def test_no_train_closes_memory_and_exports_without_training(self):
        terminal = self.execute()
        self.assertEqual(terminal["status"], "VALIDATION_COMPLETE")
        self.assertEqual(terminal["formal_valid_round_contribution"], 0)
        self.assertTrue((self.run / "tail/MEMORY.json").is_file())
        self.assertFalse((self.run / "training").exists())
        self.assertFalse((self.run / "offoff").exists())
        self.assertEqual(read_ref(terminal["export_ref"])["independent_new_source_sample_count"], 0)

    def test_training_and_offoff_only_follow_train_and_native_outcome(self):
        for outcome in ("PROMOTED", "ROLLED_BACK"):
            with self.subTest(outcome=outcome):
                self.run = self.root / outcome
                terminal = self.execute(NativeFixture(outcome))
                self.assertTrue((self.run / "training/TRAINED.json").is_file())
                self.assertTrue((self.run / "offoff/TERMINAL.json").is_file())
                self.assertEqual(read_ref(terminal["result_ref"])["outcome"], outcome)

    def test_completed_invocation_cannot_resend_provider_or_training(self):
        first = self.execute()
        def forbidden(*args):
            raise AssertionError("PRE sent twice")
        self.assertEqual(self.execute(pre=forbidden), first)

    def test_live_parent_drift_rejects_before_intent_or_pre(self):
        self.authority["live_parent_ref"] = save(self.root / "LIVE_PARENT.json", {"policy_id": "changed", "artifact_sha256": "3" * 64})
        with self.assertRaisesRegex(ValidationError, "PARENT"):
            self.execute()
        self.assertFalse((self.run / "INTENT.json").exists())

    def test_failed_provider_stage_cannot_be_resent_after_restart(self):
        def failed(*args):
            raise RuntimeError("provider response unknown")
        with self.assertRaisesRegex(RuntimeError, "unknown"):
            self.execute(pre=failed)
        with self.assertRaisesRegex(ValidationError, "STOP|AMBIGUOUS"):
            self.execute()
        self.assertFalse((self.run / "analyzer/pre/PRE_SENT.json").exists())

    def test_existing_intent_cannot_change_strategy_implementation(self):
        self.execute()
        self.authority["implementation_sha256"] = "8" * 64
        with self.assertRaisesRegex(ValidationError, "IMMUTABLE|IDENTITY"):
            self.execute()

    def test_old_pre_identity_is_rejected_before_capture(self):
        def old(*args):
            return ({"accepted_pre_logical_call_id": "6" * 64}, {"selected_states": [{}]})
        with self.assertRaisesRegex(ValidationError, "PRE.*IDENTITY"):
            self.execute(pre=old)
        self.assertFalse((self.run / "analyzer/h44/CAPTURE.json").exists())

    def test_source_ref_outside_typed_root_is_rejected(self):
        self.authority["source_files"]["census"] = save(self.root / "wrong.json", {"sources": {}})
        with self.assertRaisesRegex(ValidationError, "SOURCE.*PATH"):
            self.execute()

    def test_immutable_ref_detects_source_content_drift(self):
        Path(self.authority["source_request_ref"]["path"]).write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "SHA"):
            self.execute()

    def test_stage_receipt_without_prior_intent_cannot_be_adopted(self):
        save(self.run / "stages/PRE/RESULT.json", {"intent_ref": {}, "output": {}})
        with self.assertRaisesRegex(ValidationError, "RESULT_WITHOUT_INTENT"):
            _stage(self.run, "PRE", {}, lambda: {})
        self.assertFalse((self.run / "stages/PRE/INTENT.json").exists())

    def test_completed_terminal_cannot_be_relabelled_as_new_formal_round(self):
        terminal = self.execute()
        terminal["formal_valid_round_contribution"] = 1
        save(self.run / "VALIDATION_TERMINAL.json", terminal)
        with self.assertRaisesRegex(ValidationError, "TERMINAL.*SCOPE"):
            self.execute()

    def test_second_writer_cannot_enter_same_validation(self):
        with validation_lock(self.run):
            with self.assertRaisesRegex(ValidationError, "WRITER_ALREADY_ACTIVE"):
                self.execute()
        self.assertFalse((self.run / "INTENT.json").exists())

    def test_pre_binding_changes_are_persisted_without_rewriting_initial_binding(self):
        def changed(binding, values, core, tail, universe, out):
            binding["refs"]["cue_strategy_registry"] = save(Path(out) / "CUES.json", {"complete": True})
            return ({"accepted_pre_logical_call_id": "7" * 64}, {"selected_states": [{}]})
        self.execute(pre=changed)
        initial = json.loads((self.run / "INITIAL_ANALYZER_BINDING.json").read_bytes())
        current = json.loads((self.run / "CURRENT_ANALYZER_BINDING.json").read_bytes())
        self.assertNotIn("cue_strategy_registry", initial["refs"])
        self.assertTrue(read_ref(current["refs"]["cue_strategy_registry"])["complete"])

    def test_native_completed_pre_can_be_adopted_without_resending(self):
        output = {"accepted": {"accepted_pre_logical_call_id": "7" * 64},
                  "handoff": {"selected_states": [{}]},
                  "candidate_universe_ref": self.authority["source_files"]["universe"]}
        def interrupted(binding, values, core, tail, universe, out):
            save(Path(out) / "NATIVE_ACCEPTED.json", output)
            raise RuntimeError("native completed; wrapper interrupted")
        with self.assertRaisesRegex(RuntimeError, "interrupted"):
            self.execute(pre=interrupted)
        before = (self.run / "analyzer/pre/NATIVE_ACCEPTED.json").read_bytes()
        def recover(*, stage, inputs, stage_intent_ref, experiment_root):
            self.assertEqual(stage, "PRE")
            value = json.loads((Path(experiment_root) / "analyzer/pre/NATIVE_ACCEPTED.json").read_bytes())
            ref = save(Path(experiment_root) / "recovery/PRE.json", {
                "schema_id": "SINGLE_VALIDATION_NATIVE_STAGE_RECOVERY_V1", "stage": stage,
                "intent_ref": stage_intent_ref, "status": "VERIFIED_NATIVE_STAGE_RECOVERY"})
            return {"output": value, "native_recovery_ref": ref}
        def forbidden(*args):
            raise AssertionError("provider resent")
        terminal = self.execute(pre=forbidden, recover=recover)
        self.assertEqual(terminal["status"], "VALIDATION_COMPLETE")
        self.assertEqual((self.run / "analyzer/pre/NATIVE_ACCEPTED.json").read_bytes(), before)

    def test_memory_reuse_preserves_original_local_root_and_uses_new_universe(self):
        derived = save(self.run / "NEW_UNIVERSE.json", {"round_id": "FORMAL-R5", "parent_policy_id": "parent", "pair_table": [{"candidate": "new"}]})
        module = types.ModuleType("fixture_memory")
        module.__dict__.update(Path=Path, _read=lambda path: json.loads(Path(path).read_bytes()))
        exec("def materialize_round_memory(*, analyzer_output_root, **kw):\n"
             " root=Path(analyzer_output_root).absolute()\n"
             " return {'root':str(root), 'census':_read(root/'local/GROUP_PREPARATION_CENSUS.json'), 'universe':_read(root/'group/V1232U_DYNAMIC_PLANNER_PAIR_UNIVERSE_V1.json')}\n", module.__dict__)
        original = module.materialize_round_memory
        with memory_reuse_context(module, self.authority, derived):
            result = module.materialize_round_memory(analyzer_output_root=self.run / "analyzer")
        self.assertEqual(result["root"], str(self.source))
        self.assertEqual(result["universe"]["pair_table"], [{"candidate": "new"}])
        self.assertIs(module.materialize_round_memory, original)

    def test_native_export_lanes_have_zero_formal_increment_and_no_shared_write(self):
        source = Path(__file__).parents[1] / "fixtures/native_paper_export.py"
        spec = importlib.util.spec_from_file_location("native_export", source)
        native = importlib.util.module_from_spec(spec); spec.loader.exec_module(native)
        lanes = {name: {"required_fields": ["round"]} for name in native.LANES}
        contract = {"schema_id": "PCHSI_PAPER_ROUND_EXPORT_CONTRACT_V1", "contract_sha256": "9" * 64, "lanes": lanes}
        contract_ref = save(self.source / "PAPER_CONTRACT.json", contract)
        shared = self.root / "SHARED_FORMAL_EXPORT"
        binding = {"schema_id": "FORMAL_MAX10_PAPER_TELEMETRY_BINDING_V1", "paper_export_root": str(shared),
            "paper_export_contract_file_sha256": contract_ref["sha256"], "paper_export_contract_sha256": "9" * 64,
            "primary_independent_unit": "SOURCE_STATE", **{name: ["round"] for name in native.LANES}}
        self.authority.update(paper_binding_ref=save(self.source / "PAPER_BINDING.json", binding), paper_contract_ref=contract_ref)
        terminal = self.execute()
        ref = export_validation(start=self.start, result=read_ref(terminal["result_ref"]), authority=self.authority,
                                experiment_root=self.run, native_module=native)
        index = read_ref(ref)
        self.assertEqual(index["formal_valid_round_contribution"], 0)
        native_index = read_ref(index["attempt_export_index_ref"])
        self.assertEqual(native_index["valid_round_contribution"], 0)
        self.assertEqual(native_index["independent_new_source_sample_count"], 0)
        self.assertEqual(set(native_index["lanes"]), set(native.LANES))
        self.assertFalse(shared.exists())


if __name__ == "__main__":
    unittest.main()
