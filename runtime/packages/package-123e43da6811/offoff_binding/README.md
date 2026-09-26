# Current native OFF/OFF execution adapter

This candidate reuses fixed-bba native SELECT condition/runtime/identity types,
I1 profile, Stage0 `_recover_or_execute_cell`, `run_single_episode`, artifact
publisher/loader, Stage4E identity/publication audits and Stage0 paired numeric
aggregation. It does not implement a new evaluator, scoring rule or promotion
criterion. No sealed reference source is edited. The two historical operational
run labels are adapted using the same exact-anchor method as Stage4D; actual
parent/candidate weights remain separate, content-verified native identities.

## Callable interface

The owner supplies source refs to `Native.load(native_repo_root, source_refs)`.
Every ref is `{path: absolute_path, sha256: file_bytes_sha256}`. `REQUIRED` lists
direct source dependencies; the owner must register/seal the complete imported
native source and schema closure, including this adapter and current rule source.
There is no server/worktree/latest-version discovery.

`materialize(native=..., request_ref=..., parent_ref=..., candidate_ref=...,
protocol_ref=..., infrastructure_ref=..., sink=...)` validates the current
request and source bytes, constructs native condition/runtime/schedule documents,
and returns a `CURRENT_NATIVE_OFFOFF_EXECUTION_BINDING_V1` file ref. Repeating the
same materialization adopts identical bytes; conflicting outputs are rejected.

`execute_binding(binding_ref, host='127.0.0.1', port=allocated_port)` runs inside
the owner's existing authorized Linux allocation. It starts and owns one local
vLLM process with current static LoRA registrations, uses both native arms on the
same complete task/seed grid, and shuts down only its own child. It submits no
scheduler jobs. The module CLI exposes these same arguments as `--binding`,
`--binding-sha256`, `--host`, and `--port`; the owner sets Python's import paths to
the sealed V17 adapter and fixed native `src` directories. The CLI requires an
explicit `--mode single`, `--mode worker`, or `--mode finalize`.

Published cells are read and audited. Started, staged, or terminal attempts
without a published scientific artifact stop without an automatic resend. Any
existing higher attempt ordinal requires the separately registered recovery
path. Missing cells are never treated as failures. Native detailed/task-level
evidence remains under `restricted/`; only the aggregate is suitable for the
planner's TRAIN_SELECT summary boundary.

## Exact machine input fields

The current native rollout request is unmodified. Parent/candidate policy binding
objects have `policy_id`, `kind` (`BASE_MODEL` or `LORA_ADAPTER`),
`artifact_sha256`, `artifact_root`, `artifact_manifest` ref,
`base_model_repository`, and `base_model_revision`. The real manifest has its
native finite `files` map of `{size_bytes, sha256}`. LoRA additionally requires
`logical_condition_id`, `checkpoint_instance_id`, `training_seed`, `adapter_rank`,
`training_run_id`, and `training_config_ref`. A candidate also binds current
`round_id`, `execution_attempt_id`, `request_sha256`, `parent_policy_id`, and
`parent_policy_artifact_sha256`; its artifact must differ from its parent.

A current clean base uses `runtime_ref` pointing to the real
`CLEAN_PI0_LIVE_RUNTIME_BINDING_V2`. Its `policy_runtime_manifest_sha256` remains
the current policy artifact identity; it is **not** replaced by the runtime file
SHA or base manifest file SHA. `derive_clean_parent_policy` consumes current
request/runtime/profile refs and reuses
`training_binding.clean_base.derive_clean_parent_metadata` to locate the existing
base manifest. Original Stage4A `verify_clean_base` verifies the actual clean
snapshot. The historical training profile supplies only registered base/code
provenance through that existing helper, never a historical dataset or recipe.

The frozen protocol ref supplies `access_class='TRAIN_SELECT'`,
`memory_state='OFF'`, `harness_state='OFF'`, `protocol_frozen=true`,
`benchmark_feedback_authorized=false`, `primary_statistical_unit='unique_task'`,
`task_access_ref`, ordered `task_ids`, `replicate_seeds`,
`policy_request_schema_sha256`, `raw_protocol_sha256`, `runtime_core_commit`,
`evaluator_commit`, `design_merge_commit`, `promotion_rule_ref`, and explicit
`episode_budget` fields `max_policy_attempts`, `max_environment_steps`,
`max_consecutive_nonexecuted_attempts`. The task-access ref is an actual native
`DISTILLATION_TASK_ACCESS_MANIFEST_V1` restricted to train SELECT_SUMMARY_ONLY.
No heldout task may enter. Seeds and I1 identity must be supported by the native
evaluator; the adapter imposes no new numerical science defaults.

The infrastructure ref supplies `base_policy_ref`, `environment_runtime_ref`,
`gamefile_identity_ref`, and `server_runtime_parameters`: all native
`SelectServerRuntimeManifestV1` fields except `static_lora_registry`. The registry
is mechanically built from the actual policy bindings. Native vLLM, rank, dtype
and parallelism constraints remain enforced by the original native constructor.

## Promotion boundary and remaining server registration

Original `freeze_promotion_decision` validates a supplied disposition; it does
not choose one from success rates. Stage4C's historical protocol is diagnostic
and contains no formal promotion threshold. Stage4E's existing diagnostic
ROLLBACK function cannot stand in for a Formal rule.

