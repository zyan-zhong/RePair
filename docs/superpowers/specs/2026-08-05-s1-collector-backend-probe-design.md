# S1 Collector Backend Probe Design

## Status

This document remains a design artifact only.

The following scope decision has been granted externally:

- `FINAL_SPEC_REVISION_SCOPE_APPROVED = YES`

This approval covers only the final four consistency corrections:

1. a dedicated Landlock attribution profile;
2. a P7 per-syscall submatrix;
3. explicit P1 observer roles;
4. sandbox-private sealed bootstrap and collector source copies.

Current state:

- `DESIGN_REVISION_STATUS =
  READY_FOR_FINAL_USER_REVIEW`
- `DESIGN_STATUS =
  CHANGES_REQUIRED_BEFORE_FINAL_APPROVAL`
- `BACKEND_PROBE_IMPLEMENTATION_PLAN =
  NOT_AUTHORIZED`
- `BACKEND_PROBE_EXECUTION =
  NOT_APPROVED`
- `COLLECTOR_BACKEND_FINAL_APPROVAL =
  PENDING`
- `READ_ONLY_INVENTORY_EXECUTION =
  NOT_APPROVED`

This document does not approve:

- final backend-probe design;
- backend-probe implementation;
- backend-probe execution;
- inventory collection;
- ALFWorld environment creation;
- `env.reset()`;
- `env.step()`;
- expert execution;
- model calls;
- smoke execution;
- E1-Dev execution;
- E1-Confirmatory execution.

The stable formal design ID remains:

`S1_COLLECTOR_BACKEND_PROBE_V1`

Commit history records design revisions. No conversational version suffix
is introduced into the formal protocol ID.

## Purpose

The backend probe must establish whether the current server can provide
an operating-system-enforced sandbox for a collector process that may be
buggy or hostile.

The future collector will inspect static ALFWorld files and produce
inventory evidence. It must not be trusted to enforce its own read-only
behavior.

The probe therefore tests the security backend independently of the
collector implementation.

## Formal identifiers

- Probe design ID:
  `S1_COLLECTOR_BACKEND_PROBE_V1`
- Backend ID:
  `ROOTLESS_RESTRICTED_ROOT_NAMESPACE_SANDBOX_V2`
- Threat model:
  `COLLECTOR_PROCESS_MAY_BE_BUGGY_OR_HOSTILE`
- Dataset-root contract:
  `EXPLICIT_ARGUMENT_ONLY`
- Seccomp policy:
  `MANDATORY_DEFAULT_DENY_TWO_STAGE_ALLOWLIST`
- Evidence stream protocol:
  `PCHSI_EVIDENCE_STREAM_V1`
- Semantic evidence schema:
  `S1_COLLECTOR_BACKEND_PROBE_SEMANTIC_EVIDENCE_V1`
- Local evidence schema:
  `S1_COLLECTOR_BACKEND_PROBE_LOCAL_EVIDENCE_V1`
- Sealed-source-copy manifest:
  `S1_SEALED_SOURCE_COPY_MANIFEST_V1`
- P7 submatrix contract:
  `S1_P7_SYSCALL_SUBMATRIX_V1`
- Landlock attribution profile:
  `S1_LANDLOCK_ATTRIBUTION_TEST_PROFILE_V1`
- RLIMIT attribution profile:
  `S1_RLIMIT_ATTRIBUTION_TEST_PROFILE_V1`

## Threat model

### Untrusted components

The following are containment-untrusted and may be buggy or hostile:

- inventory collector source;
- collector control flow;
- collector input parsing;
- collector standard-library use after the second seccomp filter;
- collector-generated evidence;
- collector-generated temporary files;
- collector stdout and stderr;
- adversarial probe payload processes.

Adversarial payloads receive no privileged treatment merely because
their hashes and expected outcomes are reviewed.

### Runtime enforcement TCB

The runtime enforcement trusted computing base consists of components
that actively prevent sandbox escape or unsafe publication:

- Linux kernel as a trusted platform dependency;
- native outer supervisor;
- trusted namespace-init process;
- restricted-root constructor;
- trusted Python bootstrap;
- compiled bootstrap seccomp filter;
- compiled collector seccomp filter;
- frozen Python runtime closure;
- evidence publication validator.

All repository-controlled runtime TCB artifacts must be
content-addressed.

The booted Linux kernel is not represented as a repository artifact.
It is a trusted platform dependency identified in local evidence by:

- kernel release;
- machine architecture;
- boot ID;
- active LSM list when available;
- kernel configuration digest when available;
- loaded-module-list digest when available.

Absence of an optional kernel identity field must be explicit. It must
not be replaced by a fabricated value.

### Verification and assurance TCB

The verification and assurance TCB determines whether the security
properties have been adequately tested:

- probe orchestrator;
- adversarial payload corpus;
- expected-outcome manifest;
- syscall-table manifest;
- evidence oracle;
- test-profile selector.

These artifacts must be content-addressed and reviewed. They do not
receive runtime privileges inside the sandbox.

### Excluded attacks

This design does not claim resistance to:

- Linux kernel exploitation;
- a hostile host root administrator;
- a compromised Ceph server;
- a compromised runtime-enforcement TCB component;
- a compromised compiler or linker used for trusted native artifacts;
- physical storage compromise.

### Security objective

Assuming the runtime enforcement TCB is intact and no kernel
vulnerability is exploited, the untrusted collector must be unable to:

- access trusted PID 1 through procfs;
- recover PID 1 file descriptors or publication channels;
- read or modify PID 1 memory or environment;
- write any host-backed mount;
- access the original host root;
- regain namespace or mount capabilities;
- create processes or threads;
- execute another program after collector entry;
- create or use network sockets;
- inherit host writable file descriptors;
- write directly to any host persistent path;
- overwrite an existing published evidence result;
- exceed frozen resource and output limits.

The backend probe does not prove a bound on aggregate Ceph read bytes,
read IOPS or bandwidth. Those limits belong to the future collector
execution contract.

## Global security invariants

The backend is acceptable only when all of the following hold:

1. Repository is visible through one host-backed mount:
   `/input/repo`.
2. Dataset is visible through one host-backed mount:
   `/input/dataset`.
3. Frozen runtime is visible through one host-backed mount:
   `/runtime`.
4. `HOST_BACKED_MOUNT_CLASS_COUNT = 3`.
5. `/bootstrap` is a sandbox-private sealed byte copy.
6. `/collector` is a sandbox-private sealed byte copy.
7. Neither `/bootstrap` nor `/collector` is a host bind mount.
8. Bootstrap and collector copies are produced from the same opened FDs
   whose bytes and identities were verified.
9. `/collector/read_only_inventory_collector.py` is the only
   runtime-selected collector entry path.
10. Identical read-only source bytes may also exist as ordinary data
    below `/input/repo`; they are not runtime-selected entry paths.
11. Every host-backed mount and nested submount satisfies its frozen
    mount contract.
