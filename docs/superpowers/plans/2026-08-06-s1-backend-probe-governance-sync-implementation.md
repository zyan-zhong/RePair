# S1 Backend Probe Governance Synchronization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record the already reviewed and merged S1 backend-probe candidate in machine and human-readable governance without changing runtime behavior or granting execution approval.

**Architecture:** Use three review-preserving commits. The first two freeze the design and implementation plan; the third applies one machine-readable JSON insertion and two append-only Markdown governance sections. External audit code verifies exact paths, immutable hashes, unchanged semantic projections, test results, and closed execution states.

**Tech Stack:** Git, Bash, Python 3.12, JSON, Markdown, pytest, GNU Make, SHA-256.

## Global Constraints

- Base commit must be `71ff322ecba105521baf2cb4c2d84024529824b9`.
- Branch must be `governance/s1-backend-probe-candidate-approval`.
- Cumulative changed paths must equal exactly five frozen paths.
- Implementation commit must change exactly three governance paths.
- `BACKEND_PROBE_EXECUTION=NOT_APPROVED`.
- `READ_ONLY_INVENTORY_EXECUTION=NOT_APPROVED`.
- `COLLECTOR_BACKEND_FINAL_APPROVAL=PENDING`.
- `SPLIT_AND_ACCESS_V1` remains not frozen.
- ALFWorld evaluator remains not implemented.
- E1-Dev and E1-Confirmatory execution remain not approved.
- No P1–P20, inventory, ALFWorld, model, GPU, or rollout execution is permitted.
- Candidate binary SHA-256 must remain `3f03b30b408e16466981bca1556983bdf709edf065a11d3b15bb626c3032e713`.
- Runtime Core semantics projection must remain `d3995f96dfb80be4a21ca7955fad5135227cb80338d611e5547c43f7c3d1b471`.
- Execution-profile projection must remain `62478bf6b78a2b0a975604e7fe1f6a1bc5a87713f9f6bd05679f7687f5560829`.

---

### Task 1: Commit the approved synchronization design

**Files:**
- Create: `docs/superpowers/specs/2026-08-06-s1-backend-probe-governance-sync-design.md`

**Interfaces:**
- Consumes: PR #11 fixed review and merge identities.
- Produces: immutable synchronization requirements for Tasks 2 and 3.

- [ ] **Step 1: Verify the branch and base**

```bash
test "$(git branch --show-current)" =   "governance/s1-backend-probe-candidate-approval"
test "$(git rev-parse HEAD)" =   "71ff322ecba105521baf2cb4c2d84024529824b9"
test -z "$(git status --porcelain=v1 --untracked-files=all)"
```

Expected: all commands return `0`.

- [ ] **Step 2: Write and audit the approved design**

Create the exact design document supplied in the reviewed external work
package. Verify the merge binding and non-execution markers and reject
unfinished placeholder text.

- [ ] **Step 3: Commit**

```bash
git add --   docs/superpowers/specs/2026-08-06-s1-backend-probe-governance-sync-design.md
git diff --cached --check
git commit -m "Design S1 backend probe governance synchronization"
```

Expected: one-file commit.

---

### Task 2: Commit the implementation plan

**Files:**
- Create: `docs/superpowers/plans/2026-08-06-s1-backend-probe-governance-sync-implementation.md`

**Interfaces:**
- Consumes: Task 1 design.
- Produces: exact TDD and verification procedure for Task 3.

- [ ] **Step 1: Write and audit the complete plan**

Create this exact plan from the external work package. Confirm it includes
Task 3 and contains no placeholders.

- [ ] **Step 2: Commit**

```bash
git add --   docs/superpowers/plans/2026-08-06-s1-backend-probe-governance-sync-implementation.md
git diff --cached --check
git commit -m "Plan S1 backend probe governance synchronization"
```

Expected: one-file commit whose parent is Task 1.

---

### Task 3: Synchronize machine and human-readable governance

**Files:**
- Modify: `configs/protocols/raw_with_menu_v1.json`
- Modify: `docs/code_map.md`
- Modify: `docs/experiments/EXPERIMENT_LEDGER.md`

**Interfaces:**
- Consumes: immutable review, merge, artifact, and execution-state facts.
- Produces: machine-readable and human-readable repository governance.

- [ ] **Step 1: Run the RED governance audit**

Run the external audit requiring
`governance.current_facts.s1_backend_probe` and both new Markdown sections.

Expected: exit code `1` before implementation because the records are absent.

- [ ] **Step 2: Insert the machine-readable object**

Load the JSON with Python and insert `s1_backend_probe` under
`governance.current_facts` with the exact frozen review, merge, artifact,
approval, and not-approved execution values.

- [ ] **Step 3: Append the human-readable records**

Append one Code Map section headed:

```text
## S1 Collector Backend Probe merged candidate
```

Append one Experiment Ledger section headed:

```text
## S1 backend-probe engineering and governance status
```

- [ ] **Step 4: Run the GREEN governance audit**

Expected: exit code `0` and marker
`S1_BACKEND_PROBE_GOVERNANCE_SYNC_GREEN`.

- [ ] **Step 5: Run semantic and artifact verification**

```bash
python -m pytest -q
python -m compileall -q src tests scripts
make -C native/s1_backend_probe clean all unit probe-payloads
sha256sum native/s1_backend_probe/build/pchsi-s1-backend-probe
```

Expected: `477 passed`, unchanged candidate binary hash, unchanged Runtime
Core semantics projection, and unchanged execution-profile projection.

- [ ] **Step 6: Verify exact scope and commit**

The implementation diff must equal exactly the three governance files.

```bash
git add --   configs/protocols/raw_with_menu_v1.json   docs/code_map.md   docs/experiments/EXPERIMENT_LEDGER.md
git diff --cached --check
git commit -m "Synchronize merged S1 backend probe governance"
```

- [ ] **Step 7: Post-commit verification**

Re-run the GREEN audit, full pytest, compileall, native build, binary hash,
semantic projections, exact three-file implementation scope, exact
five-file cumulative scope, and clean-worktree check.

- [ ] **Step 8: Push and verify**

```bash
git push -u origin   governance/s1-backend-probe-candidate-approval
git fetch origin   governance/s1-backend-probe-candidate-approval
git rev-list --left-right --count   HEAD...origin/governance/s1-backend-probe-candidate-approval
```

Expected: `0 0`.

Create a PR targeting `main` and merge with **Create a merge commit** only.
