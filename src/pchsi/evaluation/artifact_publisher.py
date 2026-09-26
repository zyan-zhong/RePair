"""Crash-consistent, directory-level publication for E1 attempt artifacts."""
from __future__ import annotations

from collections.abc import Callable
import ctypes
from dataclasses import dataclass
import errno
from enum import Enum
import os
from pathlib import Path

from .episode_artifact import AttemptBundleBytes
from .schema_models import (
    AttemptReceiptV1,
    ScientificCellLockV1,
)


class PublicationFaultPoint(str, Enum):
    AFTER_STARTED_RECEIPT = "AFTER_STARTED_RECEIPT"
    AFTER_PARTIAL_STAGING = "AFTER_PARTIAL_STAGING"
    AFTER_COMPLETE_STAGING_BEFORE_FSYNC = (
        "AFTER_COMPLETE_STAGING_BEFORE_FSYNC"
    )
    AFTER_CELL_LOCK = "AFTER_CELL_LOCK"
    AFTER_DIRECTORY_RENAME_BEFORE_PARENT_FSYNC = (
        "AFTER_DIRECTORY_RENAME_BEFORE_PARENT_FSYNC"
    )
    AFTER_PARENT_FSYNC_BEFORE_TERMINAL_RECEIPT = (
        "AFTER_PARENT_FSYNC_BEFORE_TERMINAL_RECEIPT"
    )


class InjectedPublicationFault(RuntimeError):
    pass


class PublicationRecoveryStatus(str, Enum):
    PUBLISHED = "PUBLISHED"
    ALREADY_PUBLISHED = "ALREADY_PUBLISHED"
    STAGING_LOST_UNRESOLVED = (
        "STAGING_LOST_UNRESOLVED"
    )


@dataclass(frozen=True, slots=True)
class PublicationRecoveryResult:
    status: PublicationRecoveryStatus
    published_path: Path | None


_AT_FDCWD = -100
_RENAME_NOREPLACE = 1


def _ensure_directory(path: Path) -> None:
    try:
        path.mkdir(mode=0o700, parents=True)
    except FileExistsError:
        if path.is_symlink() or not path.is_dir():
            raise ValueError(
                f"expected a real directory: {path}"
            )
    os.chmod(path, 0o700)


def _write_all(descriptor: int, payload: bytes) -> None:
    view = memoryview(payload)
    while view:
        written = os.write(descriptor, view)
        if written <= 0:
            raise OSError("short write while publishing artifact")
        view = view[written:]