12. Both sealed-source tmpfs mounts are read-only before collector fork.
13. Old host root is unreachable.
14. Collector and trusted namespace init use distinct mapped
    credentials.
15. Trusted namespace init has `PR_SET_DUMPABLE=0`.
16. Collector cannot access trusted PID 1 procfs channels.
17. Final procfs is private, read-only, PID-only and uses `hidepid=4`.
18. No host persistent writable mount is visible.
19. `/output/evidence` and `/tmp` are private bounded tmpfs.
20. `/landlock` exists only under the dedicated P18 profile.
21. Collector retains only FDs 0, 1 and 2.
22. All collector capability sets are zero.
23. Securebits are locked and `NoNewPrivs` equals 1.
24. Both seccomp filters use architecture-aware default-deny
    allowlists.
25. Collector cannot fork, clone, exec, mount, unshare, setns or create
    sockets.
26. P7 cannot aggregate results from a single process.
27. P1 records both trusted-init and collector observer results.
28. Evidence paths use one byte-exact parser.
29. Publication is no-clobber.
30. Trusted publication occurs only after successful validation.

## Explicit inputs

The future probe command must require:

- `--repo-root`
- `--dataset-root`
- `--bootstrap-source`
- `--collector-source`
- `--runtime-manifest`
- `--sealed-source-copy-manifest`
- `--bootstrap-filter`
- `--collector-filter`
- `--p7-submatrix-manifest`
- `--landlock-profile-manifest`
- `--probe-output-root`

The launcher must not:

- infer dataset root from `ALFWORLD_DATA`;
- silently use the default ALFWorld cache;
- choose among multiple dataset copies;
- infer dataset root from the legacy all134 manifest;
- follow a supplied root or source symlink;
- select bootstrap or collector code directly from `/input/repo`
  during runtime;
- synthesize a missing profile manifest;
- accept an unbound P7 or P18 profile hash.

## Path validation

All roots and repository-controlled source paths are validated before
namespace creation.

The launcher must:

- open repository root as a trusted dirfd;
- resolve bootstrap and collector sources beneath that dirfd;
- reject symlinks and magic links;
- require both sources to be regular files;
- open each source once with read-only and close-on-exec flags;
- retain those exact opened FDs through sealed-copy construction;
- record `fstat` identity before and after copying;
- compute source SHA-256 through those same opened FDs;
- compare copied bytes against the expected manifest hashes;
- fail if source identity or metadata changes during validation/copy.

Repository, dataset and output roots must be pairwise non-nested.

Dataset root must contain:

- `json_2.1.1/train`;
- `json_2.1.1/valid_seen`;
- `json_2.1.1/valid_unseen`.

Absolute paths, inode numbers, device numbers and mount IDs belong only
to local evidence.

Failure codes include:

- `PROBE_SOURCE_PATH_INVALID`
- `PROBE_SOURCE_IDENTITY_CHANGED`
- `PROBE_SEALED_SOURCE_HASH_MISMATCH`
- `PROBE_ROOT_NESTING_INVALID`

## Process architecture

The backend has four process roles.

### 1. Outer trusted supervisor

The outer supervisor remains outside sandbox namespaces.

It:

- validates all explicit paths and trusted hashes;
- opens bootstrap and collector sources beneath the repository dirfd;
- computes each source hash through the exact opened FD;
- passes only those source FDs to trusted namespace init;
- creates bounded logs and publication channel;
- creates the two-identity user mapping;
- starts trusted namespace init;
- enforces global and per-case deadlines;
- receives only validated evidence bytes;
- performs no-clobber publication;
- never executes collector code.

### 2. Trusted namespace init

Trusted namespace init becomes sandbox PID 1.

Before collector fork it:

1. builds restricted root;
2. attaches the three host-backed mounts;
3. creates private `/bootstrap` and `/collector` tmpfs mounts;
4. copies bytes from the exact validated source FDs;
5. verifies copied exact-byte hashes;
6. verifies no extra source file exists;
7. changes both source-copy mounts to read-only;
8. verifies read-only, nosuid, nodev and noexec flags;
9. closes both original host source FDs;
10. proves those FDs are absent;
11. performs `pivot_root`;
12. protects trusted PID 1;
13. forks collector with distinct credentials.

Trusted namespace init retains the publication pipe. Collector never
inherits it.

### 3. Untrusted collector child

The collector child:

- uses a distinct mapped nonzero UID/GID;
- sees only the sealed source copies;
- keeps only FDs 0, 1 and 2;
- cannot choose an entry path below `/input/repo`;
- starts Python with exactly:
  `/collector/read_only_inventory_collector.py`;
- receives all capability, Landlock, seccomp and resource restrictions.

### 4. Trusted publication phase

After successful collector exit, trusted namespace init validates the
private evidence tree and streams validated bytes.

Outer supervisor publishes relative to one frozen output-root dirfd and
never replaces an existing result.

## Namespace contract

The backend must create:

- user namespace;
- private mount namespace;
- network namespace;
- PID namespace;
- IPC namespace;
- final private procfs.

The user namespace must contain distinct mapped credentials for:

- trusted namespace init;
- untrusted collector.

One-ID `--map-root-user` alone is insufficient for the final backend.

Required sequence:

1. validate a two-identity UID/GID mapping;
2. create user, mount, network, PID and IPC namespaces;
3. fork trusted namespace init as sandbox PID 1;
4. make mount propagation recursive private;
5. construct new root as a separate mount point;
6. attach host-backed mounts under their frozen contracts;
7. create private tmpfs mounts;
8. perform `pivot_root`;
9. close old-root directory FDs;
10. detach and unmount old root;
11. mount procfs at final `/proc` using:
    - `hidepid=4`;
    - `subset=pid`;
    - read-only;
    - nosuid;
    - nodev;
    - noexec;
12. clear and allowlist trusted-init environment;
13. set and verify `PR_SET_DUMPABLE=0`;
14. verify collector cannot observe or access trusted PID 1;
15. continue security setup.

No fallback to a host-root procfs mount is permitted.

If `hidepid=4`, `subset=pid`, read-only procfs, or distinct mapped
credentials cannot be established and behaviorally verified, backend
probe fails closed.

## Restricted-root layout

The base production restricted root may expose only:

- `/runtime/python`
- `/runtime/stdlib`
- `/runtime/shared-libraries`
- `/runtime/dynamic-linker`
- `/bootstrap/trusted_bootstrap.py`
- `/collector/read_only_inventory_collector.py`
- `/input/repo`
- `/input/dataset`
- `/output/evidence`
- `/tmp`
- `/proc`
- `/dev/null`
- `/dev/zero`
- `/dev/random`
- `/dev/urandom`

### Host-backed mounts

| Sandbox path | Recursive | Read-only | nosuid | nodev | noexec |
|---|---:|---:|---:|---:|---:|
| `/runtime` | yes | yes | yes | yes | no |
| `/input/repo` | yes | yes | yes | yes | yes |
| `/input/dataset` | yes | yes | yes | yes | yes |

There are exactly three host-backed mount classes.

