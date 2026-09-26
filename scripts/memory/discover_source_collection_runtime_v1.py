#!/usr/bin/env python3
"""Discover the exact pi1/Train17 source-collection runtime identity.

Discovery is identity-only. It reads existing formal SELECT attempt artifacts
and exact runtime manifests. It never uses task outcomes to choose a model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_file,
    strict_json_loads,
)
from pchsi.evaluation.schema_models import EpisodeArtifactV1
from pchsi.evaluation.select_policy_runtime import (
    SelectPolicyRuntimeManifestV1,
    SelectServerRuntimeManifestV1,
)
from pchsi.memory.source_collection import (
    PRIMARY_CHECKPOINT_INSTANCE_ID,
    PRIMARY_LOGICAL_CONDITION_ID,
    PRIMARY_TRAINING_SEED,
)


def _find_files_with_sha(
    *,
    roots: tuple[Path, ...],
    expected_sha256: str,
    max_size: int = 8 * 1024 * 1024,
) -> tuple[Path, ...]:
    matches = []
    seen = set()

    for root in roots:
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root, topdown=True):
            dirnames[:] = [
                name
                for name in dirnames
                if name
                not in {
                    ".git",
                    "__pycache__",
                    ".pytest_cache",
                    "node_modules",
                    "build",
                    "conda_envs",
                    ".cache",
                    "site-packages",
                }
            ]
            for name in filenames:
                path = Path(dirpath) / name
                try:
                    if path.is_symlink() or not path.is_file():
                        continue
                    size = path.stat().st_size
                    if size <= 0 or size > max_size:
                        continue
                    resolved = str(path.resolve())
                    if resolved in seen:
                        continue
                    seen.add(resolved)
                    if sha256_file(path) == expected_sha256:
                        matches.append(path.resolve())
                except OSError:
                    continue

    return tuple(sorted(matches, key=lambda path: str(path)))


def _load_attempt_episodes(attempt_root: Path) -> tuple[EpisodeArtifactV1, ...]:
    if attempt_root.is_symlink() or not attempt_root.is_dir():
        raise SystemExit("STOP=FORMAL_TRAIN17_ATTEMPT_ROOT_INVALID")

    episodes = []
    for path in sorted(attempt_root.glob("*/attempt.json")):
        if path.is_symlink() or not path.is_file():
            continue
        episode = EpisodeArtifactV1.from_json(path.read_bytes())
        if (
            episode.evaluation_context != "P4_HARNESS_OFF_SELECT"
            or episode.logical_condition_id != PRIMARY_LOGICAL_CONDITION_ID
            or episode.checkpoint_instance_id != PRIMARY_CHECKPOINT_INSTANCE_ID
            or episode.training_seed != PRIMARY_TRAINING_SEED
        ):
            raise SystemExit(
                "STOP=FORMAL_TRAIN17_ATTEMPT_IDENTITY_MISMATCH:"
                + str(path)
            )
        episodes.append(episode)

    if not episodes:
        raise SystemExit("STOP=NO_FORMAL_TRAIN17_ATTEMPT_IDENTITY_EVIDENCE")
    return tuple(episodes)


def _consensus(episodes, field: str):
    values = {getattr(item, field) for item in episodes}
    if len(values) != 1:
        raise SystemExit(
            "STOP=FORMAL_TRAIN17_IDENTITY_NOT_UNIQUE:"
            + field
            + ":"
            + repr(sorted(values, key=repr))
        )
    return next(iter(values))


def _resolve_base_model_local_path(
    *,
    repository: str,
    revision: str,
) -> Path:
    try:
        from huggingface_hub import snapshot_download
    except Exception as exc:
        raise SystemExit(
            "STOP=HUGGINGFACE_HUB_IMPORT_FAILED:"
            + type(exc).__name__
        ) from exc

    try:
        resolved = snapshot_download(
            repo_id=repository,
            revision=revision,
            local_files_only=True,
        )
    except Exception as exc:
        raise SystemExit(
            "STOP=FROZEN_BASE_MODEL_NOT_AVAILABLE_LOCALLY:"
            + type(exc).__name__
            + ":"
            + str(exc)
        ) from exc

    path = Path(resolved).resolve()
    if path.is_symlink() or not path.is_dir():
        raise SystemExit("STOP=FROZEN_BASE_MODEL_LOCAL_PATH_INVALID")
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--formal-train17-attempt-root", required=True)
    parser.add_argument("--search-root", action="append", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output = Path(args.output)
    if output.exists() or output.is_symlink():
        raise SystemExit("STOP=RUNTIME_BINDING_OUTPUT_ALREADY_EXISTS")
    if output.parent.is_symlink() or not output.parent.is_dir():
        raise SystemExit("STOP=RUNTIME_BINDING_OUTPUT_PARENT_INVALID")

    episodes = _load_attempt_episodes(
        Path(args.formal_train17_attempt_root)
    )

    consensus_fields = (
        "runtime_core_commit",
        "raw_protocol_sha256",
        "environment_runtime_manifest_sha256",
        "policy_runtime_manifest_sha256",
        "policy_request_schema_sha256",
    )
    identity = {
        field: _consensus(episodes, field)
        for field in consensus_fields
    }

    search_roots = tuple(Path(item) for item in args.search_root)

    policy_runtime_matches = _find_files_with_sha(
        roots=search_roots,
        expected_sha256=identity["policy_runtime_manifest_sha256"],
    )
    if not policy_runtime_matches:
        raise SystemExit("STOP=SELECT_POLICY_RUNTIME_MANIFEST_NOT_FOUND")

    parsed_policy_runtimes = []
    for path in policy_runtime_matches:
        try:
            runtime = SelectPolicyRuntimeManifestV1.from_json(
                path.read_bytes()
            )
        except Exception:
            continue
        if (
            runtime.logical_condition_id == PRIMARY_LOGICAL_CONDITION_ID
            and runtime.checkpoint_instance_id
            == PRIMARY_CHECKPOINT_INSTANCE_ID
            and runtime.training_seed == PRIMARY_TRAINING_SEED
        ):
            parsed_policy_runtimes.append((path, runtime))

    if not parsed_policy_runtimes:
        raise SystemExit("STOP=TRAIN17_POLICY_RUNTIME_NOT_PARSEABLE")

    canonical_policy_bytes = {
        item[1].to_json().encode("utf-8")
        for item in parsed_policy_runtimes
    }
    if len(canonical_policy_bytes) != 1:
        raise SystemExit("STOP=TRAIN17_POLICY_RUNTIME_CONFLICT")
    policy_runtime_path, policy_runtime = sorted(
        parsed_policy_runtimes,
        key=lambda item: str(item[0]),
    )[0]

    if policy_runtime.adapter_path is None:
        raise SystemExit("STOP=TRAIN17_ADAPTER_PATH_MISSING")
    adapter_path = Path(policy_runtime.adapter_path).resolve()
    if adapter_path.is_symlink() or not adapter_path.is_dir():
        raise SystemExit("STOP=TRAIN17_ADAPTER_PATH_INVALID")

    server_runtime_matches = _find_files_with_sha(
        roots=search_roots,
        expected_sha256=policy_runtime.server_runtime_manifest_sha256,
    )
    parsed_servers = []
    for path in server_runtime_matches:
        try:
            server = SelectServerRuntimeManifestV1.from_json(
                path.read_bytes()
            )
        except Exception:
            continue
        parsed_servers.append((path, server))

    if not parsed_servers:
        raise SystemExit("STOP=SELECT_SERVER_RUNTIME_MANIFEST_NOT_FOUND")

    canonical_server_bytes = {
        item[1].to_json().encode("utf-8")
        for item in parsed_servers
    }
    if len(canonical_server_bytes) != 1:
        raise SystemExit("STOP=SELECT_SERVER_RUNTIME_CONFLICT")
    server_runtime_path, server_runtime = sorted(
        parsed_servers,
        key=lambda item: str(item[0]),
    )[0]

    registry = tuple(
        item
        for item in server_runtime.static_lora_registry
        if (
            item.logical_condition_id == PRIMARY_LOGICAL_CONDITION_ID
            and item.checkpoint_instance_id == PRIMARY_CHECKPOINT_INSTANCE_ID
            and item.training_seed == PRIMARY_TRAINING_SEED
        )
    )
    if len(registry) != 1:
        raise SystemExit("STOP=SERVER_TRAIN17_LORA_REGISTRATION_NOT_UNIQUE")
    server_lora = registry[0]

    if (
        server_lora.served_model_name != policy_runtime.served_model_name
        or server_lora.adapter_bundle_sha256
        != policy_runtime.adapter_bundle_sha256
        or Path(server_lora.adapter_path).resolve() != adapter_path
    ):
        raise SystemExit("STOP=SERVER_POLICY_RUNTIME_LORA_BINDING_MISMATCH")

    base_model_local_path = _resolve_base_model_local_path(
        repository=server_runtime.base_model_repository,
        revision=server_runtime.base_model_revision,
    )

    # Verify local tokenizer/chat-template authority before any model execution.
    try:
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(
            str(base_model_local_path),
            revision=server_runtime.base_model_revision,
            local_files_only=True,
            trust_remote_code=False,
        )
    except Exception as exc:
        raise SystemExit(
            "STOP=FROZEN_TOKENIZER_LOCAL_LOAD_FAILED:"
            + type(exc).__name__
            + ":"
            + str(exc)
        ) from exc

    chat_template = getattr(tokenizer, "chat_template", None)
    if not isinstance(chat_template, str) or not chat_template:
        raise SystemExit("STOP=FROZEN_TOKENIZER_CHAT_TEMPLATE_MISSING")
    observed_chat_sha = hashlib.sha256(
        chat_template.encode("utf-8")
    ).hexdigest()
    if observed_chat_sha != server_runtime.chat_template_sha256:
        raise SystemExit("STOP=CHAT_TEMPLATE_SHA_MISMATCH")

    try:
        import vllm

        observed_vllm_version = vllm.__version__
    except Exception as exc:
        raise SystemExit(
            "STOP=VLLM_IMPORT_FAILED:" + type(exc).__name__
        ) from exc
    if observed_vllm_version != server_runtime.vllm_version:
        raise SystemExit(
            "STOP=VLLM_VERSION_MISMATCH:"
            + observed_vllm_version
            + "!="
            + server_runtime.vllm_version
        )

    payload = {
        "schema_id": "FAILURE_MEMORY_SOURCE_COLLECTION_RUNTIME_BINDING_V1",
        "schema_version": 1,
        "identity_source": "FORMAL_SELECT_TRAIN17_IDENTITY_ONLY_NO_OUTCOME_SELECTION",
        "formal_attempt_count_checked": len(episodes),
        "logical_condition_id": policy_runtime.logical_condition_id,
        "checkpoint_instance_id": policy_runtime.checkpoint_instance_id,
        "training_seed": policy_runtime.training_seed,
        "served_model_name": policy_runtime.served_model_name,
        "adapter_path": str(adapter_path),
        "adapter_bundle_sha256": policy_runtime.adapter_bundle_sha256,
        "adapter_rank": policy_runtime.adapter_rank,
        "policy_runtime_manifest_path": str(policy_runtime_path),
        "policy_runtime_manifest_sha256": (
            identity["policy_runtime_manifest_sha256"]
        ),
        "server_runtime_manifest_path": str(server_runtime_path),
        "server_runtime_manifest_sha256": (
            policy_runtime.server_runtime_manifest_sha256
        ),
        "environment_runtime_manifest_sha256": (
            identity["environment_runtime_manifest_sha256"]
        ),
        "formal_runtime_core_commit": identity["runtime_core_commit"],
        "raw_protocol_sha256": identity["raw_protocol_sha256"],
        "policy_request_schema_sha256": (
            identity["policy_request_schema_sha256"]
        ),
        "base_model_repository": server_runtime.base_model_repository,
        "base_model_revision": server_runtime.base_model_revision,
        "base_model_local_path": str(base_model_local_path),
        "tokenizer_identity_manifest_sha256": (
            server_runtime.tokenizer_identity_manifest_sha256
        ),
        "chat_template_sha256": server_runtime.chat_template_sha256,
        "vllm_version": server_runtime.vllm_version,
        "dtype": server_runtime.dtype,
        "tensor_parallel_size": server_runtime.tensor_parallel_size,
        "generation_config_mode": server_runtime.generation_config_mode,
        "chat_template_content_format": (
            server_runtime.chat_template_content_format
        ),
        "enable_lora": server_runtime.enable_lora,
        "max_lora_rank": server_runtime.max_lora_rank,
        "max_loras": server_runtime.max_loras,
        "max_cpu_loras": server_runtime.max_cpu_loras,
        "lora_dtype": server_runtime.lora_dtype,
        "runtime_dynamic_lora_updates": (
            server_runtime.runtime_dynamic_lora_updates
        ),
        "memory_mode": "MEMORY_OFF_M0",
        "harness_mode": "HARNESS_OFF",
        "performance_estimand": "NO_PERFORMANCE_ESTIMAND",
    }
    raw = canonical_json_bytes(payload)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(output, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        output.unlink(missing_ok=True)
        raise

    print("FORMAL_TRAIN17_IDENTITY_ATTEMPT_COUNT=" + str(len(episodes)))
    print("SOURCE_COLLECTION_SERVED_MODEL=" + policy_runtime.served_model_name)
    print("SOURCE_COLLECTION_ADAPTER_PATH=" + str(adapter_path))
    print("SOURCE_COLLECTION_BASE_MODEL_LOCAL_PATH=" + str(base_model_local_path))
    print("SOURCE_COLLECTION_RUNTIME_BINDING_SHA256=" + hashlib.sha256(raw).hexdigest())
    print("SOURCE_COLLECTION_RUNTIME_DISCOVERY_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
