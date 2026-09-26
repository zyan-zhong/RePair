# G0 Merged E1 Runtime Core Governance Synchronization Design

## Status

This design is approved under the external decision:

`DESIGN_APPROVED_G0_MERGED_RUNTIME_CORE_GOVERNANCE_SYNC`

Stable formal names are used throughout this document. Conversational
design-version suffixes are not repository protocol identifiers.

## Purpose

G0 synchronizes the repository governance state with facts that have
already occurred:

- the E1 Runtime Core cumulative code review passed;
- `CODE_APPROVED_E1_RUNTIME_CORE_V1` was granted externally;
- `MERGE_APPROVED_E1_RUNTIME_CORE_V1` was granted externally;
- PR #9 was merged using a merge commit;
- the merged Runtime Core does not authorize experiment execution.

G0 changes governance metadata only. It does not change Runtime Core
semantics, execution-profile semantics, split membership, evaluator
logic, model behavior, or experimental results.

## Immutable evidence binding

| Evidence item | Immutable value |
|---|---|
| G0 branch base | `1ce3622b3b247c44e962a6b98eb78192f724580b` |
| Approved review base | `b079f2b3696fb6525353a6694be2bb78ee8d027a` |
| Approved review head | `85e102b46a9bb09b92f1d8d39edcaee5bd9aa7d7` |
| Runtime Core merge commit | `1ce3622b3b247c44e962a6b98eb78192f724580b` |
| Code approval decision | `CODE_APPROVED_E1_RUNTIME_CORE_V1` |
| Merge approval decision | `MERGE_APPROVED_E1_RUNTIME_CORE_V1` |
| Verified test result | `271 passed` |
| Runtime semantics projection SHA-256 | `d3995f96dfb80be4a21ca7955fad5135227cb80338d611e5547c43f7c3d1b471` |
| Execution profile projection SHA-256 | `62478bf6b78a2b0a975604e7fe1f6a1bc5a87713f9f6bd05679f7687f5560829` |

The approval-decision strings record completed external decisions. They
are evidence labels, not self-authorizing execution tokens.

## Current stale state

The merged configuration still records the pre-merge candidate state:

- `status = runtime_core_implemented_pending_code_approval`
- `governance.current_status = runtime_core_implemented_pending_code_approval`
- `cumulative_code_approval = pending`
- `merge_status = not_merged`
- `runtime_core_implementation = implemented_on_candidate_branch`

These values no longer describe the repository after PR #9 was merged.

## Target machine state

The exact target top-level status is:

`runtime_core_code_approved_execution_not_approved`

The following values must be identical:

- `status`
- `governance.current_status`

The target `governance.current_facts` values are:

- `runtime_core_implementation = implemented_on_main`
- `task_level_review = passed`
- `cumulative_code_approval = approved`
- `merge_status = merged`
- `approved_review_base = b079f2b3696fb6525353a6694be2bb78ee8d027a`
- `approved_review_head = 85e102b46a9bb09b92f1d8d39edcaee5bd9aa7d7`
- `runtime_core_merge_commit = 1ce3622b3b247c44e962a6b98eb78192f724580b`
- `code_approval_decision = CODE_APPROVED_E1_RUNTIME_CORE_V1`
- `merge_approval_decision = MERGE_APPROVED_E1_RUNTIME_CORE_V1`

The following facts must remain unchanged:

- `split_and_access_v1 = not_frozen`
- `alfworld_evaluator = not_implemented`
- `e1_dev_execution = not_approved`
- `e1_confirmatory_execution = not_approved`

## Audit-contract transition

The exact target trace-contract status is:

`audit_contract.runtime_core_trace_contract.status = implemented_on_main_code_approved_execution_not_approved`

The following values must remain unchanged:

- `audit_contract.fake_environment_integration.status = test_only_implemented`
- `audit_contract.future_evaluator_contract.status = not_designed`
- `audit_contract.future_evaluator_contract.schema = null`

The following Runtime Core trace-contract facts must also remain
unchanged:

- source module;
- source types;
- Task 5 commit;
- ActionTrace consistency-correction commit;
- counter-lineage fields;
- historical-constructor compatibility;
- `tested_to_dict_output` as the source of truth.

## Allowed implementation scope

The G0 implementation may modify exactly these three files:

- `configs/protocols/raw_with_menu_v1.json`
- `docs/code_map.md`
- `docs/experiments/EXPERIMENT_LEDGER.md`

The design and implementation-plan documents are preparatory artifacts
and are committed separately before the three-file implementation.

G0 must not modify:

- `src/`;
- `tests/`;
- `data/manifests/`;
- `configs/data/`;
- ALFWorld data or source files;
- model files;
- Runtime Core policy semantics;
- execution-profile semantics.

## Status consistency requirements

