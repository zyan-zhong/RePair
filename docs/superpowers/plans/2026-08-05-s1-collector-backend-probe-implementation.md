# S1 Collector Backend Probe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement content-addressed, non-executing tooling for the approved S1 hostile-collector backend probe while keeping every real namespace, mount, seccomp, Landlock, P1-P20 and inventory execution path closed until separate external approval.

**Architecture:** Native C17 code owns restricted-root planning, namespace and mount execution interfaces, credentials, seccomp BPF, process supervision and trusted publication. Python 3.12 owns canonical manifests, profile contracts, result aggregation, runtime-closure generation and orchestration. Privileged or security-changing operations are divided into pure planners, injected executors and real syscall adapters; implementation tests use fake executors and static fixtures only.

**Tech Stack:** GCC 11.4, C17, GNU Make 4.3, Linux 5.15 UAPI headers, raw `mount_setattr` and `openat2` syscalls, classic seccomp BPF, glibc 2.35 `close_range`, Python 3.12.13 and pytest 9.0.3.

## Global Constraints

- Plan revision scope decision: `PLAN_REVISION_SCOPE_APPROVED_S1_COLLECTOR_BACKEND_PROBE_V1`.

### Governance

- Approved design commit:
  `6199510501841ce3ce3d9ca6da87d70f10d4c787`.
- Current plan revision parent:
  `ae3a8c0389368afbbd3281eb12a445bf33d07f2b`.
- Formal design ID:
  `S1_COLLECTOR_BACKEND_PROBE_V1`.
- Backend ID:
  `ROOTLESS_RESTRICTED_ROOT_NAMESPACE_SANDBOX_V2`.
- Threat model:
  `COLLECTOR_PROCESS_MAY_BE_BUGGY_OR_HOSTILE`.
- Dataset-root resolution:
  `EXPLICIT_ARGUMENT_ONLY`.
- Seccomp model:
  `MANDATORY_DEFAULT_DENY_TWO_STAGE_ALLOWLIST`.
- `BACKEND_PROBE_EXECUTION = NOT_APPROVED`.
- `READ_ONLY_INVENTORY_EXECUTION = NOT_APPROVED`.
- No repository artifact may create, infer or self-grant an external approval.
- No implementation test may execute P1-P20.
- No force push, rebase, amend or direct push to `main`.

### Frozen toolchain

- Python:
  `/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python`.
- Python version:
  `3.12.13`.
- pytest:
  `9.0.3`.
- Compiler:
  `/usr/bin/cc`, GCC `11.4.0`.
- Build:
  GNU Make `4.3`.
- Kernel planning target:
  Linux `5.15.0-94-generic`, `x86_64`.
- libc:
  glibc `2.35`.
- Mount API:
  isolated `<linux/mount.h>` translation unit and raw
  `SYS_mount_setattr`.
- Never include `<linux/mount.h>` and `<sys/mount.h>` in one translation
  unit.
- Source resolution:
  isolated `<linux/openat2.h>` translation unit and raw `SYS_openat2`.
- Seccomp:
  Linux UAPI plus classic BPF; no libseccomp development dependency.
- Landlock:
  Linux UAPI plus runtime ABI query.
- FD closure:
  native libc
  `close_range(3, UINT_MAX, CLOSE_RANGE_UNSHARE)`.
- Python must not assume `os.close_range` exists.

### Security boundaries

- `HOST_BACKED_MOUNT_CLASS_COUNT = 3`.
- Host-backed mounts:
  `/runtime`, `/input/repo`, `/input/dataset`.
- `/bootstrap` and `/collector` are sandbox-private sealed tmpfs copies.
- Bootstrap and collector sources are opened beneath a trusted repository
  dirfd with:
  - `RESOLVE_BENEATH`;
  - `RESOLVE_NO_SYMLINKS`;
  - `RESOLVE_NO_MAGICLINKS`.
- The same successfully opened source FD is used for identity validation,
  SHA-256 calculation and sealed-source copying.
- All namespace, mount, credential, capability, seccomp, Landlock,
  process-control and trusted-publication operations must pass through an
  injected executor boundary.
- Unit and implementation integration tests use fake injected operations.
- Ordinary isolated temporary-directory tests may use real unprivileged
  file operations only when the task explicitly permits them.
- No implementation test may invoke:
  - namespace creation;
  - `mount`;
  - `umount2`;
  - `mount_setattr`;
  - `pivot_root`;
  - seccomp installation;
  - `landlock_restrict_self`;
  - ALFWorld;
  - an expert;
  - a model.

