# Exact Analyzer / PRE / H4.4 adapter

This is an internal stage adapter consumed by the existing first-round and resident operation bindings. It does not create a third top-level binding, scientific framework, model caller, or campaign gate. Reference packages remain unchanged.

## Implemented entry points

```python
from exact_bindings import build_from_rollout_result, build_from_index, immutable_json
from adapter import run_bound_round

binding = build_from_rollout_result(
    rollout_materialization_result,
    source_binding=operation_binding["analyzer_stage"],
    current_index=current_typed_stage_index,
    output_root=round_output / "analyzer",
)
immutable_json(round_output / "ANALYZER_STAGE_INPUT.json", binding)
result = run_bound_round(binding, execute=True)
```

Add this directory to the parent execution process's import path. CLI for the already materialized internal input: `python -B adapter.py --binding ABSOLUTE_FILE --execute`. Omit `--execute` to verify refs and materialize the local registry without invoking scientific executors.

The implemented call chain is Q evidence/unit builders → current native `registry_runner.run_registry` → Q source/group builders → U G/C/P/X execution and validators → X Dynamic PRE V2 builders/finalizer → original H4.4 native capture, `prepare_plan`, and `run_controller`. H4.4 runs in a separate process using its own included native source. Its four historical Z receipt locators and single POST manifest glob are changed in memory to the exact accepted PRE ref and manifest. Source drift rejects the adaptation. Existing H4.4 actor-commit, replay, request-wire, candidate, task, and verifier checks remain active.

The result is `EXACT_ANALYZER_PRE_H44_EXECUTION_RESULT_V1_6`, with exact accepted PRE and H4.4 terminal refs. It explicitly reports `full_campaign_closed: false`. It does not own TRAIN, promotion, Memory update, next-round creation, or max10 completion.

## Automatic input mapping

Refs use `{path, file_sha256}` with original file bytes; rollout materializer refs named `sha256` are converted mechanically. No receipt-graph traversal, filesystem census, latest/mtime lookup, or operator runner choice is used.

| Internal field | Exact source / JSON pointer |
|---|---|
| `state_root` | Rollout materialization `/root` |
| `refs.request` | `/request_path`, `/request_file_sha256`; identity checked against `/round_id`, `/request_sha256` |
| `round_id`, `parent_policy_id` | Verified request `/round_id`, `/parent_policy_id` |
| `refs.handoff` | `/root` + `round_evidence/ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1.json` |
| `refs.global_terminal` | `/root` + `round_evidence/PCHSI_V1232K_GLOBAL_TERMINAL_V1.json` |
| `refs.universe` | `/root` + `round_evidence/ROUND_ROLLOUT_UNIVERSE_SEAL_V1.json` |
| `refs.cohort` | `/root` + `round_evidence/ROUND_FAILURE_COHORT_SELECTION_MANIFEST_V1.json` |
| `refs.bundle_index` | `/root` + `round_evidence/ROUND_SHARDED_ATTEMPT_BUNDLE_INDEX_V1.json` |
| `refs.actor_runtime` | `/root/input_capsule/` + `/input_member_manifest/runtime/member`; SHA from the same row |
| `refs.memory_runtime` | Same mapping at `/input_member_manifest/memory` |
| `refs.train_update_manifest` | Same mapping at `/input_member_manifest/train_manifest`; remains JSONL bytes |
| Remaining current refs | Current finite typed index `/refs`; conflict with mapped rollout refs is rejected |
| Static source/runtime refs and directories | Existing operation's internal `source_binding`; per-round index refs supersede defaults |

The latter source binding is **consumed, not automatically constructed by this module** from all received archives. Its caller supplies `scientific_repo_root`, `analyzer_snapshot_directory`, `train_root`, package refs `q/u/x/h44` (each `{root, manifest:{path,file_sha256}}`), and refs `runtime_manifest`, `experiment_contract`, `role_authority`, `analyzer_token_contract`, `f0f1_protocol`, plus `researcher_view` or a finite `researcher_views` list. This remaining constructor/integration work is not evidence that scientific authority is absent. Optional campaign startup and bounded PRE recovery refs use existing authorized policy; no extra approval flow is introduced here.

Read-only Memory objects do not need an invented `round_id`. The actual request binds their raw file SHA, active snapshot SHA and token contract SHA. Promoted rounds obtain their runtime and Memory refs from their own rollout materialization.

## Verification and limits

16 focused local tests pass: exact refs and immutable outputs, current-round builder, Memory snapshot binding, PRE identity/reuse boundaries, orchestration calls, global-stop behavior, manifest checks for all four reused packages, exact H4.4 locator adaptation, and five original X semantic/recovery fixture checks in an isolated process. The orchestration test uses stage doubles; it does not establish scientific end-to-end execution. `PCHSI_TEST_PACKAGE_ROOT` selects a fresh bundle root; otherwise tests recognize the development or bundle layout.

The actual local `native_bba` capture contains only selected current modules. The deployed registered scientific checkout must supply its Analyzer, Memory, reference-loop, and research-intelligence dependencies. The adapter does not silently merge incompatible checkouts. H4.4's native source remains separately isolated. Source registration and a compatible full checkout must be established by the parent source binding before live invocation.

No provider call, live rollout, native environment execution, H4.4 causal completion, training, or max10 run was performed during this implementation. Existing H4.4 cannot treat zero selected PRE states as scientific NO_TRAIN; the adapter preserves an explicit incomplete boundary there. The external campaign's training recipe and source-binding constructor are outside this adapter. These limitations prevent a claim of complete unattended readiness.
