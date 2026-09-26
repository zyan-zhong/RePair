# G0 Merged E1 Runtime Core Governance Synchronization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Synchronize the merged E1 Runtime Core governance state with the completed code approval and PR #9 merge without changing Runtime Core or execution-profile semantics.

**Architecture:** G0 is a metadata-only state transition. A strict read-only RED audit first proves that the three committed governance artifacts still contain the stale pre-merge state. The implementation then changes exactly the machine protocol, Code Map, and Experiment Ledger, verifies that both semantic projections are unchanged, and preserves all execution prohibitions.

**Tech Stack:** Python 3.12 standard library, strict JSON parsing, SHA-256, Git, pytest, compileall, Markdown.

## Global Constraints

- Branch must be `implementation/split-and-access-v1`.
- G0 branch base is `1ce3622b3b247c44e962a6b98eb78192f724580b`.
- G0 design commit is `b148f6e8820e86e79cf1e35360585ff111cb2055`.
- Approved review base is `b079f2b3696fb6525353a6694be2bb78ee8d027a`.
- Approved review head is `85e102b46a9bb09b92f1d8d39edcaee5bd9aa7d7`.
- Runtime Core merge commit is `1ce3622b3b247c44e962a6b98eb78192f724580b`.
- Code approval decision is `CODE_APPROVED_E1_RUNTIME_CORE_V1`.
- Merge approval decision is `MERGE_APPROVED_E1_RUNTIME_CORE_V1`.
- Runtime semantics projection SHA-256 must remain `d3995f96dfb80be4a21ca7955fad5135227cb80338d611e5547c43f7c3d1b471`.
- Execution profile projection SHA-256 must remain `62478bf6b78a2b0a975604e7fe1f6a1bc5a87713f9f6bd05679f7687f5560829`.
- Implementation may modify exactly three governance files.
- `split_and_access_v1` must remain `not_frozen`.
- ALFWorld evaluator status must remain `not_implemented`.
- E1-Dev and E1-Confirmatory execution must remain `not_approved`.
- Do not amend, rebase, force-push, squash, or directly push to `main`.
- G0 does not access ALFWorld data, call an environment, call a model, or create experiment results.

---

## File Structure

**Preparatory artifacts already committed**

- Design: `docs/superpowers/specs/2026-08-04-g0-merged-runtime-core-governance-design.md`
- Plan: `docs/superpowers/plans/2026-08-04-g0-merged-runtime-core-governance.md`

**Implementation files**

- Modify: `configs/protocols/raw_with_menu_v1.json`
  - Stores the machine-readable governance state and immutable approval evidence.
- Modify: `docs/code_map.md`
  - Describes the Runtime Core as approved and merged, while preserving execution boundaries.
- Modify: `docs/experiments/EXPERIMENT_LEDGER.md`
  - Separates completed engineering governance from the still-unexecuted E1 experiment.

No source or test file may be modified.

---

### Task 1: Prove the merged governance metadata is stale

**Files:**

- Read: `configs/protocols/raw_with_menu_v1.json`
- Read: `docs/code_map.md`
- Read: `docs/experiments/EXPERIMENT_LEDGER.md`
- Evidence only: `$HOME/.cache/pchsi/g0-governance-sync/red-audit.txt`

**Interfaces:**

- Consumes: the three governance artifacts at commit `b148f6e8820e86e79cf1e35360585ff111cb2055`
- Produces: a read-only RED report proving that implementation is required

- [ ] **Step 1: Verify immutable preconditions**

    cd ~/run/sdar_repro/badcase/github_exports/phase-critical-harness-guided-self-improvement

    test "$(git branch --show-current)" = \
      "implementation/split-and-access-v1"

    test "$(git rev-parse HEAD)" = \
      "b148f6e8820e86e79cf1e35360585ff111cb2055"

    test -z "$(
      git status --porcelain=v1 --untracked-files=all
    )"