### JSON and canonicalization

- Strict parsing is bytes-first:
  `strict_json_loadb(data: bytes)`.
- `strict_json_loads(text: str)` is a UTF-8 convenience wrapper.
- Invalid UTF-8 is rejected before JSON parsing.
- JSON object keys are unique.
- JSON numbers are signed 64-bit decimal integers only:
  `[-9223372036854775808, 9223372036854775807]`.
- Fractions, exponents, NaN, Infinity, leading plus, leading zeroes and
  negative zero are rejected.
- Canonical integers use the shortest base-10 representation.
- Canonical JSON uses UTF-8, sorted object keys, compact separators and
  a final LF.
- Maximum nesting depth is `64`.

### Exact approved resource constants

- Evidence tmpfs:
  `8 MiB`, `256` inodes.
- Temporary tmpfs:
  `16 MiB`, `512` inodes.
- Bootstrap sealed-source tmpfs:
  `4 MiB`, `32` inodes.
- Collector sealed-source tmpfs:
  `4 MiB`, `32` inodes.
- P18 Landlock tmpfs:
  `4 MiB`, `64` inodes.
- Maximum evidence regular files:
  `16`.
- Maximum total evidence bytes:
  `4194304`.
- Maximum single evidence file:
  `2097152`.
- Maximum stdout bytes:
  `1048576`.
- Maximum stderr bytes:
  `1048576`.
- Maximum evidence directory depth:
  `1`.
- `RLIMIT_CPU` soft:
  `2` seconds.
- `RLIMIT_CPU` hard:
  `3` seconds.
- `RLIMIT_AS`:
  `268435456`.
- `RLIMIT_FSIZE`:
  `4194304`.
- `RLIMIT_NOFILE`:
  `32`.
- `RLIMIT_NPROC`:
  `1`.
- `RLIMIT_CORE`:
  `0`.
- Per-probe wall-clock timeout:
  `10` seconds.
- P7 case timeout:
  `2` seconds.
- P7 aggregate deadline:
  `30 + (3 * case_count)` seconds.

### Reproducible native build

- Build wrapper exports:
  `SOURCE_DATE_EPOCH=$(git show -s --format=%ct HEAD)`.
- Build environment sets:
  `LC_ALL=C`, `LANG=C`, `TZ=UTC`.
- C flags include:
  - `-Werror=date-time`;
  - `-ffile-prefix-map=$(CURDIR)=.`;
  - `-fdebug-prefix-map=$(CURDIR)=.`;
  - `-fmacro-prefix-map=$(CURDIR)=.`.
- `__DATE__`, `__TIME__` and `__TIMESTAMP__` are forbidden.
- Object and link order are explicit and stable.
- Archive mode, if used, is deterministic:
  `ARFLAGS=rcD`.
- Linker build ID is deterministic:
  `-Wl,--build-id=sha1`.
- Compiler version, linker version and all build flags are recorded in a
  build manifest.
- Two clean builds from identical inputs must produce identical binary
  SHA-256 values before the candidate binary may be frozen.

---

## File Ownership

### Python modules

- Task 1 creates:
  `src/pchsi/security/__init__.py`,
  `execution_gate.py`, initial `orchestrator.py`.
- Task 2 creates:
  `canonical.py`, `contracts.py`.
- Task 3 creates:
  `evidence_path.py`, `evidence_stream.py`.
- Task 4 creates:
  `manifests.py`.
- Task 8 creates:
  `syscall_table.py`.
- Task 9 creates:
  `trusted_bootstrap.py`.
- Task 10 creates:
  `probe_results.py`.
- Task 11 modifies:
  `execution_gate.py`, `orchestrator.py`.
- Task 14 modifies:
  manifest and syscall-table modules only through their public interfaces.

### Native modules

- Task 1 creates the Makefile, common error layer and closed CLI.
- Task 2 creates strict JSON.
- Task 3 creates path and evidence framing.
- Task 4 creates SHA-256.
- Task 5 creates complete injected system operations and raw UAPI adapters.
- Task 6 creates mount contracts and sealed-source copying.
- Task 7 creates security-state and resource/profile contracts.
- Task 8 creates static seccomp BPF generation and verification.
- Task 10 creates evidence-tree validation and publication.
- Task 12 creates adversarial payload sources only.
- Task 13 creates supervisor and namespace-init planners and executors.

### Shared test ownership

- A task may modify a test created by an earlier task only when the
  `Files` block explicitly marks it `Modify`.
- Every task commits only the paths in its own `Exact commit scope`.
- Later tasks must not silently rename earlier public interfaces.