The exact `promotion_rule_ref` must therefore identify the independently frozen
existing rule and its registered producer: `decision_rule_id` and
`decision_producer={source_ref, entrypoint}`. The referenced source must be in the
owner's registered source set. Its callable receives `frozen_rule` and `aggregate`
and returns exactly `{decision, decision_rule_id}`. This dispatcher supplies no
fallback threshold, default verdict or new scientific algorithm. The producer
is resolved before any outcomes are read. Only PROMOTE/ROLLBACK currently map to
the original entry's trained-round terminal contract; HOLD is not silently
renamed. Native promotion then binds the actual aggregate and current policies.

The repository/ledger sources examined so far do not identify an executable
Formal decision criterion. Live invocation must receive that exact registered
source before this chain can be declared server-ready. Current server protocol,
artifact and engine refs also remain owner integration inputs; tests do not
establish their availability or authorize deployment.

## Verification

Run `python -B -m pytest -q -p no:cacheprovider work/v17/offoff_binding/tests`.
Fixtures exercise base and LoRA parents, actual changed adapter bytes, current
attempt rejection, frozen grid, interrupted-attempt rejection, registered-rule
dispatch and native promotion freezing. One integration fixture calls the real
Stage0 cell runner, original I1 evaluator, original publisher, original attempt
loader and original full SELECT/publication audit, then resumes without another
environment call. Environment, HTTP and tokenizer use explicit native test
doubles. On Windows only, test shims implement binary writes/rename and skip
POSIX locks/directory fsync. No scientific evaluator/auditor is mocked. These are
local fixtures, not live policy evaluation or evidence of campaign improvement.

## Registered parallel execution

Parallel invocation follows the registered Stage4D partition rather than placing
the 1,775-pair grid into one short GPU job. `parallel.materialize_parallel` takes
the current native binding ref and sink, revalidates its current inputs, loads
the exact Stage4E config's array_policy and original Stage4D partition_ordinals,
and freezes all four shard assignments. The required native source set includes
that config and Stage4D __init__/contract/parallel sources.

`python -m offoff_binding --mode worker --binding PARALLEL_JSON
--binding-sha256 SHA --shard-id N --resumption-ordinal 0 --host 127.0.0.1
--port PORT` runs one shard inside the resident owner's one-GPU allocation.
The original registered worker budget is 11,700 seconds, with a stop only at a
paired boundary. The independent receipt roots avoid concurrent append writers.
Resume ordinal 1 requires the prior explicit graceful-partial status; an
unfinished STARTED operation or failed/incomplete episode is never resent.
The scheduler owner described below also requires the original scheduler
COMPLETED/0:0 status before submitting this single allowed resumption. No task,
seed or recipe changes occur.

`--mode finalize --binding PARALLEL_JSON --binding-sha256 SHA` requires all four
shards complete and reloads every actual native attempt/publication, performs the
original Stage4E identity audits and full grid checks, then uses the original
paired aggregate and registered frozen promotion producer. It creates no model
server or episode. `--mode single` is retained for explicitly sized allocations.
The real historical Stage4C protocol is frozen but diagnostic and not promotion
eligible; it contains no formal criterion. Nothing in this adapter upgrades that
historical authority or supplies a delta/CI threshold.

## Current asset projection and scheduler owner

`registered_inputs.materialize_registered_inputs(registration=..., request_ref=...,
parent_ref=..., candidate_ref=..., current_runtime_ref=..., sink=...)` consumes
`deployment.offoff_source_registration`. That registration contains
`native_repo_root`, `source_refs`, `code_source_ref`, `promotion_rule_ref`, and
exact `assets` refs named `historical_protocol`, `binding_identity`, `task_access`,
`server_runtime`, `environment_runtime`, `gamefile_identity`, `raw_protocol`, and
`tokenizer_identity`. The code-source receipt must register the fixed commit and
tree; its original capture paths are not runtime discovery inputs. Historical
semantic hashes use the original readiness module's compact JSON domain, while
file refs always use raw file bytes. The helper checks the original protocol
grid, native SELECT-only task access, I1/tokenizer/base identity and frozen rule
source, then publishes current protocol/infrastructure refs. Historical candidate
identity and its diagnostic disposition are not reused as current authority.

`entry.offoff_job.execute_current_offoff_job(start=..., current_inputs_ref=...,
trained=..., output_root=..., deployment=...)` calls the actual accepted-candidate
publisher, projects these registered inputs, freezes the native four-shard
binding and runs the original Stage4A submit-once owner. It returns
`terminal_ref`, `next_policy_input_refs`, and `current_parent_context`. The
operational Python and submit owner come from `training_source_registration`;
the native array policy supplies partition, walltime, worker budget and the one
allowed graceful resumption. Queue/accounting reads select only the exact root
job, and only COMPLETED/0:0 plus the exact native graceful-partial status permit
resumption. An ambiguous submission, failed job or interrupted cell cannot be
resent automatically.

Each job persists its registered `rollout_settings.watch_timeout_seconds`
deadline; the deployment must allow the native 03:30:00 allocation and queue
time. Terminal/stop files use atomic publication. A persisted owner stop is
reused before further scheduler operations, and worker bootstrap failures also
publish a stop. On error, containment targets only job IDs in this owner's
immutable submission receipts. Scheduler tests use explicit scheduler-only
fixtures and submit no real jobs.

`execute.validate_completed_offoff_terminal(terminal_ref)` reloads the recorded
ordinal-to-execution-root map and repeats the native full cell/publication audit,
aggregate, registered rule and terminal identity checks. The entry recovery path
also re-reads the accepted training output and actual adapter manifest through
the candidate publisher. Recovery performs no new training or episode calls.