### Sandbox-private sealed sources

| Sandbox path | Backing | Final flags |
|---|---|---|
| `/bootstrap` | private setup tmpfs | ro,nosuid,nodev,noexec |
| `/collector` | private setup tmpfs | ro,nosuid,nodev,noexec |

The source-copy tmpfs mounts are writable only during trusted setup.
They are sealed read-only before collector fork.

`/collector/read_only_inventory_collector.py` is the only
runtime-selected collector entry path.

The same read-only bytes may be visible as repository data below
`/input/repo`. This is not a second host-backed alias: `/bootstrap` and
`/collector` contain sandbox-private copied inodes rather than bind
mounts of those repository files.

The root must not expose host `/home`, `/data`, `/run`, `/var`, `/tmp`,
`/sys`, complete `/dev`, host sockets, caches or credentials.

## Frozen Python runtime

Python must be invoked through the frozen dynamic linker:

    /runtime/dynamic-linker
      --library-path /runtime/shared-libraries
      /runtime/python
      -I
      -S
      -B
      /bootstrap/trusted_bootstrap.py

The runtime closure must be frozen before probe execution.

The runtime manifest must contain:

- schema version;
- Python version;
- Python binary SHA-256;
- dynamic-linker SHA-256;
- standard-library semantics SHA-256;
- shared-library manifest SHA-256;
- trusted-bootstrap SHA-256;
- bootstrap-filter SHA-256;
- collector-filter SHA-256;
- Linux UAPI header SHA-256;
- architecture syscall-table SHA-256;
- every runtime relative path;
- file type;
- file mode;
- exact-byte SHA-256;
- symlink target where applicable;
- ELF dependency closure.

Every runtime symlink target must remain inside the frozen runtime
closure.

The sandbox must not expose `/etc/ld.so.cache`.

## Runtime-tree semantic hash

The runtime-tree semantic projection consists of a canonical array
sorted by relative UTF-8 path bytes.

Each entry contains:

- relative path;
- file type;
- file mode;
- exact-byte SHA-256;
- symlink target or null.

The canonical JSON rules are:

- UTF-8;
- sorted object keys;
- compact separators;
- no NaN;
- no Infinity;
- no timestamp;
- no host absolute path.

## Host-backed mount and sealed-source contracts

### Host-backed mount contract

The recursive host-backed mount helper protects exactly:

- `/runtime`;
- `/input/repo`;
- `/input/dataset`.

Preferred implementation:

- recursive bind;
- `mount_setattr`;
- `AT_RECURSIVE`;
- recursive VFS attribute verification.

Fallback:

1. recursively bind;
2. enumerate all submounts;
3. sort deepest-first;
4. remount each with required attributes;
5. parse final mountinfo;
6. verify each mount independently.

P3 writable positive controls exercise the same production helper for
all three mount classes.

### Sandbox-private sealed-source contract

Bootstrap and collector sources are not host-backed mounts.

For each source:

1. outer supervisor opens the source once beneath repo dirfd;
2. source identity and bytes are verified through that FD;
3. trusted init copies from the same FD into a private tmpfs;
4. copy SHA-256 must equal expected source SHA-256;
5. source FD is closed before collector fork;
6. tmpfs is changed to read-only;
7. final file mode is 0444;
8. final directory mode is 0555;
9. final mount flags are ro,nosuid,nodev,noexec;
10. mutation attempts must fail with `EROFS`;
11. copied bytes are rehashed after sealing.

The sealed-source-copy manifest binds:

- manifest schema;
- bootstrap source SHA-256;
- collector source SHA-256;
- opened-FD identity evidence;
- copy SHA-256 values;
- source-copy mount options;
- expected relative paths;
- allowed file count;
- final modes;
- manifest exact-byte SHA-256.

Failure produces:

`PROBE_SEALED_SOURCE_COPY_FAILED`

## Old-root and trusted-PID isolation

The new root must be a separate mount point.

After `pivot_root`, trusted namespace init must:

- change directory to `/`;
- close every old-root directory FD;
- detach and unmount old root;
- verify old root is absent from mountinfo;
- verify original host absolute paths return `ENOENT`;
- verify `/proc/self/root` does not expose old root.

### Trusted PID 1 protection

Trusted namespace init must:

- use credentials distinct from collector;
- clear its environment to a frozen allowlist;
- hold no old-root FD;
- set `PR_SET_DUMPABLE=0`;
- reapply it after every credential change;
- verify `PR_GET_DUMPABLE == 0`.

The final procfs must use the exact isolation contract defined above.

Collector adversarial tests must attempt:

- enumerate `/proc/1`;
- open `/proc/1/fd`;
- open and read every visible `/proc/1/fd/*`;
- open `/proc/1/mem`;
- open `/proc/1/environ`;
- open `/proc/1/root`;
- open `/proc/1/cwd`;
- open `/proc/1/ns/*`;
- use readlink on those paths.

Expected result:

- PID 1 is absent or inaccessible;
- publication pipe cannot be recovered;
- trusted environment cannot be read;
- trusted memory cannot be read or written;
- trusted namespace FDs cannot be obtained.

Failure produces:

`PROBE_TRUSTED_PID_EXPOSURE`

## Private tmpfs contract

### Evidence tmpfs

`/output/evidence`:

- size: 8 MiB;
- inode limit: 256;
- nosuid,nodev,noexec;
- mode 0700.

### Temporary tmpfs

`/tmp`:

- size: 16 MiB;
- inode limit: 512;
- nosuid,nodev,noexec;
- mode 0700.

### Bootstrap sealed-source tmpfs

`/bootstrap`:

- size: 4 MiB;
- inode limit: 32;
- writable only during trusted setup;
- sealed ro,nosuid,nodev,noexec;
- final mode 0555.

### Collector sealed-source tmpfs

`/collector`:

- size: 4 MiB;
- inode limit: 32;
- writable only during trusted setup;
- sealed ro,nosuid,nodev,noexec;
- final mode 0555.

### P18-only Landlock attribution tmpfs

`/landlock` exists only under:

`S1_LANDLOCK_ATTRIBUTION_TEST_PROFILE_V1`

It uses:

- size: 4 MiB;
- inode limit: 64;
- nosuid,nodev,noexec;
- mode 0700.

The production collector profile contains no `/landlock` mount.

No private tmpfs is a host persistent writable bind.

Private tmpfs contents disappear with sandbox destruction.

## Evidence quotas and path grammar

Probe evidence limits remain:

- maximum regular files: 16;
- maximum total evidence bytes: 4 MiB;
- maximum single-file bytes: 2 MiB;
- maximum stdout bytes: 1 MiB;
- maximum stderr bytes: 1 MiB;
- maximum directory depth below evidence root: 1;
- hard-link count: exactly 1;
- allowed payload type: regular file only.

### Canonical relative-path grammar

Evidence paths are length-prefixed bytes and must decode as strict
ASCII.

Each segment must match:

`[A-Za-z0-9][A-Za-z0-9._-]{0,127}`

