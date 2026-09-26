# S1 Backend Probe Execution Preflight V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, dataset-bound, non-executing preflight bundle for a later external S1 backend-probe execution decision.

**Architecture:** Use three review-preserving commits. Commit 1 freezes the design; Commit 2 freezes this plan; Commit 3 adds one strict schema, one pure preflight module, one closed CLI, and focused tests. The implementation observes and hashes explicit inputs but cannot open or invoke the backend probe.

**Tech Stack:** Python 3.12, JSON, pathlib, hashlib, pytest, Git, GNU Make.

## Global Constraints

- Base commit: `57a15945d0d790aa7f7033ffc86ac79273dd1d8d`.
- Branch: `implementation/s1-backend-probe-execution-preflight-v1`.
- No modification to `require_execution_approval()`.
- No modification to native supervisor or namespace execution.
- No P1–P20 execution.
- No inventory, ALFWorld, model, GPU, or rollout execution.
- Dataset paths are explicit inputs and are never inferred.
- Preflight output is outside the repository.
- `--execute` returns `77`.
- Reviewed candidate binary SHA-256 remains `3f03b30b408e16466981bca1556983bdf709edf065a11d3b15bb626c3032e713`.

---

### Task 1: Freeze the execution-preflight design

**Files:**
- Create: `docs/superpowers/specs/2026-08-06-s1-backend-probe-execution-preflight-v1-design.md`

**Interfaces:**
- Consumes: merged S1 candidate and governance identities.
- Produces: immutable scope and safety requirements.

- [ ] **Step 1: Verify base and clean branch**

```bash
test "$(git branch --show-current)" = \
  "implementation/s1-backend-probe-execution-preflight-v1"
test "$(git rev-parse HEAD)" = \
  "57a15945d0d790aa7f7033ffc86ac79273dd1d8d"
test -z "$(git status --porcelain=v1 --untracked-files=all)"
```

- [ ] **Step 2: Write and audit the exact design**

Use the reviewed external payload. Confirm all immutable hashes and
not-approved boundaries are present and that no unfinished placeholders
remain.

- [ ] **Step 3: Commit**

```bash
git add -- \
  docs/superpowers/specs/2026-08-06-s1-backend-probe-execution-preflight-v1-design.md
git diff --cached --check
git commit -m "Design S1 backend probe execution preflight"
```

---

### Task 2: Freeze the implementation plan

**Files:**
- Create: `docs/superpowers/plans/2026-08-06-s1-backend-probe-execution-preflight-v1-implementation.md`

**Interfaces:**
- Consumes: Task 1 design.
- Produces: exact TDD and audit sequence for Task 3.

- [ ] **Step 1: Write and audit this exact plan**

Confirm Task 3 names every implementation path and every non-execution
boundary.

- [ ] **Step 2: Commit**

```bash
git add -- \
  docs/superpowers/plans/2026-08-06-s1-backend-probe-execution-preflight-v1-implementation.md
git diff --cached --check
git commit -m "Plan S1 backend probe execution preflight"
```

---

### Task 3: Implement the non-executing preflight

**Files:**
- Create: `configs/security/schemas/backend_probe_execution_decision_v1.json`
- Create: `src/pchsi/security/execution_preflight.py`
- Create: `scripts/security/prepare_backend_probe_execution.py`
- Create: `tests/security/test_execution_preflight.py`
- Modify: `tests/security/test_contracts.py`

**Interfaces:**
- Consumes:
  - explicit dataset root;
  - explicit legacy manifest;
  - explicit input contract;
  - current repository and candidate artifacts.
- Produces:
  - `DatasetIdentity`;
  - deterministic preflight manifest;
  - exact future decision template;
  - output SHA-256 sidecar.

- [ ] **Step 1: Write the failing tests**

The tests must require:

- exact 22-probe corpus;
- payload/source SHA-256 agreement;
- mountinfo longest-prefix selection;
- rejection of symlinked dataset and input files;
- required split directories;
- output root outside repository;
- deterministic manifest bytes;
- exact three output files;
- `--execute` exit code `77`.

- [ ] **Step 2: Run RED**

```bash
python -m pytest -q tests/security/test_execution_preflight.py
```

Expected: collection or assertion failure because implementation files do not
exist.

- [ ] **Step 3: Add schema, module, and CLI**

Implement the exact reviewed payloads. The module must remain pure with
respect to execution: no shell, network, namespace, mount, seccomp, Landlock,
model, or environment operation is allowed.

- [ ] **Step 4: Run focused GREEN**

```bash
python -m pytest -q tests/security/test_execution_preflight.py
```

Expected: all focused tests pass.

- [ ] **Step 5: Run cumulative verification**

```bash
python -m pytest -q
python -m compileall -q src tests scripts
make -C native/s1_backend_probe clean all unit probe-payloads
```

Expected: full suite passes and native target remains compile-only for probe
payloads.

- [ ] **Step 6: Run static non-execution audit**

Verify the new production module and CLI do not import or call:

```text
subprocess
socket
ctypes
os.system
os.exec*
os.spawn*
unshare
mount
pivot_root
seccomp
landlock_restrict_self
env.step
alfworld
vllm
torch
```

Verify `src/pchsi/security/execution_gate.py`,
`native/s1_backend_probe/src/supervisor.c`, and
`native/s1_backend_probe/src/namespace_init.c` are byte-identical to the
base commit.

- [ ] **Step 7: Verify exact implementation scope**

Expected exactly:

```text
configs/security/schemas/backend_probe_execution_decision_v1.json
scripts/security/prepare_backend_probe_execution.py
src/pchsi/security/execution_preflight.py
tests/security/test_execution_preflight.py
tests/security/test_contracts.py
```

- [ ] **Step 8: Commit**

```bash
git add -- \
  configs/security/schemas/backend_probe_execution_decision_v1.json \
  scripts/security/prepare_backend_probe_execution.py \
  src/pchsi/security/execution_preflight.py \
  tests/security/test_execution_preflight.py \
  tests/security/test_contracts.py
git diff --cached --check
git commit -m "Implement dataset-bound S1 execution preflight"
```

- [ ] **Step 9: Post-commit verification and push**

Re-run focused tests, full tests, compileall, native build, exact cumulative
seven-path audit, and clean-worktree audit. Push the branch and verify
`local_only=0` and `remote_only=0`.

### Schema inventory integration requirement

Adding a strict schema under `configs/security/schemas/` requires updating
the frozen schema inventory in `tests/security/test_contracts.py`. The
implementation commit therefore changes exactly five paths, and the
cumulative branch changes exactly seven paths. This correction was recorded
before the plan branch was published.

## Execution handoff

After merge, run the preflight only after supplying the exact dataset root,
legacy manifest, and input contract. The generated decision template remains
`NOT_GRANTED`; it is input to a later external approval and native execution
enablement design.