---

### Task 1: Establish reproducible build skeleton and closed execution gate

**Files**

- Create: `native/s1_backend_probe/Makefile`
- Create: `native/s1_backend_probe/include/pchsi_s1/common.h`
- Create: `native/s1_backend_probe/include/pchsi_s1/errors.h`
- Create: `native/s1_backend_probe/src/errors.c`
- Create: `native/s1_backend_probe/src/main.c`
- Create: `src/pchsi/security/__init__.py`
- Create: `src/pchsi/security/execution_gate.py`
- Create: `src/pchsi/security/orchestrator.py`
- Create: `tests/security/test_native_build.py`
- Create: `tests/security/test_execution_gate.py`
- Create: `tests/security/test_no_probe_execution.py`

**Interfaces**

```python
class ExecutionNotApprovedError(RuntimeError):
    pass

def require_execution_approval(
    *,
    approval_path: Path | None,
    expected_design_commit: str,
    expected_artifact_manifest_sha256: str | None,
) -> NoReturn:
    ...
```

Native binary:
`native/s1_backend_probe/build/pchsi-s1-backend-probe`.

Allowed commands:
`--describe`, `--version`, `--validate-manifest`.

Closed command:
`--execute` returns `PCHSI_EXECUTION_NOT_APPROVED` before any injected
operation is called.

- [ ] **RED:** Write tests for missing binary, missing package, and closed
  `--execute`.
- [ ] **Expected RED:** pytest reports missing module/binary; no security
  syscall marker appears.
- [ ] **Minimal implementation:** Add deterministic Makefile, CLI metadata,
  Python exception and closed orchestrator.
- [ ] **GREEN:**

```bash
PYTHON=/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python
make -C native/s1_backend_probe clean all
"$PYTHON" -m pytest \
  tests/security/test_native_build.py \
  tests/security/test_execution_gate.py \
  tests/security/test_no_probe_execution.py \
  -q
```

- [ ] **Static audit:** Scan implementation tests for actual invocations of
  forbidden security operations.
- [ ] **Exact commit scope:** The eleven paths listed in this task only.
- [ ] **Commit:** `Build closed S1 backend probe skeleton`.

---

### Task 2: Implement bytes-first strict JSON and immutable contracts

**Files**

- Create: `src/pchsi/security/canonical.py`
- Create: `src/pchsi/security/contracts.py`
- Create: `native/s1_backend_probe/include/pchsi_s1/strict_json.h`
- Create: `native/s1_backend_probe/src/strict_json.c`
- Create: `native/s1_backend_probe/tests/test_strict_json.c`
- Create: `tests/security/test_canonical.py`
- Create: `tests/security/test_contracts.py`
- Create: `tests/security/fixtures/canonical_vectors.json`
- Create: `configs/security/schemas/backend_probe_contract_v1.json`
- Create: `configs/security/schemas/runtime_manifest_v1.json`
- Create: `configs/security/schemas/sealed_source_manifest_v1.json`
- Create: `configs/security/schemas/seccomp_filter_manifest_v1.json`
- Create: `configs/security/schemas/probe_profile_manifest_v1.json`
- Create: `configs/security/schemas/probe_evidence_v1.json`

**Interfaces**

```python
def strict_json_loadb(data: bytes) -> object:
    ...

def strict_json_loads(text: str) -> object:
    return strict_json_loadb(text.encode("utf-8"))

def canonical_json_bytes(value: object) -> bytes:
    ...

def sha256_hex(data: bytes) -> str:
    ...
```

```c
enum pchsi_json_status pchsi_json_validate_strict(
    const unsigned char *data,
    size_t size,
    struct pchsi_json_error *error
);
```

- [ ] **RED:** Add shared vectors for invalid UTF-8, duplicate keys,
  fractions, exponents, negative zero, integer overflow, leading zeroes,
  trailing bytes and depth `65`.
- [ ] **Expected RED:** Python and C tests fail because strict parsers do not
  exist.
- [ ] **Minimal implementation:** Implement the frozen signed-64-bit
  integer-only domain and immutable contract dataclasses.
- [ ] **GREEN:**

```bash
make -C native/s1_backend_probe unit
"$PYTHON" -m pytest \
  tests/security/test_canonical.py \
  tests/security/test_contracts.py \
  -q
```

- [ ] **Static audit:** Prove Python and C vectors have identical accepted
  and rejected case IDs.
- [ ] **Exact commit scope:** The fourteen paths listed in this task only.
- [ ] **Commit:** `Define strict backend probe contracts`.

---