def _write_file_no_clobber(
    *,
    path: Path,
    payload: bytes,
    fsync_file: bool,
) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    descriptor = os.open(path, flags, 0o600)
    try:
        _write_all(descriptor, payload)
        if fsync_file:
            os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_file(path: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


_NOREPLACE_UNSUPPORTED_ERRNOS = frozenset(
    {
        errno.EINVAL,
        errno.ENOSYS,
        errno.EOPNOTSUPP,
    }
)


def _rename_directory_native_noreplace(
    source: Path,
    destination: Path,
) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise OSError(
            errno.ENOSYS,
            "renameat2 is unavailable",
            str(destination),
        )
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    result = renameat2(
        _AT_FDCWD,
        os.fsencode(source),
        _AT_FDCWD,
        os.fsencode(destination),
        _RENAME_NOREPLACE,
    )
    if result == 0:
        return

    error_number = ctypes.get_errno()
    if error_number == errno.EEXIST:
        raise FileExistsError(destination)

    raise OSError(
        error_number,
        os.strerror(error_number),
        str(destination),
    )


def _rename_directory_guarded_posix(
    source: Path,
    destination: Path,
) -> None:
    if (
        destination.exists()
        or destination.is_symlink()
    ):
        raise FileExistsError(destination)

    if source.is_symlink() or not source.is_dir():
        raise FileNotFoundError(source)

    os.rename(source, destination)

    if source.exists() or source.is_symlink():
        raise RuntimeError(
            "guarded directory publication left the source visible"
        )
    if (
        destination.is_symlink()
        or not destination.is_dir()
    ):
        raise RuntimeError(
            "guarded directory publication did not create a real directory"
        )


def _rename_directory_no_clobber(
    source: Path,
    destination: Path,
    *,
    guarded_posix_fallback_authorized: bool,
) -> None:
    try:
        _rename_directory_native_noreplace(
            source,
            destination,
        )
        return
    except OSError as error:
        if (
            error.errno
            not in _NOREPLACE_UNSUPPORTED_ERRNOS
        ):
            raise
        if not guarded_posix_fallback_authorized:
            raise

    # Some POSIX filesystems support atomic rename while rejecting the
    # RENAME_NOREPLACE flag. The immutable scientific cell lock is the
    # application-level exclusive claim for this exact scheduled cell and
    # attempt. All legitimate recovery for one attempt also uses the same
    # staging source path, so the first successful rename removes that source.
    _rename_directory_guarded_posix(
        source,
        destination,
    )


def _receipt_filename(receipt: AttemptReceiptV1) -> str:
    suffix = (
        "started"
        if receipt.receipt_kind == "STARTED"
        else "terminal"
    )
    return f"{receipt.execution_attempt_id}.{suffix}.json"


class ArtifactPublisher:
    def __init__(
        self,
        *,
        run_root: Path,
        fault_injector: (
            Callable[[PublicationFaultPoint], None]
            | None
        ) = None,
    ) -> None:
        self.run_root = Path(run_root)
        if self.run_root.is_symlink():
            raise ValueError("run_root must not be a symlink")
        self.attempt_ledger = (
            self.run_root / "attempt_ledger"
        )
        self.attempts = self.run_root / "attempts"
        self.staging_root = (
            self.attempts / ".staging"
        )
        self.cell_locks = self.run_root / "cell_locks"
        for directory in (
            self.run_root,
            self.attempt_ledger,
            self.attempts,
            self.staging_root,
            self.cell_locks,
        ):
            _ensure_directory(directory)
        self._fault_injector = fault_injector

    def _fault(self, point: PublicationFaultPoint) -> None:
        if self._fault_injector is not None:
            self._fault_injector(point)

    def write_started_receipt(
        self,
        receipt: AttemptReceiptV1,
    ) -> Path:
        if not isinstance(receipt, AttemptReceiptV1):
            raise TypeError("receipt must be AttemptReceiptV1")
        if receipt.receipt_kind != "STARTED":
            raise ValueError("started receipt must have kind STARTED")
        path = self.attempt_ledger / _receipt_filename(receipt)
        _write_file_no_clobber(
            path=path,
            payload=receipt.to_json().encode("utf-8"),
            fsync_file=True,
        )
        _fsync_directory(self.attempt_ledger)
        self._fault(
            PublicationFaultPoint.AFTER_STARTED_RECEIPT
        )
        return path

    def stage_bundle(
        self,
        *,
        execution_attempt_id: str,
        bundle: AttemptBundleBytes,
    ) -> Path:
        if (
            not isinstance(execution_attempt_id, str)
            or not execution_attempt_id
        ):
            raise ValueError(
                "execution_attempt_id must be non-empty"
            )
        if not isinstance(bundle, AttemptBundleBytes):
            raise TypeError("bundle must be AttemptBundleBytes")
        staging = self.staging_root / execution_attempt_id
        final = self.attempts / execution_attempt_id
        if final.exists() or final.is_symlink():
            raise FileExistsError(final)
        try:
            staging.mkdir(mode=0o700)
        except FileExistsError as error:
            raise FileExistsError(staging) from error

        file_items = bundle.file_bytes()
        for index, (name, payload) in enumerate(file_items):
            _write_file_no_clobber(
                path=staging / name,
                payload=payload,
                fsync_file=False,
            )
            if index == 0:
                self._fault(
                    PublicationFaultPoint.AFTER_PARTIAL_STAGING
                )

        self._fault(
            PublicationFaultPoint
            .AFTER_COMPLETE_STAGING_BEFORE_FSYNC
        )

        for name, _ in file_items:
            _fsync_file(staging / name)
        _fsync_directory(staging)
        return staging

    def write_scientific_cell_lock(
        self,
        lock: ScientificCellLockV1,
    ) -> Path:
        if not isinstance(lock, ScientificCellLockV1):
            raise TypeError(
                "lock must be ScientificCellLockV1"
            )
        path = (
            self.cell_locks
            / f"{lock.scheduled_cell_id}.json"
        )
        _write_file_no_clobber(
            path=path,
            payload=lock.to_json().encode("utf-8"),
            fsync_file=True,
        )
        _fsync_directory(self.cell_locks)
        self._fault(
            PublicationFaultPoint.AFTER_CELL_LOCK
        )
        return path

    def publish_staged_directory(
        self,
        *,
        execution_attempt_id: str,
        lock: ScientificCellLockV1,
    ) -> Path:
        if not isinstance(lock, ScientificCellLockV1):
            raise TypeError(
                "lock must be ScientificCellLockV1"
            )
        if (
            lock.execution_attempt_id
            != execution_attempt_id
        ):
            raise ValueError(
                "publication lock attempt identity mismatch"
            )

        staging = self.staging_root / execution_attempt_id
        final = self.attempts / execution_attempt_id

        if not staging.is_dir() or staging.is_symlink():
            raise FileNotFoundError(staging)

        lock_path = (
            self.cell_locks
            / f"{lock.scheduled_cell_id}.json"
        )
        if (
            not lock_path.is_file()
            or lock_path.is_symlink()
        ):
            raise FileNotFoundError(lock_path)

        observed_lock = ScientificCellLockV1.from_json(
            lock_path.read_bytes()
        )
        if observed_lock != lock:
            raise ValueError(
                "publication lock does not match immutable attempt"
            )

        _rename_directory_no_clobber(
            staging,
            final,
            guarded_posix_fallback_authorized=True,
        )
        self._fault(
            PublicationFaultPoint
            .AFTER_DIRECTORY_RENAME_BEFORE_PARENT_FSYNC
        )
        _fsync_directory(self.attempts)
        self._fault(
            PublicationFaultPoint
            .AFTER_PARENT_FSYNC_BEFORE_TERMINAL_RECEIPT
        )
        return final

    def write_terminal_receipt(
        self,
        receipt: AttemptReceiptV1,
    ) -> Path:
        if not isinstance(receipt, AttemptReceiptV1):
            raise TypeError("receipt must be AttemptReceiptV1")
        if receipt.receipt_kind != "TERMINAL":
            raise ValueError(
                "terminal receipt must have kind TERMINAL"
            )
        path = self.attempt_ledger / _receipt_filename(receipt)
        _write_file_no_clobber(
            path=path,
            payload=receipt.to_json().encode("utf-8"),
            fsync_file=True,
        )
        _fsync_directory(self.attempt_ledger)
        return path

    def _validate_bundle_directory(
        self,
        *,
        directory: Path,
        bundle: AttemptBundleBytes,
    ) -> None:
        if not directory.is_dir() or directory.is_symlink():
            raise ValueError(
                "staging bytes are not identical to the immutable bundle"
            )
        observed_names = {
            path.name
            for path in directory.iterdir()
            if path.is_file() and not path.is_symlink()
        }
        expected_names = {
            name for name, _ in bundle.file_bytes()
        }
        if observed_names != expected_names:
            raise ValueError(
                "staging bytes are not identical to the immutable bundle"
            )
        for name, expected in bundle.file_bytes():
            path = directory / name
            if path.is_symlink() or path.read_bytes() != expected:
                raise ValueError(
                    "staging bytes are not identical to the immutable bundle"
                )

    def _validate_disk_lock(
        self,
        lock: ScientificCellLockV1,
    ) -> None:
        path = (
            self.cell_locks
            / f"{lock.scheduled_cell_id}.json"
        )
        if not path.exists():
            self.write_scientific_cell_lock(lock)
            return
        if path.is_symlink() or not path.is_file():
            raise ValueError("cell lock path is invalid")
        observed = ScientificCellLockV1.from_json(
            path.read_bytes()
        )
        if observed != lock:
            raise ValueError(
                "existing cell lock does not match immutable bundle"
            )

    def recover_publication(
        self,
        *,
        lock: ScientificCellLockV1,
        bundle: AttemptBundleBytes,
    ) -> PublicationRecoveryResult:
        if not isinstance(lock, ScientificCellLockV1):
            raise TypeError("lock must be ScientificCellLockV1")
        if not isinstance(bundle, AttemptBundleBytes):
            raise TypeError("bundle must be AttemptBundleBytes")
        if (
            lock.episode_semantic_sha256
            != bundle.episode_semantic_sha256
            or lock.attempt_bundle_sha256
            != bundle.attempt_bundle_sha256
        ):
            raise ValueError(
                "cell lock does not identify identical immutable bundle bytes"
            )

        attempt_id = lock.execution_attempt_id
        final = self.attempts / attempt_id
        staging = self.staging_root / attempt_id

        if final.exists():
            self._validate_bundle_directory(
                directory=final,
                bundle=bundle,
            )
            self._validate_disk_lock(lock)
            return PublicationRecoveryResult(
                status=(
                    PublicationRecoveryStatus
                    .ALREADY_PUBLISHED
                ),
                published_path=final,
            )

        if not staging.exists():
            return PublicationRecoveryResult(
                status=(
                    PublicationRecoveryStatus
                    .STAGING_LOST_UNRESOLVED
                ),
                published_path=None,
            )

        self._validate_bundle_directory(
            directory=staging,
            bundle=bundle,
        )
        self._validate_disk_lock(lock)
        published = self.publish_staged_directory(
            execution_attempt_id=attempt_id,
            lock=lock,
        )
        return PublicationRecoveryResult(
            status=PublicationRecoveryStatus.PUBLISHED,
            published_path=published,
        )

    def _validate_inputs(
        self,
        *,
        started_receipt: AttemptReceiptV1,
        terminal_receipt: AttemptReceiptV1,
        lock: ScientificCellLockV1,
        bundle: AttemptBundleBytes,
    ) -> None:
        if started_receipt.receipt_kind != "STARTED":
            raise ValueError("started_receipt has wrong kind")
        if terminal_receipt.receipt_kind != "TERMINAL":
            raise ValueError("terminal_receipt has wrong kind")
        identities = {
            started_receipt.execution_attempt_id,
            terminal_receipt.execution_attempt_id,
            lock.execution_attempt_id,
        }
        if len(identities) != 1:
            raise ValueError(
                "publication inputs do not share one attempt identity"
            )
        cells = {
            started_receipt.scheduled_cell_id,
            terminal_receipt.scheduled_cell_id,
            lock.scheduled_cell_id,
        }
        if len(cells) != 1:
            raise ValueError(
                "publication inputs do not share one cell identity"
            )
        if (
            terminal_receipt.episode_semantic_sha256
            != bundle.episode_semantic_sha256
            or terminal_receipt.attempt_bundle_sha256
            != bundle.attempt_bundle_sha256
            or lock.episode_semantic_sha256
            != bundle.episode_semantic_sha256
            or lock.attempt_bundle_sha256
            != bundle.attempt_bundle_sha256
        ):
            raise ValueError(
                "publication inputs do not share bundle identities"
            )

    def publish_scientific_attempt(
        self,
        *,
        started_receipt: AttemptReceiptV1,
        terminal_receipt: AttemptReceiptV1,
        lock: ScientificCellLockV1,
        bundle: AttemptBundleBytes,
    ) -> Path:
        self._validate_inputs(
            started_receipt=started_receipt,
            terminal_receipt=terminal_receipt,
            lock=lock,
            bundle=bundle,
        )
        self.write_started_receipt(started_receipt)
        self.stage_bundle(
            execution_attempt_id=(
                lock.execution_attempt_id
            ),
            bundle=bundle,
        )
        self.write_scientific_cell_lock(lock)
        published = self.publish_staged_directory(
            execution_attempt_id=(
                lock.execution_attempt_id
            ),
            lock=lock,
        )
        self.write_terminal_receipt(terminal_receipt)
        return published
