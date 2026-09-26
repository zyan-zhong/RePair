# V1.23.3N.4.1 — Exact producer fresh-round binding + bounded Git preflight timeout resilience

## Scope

This is a repair of the exported V1232K producer at its current-round request boundary, not a replacement rollout implementation or a max-10 release. It consumes the actual N.3 export-reviewed source and the server's immutable authorities. It does **not** use N.2's 41-file proposed copy set.

The original shard fatal receipt is read at the exact path declared by the producer:
`<failed-root>/shards/<gate-id:04d>/PCHSI_V1232S_SHARD_FATAL_V1.json`.
Recovery is eligible only when it proves the failed input is the missing, registered source capsule, before any allocation preflight, schedule assignment, service probe, cell execution, or shard terminal. Another missing-file cause stops without submitting.

## Reused code and minimal changes

Unchanged: `formal_rollout_support.py`, `safe_io.py`, `shard_math.py`, `submission_contract.py`, the evaluator/runtime in the existing execution worktree, and `vendor/V1232Q`.

Modified original modules: `producer/shard_worker.py`, `producer/global_finalize.py`. One new shared helper, `producer/fresh_round_contract.py`, binds both to the same native current request and attempt identity. Original worker rejected ordinal zero; original finalizer used the capsule's old round and unrebound schedule. The new path uses the current independently validated request, preserving the capsule bytes and control hashes. Positive ordinals use the same native identity builder in both modules. No ordinal is silently incremented.

The native finalizer also exports the actual attempt-bundle path from the already-published root and execution ID, instead of a null projection. This does not copy or create old outcomes.

## Input/output boundary

Only current request bytes and an explicit new shard plan/runner are written to a separate infrastructure recovery root. The original capsule remains at its SHA-bound path. Its archive inventory is reviewed and rechecked before submission. Old root logs, cell terminals, service readiness, probes and attempts are never reconstructed into the new root. Each shard generates its own allocation/service evidence and evaluator results.

The current R2 request, parent policy, Memory snapshot/runtime, TRAIN_UPDATE manifest/seed, token budget, execution profile, shard assignment/resource plan and scientific attempt ordinal remain unchanged. New infrastructure output root is separate; no new scientific round is counted. This compatibility path deliberately requires the current request's input fingerprints to match the registered capsule. It is **not** a general recipe for a later promoted policy; a changed policy/Memory requires native fresh authority generation.

## Before submitting

1. Verify registered producer source hashes against the uploaded evidence.
2. Verify current/previous runner, request and plan bindings.
3. Read the exact original fatal JSON and prove no original scientific work was started.
4. Verify capsule SHA/inventory and native execution worktree HEAD/source equality.
5. In an isolated CPU process call the **native** request class, task-manifest loader, schedule builder, execution-attempt identity and allocation-contract builder. This validates actual registered task-file hashes, not toy production inputs. No model load/environment/API call.
6. Call the existing V1232Q discovery and native API preflight, without invoking its `main`. Pin that Analyzer worktree until entry.
7. Require predecessor array inactivity from exact queue/accounting and gate-cancellation evidence. Never demand independent accounting rows for cancelled uninstantiated siblings.

## Execution

After uploading the ZIP and selecting the registered Python:

```bash
PCHSI_PYTHON="$PCHSI_PY" bash ./RUN_RECOVER.sh \
  --round-tail-state-root "$ROUND_TAIL_ROOT" \
  --watch-timeout-seconds 86400 \
  --analyzer-timeout-seconds 21600 \
  --execute-if-safe
RC=$?
echo "N4_1_LAUNCH_RC=$RC"
```

Timeout values are startup control limits, not source-compiled scientific budgets. `--native-preflight-timeout-seconds`, `--poll-seconds` and `--publication-grace-seconds` are optional engineering limits. Omit `--execute-if-safe` for preflight only.

One submission intent is durably created before `sbatch`; an intent without a receipt cannot be resent. Same READY/receipt is adopted on repeat. A round-tail owner prevents a second independent patch/settings root from submitting the same scientific request. The array is submitted held/no-requeue using the original resource argv builder; the monitor starts and owns the first gate release. Siblings are released by the original worker's scientific gate.

The detached monitor records a JSON heartbeat per configured poll in `resident.log` and `RECOVERY_STATUS.json`. It reacts to durable gate/finalizer failure, requires the **global terminal plus valid handoff** before Analyzer entry, and uses queue emptiness only with a publication grace. It never resubmits. A failed monitor spawn triggers cancellation of its newly submitted held array. Unresolved/ambiguous control state is terminal, not an invitation for manual retry.

## Status (observation only, not needed to advance execution)

```bash
PCHSI_PYTHON="$PCHSI_PY" bash ./RUN_STATUS.sh --round-tail-state-root "$ROUND_TAIL_ROOT"
```

Useful states:

- `NATIVE_PREFLIGHT_PASS_NO_SUBMISSION`: preparation only.
- `NATIVE_PRODUCER_RECOVERY_SUBMITTED_HELD_RESIDENT_STARTED`: submission/resident launch, **not** rollout success.
- `WAITING_FOR_NATIVE_SCIENTIFIC_HANDOFF`: monitor is active; no manual observer is required.
- `R2_VALID_ROLLOUT_AND_ANALYZER_LOCAL_PREP_COMPLETED`: valid rollout and V1232Q local-wave/group-prep completion only.
- `R2_VALID_ROLLOUT_ANALYZER_TYPED_TERMINAL_NO_RESEND`: valid rollout; existing Analyzer returned nonzero, preserved without another provider entry.
- failure/deadline states: terminal/no resubmission; retain all exact receipts.

## Important autonomy/claim correction

Actual V1232Q code stops after local-wave/group preparation and may return 20 on censored sources. It writes a next-stage pointer but does not execute the entire G-A2/G-A3/C/P/X/PRE/POST/TRAIN chain. This package never labels Q completion as a complete hierarchical Analyzer or full campaign release.

Existing full-tail modules must be integrated with current evidence in the durable orchestrator; software TRAIN/NO_TRAIN/Memory/stop/recovery routes need integration tests before max-10 release. No synthetic test is a scientific Benefit. Current canary's Memory carry-forward is not full negative/neutral cross-round Memory governance. Strategy-aware task-policy gradient and OFF/OFF improvement remain empirically unproven.

`FULL_MAX10_AUTONOMOUS_CAMPAIGN_RELEASED=false` throughout. This package does not change the server Git worktree, main/integration refs, policy parameters, Memory content, or R1 scientific evidence. Runtime task/provider work is performed only by the explicitly executed existing rollout and Analyzer paths after preflight. No F0/F1/PRE/POST rerun is triggered here.

## Verification limits

Whole-package tests include unchanged V1232Q tests, native request/schedule/finalizer integration on isolated synthetic task fixtures, actual original worker missing-capsule publication, and control lifecycle tests with mocked scheduler/provider boundaries. All server dependencies are revalidated live before submission. No server GPU/provider execution or complete repository-wide regression was performed in the artifact-building environment.


## N.4.1 bounded Git preflight timeout resilience

Server N.4 reached the native CPU preflight and then timed out on the exact read-only command `git -C <registered-worktree> status --porcelain=v1 --untracked-files=all`. No Slurm submission or scientific rollout was started by that invocation. Historical V181/V1.31 already froze the project pattern for slow-filesystem Git preflight timeouts: preserve the acceptance criterion and exact argv, retry once only after a timeout, then fail closed.

N.4.1 applies that pattern only to the native worktree-status check. The current N.4 initial timeout remains 120 seconds; the bounded second timeout is 180 seconds from `audit/GIT_PREFLIGHT_TIMEOUT_RESILIENCE_V1.json`. Ordinary Git failures are never retried. Producer, request, schedule, Memory, TRAIN_UPDATE, F0/F1, Analyzer, training, and campaign semantics are unchanged.

## N4.2 runtime-surface preflight correction

N4/N4.1 incorrectly generalized the historical repository cleanliness gate into
`git status --porcelain=v1 --untracked-files=all` over the entire historical
worktree. The canonical V1.31 history instead froze a bounded untracked-runtime-
surface scan (`git ls-files --others --exclude-standard -- <runtime surfaces>`)
with one identical-argv retry only on timeout.

N4.2 restores that boundary and applies the same validator in both the CPU
preflight and the actual shard worker. Tracked changes are checked only under the
registered producer runtime surfaces; five capsule-bound critical sources are
also byte-compared against the registered input capsule. Files outside the
producer runtime surfaces are not used to decide scientific execution
readiness. This does not relax policy/Memory/request/schedule/capsule identities
and does not itself prove live R2 recovery.

## N4.3 native request-hash repair

Server N4.2 reached the native `RoundRolloutCollectionRequestV1` constructor and
failed with `request SHA mismatch` before any new Slurm submission.  Review of
the original V1233I next-round builder and the exact current request proved a
single serialization-integrity defect: V1233I used plain SHA-256 of the
canonical request payload, while the native contract uses the domain-separated
`ROUND_ROLLOUT_COLLECTION_REQUEST_V1` hash.  All non-hash request fields match
the intended R2 authority.

N4.3 does **not** overwrite the immutable V1233I request.  In a new recovery
root it imports the native request class from the already-registered execution
worktree, after the bounded runtime-surface preflight, and permits repair only
when the source embedded hash exactly equals the registered V1233I legacy
plain-hash pattern.  The canonical request is reconstructed with the native
class, and every field other than `request_sha256` must be identical.  Unknown
hash failures remain fail-closed.

The repair receipt records source/canonical file hashes, embedded hashes, round,
execution-attempt, policy, Memory and TRAIN_UPDATE preservation.  Worker,
finalizer and monitor consume only the canonical repaired copy.  The original
request and V1233I history remain immutable.

The Strong Analyzer credential path is not hard-coded by this recovery.  The
existing cognitive-runtime manifest remains the credential authority; the
current project manifest's historical loader points to the existing server
secret loader.  Provider entry occurs only after a valid fresh R2 rollout.

`FULL_MAX10_AUTONOMOUS_CAMPAIGN_RELEASED=false` remains mandatory.  Durable
Gate-2 consolidation must replace the V1233I ad-hoc request hash builder with
the native request contract so later rounds never need this compatibility
repair.