### Task 3: Implement evidence path grammar and byte stream

**Files**

- Create: `src/pchsi/security/evidence_path.py`
- Create: `src/pchsi/security/evidence_stream.py`
- Create: `native/s1_backend_probe/include/pchsi_s1/path_contract.h`
- Create: `native/s1_backend_probe/include/pchsi_s1/evidence.h`
- Create: `native/s1_backend_probe/src/path_contract.c`
- Create: `native/s1_backend_probe/src/evidence.c`
- Create: `native/s1_backend_probe/tests/test_path_contract.c`
- Create: `native/s1_backend_probe/tests/test_evidence.c`
- Create: `tests/security/test_evidence_path.py`
- Create: `tests/security/test_evidence_stream.py`
- Create: `tests/security/fixtures/path_vectors.json`

**Interfaces**

```python
def validate_evidence_path(raw_path: bytes) -> tuple[bytes, ...]:
    ...

def encode_evidence_stream(
    entries: Sequence[EvidenceEntry],
) -> bytes:
    ...

def decode_evidence_stream(
    data: bytes,
) -> tuple[EvidenceEntry, ...]:
    ...
```

- [ ] **RED:** Add valid one/two-segment ASCII cases and all approved invalid
  path classes.
- [ ] **Expected RED:** Missing functions and C symbols.
- [ ] **Minimal implementation:** Implement the exact segment grammar,
  512-byte total limit, maximum depth `1`, sorted canonical index and u64
  big-endian framing.
- [ ] **GREEN:** Run native unit suite and the two Python test files.
- [ ] **Static audit:** Verify inner validator and outer decoder consume the
  same vector file.
- [ ] **Exact commit scope:** The eleven paths listed in this task only.
- [ ] **Commit:** `Implement backend probe evidence protocol`.

---

### Task 4: Implement native SHA-256 and manifest identities

**Files**

- Create: `native/s1_backend_probe/include/pchsi_s1/sha256.h`
- Create: `native/s1_backend_probe/src/sha256.c`
- Create: `native/s1_backend_probe/tests/test_sha256.c`
- Create: `src/pchsi/security/manifests.py`
- Create: `tests/security/test_manifests.py`

**Interfaces**

```c
void pchsi_sha256_init(struct pchsi_sha256_context *context);
void pchsi_sha256_update(
    struct pchsi_sha256_context *context,
    const unsigned char *data,
    size_t size
);
void pchsi_sha256_final(
    struct pchsi_sha256_context *context,
    unsigned char digest[32]
);
```

- [ ] **RED:** Add standard known-answer tests, chunking and FD-streaming
  tests.
- [ ] **Expected RED:** Link failure for missing SHA symbols.
- [ ] **Minimal implementation:** Focused FIPS-180-4 SHA-256 with fixed-width
  integers and context zeroization.
- [ ] **GREEN:** Native unit suite and `test_manifests.py`.
- [ ] **Static audit:** No OpenSSL or dynamically selected hash provider.
- [ ] **Exact commit scope:** The five paths listed in this task only.
- [ ] **Commit:** `Add content-addressed probe manifests`.

---

### Task 5: Implement complete injected system-operation boundary

**Files**

- Create: `native/s1_backend_probe/include/pchsi_s1/system_ops.h`
- Create: `native/s1_backend_probe/include/pchsi_s1/linux_compat.h`
- Create: `native/s1_backend_probe/src/linux_compat.c`
- Create: `native/s1_backend_probe/src/linux_mount_uapi.c`
- Create: `native/s1_backend_probe/src/linux_openat2_uapi.c`
- Create: `native/s1_backend_probe/src/real_system_ops.c`
- Create: `native/s1_backend_probe/tests/fake_system_ops.c`
- Create: `native/s1_backend_probe/tests/test_system_ops.c`
- Create: `tests/security/test_native_unit.py`

**Interfaces**

`struct pchsi_system_ops` must inject all security-relevant operations:

- path and file:
  `openat2`, `openat`, `fstatat`, `fstat`, `read`, `write`, `lseek`,
  `close`, `close_range`, `mkdirat`, `unlinkat`, `renameat2`, `fsync`;
- namespace and mount:
  `clone3`, `unshare`, `setns`, `mount`, `umount2`, `mount_setattr`,
  `pivot_root`;
- credentials:
  `setgroups`, `setresuid`, `setresgid`, `setfsuid`, `setfsgid`;
- security:
  `prctl`, `seccomp`, `landlock_create_ruleset`, `landlock_add_rule`,
  `landlock_restrict_self`, `setrlimit`;
