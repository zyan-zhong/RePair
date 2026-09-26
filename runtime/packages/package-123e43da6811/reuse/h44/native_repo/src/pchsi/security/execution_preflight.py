"""Dataset-bound, non-executing S1 backend-probe preflight."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Final

from pchsi.security.canonical import canonical_json_bytes
from pchsi.security.dataset_identity import DatasetIdentity


__all__ = [
    "EXPECTED_PROBE_IDS",
    "PREFLIGHT_STATUS",
    "PreflightError",
    "build_preflight_bundle",
    "observe_dataset_identity",
    "parse_mountinfo",
]


PREFLIGHT_STATUS: Final[str] = (
    "PREFLIGHT_ONLY_EXECUTION_NOT_APPROVED"
)
GOVERNANCE_MERGE_COMMIT: Final[str] = (
    "57a15945d0d790aa7f7033ffc86ac79273dd1d8d"
)
CANDIDATE_REVIEW_HEAD: Final[str] = (
    "465503d14ee968d2acf23a314c66c65c52260583"
)
CANDIDATE_TREE_SHA256: Final[str] = (
    "d61493ccbb433babf2fed2a7e749dc483fe2e63bc6d43422048440d84ad96885"
)
CANDIDATE_BINARY_SHA256: Final[str] = (
    "3f03b30b408e16466981bca1556983bdf709edf065a11d3b15bb626c3032e713"
)
SOURCE_MANIFEST_SHA256: Final[str] = (
    "41f7461ac7ac7213ca13024a7c755a551f9ad0ab363ac46bc414040af3904eb7"
)
RUNTIME_MANIFEST_SHA256: Final[str] = (
    "4a524d95339afedbdc282a027cc99d388f4e99005f6ad109ff2bc61158effcfc"
)
_GIT_SHA_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")

EXPECTED_PROBE_IDS: Final[tuple[str, ...]] = (
    *(f"P{index:02d}" for index in range(1, 15)),
    "P15_CONTROL",
    "P15_LIMITED",
    "P16",
    "P17",
    "P18_BASELINE",
    "P18_RESTRICTED",
    "P19",
    "P20",
)

_OUTPUT_NAMES: Final[tuple[str, ...]] = (
    "backend_probe_execution_preflight.json",
    "backend_probe_execution_preflight.json.sha256",
    "backend_probe_execution_decision_template.json",
)


class PreflightError(ValueError):
    """Raised when the preflight input violates the frozen contract."""


@dataclass(frozen=True, slots=True)
class MountIdentity:
    mount_id: int
    mount_point: str
    filesystem_type: str


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_sha256(name: str, value: str) -> None:
    if _SHA256_RE.fullmatch(value) is None:
        raise PreflightError(f"{name} must be a lowercase SHA-256")


def _resolve_existing_no_symlink(path: Path, *, kind: str) -> Path:
    if not path.is_absolute():
        raise PreflightError(f"{kind} must be an absolute path")

    lexical = Path(os.path.abspath(os.fspath(path)))
    try:
        status = lexical.lstat()
    except FileNotFoundError as error:
        raise PreflightError(f"{kind} does not exist") from error

    if stat.S_ISLNK(status.st_mode):
        raise PreflightError(f"{kind} must not be a symbolic link")

    resolved = lexical.resolve(strict=True)
    if resolved != lexical:
        raise PreflightError(
            f"{kind} must not resolve through symbolic links"
        )
    return resolved


def _require_regular_file(path: Path, *, kind: str) -> Path:
    resolved = _resolve_existing_no_symlink(path, kind=kind)
    if not resolved.is_file():
        raise PreflightError(f"{kind} must be a regular file")
    return resolved


def _unescape_mountinfo_field(value: str) -> str:
    replacements = {
        r"\040": " ",
        r"\011": "\t",
        r"\012": "\n",
        r"\134": "\\",
    }
    for escaped, plain in replacements.items():
        value = value.replace(escaped, plain)
    return value


def parse_mountinfo(
    text: str,
    *,
    target: Path,
) -> MountIdentity:
    """Return the longest mount-point match for one resolved path."""

    if not target.is_absolute():
        raise PreflightError("mountinfo target must be absolute")

    matches: list[MountIdentity] = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line:
            continue
        left, separator, right = line.partition(" - ")
        if not separator:
            raise PreflightError(
                f"invalid mountinfo line {line_number}"
            )

        left_fields = left.split()
        right_fields = right.split()
        if len(left_fields) < 6 or len(right_fields) < 3:
            raise PreflightError(
                f"invalid mountinfo fields on line {line_number}"
            )

        try:
            mount_id = int(left_fields[0], 10)
        except ValueError as error:
            raise PreflightError(
                f"invalid mount ID on line {line_number}"
            ) from error

        mount_point = Path(
            _unescape_mountinfo_field(left_fields[4])
        )
        filesystem_type = right_fields[0]

        try:
            target.relative_to(mount_point)
        except ValueError:
            continue

        matches.append(
            MountIdentity(
                mount_id=mount_id,
                mount_point=mount_point.as_posix(),
                filesystem_type=filesystem_type,
            )
        )

    if not matches:
        raise PreflightError("dataset root has no mountinfo match")

    matches.sort(
        key=lambda item: len(Path(item.mount_point).parts),
        reverse=True,
    )
    return matches[0]


def observe_dataset_identity(
    *,
    dataset_root: Path,
    legacy_manifest: Path,
    input_contract: Path,
    logical_root_id: str,
    mountinfo_text: str,
) -> DatasetIdentity:
    """Observe the exact dataset identity without reading trajectory data."""

    if (
        not isinstance(logical_root_id, str)
        or not logical_root_id
        or logical_root_id.startswith("/")
        or "\x00" in logical_root_id
    ):
        raise PreflightError("logical_root_id is invalid")

    root = _resolve_existing_no_symlink(
        dataset_root,
        kind="dataset_root",
    )
    if not root.is_dir():
        raise PreflightError("dataset_root must be a directory")

    split_presence: dict[str, bool] = {}
    for split_name in ("train", "valid_seen", "valid_unseen"):
        split_path = root / split_name
        split_presence[split_name] = (
            split_path.is_dir() and not split_path.is_symlink()
        )

    if not all(split_presence.values()):
        raise PreflightError(
            "dataset_root must contain train, valid_seen, "
            "and valid_unseen directories"
        )

    manifest = _require_regular_file(
        legacy_manifest,
        kind="legacy_manifest",
    )
    contract = _require_regular_file(
        input_contract,
        kind="input_contract",
    )

    root_status = root.stat()
    mount = parse_mountinfo(
        mountinfo_text,
        target=root,
    )

    return DatasetIdentity(
        dataset_version="json_2.1.1",
        logical_root_id=logical_root_id,
        train_present=split_presence["train"],
        valid_seen_present=split_presence["valid_seen"],
        valid_unseen_present=split_presence["valid_unseen"],
        legacy_manifest_exact_file_sha256=_sha256_file(manifest),
        input_contract_sha256=_sha256_file(contract),
        resolved_device=root_status.st_dev,
        resolved_inode=root_status.st_ino,
        resolved_mount_id=mount.mount_id,
        filesystem_type=mount.filesystem_type,
    )


def _bundle_hash(entries: list[dict[str, str]]) -> str:
    return hashlib.sha256(canonical_json_bytes(entries)).hexdigest()


def _collect_probe_corpus(
    *,
    repository_root: Path,
) -> tuple[tuple[str, ...], str, str]:
    manifests_root = repository_root / "configs/security/probes"
    sources_root = repository_root / "native/s1_backend_probe/probes"

    manifests = sorted(manifests_root.glob("*.json"))
    sources = sorted(sources_root.glob("*.c"))

    if len(manifests) != 22 or len(sources) != 22:
        raise PreflightError(
            "probe corpus must contain exactly 22 manifests "
            "and 22 sources"
        )

    source_by_stem = {path.stem: path for path in sources}
    manifest_entries: list[dict[str, str]] = []
    source_entries: list[dict[str, str]] = []
    observed_ids: list[str] = []

    for manifest_path in manifests:
        payload = json.loads(
            manifest_path.read_text(encoding="utf-8")
        )
        source_path = source_by_stem.get(manifest_path.stem)
        if source_path is None:
            raise PreflightError(
                f"missing probe source for {manifest_path.name}"
            )

        if payload.get("execution_status") != "NOT_APPROVED":
            raise PreflightError(
                f"{manifest_path.name} is not execution-closed"
            )
        if payload.get("permitted_side_effects") != []:
            raise PreflightError(
                f"{manifest_path.name} permits side effects"
            )

        source_sha256 = _sha256_file(source_path)
        if payload.get("payload_sha256") != source_sha256:
            raise PreflightError(
                f"payload SHA-256 mismatch for {manifest_path.name}"
            )

        probe_id = payload.get("probe_id")
        if not isinstance(probe_id, str):
            raise PreflightError(
                f"invalid probe ID in {manifest_path.name}"
            )

        observed_ids.append(probe_id)
        manifest_entries.append(
            {
                "path": manifest_path.relative_to(
                    repository_root
                ).as_posix(),
                "sha256": _sha256_file(manifest_path),
            }
        )
        source_entries.append(
            {
                "path": source_path.relative_to(
                    repository_root
                ).as_posix(),
                "sha256": source_sha256,
            }
        )

    if tuple(sorted(observed_ids)) != tuple(
        sorted(EXPECTED_PROBE_IDS)
    ):
        raise PreflightError("probe IDs do not match the frozen corpus")

    return (
        tuple(EXPECTED_PROBE_IDS),
        _bundle_hash(manifest_entries),
        _bundle_hash(source_entries),
    )


def _exclusive_write(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC

    descriptor = os.open(path, flags, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short write")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _prepare_output_root(
    *,
    output_root: Path,
    repository_root: Path,
) -> Path:
    if not output_root.is_absolute():
        raise PreflightError("output_root must be absolute")
    if output_root.exists():
        raise PreflightError("output_root must not already exist")

    parent = output_root.parent.resolve(strict=True)
    resolved_repository = repository_root.resolve(strict=True)
    candidate = parent / output_root.name

    if (
        candidate == resolved_repository
        or resolved_repository in candidate.parents
        or candidate in resolved_repository.parents
    ):
        raise PreflightError(
            "output_root must be outside the repository"
        )

    candidate.mkdir(mode=0o700)
    return candidate


def build_preflight_bundle(
    *,
    repository_root: Path,
    preflight_source_commit: str,
    dataset_root: Path,
    legacy_manifest: Path,
    input_contract: Path,
    logical_root_id: str,
    mountinfo_path: Path,
    native_binary: Path,
    profile_description: Path,
    decision_schema: Path,
    output_root: Path,
) -> dict[str, object]:
    """Create a deterministic preflight and a NOT_GRANTED template."""

    if _GIT_SHA_RE.fullmatch(preflight_source_commit) is None:
        raise PreflightError(
            "preflight_source_commit must be a lowercase Git SHA"
        )

    repository = _resolve_existing_no_symlink(
        repository_root,
        kind="repository_root",
    )
    if not repository.is_dir():
        raise PreflightError("repository_root must be a directory")

    mountinfo = _require_regular_file(
        mountinfo_path,
        kind="mountinfo_path",
    )
    binary = _require_regular_file(
        native_binary,
        kind="native_binary",
    )
    profile = _require_regular_file(
        profile_description,
        kind="profile_description",
    )
    schema = _require_regular_file(
        decision_schema,
        kind="decision_schema",
    )

    observed_binary_sha256 = _sha256_file(binary)
    if observed_binary_sha256 != CANDIDATE_BINARY_SHA256:
        raise PreflightError(
            "observed native binary does not match reviewed candidate"
        )

    dataset_identity = observe_dataset_identity(
        dataset_root=dataset_root,
        legacy_manifest=legacy_manifest,
        input_contract=input_contract,
        logical_root_id=logical_root_id,
        mountinfo_text=mountinfo.read_text(encoding="utf-8"),
    )

    probe_ids, manifest_bundle, source_bundle = (
        _collect_probe_corpus(
            repository_root=repository,
        )
    )

    launcher = repository / "scripts/security/run_backend_probe.py"
    gate = repository / "src/pchsi/security/execution_gate.py"
    if not launcher.is_file() or not gate.is_file():
        raise PreflightError("launcher or execution gate is missing")

    manifest: dict[str, object] = {
        "schema_version": 1,
        "status": PREFLIGHT_STATUS,
        "preflight_source_commit": preflight_source_commit,
        "governance_merge_commit": GOVERNANCE_MERGE_COMMIT,
        "candidate_review_head": CANDIDATE_REVIEW_HEAD,
        "candidate_tree_sha256": CANDIDATE_TREE_SHA256,
        "candidate_binary_sha256": CANDIDATE_BINARY_SHA256,
        "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
        "runtime_manifest_sha256": RUNTIME_MANIFEST_SHA256,
        "launcher_sha256": _sha256_file(launcher),
        "execution_gate_sha256": _sha256_file(gate),
        "decision_schema_sha256": _sha256_file(schema),
        "profile_description_sha256": _sha256_file(profile),
        "probe_manifest_bundle_sha256": manifest_bundle,
        "probe_source_bundle_sha256": source_bundle,
        "observed_candidate_binary_sha256": (
            observed_binary_sha256
        ),
        "dataset_identity": dataset_identity.to_dict(),
        "probe_ids": list(probe_ids),
        "approved_output_names": [
            "semantic_evidence.json",
            "local_evidence.json",
            "local_evidence.json.sha256",
        ],
        "execution_boundaries": {
            "backend_probe_execution": "NOT_APPROVED",
            "read_only_inventory_execution": "NOT_APPROVED",
            "alfworld_execution": "NOT_APPROVED",
            "model_execution": "NOT_APPROVED",
        },
    }

    manifest_bytes = canonical_json_bytes(manifest)
    manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
    _require_sha256("preflight_manifest_sha256", manifest_sha256)

    decision_id = hashlib.sha256(
        manifest_bytes + b"S1_EXECUTION_DECISION_TEMPLATE_V1"
    ).hexdigest()

    decision_template: dict[str, object] = {
        "schema_version": 1,
        "decision": "NOT_GRANTED",
        "decision_id": decision_id,
        "external_decision_reference": "external://unassigned",
        "preflight_source_commit": preflight_source_commit,
        "execution_enablement_source_commit": None,
        "candidate_review_head": CANDIDATE_REVIEW_HEAD,
        "candidate_tree_sha256": CANDIDATE_TREE_SHA256,
        "candidate_binary_sha256": CANDIDATE_BINARY_SHA256,
        "source_manifest_sha256": SOURCE_MANIFEST_SHA256,
        "runtime_manifest_sha256": RUNTIME_MANIFEST_SHA256,
        "preflight_manifest_sha256": manifest_sha256,
        "dataset_identity": dataset_identity.to_dict(),
        "approval_scope": list(probe_ids),
        "one_shot": True,
        "inventory_execution_approved": False,
        "alfworld_execution_approved": False,
        "model_execution_approved": False,
    }

    destination = _prepare_output_root(
        output_root=output_root,
        repository_root=repository,
    )

    _exclusive_write(
        destination / _OUTPUT_NAMES[0],
        manifest_bytes,
    )
    _exclusive_write(
        destination / _OUTPUT_NAMES[1],
        f"{manifest_sha256}  {_OUTPUT_NAMES[0]}\n".encode("utf-8"),
    )
    _exclusive_write(
        destination / _OUTPUT_NAMES[2],
        canonical_json_bytes(decision_template),
    )

    directory_descriptor = os.open(
        destination,
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0),
    )
    try:
        os.fsync(directory_descriptor)
    finally:
        os.close(directory_descriptor)

    return {
        "preflight_manifest_sha256": manifest_sha256,
        "decision_id": decision_id,
        "output_names": list(_OUTPUT_NAMES),
        "status": PREFLIGHT_STATUS,
    }
