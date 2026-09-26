from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from stage4d_pkg.common import (
    EXPECTED_ADAPTER_BUNDLE_SHA256,
    PI0_SERVED_NAME,
    T2_SERVED_NAME,
    Stage4DError,
    build_vllm_command,
    package_output_root,
    resolve_gamefile,
    sha1_file,
    sha256_file,
    verify_disjoint_pools,
)
from stage4d_pkg.prepare import (
    verify_existing_output_inventory,
    verify_frozen_protocol_grid,
)


ROOT = Path(__file__).resolve().parents[1]


class Stage4DContractTests(unittest.TestCase):

    def test_stage4c_grid_uses_canonical_paired_cells_field(self) -> None:
        crosswalk = [
            {"task_id": "t0", "select_local_index": 0, "source_index": 3},
            {"task_id": "t1", "select_local_index": 1, "source_index": 4},
        ]
        seeds = [17, 31]
        pairs = [
            {
                "task_id": row["task_id"],
                "select_local_index": row["select_local_index"],
                "source_index": row["source_index"],
                "seed": seed,
            }
            for seed in seeds
            for row in crosswalk
        ]
        grid = {
            "task_count": 2,
            "replicate_seeds": seeds,
            "paired_cells": 4,
            "condition_episodes": 8,
            "index_crosswalk": crosswalk,
            "pairs": pairs,
        }
        verify_frozen_protocol_grid(
            grid,
            expected_task_count=2,
            expected_seeds=(17, 31),
            expected_pair_cells=4,
            expected_condition_episodes=8,
        )
        grid["paired_task_seed_cells"] = 4
        grid.pop("paired_cells")
        with self.assertRaisesRegex(Stage4DError, "PROTOCOL_PAIR_CELL_COUNT_CHANGED"):
            verify_frozen_protocol_grid(
                grid,
                expected_task_count=2,
                expected_seeds=(17, 31),
                expected_pair_cells=4,
                expected_condition_episodes=8,
            )

    def test_vllm_static_base_plus_one_lora(self) -> None:
        command = build_vllm_command(
            python_executable="/abs/python",
            base_model_path="/abs/base",
            adapter_path="/abs/adapter",
            host="127.0.0.1",
            port=12345,
        )
        self.assertEqual(command[0], "/abs/python")
        self.assertIn("--served-model-name", command)
        self.assertEqual(
            command[command.index("--served-model-name") + 1],
            PI0_SERVED_NAME,
        )
        self.assertEqual(command.count("--lora-modules"), 1)
        self.assertEqual(
            command[command.index("--lora-modules") + 1],
            f"{T2_SERVED_NAME}=/abs/adapter",
        )
        self.assertEqual(command[command.index("--max-loras") + 1], "1")
        self.assertEqual(command[command.index("--max-lora-rank") + 1], "16")
        self.assertNotIn("/v1/load_lora_adapter", " ".join(command))

    def test_output_root_stays_under_existing_control_tree(self) -> None:
        root = Path("/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/control")
        observed = package_output_root(root, "a" * 64)
        self.assertEqual(
            observed,
            root / "stage4d_existing_select_live_binding_v1" / ("a" * 64),
        )

    def test_pool_overlap_is_rejected(self) -> None:
        with self.assertRaises(Stage4DError):
            verify_disjoint_pools(
                [{"id": "a"}],
                [{"id": "a"}],
                [{"id": "b"}],
            )

    def test_gamefile_resolution_is_hash_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            file = root / "train" / "family" / "task" / "game.tw-pddl"
            file.parent.mkdir(parents=True)
            file.write_bytes(b"example")
            observed = resolve_gamefile(
                dataset_candidates=[root],
                gamefile_relpath="family/task/game.tw-pddl",
                expected_sha1=sha1_file(file),
                expected_sha256=sha256_file(file),
            )
            self.assertEqual(observed, file.resolve())

    def test_existing_output_inventory_detects_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            artifact = root / "A.json"
            artifact.write_text("{}\n", encoding="utf-8")
            inventory = root / "OUTPUT_FILES.sha256"
            inventory.write_text(
                f"{sha256_file(artifact)}  A.json\n",
                encoding="utf-8",
            )
            verify_existing_output_inventory(root)
            artifact.write_text('{"changed":true}\n', encoding="utf-8")
            with self.assertRaises(Stage4DError):
                verify_existing_output_inventory(root)

    def test_readiness_never_runs_scientific_select_cells(self) -> None:
        text = (ROOT / "stage4d_pkg/readiness.py").read_text(encoding="utf-8")
        self.assertIn('"scientific_select_cell_execution_count": 0', text)
        self.assertIn('"evaluation_execution_authorized": False', text)
        self.assertNotIn("run_single_episode(", text)
        self.assertNotIn("SpawnedAlfworldAdapter(", text)

    def test_slurm_readiness_uses_cluster_resource_policy(self) -> None:
        text = (ROOT / "RUN_PREPARE_AND_SUBMIT_READINESS.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("#SBATCH -p gpu_a800", text)
        self.assertIn("#SBATCH --gpus=1", text)
        self.assertIn("#SBATCH --time=00:10:00", text)
        self.assertIn("#SBATCH --export=NIL", text)
        for forbidden in (
            "--cpus-per-task",
            "--mem=",
            "--mem-per-cpu",
            "--mem-per-gpu",
        ):
            self.assertNotIn(forbidden, text)

    def test_no_execution_authority_is_embedded_in_prepare(self) -> None:
        text = (ROOT / "stage4d_pkg/prepare.py").read_text(encoding="utf-8")
        self.assertNotIn('"evaluation_execution_authorized": True', text)
        self.assertIn('"evaluation_execution_authorized": False', text)
        self.assertIn("EXPECTED_TRAINING_CONTRACT_FILE_SHA256", text)


if __name__ == "__main__":
    unittest.main()