- process:
  `pipe2`, `dup2`, `kill`, `waitpid`, `poll`.

- [ ] **RED:** Fake-operation tests require call ordering, arguments and
  exact errno propagation for every operation family.
- [ ] **Expected RED:** Missing `pchsi_system_ops` and adapters.
- [ ] **Minimal implementation:** Pure interfaces, one fake recorder and
  real adapters. Raw mount and raw openat2 headers remain isolated.
- [ ] **GREEN:**

```bash
make -C native/s1_backend_probe clean all unit
"$PYTHON" -m pytest \
  tests/security/test_native_unit.py \
  tests/security/test_no_probe_execution.py \
  -q
```

- [ ] **Static audit:** No planner or trusted executor directly calls a
  security syscall outside `real_system_ops.c` or the two isolated raw
  UAPI translation units.
- [ ] **Exact commit scope:** The nine paths listed in this task only.
- [ ] **Commit:** `Add injectable Linux security operations`.

---

### Task 6: Implement safe source resolution, three mount classes and sealed copies

**Files**

- Create: `native/s1_backend_probe/include/pchsi_s1/source_resolution.h`
- Create: `native/s1_backend_probe/include/pchsi_s1/mount_contract.h`
- Create: `native/s1_backend_probe/include/pchsi_s1/source_copy.h`
- Create: `native/s1_backend_probe/src/source_resolution.c`
- Create: `native/s1_backend_probe/src/mount_contract.c`
- Create: `native/s1_backend_probe/src/source_copy.c`
- Create: `native/s1_backend_probe/tests/test_source_resolution.c`
- Create: `native/s1_backend_probe/tests/test_mount_contract.c`
- Create: `native/s1_backend_probe/tests/test_source_copy.c`
- Create: `tests/security/fixtures/mountinfo_valid.txt`
- Create: `tests/security/fixtures/mountinfo_writable_nested.txt`

**Interfaces**

```c
enum pchsi_status pchsi_open_source_beneath_repo(
    int repo_dirfd,
    const char *relative_path,
    const struct pchsi_system_ops *operations,
    int *source_fd
);
```

The `openat2` request must use:

```text
flags   = O_RDONLY | O_CLOEXEC | O_NOFOLLOW
resolve = RESOLVE_BENEATH
        | RESOLVE_NO_SYMLINKS
        | RESOLVE_NO_MAGICLINKS
mode    = 0
```

```c
enum pchsi_mount_class {
    PCHSI_MOUNT_RUNTIME,
    PCHSI_MOUNT_REPOSITORY,
    PCHSI_MOUNT_DATASET
};
```

- [ ] **RED:** Reject absolute paths, `..`, symlinks, magic links, a fourth
  mount class, bootstrap/collector bind mounts, writable descendants and
  source identity change.
- [ ] **Expected RED:** Missing source-resolution and mount symbols.
- [ ] **Minimal implementation:** Safe opened-FD source pipeline, strict
  mountinfo parser, pure mount plans and sealed-copy plans.
- [ ] **GREEN:** Native unit suite using only fake mount/openat2 operations.
- [ ] **Static audit:** Same FD is used for `fstat`, hash and copy; source FD
  is closed before collector-fork state.
- [ ] **Exact commit scope:** The eleven paths listed in this task only.
- [ ] **Commit:** `Enforce S1 source and mount contracts`.

---

### Task 7: Implement security state, exact limits and compiled profiles

**Files**

- Create: `native/s1_backend_probe/include/pchsi_s1/security_state.h`
- Create: `native/s1_backend_probe/include/pchsi_s1/resource_contract.h`
- Create: `native/s1_backend_probe/src/security_state.c`
- Create: `native/s1_backend_probe/src/resource_contract.c`
- Create: `native/s1_backend_probe/tests/test_security_state.c`
- Create: `native/s1_backend_probe/tests/test_resource_contract.c`
- Create: `tests/security/fixtures/proc_status_secure.txt`
- Create: `tests/security/fixtures/proc_status_capability_leak.txt`
- Create: `tests/security/test_contracts_resources.py`

**Interfaces**

```c
enum pchsi_probe_profile_id {
    PCHSI_PROFILE_PRODUCTION,
    PCHSI_PROFILE_P7_SYSCALL_CASE,
    PCHSI_PROFILE_P15_RLIMIT_ATTRIBUTION,
    PCHSI_PROFILE_P18_LANDLOCK_ATTRIBUTION,
    PCHSI_PROFILE_P20_CLEANUP
};
```

