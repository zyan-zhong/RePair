# S1 Backend Probe Governance Synchronization Design

## Purpose

Synchronize repository governance with the already completed review and merge
of the non-executing `S1_COLLECTOR_BACKEND_PROBE_V1` candidate.

This synchronization records engineering and governance facts only. It does
not authorize backend-probe execution, P1–P20 execution, read-only inventory
execution, ALFWorld execution, model execution, or final collector-backend
approval.

## Immutable bindings

| Field | Frozen value |
|---|---|
| Approved review base | `0c5249bf6bf8c6335e77a791256654bff0f0e01d` |
| Approved review head | `465503d14ee968d2acf23a314c66c65c52260583` |
| GitHub merge commit | `71ff322ecba105521baf2cb4c2d84024529824b9` |
| Candidate commit count | `22` |
| Candidate changed-path count | `143` |
| Latest verified full suite | `477 passed` |
| Candidate tree SHA-256 | `d61493ccbb433babf2fed2a7e749dc483fe2e63bc6d43422048440d84ad96885` |
| Candidate binary SHA-256 | `3f03b30b408e16466981bca1556983bdf709edf065a11d3b15bb626c3032e713` |
| Source manifest SHA-256 | `41f7461ac7ac7213ca13024a7c755a551f9ad0ab363ac46bc414040af3904eb7` |
| Runtime manifest SHA-256 | `4a524d95339afedbdc282a027cc99d388f4e99005f6ad109ff2bc61158effcfc` |
| Code approval decision | `CODE_APPROVED_S1_COLLECTOR_BACKEND_PROBE_V1_CANDIDATE_ONLY` |
| Merge approval decision | `MERGE_APPROVED_S1_COLLECTOR_BACKEND_PROBE_V1_CANDIDATE_ONLY` |

## Scope

The cumulative governance-sync branch changes exactly five paths:

1. this design document;
2. the implementation plan;
3. `configs/protocols/raw_with_menu_v1.json`;
4. `docs/code_map.md`;
5. `docs/experiments/EXPERIMENT_LEDGER.md`.

The implementation commit changes exactly the final three governance paths.

## Machine-state design

`configs/protocols/raw_with_menu_v1.json` gains one machine-readable object at:

```text
governance.current_facts.s1_backend_probe
```

The object records implementation, review, merge, artifact, and execution
states. It must not change the top-level Runtime Core status or any Runtime
Core or execution-profile semantics.

The following states remain frozen:

```text
BACKEND_PROBE_EXECUTION=NOT_APPROVED
READ_ONLY_INVENTORY_EXECUTION=NOT_APPROVED
COLLECTOR_BACKEND_FINAL_APPROVAL=PENDING
SPLIT_AND_ACCESS_V1=NOT_FROZEN
ALFWORLD_EVALUATOR=NOT_IMPLEMENTED
E1_DEV_EXECUTION=NOT_APPROVED
E1_CONFIRMATORY_EXECUTION=NOT_APPROVED
```

## Human-readable design

`docs/code_map.md` gains a section mapping the merged S1 candidate to its
source, test, review, merge, and artifact identities.

`docs/experiments/EXPERIMENT_LEDGER.md` gains an engineering/governance
section. It explicitly records that P1–P20, inventory, ALFWorld rollout,
model calls, and scientific experiments have not occurred.

## Validation

The synchronization is accepted only when all of the following hold:

- the governance branch starts at merge commit
  `71ff322ecba105521baf2cb4c2d84024529824b9`;
- the worktree is clean before implementation;
- a RED governance audit fails before the three governance files are changed;
- the implementation commit changes exactly three paths;
- the cumulative branch changes exactly five paths;
- the full test suite reports `477 passed`;
- Python compileall succeeds;
- native `all`, `unit`, and compile-only `probe-payloads` targets succeed;
- candidate binary SHA-256 remains
  `3f03b30b408e16466981bca1556983bdf709edf065a11d3b15bb626c3032e713`;
- Runtime Core semantics projection remains
  `d3995f96dfb80be4a21ca7955fad5135227cb80338d611e5547c43f7c3d1b471`;
- execution-profile projection remains
  `62478bf6b78a2b0a975604e7fe1f6a1bc5a87713f9f6bd05679f7687f5560829`;
- local and remote governance branch heads are identical after push.

## Merge policy

The governance PR must target `main` and must use **Create a merge commit**.
Squash, rebase, force-push, and direct pushes to `main` are outside the
approved synchronization procedure.