- [ ] **Step 2: Run the strict read-only RED audit**

    Run a Python standard-library audit that:

    - rejects duplicate JSON members;
    - rejects NaN and Infinity;
    - asserts the current top-level status is
      `runtime_core_implemented_pending_code_approval`;
    - asserts `governance.current_status` has the same stale value;
    - asserts `cumulative_code_approval = pending`;
    - asserts `merge_status = not_merged`;
    - asserts `runtime_core_implementation = implemented_on_candidate_branch`;
    - asserts Code Map still contains candidate-branch language;
    - asserts Ledger still records cumulative approval as pending;
    - prints exactly:

        G0_CONFIG_STALE
        G0_CODE_MAP_STALE
        G0_LEDGER_STALE
        G0_RED_AUDIT_EXPECTED_FAILURE

    - exits with return code `1`;
    - does not modify any file.

- [ ] **Step 3: Prove RED was read-only**

    Capture SHA-256 for the three files before and after the audit.

    Require:

    - before hashes equal after hashes;
    - working tree remains clean;
    - staged tree remains empty;
    - RED return code is exactly `1`;
    - all three stale markers appear exactly once.

- [ ] **Step 4: Record RED evidence**

    Save:

    - branch;
    - HEAD;
    - three file SHA-256 values;
    - RED markers;
    - return code;
    - clean-tree assertion

    to:

        $HOME/.cache/pchsi/g0-governance-sync/red-audit.txt

    Do not commit external evidence.

---

### Task 2: Synchronize the machine protocol governance state

**Files:**

- Modify: `configs/protocols/raw_with_menu_v1.json`

**Interfaces:**

- Consumes:
  - strict current configuration;
  - approved review base/head;
  - Runtime Core merge commit;
  - code and merge approval decisions
- Produces:
  - a strictly valid JSON configuration in the approved merged-but-not-executable state

- [ ] **Step 1: Load and validate the current configuration**

    Use:

        json.loads(
            text,
            object_pairs_hook=strict_object,
            parse_constant=reject_nonstandard_constant,
        )

    Require the exact current stale state before changing anything.

    Capture canonical copies of:

    - every key in `runtime_core_semantics_projection.top_level_keys`;
    - every key in `execution_profile_projection.top_level_keys`;
    - the complete `hash_scope`;
    - `fake_environment_integration`;
    - `future_evaluator_contract`.

- [ ] **Step 2: Apply the exact status transition**

    Set:

        status =
        runtime_core_code_approved_execution_not_approved

        governance.current_status =
        runtime_core_code_approved_execution_not_approved

    Update `governance.current_facts` to:

        runtime_core_implementation = implemented_on_main
        task_level_review = passed
        cumulative_code_approval = approved
        merge_status = merged

        approved_review_base =
        b079f2b3696fb6525353a6694be2bb78ee8d027a

        approved_review_head =
        85e102b46a9bb09b92f1d8d39edcaee5bd9aa7d7

        runtime_core_merge_commit =
        1ce3622b3b247c44e962a6b98eb78192f724580b

        code_approval_decision =
        CODE_APPROVED_E1_RUNTIME_CORE_V1

        merge_approval_decision =
        MERGE_APPROVED_E1_RUNTIME_CORE_V1

    Preserve exactly:

        split_and_access_v1 = not_frozen
        alfworld_evaluator = not_implemented
        e1_dev_execution = not_approved
        e1_confirmatory_execution = not_approved

- [ ] **Step 3: Update the trace audit-contract status**

    Set exactly:

        audit_contract.runtime_core_trace_contract.status =
        implemented_on_main_code_approved_execution_not_approved

    Preserve every other trace-contract field.

    Preserve exactly:

        audit_contract.fake_environment_integration.status =
        test_only_implemented

        audit_contract.future_evaluator_contract.status =
        not_designed

        audit_contract.future_evaluator_contract.schema =
        null

- [ ] **Step 4: Write through a temporary file**

    Serialize using:

        json.dumps(
            config,
            ensure_ascii=False,
            allow_nan=False,
            indent=2,
        ) + "\n"

    Write to a sibling temporary file and use `os.replace()`.

    Do not sort or rename existing top-level keys.