- [ ] **RED:** Test all exact tmpfs, evidence, RLIMIT, wall-time and P7
  constants from Global Constraints.
- [ ] **Expected RED:** Missing resource contracts.
- [ ] **Minimal implementation:** Immutable profile table selected only by
  enum; arbitrary strings are rejected.
- [ ] **GREEN:** Native unit suite and
  `tests/security/test_contracts_resources.py`.
- [ ] **Static audit:** Production profile cannot select P15, P18 or P20
  behavior.
- [ ] **Exact commit scope:** The nine paths listed in this task only.
- [ ] **Commit:** `Define backend probe security profiles`.

---

### Task 8: Implement architecture-aware static seccomp BPF and P7 case identity

**Files**

- Create: `native/s1_backend_probe/include/pchsi_s1/seccomp_filter.h`
- Create: `native/s1_backend_probe/src/seccomp_filter.c`
- Create: `native/s1_backend_probe/tests/test_seccomp_filter.c`
- Create: `src/pchsi/security/syscall_table.py`
- Create: `scripts/security/generate_syscall_table.py`
- Create: `scripts/security/generate_seccomp_filters.py`
- Create: `tests/security/test_syscall_table.py`
- Create: `tests/security/fixtures/syscall_table_x86_64.json`

**Interfaces**

```python
def derive_p7_case_ids(
    *,
    syscall_table: SyscallTable,
    collector_allowlist: frozenset[int],
) -> tuple[str, ...]:
    ...
```

- [ ] **RED:** Missing arch guard, late x32 guard, non-kill default, duplicate
  syscall, invalid jump and incomplete P7 case set.
- [ ] **Expected RED:** Static verifier rejects all malformed programs.
- [ ] **Minimal implementation:** Deterministic classic-BPF builder and
  verifier; no installation function is called.
- [ ] **GREEN:** Native unit suite and `test_syscall_table.py`.
- [ ] **Static audit:** P7 cases are exactly
  `P7.<decimal_syscall_number>`, each with timeout `2`, aggregate deadline
  `30 + 3 * case_count`.
- [ ] **Exact commit scope:** The eight paths listed in this task only.
- [ ] **Commit:** `Generate static S1 seccomp policies`.

---

### Task 9: Implement trusted bootstrap and attributable Landlock ordering

**Files**

- Create: `src/pchsi/security/trusted_bootstrap.py`
- Create: `tests/security/test_trusted_bootstrap.py`
- Modify: `src/pchsi/security/contracts.py`
- Modify: `tests/security/test_contracts.py`

**Interfaces**

```python
class BootstrapKernelAdapter(Protocol):
    def query_landlock_abi(self) -> int | None: ...
    def install_landlock(self, policy: LandlockPolicy) -> None: ...
    def install_collector_filter(self, program: bytes) -> None: ...
```

P18 ordering is normative:

```text
close inherited FDs
verify FD allowlist
create fixtures
baseline child opens allowed and denied paths after start
destroy baseline child
Landlock child closes inherited FDs
Landlock child installs Landlock
Landlock child opens allowed and denied paths only after restriction
perform identical operations
```

- [ ] **RED:** Tests catch pre-opened denied FD reuse, Landlock install before
  FD closure, and non-identical baseline/restricted state.
- [ ] **Expected RED:** Pure validator rejects ordering violations.
- [ ] **Minimal implementation:** Bootstrap state machine and fake adapter.
- [ ] **GREEN:** `test_trusted_bootstrap.py` and modified contract tests.
- [ ] **Static audit:** Real Landlock adapter remains unreachable while
  execution gate is closed.
- [ ] **Exact commit scope:** The four paths listed in this task only.
- [ ] **Commit:** `Implement trusted S1 bootstrap contracts`.

---

### Task 10: Implement evidence validation and no-clobber publication

**Files**

- Modify: `native/s1_backend_probe/include/pchsi_s1/evidence.h`
- Modify: `native/s1_backend_probe/src/evidence.c`
- Modify: `native/s1_backend_probe/tests/test_evidence.c`
- Create: `src/pchsi/security/probe_results.py`
- Create: `tests/security/test_probe_results.py`
- Modify: `tests/security/test_evidence_stream.py`

**Interfaces**

```c
enum pchsi_status pchsi_validate_evidence_tree(
    int evidence_directory_fd,
    const struct pchsi_evidence_limits *limits,
    struct pchsi_evidence_index *index
);
```

- [ ] **RED:** Reject every malicious file type, path, size, count, depth,
  JSON and hash case from the approved design.
- [ ] **Expected RED:** Current evidence module cannot validate trees or
  publish.