Additional rules:

- total path length: 1 through 512 bytes;
- maximum segment count: 2;
- separator: `/` only;
- no leading slash;
- no trailing slash;
- no repeated slash;
- no empty segment;
- no `.` or `..`;
- no backslash;
- no NUL;
- no control character;
- no whitespace;
- no non-ASCII byte;
- comparison is byte-exact and case-sensitive;
- accepted paths are already canonical;
- no Unicode or filesystem normalization is performed.

Inner validator, stream decoder and outer publisher must use one shared
content-addressed path parser.

The canonical index path must be byte-identical to the actual
dirfd-relative walk path.

Duplicate accepted byte paths are forbidden.

The validator must reject:

- invalid UTF-8 or non-ASCII names;
- NFC/NFD variants;
- dot segments;
- empty segments;
- repeated separators;
- control characters;
- path traversal;
- duplicate paths;
- unexpected directories;
- special files;
- oversized or excess output.

## File-descriptor and proc-channel contract

Before untrusted code begins, collector keeps only:

- FD 0: `/dev/null`;
- FD 1: bounded stdout pipe;
- FD 2: bounded stderr pipe.

All descriptors from 3 onward must be closed with:

    close_range(
        3,
        UINT_MAX,
        CLOSE_RANGE_UNSHARE
    )

No fallback is accepted if `close_range` is unavailable.

Trusted namespace init retains the publication channel, but collector
must not inherit it.

After FD closure, collector must verify:

- only 0, 1 and 2 remain, apart from the transient enumeration FD;
- no writable host file exists;
- no socket exists;
- no publication FD exists;
- no old-root directory FD exists.

P9 and P10 must additionally prove that collector cannot recover any
trusted-init FD through `/proc/1/fd/*`.

Failure produces:

`PROBE_FD_OR_PROC_CHANNEL_EXPOSURE`

## Environment contract

The launcher must build an allowlisted environment from an empty
environment.

Allowed variables:

- `PATH=/runtime`;
- `LANG=C.UTF-8`;
- `LC_ALL=C.UTF-8`;
- `PYTHONHASHSEED=0`.

The following must be absent:

- `HOME`;
- `USER`;
- `LOGNAME`;
- `SHELL`;
- `PYTHONPATH`;
- `PYTHONHOME`;
- `PYTHONSTARTUP`;
- `PYTHONINSPECT`;
- `PYTHONUSERBASE`;
- `LD_PRELOAD`;
- `LD_LIBRARY_PATH`;
- `SSH_AUTH_SOCK`;
- `GIT_ASKPASS`;
- `HTTP_PROXY`;
- `HTTPS_PROXY`;
- `ALL_PROXY`;
- `NO_PROXY`;
- lowercase proxy variants;
- Slurm variables;
- Ray variables;
- CUDA variables;
- model-provider credentials.

## Capability contract

All filesystem and namespace setup must complete before capability
removal.

Before Python starts, the collector process must have:

- `CapInh = 0`;
- `CapPrm = 0`;
- `CapEff = 0`;
- `CapBnd = 0`;
- `CapAmb = 0`;
- `NoNewPrivs = 1`;
- locked noroot securebit;
- locked no-setuid-fixup securebit.

The trusted bootstrap must verify these values from `/proc/self/status`.

A successful command invocation is not sufficient evidence.

Failure produces:

`PROBE_CAPABILITY_DROP_FAILED`

## Seccomp policy model

Both formal filters use:

- default action: `SECCOMP_RET_KILL_PROCESS`;
- explicit allowlist;
- architecture guard;
- x32 ABI guard on x86-64;
- immutable compiled-filter SHA-256.

A probe process may be expected to terminate with a seccomp-related
signal. Each adversarial payload must run in its own process so one
expected termination cannot hide another result.

## Architecture guard

The initial supported architecture is:

`AUDIT_ARCH_X86_64`

Before probe execution, the launcher must verify:

- host machine architecture is x86-64;
- generated syscall table is x86-64;
- filter audit architecture is `AUDIT_ARCH_X86_64`.

Any architecture mismatch must kill the process.

On x86-64, every syscall number carrying `__X32_SYSCALL_BIT` must be
rejected before allowlist lookup.

There is no compatibility fallback to another architecture.

## Two-stage seccomp design

### Stage 1: bootstrap filter

The bootstrap filter is installed after capabilities are removed and
`no_new_privs` is set, but before execution of the frozen dynamic linker.

It permits only the system calls required to:

- execute the frozen dynamic linker once;
- start the frozen Python runtime;
- map frozen runtime libraries;
- read frozen standard-library files;
- initialize Python;
- execute the trusted bootstrap;
- query Landlock ABI;
- install Landlock rules when supported;
- install the second-stage filter;
- perform state verification;
- write bounded logs;
- exit.

The bootstrap filter must never allow:

- mount APIs;
- namespace creation or joining;
- network socket APIs;
- ptrace;
- process-vm access;
- BPF;
- keyrings;
- kernel-module operations;
- io_uring;
- userfaultfd;
- reboot;
- swap operations.

The exact bootstrap allowlist must be checked into the repository as a
reviewed content-addressed artifact before probe execution.

Runtime tracing may propose allowlist entries, but traced entries are
never approved automatically.

### Stage 2: collector filter

The trusted Python bootstrap installs the collector filter immediately
before entering collector source.

It then invokes:

    runpy.run_path(
        "/collector/read_only_inventory_collector.py",
        run_name="__main__"
    )

The collector filter must deny by omission:

- `fork`;
- `vfork`;
- `clone`;
- `clone3`;
- `execve`;
- `execveat`;
- `unshare`;
- `setns`;
- every mount API;
- every socket API;
- ptrace APIs;
- process-vm APIs;
- io_uring APIs;
- userfaultfd;
- memfd creation;
- keyrings;
- BPF;
- module loading;
- reboot;
- swap operations.

The collector allowlist may include only the system calls needed for:

- ordinary file reads;
- directory enumeration;
- stat operations;
- memory mapping;
- memory allocation;
- signal return;
- process-local clock queries;
- regular-file writes to private tmpfs;
- regular-file rename within private tmpfs;
- bounded stdout and stderr;
- normal process exit.

The exact collector allowlist must be reviewed separately before probe
execution.

## Filter identity

Each filter artifact must bind:

- filter schema version;
- architecture;
- syscall names;
- syscall numbers;
- default action;
- architecture-mismatch action;
- x32 action;
- generated classic-BPF instructions;
- instruction count;
- source-generator SHA-256;
- UAPI-header SHA-256;
- syscall-table SHA-256;
- final filter exact-byte SHA-256.

Changing any of these values creates a new filter identity.

## Landlock policy and attribution profile

Production policy remains:

`PROBE_AND_REQUIRE_IF_SUPPORTED`

If Landlock ABI is supported, production policy installation and
enforcement are mandatory.

P18 uses only:

`S1_LANDLOCK_ATTRIBUTION_TEST_PROFILE_V1`

