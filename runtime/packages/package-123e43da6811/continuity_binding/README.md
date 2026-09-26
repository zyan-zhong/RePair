# Native round continuity adapter

This directory is an isolated implementation candidate. It changes no sealed
V1.6 source, reference capture or historical output. Its tests are synthetic
local interface tests, with zero Provider, Slurm, environment, optimizer or Git
operations. They contribute no Formal rounds or scientific findings.

The adapter is one portion of the existing `NativeRoundDriver`. A caller must
validate the rollout, Analyzer/PRE, independent F0/F1 and conditional training
before accepting a whole-round result. `validate_round_tail` intentionally does
not advertise itself as a complete scientific result validator.

## Minimal NO_TRAIN correction

The copied native `no_training_update.py` retains `NO_TRAINING_UPDATE_V1`, its
existing fields and scientific hash domain. The zero-Benefit default produces
exactly the historical bytes. One additional reason, `PLANNER_SELECTED_NO_TRAIN`,
permits a positive count only with a matching current POST SHA supplied through
the added `planner_no_train_primary_record_sha256` argument. It never zeroes a
Benefit count, creates a candidate or invokes an optimizer.

The constructor is not an acceptance authority. `api.materialize_no_training_update`
first validates the native accepted logical-call record, same-call artifact
location, native POST finalizer, current complete request/attempt, H4.4 execution
plan, verifier hash/count/denominator and PRE linkage. The upstream adapter must
also replay the persisted F0/F1 evidence using H4.4 `verify_plan`; a hash alone
does not establish that evidence was scientifically produced.

Authority: full canonical ledger lines 164077–164087 identify the exact native
handoff and require NO_TRAIN -> Memory -> next. Line 164087 expressly forbids
changing Benefit to zero or training after POST chooses NO_TRAIN. H4.4
`strong_post.py::route_accepted_post_artifact` already permits positive Benefit
with NO_TRAIN and previously stopped at
`PLANNER_NO_TRAIN_WITH_BENEFIT_NATIVE_DISPOSITION_NOT_BOUND`. The new reason closes
that narrow constructor incompatibility. It does not grant training permission.

## Machine-facing fields

Every file reference is exactly `{ "path": absolute_path, "sha256": file_sha }`.
`stage_evidence_refs` comes from the current stage producers' registered index;
it is not an operator-authored science configuration. The adapter rejects aliases,
changed bytes, duplicate JSON keys and conflicting immutable outputs. It does
not scan directories or infer latest versions.

`api.validate_current_post(start, evidence_refs)` and
`api.materialize_no_training_update(start, evidence_refs, sink)` require:

- `execution_plan`: current H4.4 plan, including complete `source_request`.
- `verifier`: current `CURRENT_ROUND_INDEPENDENT_VERIFIER_RESULT_V1`.
- `post_projection`: persisted current projection, including full verifier.
- `post_logical_call`: native `logical_call.json` with ACCEPTED status.
- `post_artifact`: same call directory's `validated_artifact.json`.

`api.close_memory_round_from_refs(start, state_ref, event_refs, sink)` calls
native `MemoryRoundStateV1.from_dict`, `MemoryShadowEventV1.from_dict` and
`close_memory_round_v1`. For validation these references are named
`memory_state`, `memory_shadow_events` (list), and `memory_closure` in
`stage_evidence_refs`. They must be actual current native producer outputs;
this adapter does not invent shadow records from POST text or turn a carry
forward receipt into Memory governance.

`memory_materializer.register_initial_memory_state(start, runtime_ref, sink)`
automatically initializes the current native state from the request's actual
calibrated snapshot; an operator does not author its record bindings.
`materialize_next_memory_runtime(start, state_ref, event_refs, current_runtime_ref,
additional_member_refs, sink)` invokes the native close and snapshot builder /
publisher. New member refs are the current record producer's exact
`record`, `retrieval_key`, `fm1`, `fm2` files. Only identities selected by native
closure are admitted. Missing member artifacts stop before publication. An
unchanged record set lawfully retains the verified current runtime/snapshot;
closure still includes all native Harm/Neutral/Uncertain dispositions.

`api.validate_round_tail(start, result, repo=None)` checks those native artifacts
and the original entry result identities. NO_TRAIN additionally requires
`stage_evidence_refs.no_training_update`. TRAIN requires `PROMOTED` or
`ROLLED_BACK`; the separate training adapter verifies checkpoint/reload/OFF-OFF.

`next_request.materialize_next_request(start, result, governance,
next_inputs_ref, current_binding_ref, sink)` consumes the *already advanced*
native governor object from the owner. It never increments a second counter or
sets a numeric round budget. STOP prevents all new request writes; invalid
attempts remain the owner's bounded retry path.