- [ ] **Minimal implementation:** dirfd-relative traversal and injected
  publication executor. Real unprivileged temporary-directory tests may
  exercise `renameat2(RENAME_NOREPLACE)` and `fsync`.
- [ ] **GREEN:** Native evidence tests, evidence-stream tests and
  `test_probe_results.py`.
- [ ] **Static audit:** Outputs are exactly
  `semantic_evidence.json`, `local_evidence.json`,
  `local_evidence.json.sha256`.
- [ ] **Exact commit scope:** The six paths listed in this task only.
- [ ] **Commit:** `Validate and publish S1 probe evidence`.

---

### Task 11: Implement dataset-bound execution record and closed orchestration

**Files**

- Modify: `src/pchsi/security/execution_gate.py`
- Modify: `src/pchsi/security/orchestrator.py`
- Create: `src/pchsi/security/dataset_identity.py`
- Create: `scripts/security/generate_probe_profiles.py`
- Create: `scripts/security/run_backend_probe.py`
- Modify: `tests/security/test_execution_gate.py`
- Create: `tests/security/test_orchestrator.py`
- Create: `tests/security/test_dataset_identity.py`

**Interfaces**

```python
@dataclass(frozen=True, slots=True)
class DatasetIdentity:
    dataset_version: str
    logical_root_id: str
    train_present: bool
    valid_seen_present: bool
    valid_unseen_present: bool
    legacy_manifest_exact_file_sha256: str
    input_contract_sha256: str
    resolved_device: int
    resolved_inode: int
    resolved_mount_id: int
    filesystem_type: str
```

Absolute paths are local evidence only.

Execution record must bind:

- design commit;
- launcher and runtime hashes;
- bootstrap and collector filters;
- sealed-source manifest;
- P7, P15, P18 and P20 profile hashes;
- dataset version `json_2.1.1`;
- logical root ID;
- resolved device/inode/mount ID and filesystem type;
- legacy confirmatory manifest exact-file SHA-256;
- dataset input-contract SHA-256;
- external execution decision reference.

- [ ] **RED:** Missing or mismatched dataset fields, arbitrary profile
  strings and repository-only approval labels.
- [ ] **Expected RED:** Execution validation rejects all incomplete records.
- [ ] **Minimal implementation:** Dataset identity validator and dry
  `--describe`; real launcher remains closed.
- [ ] **GREEN:** Execution-gate, orchestrator and dataset-identity tests.
- [ ] **Static audit:** No default dataset path, no `ALFWORLD_DATA` inference.
- [ ] **Exact commit scope:** The eight paths listed in this task only.
- [ ] **Commit:** `Bind and gate S1 backend probe execution`.

---

### Task 12: Define compile-only P1-P20 payload and outcome manifests

**Files**

- Create: `native/s1_backend_probe/include/pchsi_s1/probe_protocol.h`
- Create: focused files under `native/s1_backend_probe/probes/`
- Create: manifests under `configs/security/probes/`
- Modify: `tests/security/test_orchestrator.py`
- Modify: `tests/security/test_syscall_table.py`
- Modify: `native/s1_backend_probe/Makefile`

**Interfaces**

Every payload manifest binds:
`probe_id`, `payload_id`, `payload_sha256`, `profile_id`,
`expected_normalized_outcome`, `timeout_seconds`,
`permitted_side_effects`, `forbidden_side_effects`.

- [ ] **RED:** Combined seccomp-kill payloads, missing P1 observer, missing P7
  case, non-attributable P15/P18 control and executable test target.
- [ ] **Expected RED:** Manifest validation rejects incomplete corpus.
- [ ] **Minimal implementation:** One source per adversarial action and
  compile-only Make target `probe-payloads`.
- [ ] **GREEN:** Compile payloads and run static manifest tests only.
- [ ] **Static audit:** No payload is executed.
- [ ] **Exact commit scope:** Header, probe directory, probe manifests,
  Makefile and the two modified Python tests only.
- [ ] **Commit:** `Define S1 adversarial probe payloads`.

---

### Task 13: Wire pure supervisor plans and injected executors

**Files**

- Create: `native/s1_backend_probe/include/pchsi_s1/supervisor.h`
- Create: `native/s1_backend_probe/include/pchsi_s1/namespace_init.h`
- Create: `native/s1_backend_probe/src/supervisor.c`
- Create: `native/s1_backend_probe/src/namespace_init.c`
- Create: `native/s1_backend_probe/tests/test_supervisor.c`
- Create: `native/s1_backend_probe/tests/test_namespace_init.c`
- Modify: `native/s1_backend_probe/src/main.c`
- Modify: `tests/security/test_native_unit.py`