The P18 profile:

- has a distinct immutable profile ID;
- has a distinct canonical manifest;
- has a distinct exact-byte SHA-256;
- creates private bounded `/landlock` tmpfs;
- exposes `/landlock/allowed`;
- exposes `/landlock/denied`;
- uses VFS-writable fixtures;
- uses a dedicated reviewed seccomp profile;
- cannot be selected by the production launcher;
- cannot be selected through an arbitrary CLI string;
- is selected only by a compiled profile enum;
- is rejected when profile hash differs;
- must be named in the external probe execution approval.

The profile manifest binds:

- profile ID;
- `/landlock` tmpfs size and inode limit;
- fixture paths and modes;
- baseline child configuration;
- Landlock child configuration;
- handled rights for each supported ABI;
- dedicated seccomp filter hash;
- payload hashes;
- expected outcomes;
- profile exact-byte SHA-256.

The base production restricted-root manifest does not include
`/landlock`.

## Resource limits and attribution profiles

Base untrusted probe limits remain:

- `RLIMIT_CPU` soft: 2 seconds;
- `RLIMIT_CPU` hard: 3 seconds;
- `RLIMIT_AS`: 268435456 bytes;
- `RLIMIT_FSIZE`: 4194304 bytes;
- `RLIMIT_NOFILE`: 32;
- `RLIMIT_NPROC`: 1;
- `RLIMIT_CORE`: 0;
- wall-clock timeout: 10 seconds.

### Legal-runtime positive control

Before negative resource tests, the same frozen runtime, bootstrap,
filters and limits must successfully complete a minimal legal payload.

The positive control must prove:

- frozen Python starts;
- bootstrap completes;
- one legal input read succeeds;
- one legal evidence regular-file write succeeds;
- normal exit occurs within explicit safety margin.

Failure is a setup failure, not a resource-limit PASS.

### RLIMIT attribution profile

P15 uses a dedicated content-addressed profile:

`S1_RLIMIT_ATTRIBUTION_TEST_PROFILE_V1`

This profile:

- is unavailable to the production collector launcher;
- uses a distinct manifest and hash;
- uses a dedicated mapped nonzero UID;
- temporarily allows one controlled process-creation syscall;
- first proves process creation succeeds with a permissive test limit;
- then sets `RLIMIT_NPROC=1`;
- repeats the same operation;
- requires failure attributable to the limit rather than seccomp.

The production collector profile continues to deny all process creation.

Probe execution approval must bind the exact test-profile hash.

### I/O non-claim

These limits do not establish a bound on:

- total Ceph bytes read;
- read IOPS;
- metadata IOPS;
- aggregate filesystem bandwidth.

The future collector contract must separately freeze file-count and
read-byte budgets before inventory execution.

## Probe execution model

P1-P6 and P8-P20 each run in an independent fresh sandbox.

P7 is an aggregate probe composed of independent subcases:

`P7.<decimal_syscall_number>`

For P7:

- `case_count` equals the number of syscall numbers in the frozen
  x86-64 table that are absent from the collector allowlist;
- each case receives a fresh namespace set;
- each case receives a fresh restricted root;
- each case receives one fresh process;
- each case has a two-second wall timeout;
- cases execute sequentially;
- cases are never retried automatically;
- each case emits one semantic result and one local diagnostic result;
- one case termination cannot satisfy another case;
- no process is reused after seccomp termination.

P7 aggregate deadline is:

`30 + (3 * case_count)` seconds

P7 passes only when:

- manifest syscall-table hash matches;
- expected case IDs are unique;
- observed case IDs exactly equal expected case IDs;
- every expected case has exactly one result;
- no unexpected case exists;
- all cases have the expected `SECCOMP_KILL` outcome;
- aggregate deadline is not exceeded.

Every probe or P7 subcase uses fresh private tmpfs and cleanup state.

No failed or timed-out case is retried automatically.

A new suite execution requires a new external execution approval.

## Probe-result statuses

Allowed per-probe statuses:

- `PASS`;
- `PASS_ENABLED`;
- `PASS_UNSUPPORTED`;
- `FAIL`;
- `TIMEOUT`;
- `SETUP_ERROR`.

Only P18 Landlock may return `PASS_UNSUPPORTED`.

The overall suite passes only when:

- P1-P17 are `PASS`;
- P18 is `PASS_ENABLED` or `PASS_UNSUPPORTED`;
- P19-P20 are `PASS`.

No partial pass is accepted.

## Probe matrix

### P1: namespace creation and observer roles

P1 contains two explicit observer views.

#### P1 trusted-init view

Trusted namespace init must observe:

- itself as PID 1;
- `/proc/1` referring to itself;
- private PID namespace identity;
- private mount, network, user and IPC namespace identities;
- no host processes in final procfs.

#### P1 collector view

Collector must observe:

- a different mapped UID/GID from trusted init;
- trusted PID 1 absent or inaccessible;
- `/proc/1/fd`, `/proc/1/mem`, `/proc/1/environ`,
  `/proc/1/root`, `/proc/1/cwd` and `/proc/1/ns`
  absent or inaccessible;
- no host process visibility.

A trusted-init-view success cannot substitute for the collector-view
test.

Both observer records are mandatory.

Failure codes:

- `PROBE_NAMESPACE_FAILED`
- `PROBE_OBSERVER_ROLE_MISMATCH`
- `PROBE_PROCFS_ISOLATION_FAILED`

### P2: restricted root, three host-backed mounts and sealed sources

Test:

- new root is a separate mount point;
- propagation is recursive private;
- `pivot_root` succeeds;
- old root is detached;
- exactly three host-backed mount classes are present;
- `/runtime`, `/input/repo` and `/input/dataset` match their flags;
- `/bootstrap` and `/collector` are private tmpfs copies;
- copied hashes match the same opened source FDs;
- both source-copy mounts are sealed read-only;
- source FDs are closed before collector fork;
- collector entry path is exactly
  `/collector/read_only_inventory_collector.py`;
- final procfs and credential isolation pass.

Adversarial sealed-source actions:

- overwrite;
- truncate;
- rename;
- unlink;
- create an extra file;
- chmod to gain write access.

Expected:

- all sealed-source mutations fail with `EROFS`;
- no second host-backed bootstrap or collector bind exists;
- mountinfo and source-copy manifest agree.

Failure codes:

- `PROBE_PIVOT_ROOT_FAILED`
- `PROBE_HOST_BACKED_MOUNT_FAILED`
- `PROBE_SEALED_SOURCE_COPY_FAILED`
- `PROBE_PROCFS_ISOLATION_FAILED`
- `PROBE_CREDENTIAL_ISOLATION_FAILED`

### P3: recursive read-only positive and negative control

P3 exercises the production recursive mount helper for exactly:

- runtime mount class;
- repository mount class;
- dataset mount class.

For each class, use a sacrificial source tree and nested submount.

Positive control before protection:

- same mapped collector credentials;
- create succeeds;
- overwrite succeeds;
- nested-submount write succeeds.