- [ ] **Step 5: Verify semantic projections**

    Canonicalize each projection using:

        json.dumps(
            projection,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")

    Require:

        runtime projection before == runtime projection after

        execution projection before == execution projection after

        runtime SHA ==
        d3995f96dfb80be4a21ca7955fad5135227cb80338d611e5547c43f7c3d1b471

        execution SHA ==
        62478bf6b78a2b0a975604e7fe1f6a1bc5a87713f9f6bd05679f7687f5560829

- [ ] **Step 6: Verify the hash-scope partition**

    Require:

    - runtime keys, execution keys, and non-runtime metadata keys are pairwise disjoint;
    - their union equals the actual top-level key set;
    - there is no unknown or unclassified top-level key;
    - `hash_scope` itself is unchanged.

---

### Task 3: Synchronize the Code Map and Experiment Ledger

**Files:**

- Modify: `docs/code_map.md`
- Modify: `docs/experiments/EXPERIMENT_LEDGER.md`

**Interfaces:**

- Consumes:
  - approved and merged Runtime Core facts;
  - unchanged split/evaluator/execution prohibitions
- Produces:
  - human-readable governance documents consistent with the machine configuration

- [ ] **Step 1: Update the Code Map status table**

    Replace candidate-state wording with a merged implementation table that contains exactly:

        Approved review base:
        b079f2b3696fb6525353a6694be2bb78ee8d027a

        Approved review head:
        85e102b46a9bb09b92f1d8d39edcaee5bd9aa7d7

        Runtime Core merge commit:
        1ce3622b3b247c44e962a6b98eb78192f724580b

        Runtime Core code approval:
        Complete

        Merge approval:
        Complete

        Implementation status:
        Implemented on main

        Latest verified test suite:
        271 passed

        SPLIT_AND_ACCESS_V1:
        Not frozen

        ALFWorld evaluator:
        Not implemented

        Execution status:
        Not approved

    Preserve implementation branch and focused commit history as historical provenance.

- [ ] **Step 2: Update Code Map component wording**

    For parser, prompt, budget, Runtime Core, and ActionTrace:

    - replace candidate-branch status with merged-to-main status;
    - preserve exact focused commit SHAs;
    - preserve all runtime boundaries;
    - do not call fake-environment tests a production evaluator;
    - do not describe the package as an active deployment.

- [ ] **Step 3: Update the Ledger engineering section**

    Record exactly:

        Runtime Core implementation = merged into main
        cumulative code approval = complete
        merge approval = complete
        latest verified suite = 271 collected / 271 passed
        SPLIT_AND_ACCESS_V1 = not frozen
        ALFWorld evaluator = not implemented
        E1-Dev execution = not approved
        E1-Confirmatory execution = not approved
        E1 rollout results = none

- [ ] **Step 4: Preserve the experiment boundary**

    Require the E1 row to remain:

        Not executed

    Require the research conclusion to continue stating that no E1
    rollout, success-rate, model-performance, badcase-taxonomy, or
    failure-mechanism conclusion is available.

- [ ] **Step 5: Reject contradictory wording**

    Fail validation if either document contains any statement equivalent to:

    - split frozen;
    - evaluator implemented;
    - execution approved;
    - E1 succeeded;
    - active production evaluator;
    - rollout completed.

---

### Task 4: Validate and commit the exact three-file implementation

**Files:**

- Modify: `configs/protocols/raw_with_menu_v1.json`
- Modify: `docs/code_map.md`
- Modify: `docs/experiments/EXPERIMENT_LEDGER.md`

**Interfaces:**

- Consumes: Tasks 2 and 3
- Produces: one independently reviewable G0 implementation commit

- [ ] **Step 1: Verify exact worktree scope**

    Require `git status --porcelain=v1` to show exactly:

         M configs/protocols/raw_with_menu_v1.json
         M docs/code_map.md
         M docs/experiments/EXPERIMENT_LEDGER.md

    No source, test, data, manifest, or plan file may be modified.

- [ ] **Step 2: Run strict semantic validation**

    Validate:

    - strict JSON and duplicate-key rejection;
    - exact target status;
    - exact approval and merge evidence;
    - unchanged non-G0 facts;
    - unchanged runtime semantics projection;
    - unchanged execution profile projection;
    - complete hash partition;
    - Code Map merged-state assertions;
    - Ledger engineering/experiment separation;
    - no execution authorization.

- [ ] **Step 3: Run repository verification**

    Run:

        git diff --check

        python -m pytest -q

        python -m compileall -q src tests

    Expected:

        271 passed
        compileall return code 0
        no diff-check output

- [ ] **Step 4: Freeze candidate file hashes**

    Compute SHA-256 for the three modified files and save them in an
    external evidence record under:

        $HOME/.cache/pchsi/g0-governance-sync/

- [ ] **Step 5: Stage exactly three files**

    Run:

        git add -- \
          configs/protocols/raw_with_menu_v1.json \
          docs/code_map.md \
          docs/experiments/EXPERIMENT_LEDGER.md

    Require:

    - staged path set equals the exact three paths;
    - no unstaged changes;
    - staged file SHA-256 equals working-file SHA-256;
    - `git diff --cached --check` produces no output.

- [ ] **Step 6: Create the implementation commit**

    Run:

        git commit \
          -m "Resynchronize merged E1 Runtime Core governance"

    Require:

    - parent is the implementation-plan commit;
    - subject is exact;
    - committed path set is exactly three files;
    - committed file hashes match the frozen hashes;
    - working tree is clean.

- [ ] **Step 7: Re-run post-commit verification**

    Run fresh:

        python -m pytest -q
        python -m compileall -q src tests

    Expected:

        271 passed
        compileall return code 0

---

### Task 5: Push, review, and merge G0

**Files:**

- No additional repository content changes

**Interfaces:**

- Consumes: the reviewed G0 implementation commit
- Produces: a merge commit on `main` and post-merge evidence

- [ ] **Step 1: Push without rewriting history**

    Push:

        implementation/split-and-access-v1

    Forbidden:

    - `--force`;
    - `--force-with-lease`;
    - rebase;
    - amend.

    Verify local and remote branch heads are identical.

- [ ] **Step 2: Create the G0 pull request**

    PR title:

        Resynchronize merged E1 Runtime Core governance

    Base:

        main

    Head:

        implementation/split-and-access-v1

    PR body must bind:

    - design commit;
    - implementation-plan commit;
    - implementation commit;
    - approved Runtime Core review base/head;
    - Runtime Core merge commit;
    - three modified paths;
    - 271-test result;
    - both unchanged projection SHA-256 values;
    - explicit statement that execution remains unapproved.

- [ ] **Step 3: Review the PR**

    Verify:

    - no head drift;
    - only design, plan, and exact three-file implementation commits;
    - no unresolved review threads;
    - no required check failure;
    - no source, test, manifest, or data changes;
    - current state is approved/merged but execution-not-approved.

- [ ] **Step 4: Merge using a merge commit only**

    Use:

        Create a merge commit

    Forbidden:

    - squash;
    - rebase;
    - direct push to `main`.

- [ ] **Step 5: Verify post-merge main**

    Fetch `origin/main` and require:

    - the G0 implementation head is an ancestor of `main`;
    - exactly one new merge commit follows the G0 branch head;
    - the merge commit has the old `main` and G0 branch head as parents;
    - the three governance files match the reviewed G0 implementation tree;
    - `python -m pytest -q` reports exactly `271 passed`;
    - `python -m compileall -q src tests` succeeds;
    - working tree is clean.

- [ ] **Step 6: Freeze G0 completion evidence**

    Record externally:

        G0 design commit
        G0 plan commit
        G0 implementation commit
        G0 merge commit
        three file SHA-256 values
        runtime projection SHA-256
        execution projection SHA-256
        271-test result
        post-merge main SHA

    G0 completion does not freeze `SPLIT_AND_ACCESS_V1` and does not
    approve inventory collection, evaluator execution, smoke, E1-Dev, or
    E1-Confirmatory.