The `next_inputs_ref` is the existing `ROUND_ROLLOUT_INPUT_REFERENCES_V1` machine
index. Required exact refs are `runtime`, `profile`, `memory`, `train_manifest`.
It may carry the existing rollout's `train_authority`, `resource_plan` and
`engine_profile`. A promoted policy also needs `policy_launch_authority` and
`engine_profile`; the former uses existing
`ROUND_POLICY_NATIVE_LAUNCH_AUTHORITY_V1` fields and its exact `launch_contract`
ref. The native rollout materializer still performs full engine/Slurm contract
validation before execution. Changed weights may not inherit an old runtime
alias. TRAIN_UPDATE and token-budget identities remain campaign-frozen.

The exact Memory runtime contains `active_snapshot_directory`,
`active_snapshot_sha256`, `token_budget_contract_path` and
`token_budget_contract_sha256`. The existing calibrated snapshot loader verifies
the bytes and every resulting record identity must equal native closure's
`next_active_record_bindings`. A snapshot-plan SHA is never a snapshot SHA.

The materializer returns exact refs named `request`, `execution_binding`,
`memory_state`, `input_refs` plus the native `next_request` object. For TRAIN it
also returns `next_creation`, derived using native promotion/next-round APIs.
NO_TRAIN does not fabricate a promotion or OFF/OFF record.

To use the existing entry protocol, add the returned refs to
`result.stage_evidence_refs` as `next_inputs`, `next_execution_binding`,
`next_memory_state`, and conditional `next_creation`; register the current
binding as `rollout_execution_binding`. Set `result.next_request` to the returned
native object. `validate_native_next_request(start, result, next_request,
governance, repo=None)` then replays this materialization read-only. The owner
must first run the full composed scientific validator.

## Verified scope and remaining integration

Focused tests cover native POST/NO_TRAIN, positive Benefit preservation, old
attempt rejection, accepted-call mixing, hash mutation, native Benefit/Harm/
Neutral Memory disposition, promotion/rollback/retention request identities,
native source-binding refresh, governor STOP and invalid-attempt exclusion.
The H4.4 plan/verifier test hashes are produced by the captured `io_utils.py`,
including its final LF; the native domain hashes remain their own contract.

The full fixed-commit source `work/v17/native_bba_full` supplies the current
native dependencies and test fixtures. Two integration tests now use its real
record builder, source-integrity checker, eligibility governor, projections,
snapshot builder/publisher/loader and round close. They cover both retained
snapshot -> next request -> entry revalidation and a new admitted Benefit
record -> changed snapshot -> restart adoption. On Windows only, tests substitute
binary exclusive file writing and skip POSIX directory fsync in the native
publisher; no scientific function is mocked. These tests are synthetic and do
not prove server durability or a live Memory source producer.

The actual Analyzer-to-native source/assembly registration remains a separate
upstream integration point: fixed native `SequenceSourceTaskAccessBindingV1`
requires `TRAIN_MEMORY_SOURCE` and its protected manifest, while fresh rollout
is `TRAIN_UPDATE`. Native `MemorySourcePartitionV1` also has no `TRAIN_UPDATE`
member. The only native calibrated-snapshot record kind is
`ProceduralFailureMemoryRecordV1`; its assembly contract requires
`SEQUENCE_FAILURE_EXPERIENCE_V1` sources. Component ingress ports do not provide
an alternative snapshot record kind. `ApplicabilityBoundarySetV1` also requires
actual activation and release/termination clauses, which the accepted Analyzer
repair schema does not currently supply for every repair.

The adapter does not relabel the partition, invent clauses, emit synthetic
current shadow events, or use the historical human-stamped assembly producer
unchanged. Ledger V139-3 and V141-8 require actual producer identities. Current
TRAIN_UPDATE source typing, Strong-authored typed applicability and verifier-bound
event production need an explicit minimal upstream integration design. No new
Memory source schema or scientific field is introduced in this candidate.
An empty event list is legal only when the upstream producer has established
that the current registration is complete; accepting an arbitrary empty list
does not prove completion. Automatic current-round event production, TRAIN
end-to-end, a live campaign and server resident are not claimed here.

Run local tests from workspace root:

```text
python -B -m pytest -q -p no:cacheprovider work/v17/continuity_binding/tests
```

`SOURCE_LINEAGE.json` and `no_training_update.patch` identify the unchanged source
and isolated modification. Root package integration must seal this directory and
all native dependencies actually imported, including schema files; this small
lineage record is not a replacement for that complete executable source seal.