Negative control after the production mount pipeline:

- identical create fails with `EROFS`;
- identical overwrite fails with `EROFS`;
- identical nested-submount write fails with `EROFS`;
- mountinfo reports required flags.

Bootstrap and collector are excluded from P3 because they are
sandbox-private sealed source copies, not host-backed mount classes.
Their behavior is tested by P2.

Failure code:

`PROBE_RECURSIVE_READONLY_FAILED`

### P4: private evidence tmpfs

Test:

- evidence tmpfs exists;
- ordinary regular-file write succeeds;
- host has no direct writable bind inside sandbox;
- tmpfs disappears after namespace destruction.

Failure code:

`PROBE_PRIVATE_TMPFS_FAILED`

### P5: capability and securebits enforcement

Test:

- all capability sets;
- securebits locks;
- `NoNewPrivs`;
- attempted tmpfs mount;
- attempted remount;
- attempted setuid capability recovery.

Expected:

- capability values are zero;
- privileged actions fail.

Failure code:

`PROBE_CAPABILITY_DROP_FAILED`

### P6: bootstrap seccomp filter

Test:

- frozen Python starts;
- trusted bootstrap starts;
- Landlock probe calls can run;
- collector filter can be installed;
- mount, namespace and socket adversarial syscalls terminate the payload.

Failure code:

`PROBE_BOOTSTRAP_SECCOMP_FAILED`

### P7: collector seccomp per-syscall submatrix

P7 contract:

`S1_P7_SYSCALL_SUBMATRIX_V1`

Expected case set is generated from:

- frozen x86-64 syscall-table hash;
- frozen collector allowlist hash.

For every table syscall number absent from the allowlist, create:

`P7.<decimal_syscall_number>`

Each case uses:

- independent sandbox;
- independent namespace set;
- independent restricted root;
- independent process;
- independent two-second timeout;
- independent result;
- independent cleanup verification.

The case invokes exactly one target syscall number.

Expected result:

- process terminates under `SECCOMP_RET_KILL_PROCESS`;
- target syscall has no observable side effect;
- semantic outcome is `SECCOMP_KILL`.

P7 aggregate validation requires:

- complete expected case-set equality;
- no missing result;
- no duplicate result;
- no unexpected result;
- frozen syscall-table hash match;
- frozen allowlist hash match;
- all cases passing;
- aggregate deadline
  `30 + (3 * case_count)` seconds not exceeded.

P7 does not claim exhaustive coverage unless all conditions above hold.

Failure codes:

- `PROBE_COLLECTOR_SECCOMP_FAILED`
- `PROBE_P7_CASESET_INCOMPLETE`
- `PROBE_P7_AGGREGATE_TIMEOUT`

### P8: network and pathname-socket isolation

Test:

- interface inventory;
- routing table;
- loopback state;
- TCP socket creation;
- UDP socket creation;
- abstract UNIX socket;
- pathname UNIX socket;
- host `/run` visibility;
- inherited socket inventory.

Expected:

- no usable interface;
- no default route;
- socket syscalls denied;
- host socket paths absent.

Failure code:

`PROBE_NETWORK_ISOLATION_FAILED`

### P9: inherited-FD and trusted-PID channel closure

Outer test launcher intentionally opens:

- writable regular file;
- connected socket;
- pipe;
- input directory FD;
- publication-like pipe.

Expected collector state:

- only FDs 0, 1 and 2 are directly inherited;
- all intentional objects are unreachable;
- `/proc/1/fd` is absent or inaccessible;
- no PID 1 FD can be opened or duplicated;
- no publication channel can be recovered.

Failure code:

`PROBE_FD_OR_PROC_CHANNEL_EXPOSURE`

### P10: old-root and trusted-init procfs invisibility

Adversarial actions:

- open original repo path;
- open original dataset path;
- inspect `/proc/self/root`;
- walk parent directories;
- use saved host path strings;
- inspect `/proc/1/fd/*`;
- inspect `/proc/1/mem`;
- inspect `/proc/1/environ`;
- inspect `/proc/1/root`;
- inspect `/proc/1/cwd`;
- inspect `/proc/1/ns/*`.

Expected:

- original host paths return `ENOENT`;
- no old-root mount appears;
- no old-root FD exists;
- every trusted-init procfs target is absent or inaccessible;
- trusted environment, memory, namespaces and FDs remain unavailable.

Failure codes:

- `PROBE_OLD_ROOT_VISIBLE`
- `PROBE_TRUSTED_PID_EXPOSURE`

### P11: seccomp architecture and x32 ABI

Test:

- correct audit architecture;
- deliberately incorrect audit architecture;
- syscall number with `__X32_SYSCALL_BIT`.

Expected:

- correct x86-64 calls follow the allowlist;
- wrong architecture terminates;
- x32-form syscall terminates.

Failure code:

`PROBE_SECCOMP_ARCH_FAILED`

### P12: default-deny unknown syscall

Test:

- invoke a syscall number not present in the reviewed table;
- invoke a known but non-allowlisted harmless syscall.

Expected:

- each dedicated process terminates under the formal default action.

Failure code:

`PROBE_DEFAULT_DENY_FAILED`

### P13: process creation and execution denial

Adversarial actions:

- `fork`;
- `vfork`;
- `clone`;
- `clone3`;
- `execve`;
- `execveat`.

Expected:

- each dedicated collector-filter process terminates;
- no child survives.

Failure code:

`PROBE_PROCESS_CREATION_DENIAL_FAILED`

### P14: advanced-kernel-interface denial

Adversarial actions:

- io_uring setup;
- userfaultfd;
- memfd creation;
- BPF;
- keyring access.

Expected:

- every action terminates under default deny.

Failure code:

`PROBE_ADVANCED_SYSCALL_DENIAL_FAILED`

### P15: resource-limit attribution and timeout

First run the legal-runtime positive control under the production probe
limits.

Dedicated negative payloads test:

- CPU exhaustion;
- address-space exhaustion;
- oversized file;
- descriptor exhaustion;
- wall-clock timeout.

The process-limit subprobe uses only:

`S1_RLIMIT_ATTRIBUTION_TEST_PROFILE_V1`

Process-limit attribution requires:

1. controlled process creation succeeds under the test profile with a
   permissive test limit;
2. same UID, syscall and payload are repeated with
   `RLIMIT_NPROC=1`;
3. the second operation fails with the expected resource-limit
   outcome;
4. production collector profile remains unable to select the test
   profile.

No evidence is published for any negative resource payload.

Failure code:

`PROBE_RESOURCE_LIMIT_FAILED`

### P16: tmpfs quota enforcement

Dedicated payloads attempt:

- write beyond 8 MiB;
- create more than 256 evidence inodes;
- write beyond 16 MiB in `/tmp`;
- create more than 512 temporary inodes.

Expected:

- writes fail at the frozen limits;
- host persistent storage is unchanged.

Failure code:

`PROBE_TMPFS_QUOTA_FAILED`

### P17: minimal device and sysfs exposure

