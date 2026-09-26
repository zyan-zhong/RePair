from __future__ import annotations

import unittest
from pathlib import Path
import tempfile

from stage4d_full import contract


class Stage4DFullContractTests(unittest.TestCase):
    def test_exact_scientific_universe_is_frozen(self):
        self.assertEqual(contract.EXPECTED_TASK_COUNT, 355)
        self.assertEqual(contract.EXPECTED_SEEDS, (17, 31, 47, 73, 101))
        self.assertEqual(contract.EXPECTED_PAIR_CELLS, 1775)
        self.assertEqual(contract.EXPECTED_TOTAL_CELLS, 3550)

    def test_authorization_requires_exact_readiness_receipt(self):
        good = {
            "schema_id": "STAGE4D_STATIC_SERVER_ROUTE_READINESS_V1",
            "schema_version": 1,
            "status": "PASS",
            "binding_root": str(contract.EXPECTED_BINDING_ROOT),
            "model_ids": [contract.PI0_SERVED_NAME, contract.T2_SERVED_NAME],
            "probes": [],
            "model_probe_count": 2,
            "alfworld_environment_execution_count": 0,
            "scientific_select_cell_execution_count": 0,
            "scientific_outcome_generated": False,
            "evaluation_execution_authorized": False,
            "execution_authorization_ready": True,
            "next_gate": "EXPLICIT_FULL_SELECT_EXECUTION_AUTHORIZATION",
            "slurm_job_id": "156385",
            "base_url": "http://127.0.0.1:1",
        }
        contract.validate_readiness_receipt(good)
        bad = dict(good)
        bad["scientific_select_cell_execution_count"] = 1
        with self.assertRaises(contract.Stage4DFullError):
            contract.validate_readiness_receipt(bad)

    def test_execution_is_pair_boundary_resumable(self):
        self.assertEqual(contract.RESUME_MODE, "PAIR_BOUNDARY_APPEND_ONLY")
        self.assertEqual(contract.CONDITION_ORDER, ("T0", "T2"))

    def test_environment_hardening_is_execution_only(self):
        text = Path(contract.PACKAGE_ROOT / "slurm_template.sh").read_text()
        self.assertIn('export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"', text)
        self.assertIn("VLLM_NO_USAGE_STATS=1", text)
        self.assertIn("TORCHINDUCTOR_CACHE_DIR", text)
        self.assertIn("TRITON_CACHE_DIR", text)
        self.assertNotIn("--mem", text)
        self.assertNotIn("--cpus-per-task", text)
        self.assertNotIn("--mem-per-", text)


    def test_slurm_template_uses_slurm_job_user_under_export_nil(self):
        text = Path(contract.PACKAGE_ROOT / "slurm_template.sh").read_text()
        self.assertIn("${SLURM_JOB_USER}", text)
        self.assertNotIn("${USER}", text)

    def test_existing_live_spine_is_reused(self):
        self.assertEqual(
            contract.LEGACY_LIVE_RUNNER_RELATIVE,
            "scripts/engineering_snapshots/stage0/"
            "human_pilot_stage0_offoff_execution_and_closeout_v1_9/"
            "stage0/live_runner.py",
        )
        live = Path(contract.PACKAGE_ROOT / "stage4d_full/live.py").read_text()
        self.assertIn("_recover_or_execute_cell", live)
        self.assertIn("build_select_i1_execution_profile", live)
        self.assertNotIn("run_single_episode(", live)

    def test_authorization_does_not_grant_promotion(self):
        auth = contract.authorization_payload(
            binding_root=contract.EXPECTED_BINDING_ROOT,
            readiness_receipt_sha256=contract.EXPECTED_READINESS_RECEIPT_SHA256,
        )
        self.assertTrue(auth["evaluation_execution_authorized"])
        self.assertFalse(auth["promotion_authorized"])
        self.assertFalse(auth["result_interpretation_authorized"])
        self.assertEqual(auth["authorized_total_condition_cell_count"], 3550)

    def test_output_root_stays_in_existing_clean_round_tree(self):
        root = contract.execution_root("a" * 64)
        expected_parent = Path(
            "/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/control/"
            "stage4d_existing_select_live_execution_v1"
        )
        self.assertEqual(root.parent, expected_parent)


    def test_semantic_json_hash_ignores_storage_newline(self):
        import hashlib
        import json
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "artifact.json"
            value = {"b": 2, "a": 1}
            canonical = contract.canonical_json_bytes(value)
            path.write_bytes(canonical + b"\n")
            expected = hashlib.sha256(canonical).hexdigest()
            self.assertTrue(
                hasattr(contract, "semantic_json_file_sha256"),
                "semantic JSON hash helper must exist",
            )
            self.assertEqual(contract.semantic_json_file_sha256(path), expected)

    def test_binding_artifact_semantics_are_verified_through_binding_identity(self):
        import inspect
        source = inspect.getsource(contract.verify_binding_inventory)
        self.assertIn("semantic_json_file_sha256", source)
        self.assertIn('identity.get("artifacts")', source)
        self.assertNotIn("EXPECTED_ARTIFACT_SHAS.items()", source)

    def test_authorization_write_is_no_clobber(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.json"
            contract.write_new_json(path, {"x": 1})
            with self.assertRaises(FileExistsError):
                contract.write_new_json(path, {"x": 1})


if __name__ == "__main__":
    unittest.main()


class Stage4DParallelExecutionContractTests(unittest.TestCase):
    def test_parallel_execution_uses_exactly_four_gpus_without_cpu_or_memory_requests(self):
        text = Path(contract.PACKAGE_ROOT / "slurm_template.sh").read_text()
        self.assertIn("#SBATCH --nodes=1", text)
        self.assertIn("#SBATCH --gpus=4", text)
        self.assertIn("#SBATCH --time=03:30:00", text)
        self.assertNotIn("--cpus-per-task", text)
        self.assertNotIn("--mem=", text)
        self.assertNotIn("--mem-per-", text)

    def test_pair_universe_is_sharded_by_absolute_schedule_ordinal(self):
        from stage4d_full import parallel
        self.assertEqual(parallel.PARALLEL_SHARD_COUNT, 4)
        self.assertEqual([parallel.shard_for_ordinal(i) for i in range(8)], [0, 1, 2, 3, 0, 1, 2, 3])
        remaining = parallel.remaining_ordinals(completed_prefix_count=102, total_pairs=1775)
        shards = parallel.partition_ordinals(remaining, shard_count=4)
        self.assertEqual(sum(len(x) for x in shards), 1673)
        flattened = sorted(x for shard in shards for x in shard)
        self.assertEqual(flattened, list(range(102, 1775)))
        for shard_id, ordinals in enumerate(shards):
            self.assertTrue(all(o % 4 == shard_id for o in ordinals))

    def test_each_parallel_worker_is_launched_as_an_exclusive_single_gpu_slurm_step(self):
        source = Path(contract.PACKAGE_ROOT / "stage4d_full/slurm_entry.py").read_text()
        self.assertIn('"srun"', source)
        self.assertIn('"--exclusive"', source)
        self.assertIn('"--gpus=1"', source)
        worker = Path(contract.PACKAGE_ROOT / "stage4d_full/shard_worker.py").read_text()
        self.assertIn("require_single_visible_device", worker)

    def test_consolidation_restores_attempt_publication_metadata_for_canonical_recovery(self):
        live = Path(contract.PACKAGE_ROOT / "stage4d_full/live.py").read_text()
        self.assertIn("attempt_ledger", live)
        self.assertIn("cell_locks", live)
        self.assertIn(".started.json", live)
        self.assertIn(".terminal.json", live)

    def test_parallel_workers_write_only_shard_local_receipt_ledgers(self):
        live = Path(contract.PACKAGE_ROOT / "stage4d_full/live.py").read_text()
        self.assertIn("parallel_v1", live)
        self.assertIn("shard_", live)
        self.assertIn("execute_shard", live)
        self.assertIn("consolidate_shards", live)

    def test_parallelization_does_not_change_execution_authorization_hash(self):
        auth = contract.authorization_payload(
            binding_root=contract.EXPECTED_BINDING_ROOT,
            readiness_receipt_sha256=contract.EXPECTED_READINESS_RECEIPT_SHA256,
        )
        self.assertEqual(
            contract.authorization_sha(auth),
            "978ab39389d447b74b1a1acf653619ff437c0d341c9fe76b72236dd8f5fd865b",
        )

    def test_parallel_execution_keeps_same_authorized_scientific_universe(self):
        auth = contract.authorization_payload(
            binding_root=contract.EXPECTED_BINDING_ROOT,
            readiness_receipt_sha256=contract.EXPECTED_READINESS_RECEIPT_SHA256,
        )
        self.assertEqual(auth["authorized_paired_task_seed_cells"], 1775)
        self.assertEqual(auth["authorized_total_condition_cell_count"], 3550)
        self.assertEqual(auth["condition_order_within_pair"], ["T0", "T2"])
        self.assertEqual(auth["resume_mode"], "PAIR_BOUNDARY_APPEND_ONLY")