The implementation must prove:

`status == governance.current_status == runtime_core_code_approved_execution_not_approved`

The existing allowed transition from:

`runtime_core_implemented_pending_code_approval`

to:

`runtime_core_code_approved_execution_not_approved`

must remain present.

That transition must continue to require externally bound immutable
code-review evidence.

G0 must not transition directly to:

- `split_and_access_v1_frozen_pending_execution_approval`;
- `e1_dev_execution_approved`.

## Approval evidence requirements

The configuration may record the completed code-approval and
merge-approval decisions together with their immutable review and merge
commit bindings.

The configuration must continue to state:

- approval decisions are external;
- approval evidence must bind exact commits.

Recording approval evidence must not authorize evaluator execution,
model execution, smoke execution, E1-Dev, or E1-Confirmatory.

## Hash invariants

The whole-document configuration SHA-256 must change because governance
metadata changes.

The Runtime Core semantics projection must remain unchanged and retain:

`d3995f96dfb80be4a21ca7955fad5135227cb80338d611e5547c43f7c3d1b471`

The execution-profile projection must remain unchanged and retain:

`62478bf6b78a2b0a975604e7fe1f6a1bc5a87713f9f6bd05679f7687f5560829`

The hash-scope partition must remain:

- pairwise disjoint;
- complete over all top-level keys;
- free of unknown top-level keys;
- free of unclassified top-level keys.

G0 does not emit new runtime or execution-profile hashes into traces. It
only verifies the existing projection definitions and external evidence.

## Code Map requirements

`docs/code_map.md` must move from candidate-branch language to merged
implementation language.

It must record:

- Runtime Core code approval is complete;
- PR #9 merge is complete;
- merge commit is `1ce3622b3b247c44e962a6b98eb78192f724580b`;
- the latest verified suite is `271 passed`;
- `SPLIT_AND_ACCESS_V1` is not frozen;
- the ALFWorld evaluator is not implemented;
- execution is not approved.

It must not describe the Runtime Core as:

- an active ALFWorld evaluator;
- an active production deployment;
- an execution approval.

## Experiment Ledger requirements

`docs/experiments/EXPERIMENT_LEDGER.md` must continue to separate
engineering facts from experiment facts.

The engineering and governance section must record:

- Runtime Core merged into `main`;
- cumulative code approval completed;
- merge approval completed;
- `271` tests passed;
- `SPLIT_AND_ACCESS_V1` not frozen;
- ALFWorld evaluator not implemented;
- E1-Dev execution not approved;
- E1-Confirmatory execution not approved.

The E1 experiment row must remain:

`Not executed`

No success rate, model-capability claim, failure taxonomy, badcase
conclusion, or rollout result may be inferred from the Runtime Core
merge.

## Validation requirements

The G0 implementation plan must include:

1. strict JSON parsing with duplicate-member rejection;
2. exact branch-base and clean-worktree preconditions;
3. exact three-file worktree and staged scope;
4. exact current-state-to-target-state assertions;
5. verification that non-G0 governance facts remain unchanged;
6. Runtime Core semantics projection equality before and after;
7. execution-profile projection equality before and after;
8. hash-scope partition verification;
9. Code Map semantic assertions;
10. Experiment Ledger semantic assertions;
11. `git diff --check`;
12. fresh full regression with exactly `271 passed`;
13. `python -m compileall -q src tests`;
14. immutable post-commit SHA-256 evidence for all modified files;
15. remote branch equality verification after push;
16. PR review and merge-commit-only enforcement.

## Commit and merge policy

The implementation commit title is:

`Resynchronize merged E1 Runtime Core governance`

The implementation must be a new commit. It must not amend, rebase, or
rewrite Runtime Core history.

The G0 pull request must target `main`.

The only allowed merge strategy is:

`Create a merge commit`

The following are forbidden:

- squash merge;
- rebase merge;
- force push;
- direct push to `main`.

## Explicit non-goals

G0 does not:

- freeze `SPLIT_AND_ACCESS_V1`;
- create a split or data manifest;
- enumerate ALFWorld data;
- run a read-only inventory collector;
- design or implement an evaluator;
- call `env.reset()` or `env.step()`;
- call a model;
- run a smoke evaluation;
- authorize E1-Dev or E1-Confirmatory;
- modify Runtime Core behavior;
- create an experimental result.

## Completion criteria

G0 is complete only after:

1. this design document is reviewed;
2. the implementation plan is reviewed;
3. the exact three-file implementation is completed;
4. all validation checks pass;
5. the implementation commit is pushed;
6. the G0 pull request is reviewed;
7. the pull request is merged using a merge commit;
8. post-merge `main` verification passes.

Only after G0 is merged may the project begin design and review of the
read-only S1 inventory collector.