Test:

- visible `/dev` entries;
- host `/sys`;
- `/dev/fuse`;
- `/dev/kvm`;
- `/dev/net`;
- random-device functionality.

Expected:

- only the four approved device nodes exist;
- prohibited devices and `/sys` are absent;
- approved random devices are readable.

Failure code:

`PROBE_DEVICE_EXPOSURE_FAILED`

### P18: Landlock independently attributable profile

P18 runs only under:

`S1_LANDLOCK_ATTRIBUTION_TEST_PROFILE_V1`

Preconditions:

- external probe approval binds exact profile hash;
- profile manifest hash matches;
- production launcher rejects this profile;
- `/landlock` is private bounded tmpfs;
- no host persistent path backs `/landlock`.

Fixture:

- `/landlock/allowed`;
- `/landlock/denied`.

Both fixture paths are VFS-writable.

Baseline case:

- no Landlock policy;
- read/write allowed succeeds;
- read/write denied-path fixture also succeeds.

Landlock case:

- identical UID/GID;
- identical mount state;
- identical seccomp profile;
- identical rlimits;
- read/write `/landlock/allowed` succeeds;
- equivalent operation on `/landlock/denied` fails with `EACCES`.

The only differing enforcement layer is Landlock.

Allowed aggregate outcomes:

- `PASS_ENABLED`;
- `PASS_UNSUPPORTED`.

Supported ABI with failed profile, hash, setup or attribution is failure.

Failure codes:

- `PROBE_LANDLOCK_FAILED`
- `PROBE_LANDLOCK_PROFILE_MISMATCH`
- `PROBE_LANDLOCK_ATTRIBUTION_INVALID`

### P19: evidence validation and no-clobber publication

Malicious private evidence trees include:

- invalid ASCII path;
- non-ASCII or invalid UTF-8 path;
- NFC/NFD name;
- absolute path;
- dot segment;
- empty segment;
- repeated slash;
- backslash;
- control character;
- symlink;
- FIFO;
- socket;
- hard link;
- oversized file;
- excess files;
- unexpected directory;
- duplicate accepted byte path;
- malformed JSON;
- incorrect hash.

Every malicious tree must be rejected with no host final output.

Publication collision tests include:

- existing final regular file;
- existing final directory;
- existing final symlink;
- stale staging directory;
- simultaneous no-replace collision.

Valid publication must:

- use output-root dirfd-relative operations;
- create new staging only;
- fsync every file;
- fsync every staging directory;
- call `renameat2(..., RENAME_NOREPLACE)`;
- fail if final exists;
- fsync output parent after rename;
- remove staging completely after any failure.

Local evidence exact-file hash must be emitted as a detached sidecar.

Failure code:

`PROBE_PUBLICATION_VALIDATION_FAILED`

### P20: timeout and process-tree cleanup

This is a launcher-only probe profile.

A test payload creates a controlled process tree before the production
collector filter would be installed, then hangs.

Expected:

- wall timeout fires;
- complete PID namespace tree is killed;
- all descendants disappear;
- private mounts disappear;
- no partial evidence is published.

Failure code:

`PROBE_CLEANUP_FAILED`

The P20 test-only profile must never be usable as the production
collector profile.

## Evidence publication protocol

The inner validator accepts only paths satisfying the canonical ASCII
grammar.

It constructs a canonical byte-exact index sorted by path bytes.

The outer supervisor:

1. opens frozen output root as a dirfd with directory and no-follow
   checks;
2. verifies final target does not exist;
3. creates a new unique staging directory relative to the dirfd;
4. reconstructs regular files with `O_CREAT|O_EXCL|O_NOFOLLOW`;
5. verifies path, size and SHA-256;
6. fsyncs every file;
7. fsyncs each staging directory;
8. invokes `renameat2` with `RENAME_NOREPLACE`;
9. fails closed when final target exists;
10. fsyncs the output parent directory;
11. removes complete staging on any failure.

Ordinary replacing `rename()` is forbidden.

A stale staging directory is never reused.

Published files are:

- `semantic_evidence.json`;
- `local_evidence.json`;
- `local_evidence.json.sha256`.

`local_evidence.json` does not contain its own exact-file hash.

The detached sidecar contains the exact-byte SHA-256 of
`local_evidence.json`.

## Semantic evidence schema

Semantic evidence contains only cross-machine-stable fields.

Per-probe semantic result contains:

- probe ID;
- payload ID;
- payload SHA-256;
- expected normalized outcome class;
- observed normalized outcome class;
- normalized semantic assertions;
- failure code or null;
- result status.

Allowed normalized outcome classes include:

- `SUCCESS`;
- `EROFS_DENIAL`;
- `EACCES_DENIAL`;
- `SECCOMP_KILL`;
- `RESOURCE_LIMIT`;
- `TIMEOUT`;
- `SETUP_ERROR`.

Semantic evidence excludes:

- raw errno;
- raw signal number;
- PID;
- duration;
- raw log bytes;
- captured-log hash;
- host paths;
- kernel-specific diagnostic text.

Top-level semantic evidence includes:

- schema version;
- probe design ID;
- backend ID;
- threat model;
- architecture contract;
- runtime and filter hashes;
- resource-contract hash;
- restricted-root manifest hash;
- P1-P20 semantic results;
- Landlock semantic status;
- overall suite status.

## Local execution evidence schema

Local evidence contains machine-specific diagnostics:

- semantic evidence SHA-256;
- execution timestamp;
- hostname;
- kernel release;
- boot ID;
- machine architecture;
- active LSM list when available;
- kernel-config digest when available;
- loaded-module-list digest when available;
- effective UID and GID;
- util-linux and glibc versions;
- Landlock ABI;
- user-supplied and resolved paths;
- device, inode, mount ID and filesystem data;
- namespace IDs;
- complete mount verification;
- raw per-probe errno;
- raw per-probe signal;
- raw PID;
- raw duration;
- raw captured logs and log SHA-256;
- supervisor exit status;
- cleanup status;
- truncation status.

`local_evidence.json` contains no self-referential exact-file hash.

Its exact-byte SHA-256 is stored only in:

`local_evidence.json.sha256`

## Canonical evidence encoding

Semantic and local JSON use:

- UTF-8;
- sorted object keys;
- compact separators;
- no NaN;
- no Infinity;
- LF final newline.

`semantic_evidence_sha256` is calculated from exact
`semantic_evidence.json` bytes and recorded in local evidence.

`local_evidence.json.sha256` is calculated only after
`local_evidence.json` bytes are final.

No file contains its own exact-byte hash.

Raw logs and diagnostics are excluded from the semantic projection.

## Failure handling

Any required probe failure produces overall status:

`BACKEND_PROBE_FAILED`

The suite must fail closed for:

- setup uncertainty;
- missing required tool;
- unknown architecture;
- runtime hash mismatch;
- filter hash mismatch;
- mount verification ambiguity;
- timeout outside P15 or P20;
- unexpected signal;
- publication ambiguity;
- residual child process;
- residual private mount;
- partial host output.