**Interfaces**

```c
enum pchsi_status pchsi_supervisor_plan(
    const struct pchsi_probe_contract *contract,
    struct pchsi_supervisor_plan *plan
);

enum pchsi_status pchsi_supervisor_execute(
    const struct pchsi_supervisor_plan *plan,
    const struct pchsi_system_ops *operations
);
```

Namespace init uses the same planner/executor split.

- [ ] **RED:** Verify exact setup and rollback ordering for every failure
  point.
- [ ] **Expected RED:** Missing planners/executors.
- [ ] **Minimal implementation:** Pure immutable plans plus injected
  executors; real dispatcher remains unreachable.
- [ ] **GREEN:** Native unit suite and modified Python native-unit test.
- [ ] **Static audit:** Every security-changing call passes through
  `pchsi_system_ops`.
- [ ] **Exact commit scope:** The eight paths listed in this task only.
- [ ] **Commit:** `Wire trusted S1 supervisor plans`.

---

### Task 14: Generate reproducible candidate runtime and filter artifacts

**Files**

- Create: `scripts/security/build_runtime_closure.py`
- Modify: `scripts/security/generate_syscall_table.py`
- Modify: `scripts/security/generate_seccomp_filters.py`
- Modify: `scripts/security/generate_probe_profiles.py`
- Modify: `src/pchsi/security/manifests.py`
- Modify: `src/pchsi/security/syscall_table.py`
- Modify: `tests/security/test_manifests.py`
- Modify: `tests/security/test_syscall_table.py`
- Create: `tests/security/test_reproducible_native_build.py`

**Interfaces**

```python
def build_runtime_manifest(
    *,
    python_binary: Path,
    bootstrap_source: Path,
    output_root: Path,
) -> RuntimeManifest:
    ...
```

- [ ] **RED:** Interpreter mismatch, `ldd` use, escaping symlink,
  nondeterministic timestamp/path, unordered objects and unequal clean-build
  hashes.
- [ ] **Expected RED:** Candidate artifact tooling is missing.
- [ ] **Minimal implementation:** `readelf`-based closure, frozen build
  environment and candidate manifests marked
  `candidate_pending_static_and_semantic_review`.
- [ ] **GREEN:** Manifest/syscall tests plus two clean native builds with
  identical SHA-256.
- [ ] **Static audit:** No current time, checkout path or locale leaks into
  candidate bytes.
- [ ] **Exact commit scope:** The nine paths listed in this task only.
- [ ] **Commit:** `Generate reproducible candidate S1 artifacts`.

---

### Task 15: Complete non-executing verification and stop at code review

**Files**

- Create: `docs/protocol/S1_COLLECTOR_BACKEND_PROBE_V1.md`
- Modify: only test configuration required to run existing tests.
- Do not modify Runtime Core, ALFWorld, model or split files.

- [ ] **RED:** Confirm native and Python execution entry points reject
  runtime execution without a separately bound external execution record.
- [ ] **Expected RED:** Both entry points return the frozen
  not-approved error, and no runtime evidence directory is created.
- [ ] **Minimal implementation:** Add only the protocol document and any
  explicit test-runner configuration needed to execute the already
  implemented non-executing verification suite.
- [ ] **GREEN:**

```bash
PYTHON=/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python
"$PYTHON" -m pytest -q
make -C native/s1_backend_probe clean all unit probe-payloads
"$PYTHON" -m compileall -q src tests scripts
```

- [ ] **Static audit:** Prove no implementation test executed namespaces,
  mounts, pivot, seccomp, Landlock, P1-P20, ALFWorld, expert or model.
- [ ] **Reproducibility audit:** Repeat clean native build and compare exact
  binary SHA-256.
- [ ] **Dataset audit:** No data file is read except synthetic fixtures.
- [ ] **Scope audit:** No Runtime Core semantic file, model file or split
  manifest changed.
- [ ] **Freeze candidate evidence externally:** candidate head, source-tree
  hash, binary hash, toolchain manifest, runtime/filter/profile candidate
  hashes and test summaries.
- [ ] **Exact commit scope:** protocol document and explicit test
  configuration only.
- [ ] **Commit:** `Document non-executing S1 probe candidate`.
- [ ] **Stop:** The next possible external decision is
  `CODE_APPROVED_S1_COLLECTOR_BACKEND_PROBE_V1`.
- [ ] **Non-authorization:** Code approval still does not authorize P1-P20
  execution or inventory execution.
