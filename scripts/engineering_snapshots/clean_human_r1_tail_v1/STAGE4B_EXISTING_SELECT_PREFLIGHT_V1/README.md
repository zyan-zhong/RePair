# STAGE4B_EXISTING_SELECT_PREFLIGHT_V1

Offline continuation from an already completed, approved diagnostic training run.
No model weights are loaded. No model/API/environment/optimizer is invoked. No
cluster job is submitted. The source core worktree is verified and left unchanged.
A separate detached worktree holds a narrow, uncommitted SELECT I1 extension.
No commit, push, merge, checkpoint promotion, or lifecycle transition is performed.

## Reuse

- Existing Stage3Z packet reader and clean-pool metadata validator.
- Existing Stage4A plan and initialization-receipt validation.
- Original Generic Training Stage receipt, contract, native-row and order checks.
- Exact original pure formal run-plan and ledger validators (AST-selected from
  SHA-verified original source; no ML imports or rewritten math).
- Existing SELECT identity/profile, episode evaluator and final result audit.
- Existing E1 replicate-seed tuple and BudgetLimits, read from code.

## Narrow extension

The old SELECT factory and its R0 defaults remain intact. New callers must use
`build_select_i1_execution_profile()` AND bind its request-contract SHA into
EpisodeExecutionConfig. I1 calls are built by the existing bound continuation
factory. No dynamic menu enum, response repair, parser change or new episode
loop is added. The existing final SELECT identity audit gains explicit I1 wire
and RAW prompt verification; omitted authority is rejected for I1 artifacts.

Three production files plus one new test are overlaid in the detached worktree.
The original repository, historical data, model snapshots and training output
are not modified. The resulting code is NOT a newly published fixed head.

## Proposed protocol (not execution approval)

Use all entries from the already-bound TRAIN_SELECT metadata, unchanged order,
with the original five E1 replicate seeds. Both T0 and the exact T2 candidate
use the same task/seed grid, I1 + RAW, Memory OFF, Harness OFF and original
BudgetLimits. Counts derive from metadata. This is a NEW evaluation schedule
proposal; the prior training plan froze a pool and interface, not this exact
cell schedule. `protocol_frozen=false`, `live_driver_bound=false` and
`execution_authorized=false` remain visible.

The clean metadata is not passed to the hard-coded strict-134 benchmark loader.
An explicit source-index/local-index crosswalk is provided. SELECT details are
not eligible for Analyzer/Planner repair discovery or policy training. Only
permitted SELECT summaries may cross the selection boundary.

## Run

Use the existing Python 3.12 environment:

    python -B RUN_ALL.py

`current_request.json` contains this invocation's references, not scientific
constants for future rounds. Same exact inputs may be run again; the existing
isolated overlay is verified and reused. Test-log timing may produce another
content-addressed review archive. Unknown changes are never overwritten.

Successful offline completion returns 0 and stops at:
`SELECT_I1_CODE_REVIEW_AND_EVALUATION_PROTOCOL_FREEZE`.
Return 21 reports an exact failed check. No evaluation or training fallback runs.

## Remaining work

Review and fix the scoped code to a new implementation commit, explicitly freeze
the evaluation protocol, bind actual clean task/runtime/identity manifests to the
existing live runner, and authorize execution. Static candidate LoRA serving and
actual request-wire identity need live checks before full evaluation. None of
those steps is claimed complete by this offline packet.