There is no automatic retry.

There is no best-of-multiple-run selection.

A new run requires a separately approved execution record.

## Probe pseudocode

### Outer supervisor

    verify_branch_and_commit()
    verify_runtime_enforcement_tcb_hashes()
    verify_assurance_artifact_hashes()
    open_repo_root_dirfd()
    open_bootstrap_source_once_beneath_repo()
    open_collector_source_once_beneath_repo()
    hash_sources_through_same_open_fds()
    validate_profile_manifests()
    create_two_identity_uid_gid_map()
    start_namespace_init_with_source_fds()
    enforce_probe_or_subcase_deadline()
    receive_validated_stream()
    publish_with_renameat2_noreplace()

### Trusted namespace init

    become_pid_namespace_init()
    make_mounts_recursive_private()
    build_separate_new_root()
    attach_runtime_repo_dataset_host_mounts()
    create_private_bootstrap_tmpfs()
    create_private_collector_tmpfs()
    copy_from_validated_source_fds()
    verify_copy_hashes()
    seal_source_tmpfs_readonly()
    close_host_source_fds()
    verify_source_fds_absent()
    pivot_to_new_root()
    mount_final_private_proc()
    protect_trusted_pid1()
    fork_distinct_credential_collector()
    validate_private_evidence_after_exit()
    stream_validated_bytes()

### Collector child

    change_to_distinct_mapped_uid_gid()
    close_publication_pipe()
    close_range_from_fd_3()
    verify_observer_role()
    verify_proc1_inaccessible()
    apply_selected_frozen_profile()
    clear_capabilities()
    set_no_new_privs()
    install_bootstrap_filter()
    exec_frozen_python_from_runtime()
    runtime_selected_entry_path_is_collector_copy()

### P7 orchestrator

    load_frozen_syscall_table()
    load_frozen_collector_allowlist()
    derive_expected_case_ids()
    for syscall_number in expected_case_ids:
        create_fresh_sandbox()
        run_one_p7_case()
        enforce_two_second_case_timeout()
        collect_one_semantic_result()
        collect_one_local_diagnostic()
        verify_cleanup()
    enforce_aggregate_deadline()
    require_exact_case_set_equality()

### P18 orchestrator

    verify_landlock_profile_hash_binding()
    create_private_bounded_landlock_tmpfs()
    run_baseline_case()
    run_landlock_case()
    require_only_landlock_layer_differs()
    destroy_profile_tmpfs()

### Publication validator

    require_successful_exit()
    apply_canonical_path_parser()
    reject_non_regular_files()
    enforce_quotas()
    calculate_hashes()
    construct_canonical_index()
    stream_validated_bytes_only()

## Probe evidence requirements

Every probe creates two result layers.

### Semantic probe result

Contains only:

- probe ID;
- payload ID and SHA-256;
- expected normalized outcome;
- observed normalized outcome;
- semantic assertions;
- failure code;
- PASS state.

### Local probe diagnostics

Contains:

- raw errno;
- raw signal;
- PID;
- timing;
- raw log;
- log SHA-256;
- host-specific setup information.

A semantic PASS cannot be inferred only from:

- a configuration field;
- one overlapping security layer;
- another process's termination;
- missing VFS permissions;
- missing capability;
- seccomp denial when a resource limit is being tested.

P3, P15 and P18 require explicit positive controls.

## Future repository file boundaries

The implementation plan may define focused artifacts for:

- trusted outer supervisor;
- trusted namespace init;
- trusted Python bootstrap;
- three-class host-backed mount helper;
- sealed-source-copy builder;
- sealed-source-copy manifest;
- seccomp filter generator and artifacts;
- frozen runtime closure;
- P7 submatrix manifest and orchestrator;
- P18 Landlock attribution profile and manifest;
- P15 RLIMIT attribution profile;
- adversarial payloads;
- evidence validator and publisher;
- semantic/local evidence encoders;
- unit and integration tests.

Backend tooling and the future ALFWorld inventory collector remain
separate work packages.

## Required approval sequence

Required order:

1. complete this final spec revision;
2. push exact revision commit;
3. perform final semantic design review;
4. grant or deny
   the external final backend-probe design approval decision;
5. only after approval, write implementation plan;
6. implement tooling with tests;
7. perform static and semantic code review;
8. freeze runtime closure;
9. freeze bootstrap and collector seccomp allowlists;
10. freeze three-class mount contract;
11. freeze sealed-source-copy manifest hash;
12. freeze P7 submatrix manifest hash;
13. freeze P18 Landlock profile manifest hash;
14. freeze P15 RLIMIT profile manifest hash;
15. freeze all trusted artifact hashes;
16. grant separate backend-probe execution approval;
17. execute P1-P20;
18. review evidence;
19. grant or deny final backend approval;
20. separately design and approve inventory collector.

No step authorizes a later step implicitly.

## Explicit non-goals

This design does not:

- implement the sandbox;
- implement the collector;
- run a backend probe;
- scan ALFWorld files;
- create an ALFWorld environment;
- execute an expert or model;
- create split manifests;
- freeze selection budgets;
- approve probe execution;
- approve inventory execution;
- prove a bound on Ceph read bytes, IOPS or bandwidth;
- claim protection against kernel compromise.

## Design acceptance criteria

The design is eligible for final review only if it defines:

- final revision scope without final approval;
- exactly three host-backed mount classes;
- `/bootstrap` and `/collector` as sandbox-private copies;
- same-open-FD source verification and copying;
- sealed-source manifest and hash binding;
- unique runtime collector entry path;
- no requirement that identical bytes disappear from `/input/repo`;
- P1 trusted-init and collector observer roles;
- P7 per-syscall independent submatrix;
- P7 exact case-set coverage;
- P7 per-case timeout and aggregate deadline;
- dedicated P18 Landlock profile;
- private bounded `/landlock` tmpfs;
- P18 profile manifest and exact hash;
- production inability to select P18 profile;
- external execution approval binding P18 profile hash;
- P2 sealed-source mutation testing;
- P3 limited to the three host-backed classes;
- no implementation-plan authorization;
- no probe execution authorization;
- no collector execution authorization.

## Normative references

- `PR_SET_DUMPABLE` and `PR_GET_DUMPABLE`;
- procfs `hidepid` and `subset=pid`;
- `proc_pid_fd`, `proc_pid_mem` and `proc_pid_environ`;
- `renameat2` with `RENAME_NOREPLACE`;
- file and directory `fsync`;
The implementation and review must consult the official Linux
documentation for:

- `seccomp(2)`;
- Seccomp BPF kernel documentation;
- `pivot_root(2)`;
- `mount(8)` and the new mount API;
- `unshare(1)`;
- `capabilities(7)`;
- `setpriv(1)`;
- `close_range(2)`;
- `landlock(7)`;
- `tmpfs(5)`;
- `getrlimit(2)`;
- `proc_pid_fd(5)`;
- network namespaces;
- UNIX-domain sockets.
