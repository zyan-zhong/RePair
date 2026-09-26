# Source review: Stage4E V1.1 / independent GPU array adapter

## Confirmed defects in V1
- `config.json:allowed_origin_urls` admitted HTTPS and SCP-like GitHub URLs, but omitted the same repository's official SSH-over-443 transport used in historical server push logs. The current server's actual URL must still be read and validated; unknown URLs are not auto-approved.
- `source.ensure_isolated_repo()` cloned and checked out before validating origin. A rejection therefore left a real, clean, unanchored clone. Its next invocation would fail reading `stage4e.anchor`; merely adding a URL was insufficient.
- Publication validated only fetch origin, not an explicit pushurl. V1.1 checks both effective destinations and preserves the approved push transport.
- The old follower waits for one parent job and may resubmit a four-GPU launcher. It is not the correct follower for four independent allocations.

## Targeted corrections
Origin is checked before cloning. Recovery accepts only a clean clone at the exact approved HEAD/tree/branch, with an expected local-clone origin and no conflicting role/push destination. No reset, deletion, force push, or active checkout mutation is used.

Four independent Slurm array elements replace the single gang-scheduled four-GPU job. Each element reuses the unmodified Stage4D V1.3 shard worker and original scientific executor. This is data-parallel scheduling across task-seed pairs, not TP=4. Pair membership is fixed by absolute schedule ordinal modulo four.

A durable scheduling plan records old job, scientific authorization, binding, exact canonical prefix hashes, shard assignments, original package manifest, and new controller manifest. A pending-state-filtered cancellation and terminal accounting recheck precede array submission. Running/requeued/unrelated jobs are never cancelled by this adapter.

Array accounting must include all registered elements; .batch/.extern and the master cannot substitute. Native shard-status files are independently bound to physical job IDs, array IDs, shard IDs, prefix, counts and file hashes. Missing accounting is UNKNOWN with a bounded hold, never PASS. Failed or timed-out jobs are not automatically retried. A single bounded continuation is allowed only for clean graceful partials and only for incomplete shards.

Before consolidation, exact shard receipt sequences must equal their frozen expected sequence, with no extra, missing or duplicated cells. The existing V1.3 consolidate_shards then restores attempt artifacts/publication metadata and canonical receipt chains. The original Stage4E identity audit and aggregate-only projection remain unchanged.

## Preserved modules and contracts
`stage4e/audit.py`, `stage4e/__init__.py`, `stage4e/driver.py`, native tests, and all external Stage4D V1.3 code are preserved byte-for-byte. The new controller calls existing prepare/finalize and native shard/consolidation functions. No original tests are removed or weakened.

## Scope and unresolved evidence
- The local 59-test package suite exercises actual temporary Git clone/publication behavior, exact parsers, local files and scope checks. Scheduler calls are injected in scheduling tests because no cluster is available in this runtime.
- The original Stage4D 18 contract tests are rerun, not described as a full runtime test.
- Native integration here: three tests pass; two stop because the filtered uploaded tree does not contain E1_EPISODE_ARTIFACT_V1. They are not skipped or marked PASS. Server preparation still runs all original native repository tests and all five native integration tests, using the existing Stage4C prerequisite builder.
- No claim is made that the 3550 real cells, actual queued array, runtime GPU isolation, final native regression, or remote publication has executed in this assistant runtime.
- The project remains a clean Human reference round with a diagnostic candidate; this is not proof of effective self-improvement or a fully validated Strong/Local autonomous loop.

## Operating constraints
Existing scientific roots and paths remain unchanged. Added scheduler metadata lives only under the existing execution root. No existing canonical receipt, model, prior failed log, or benchmark is deleted, moved, relabelled or resampled. Runtime cache remains on run storage; no explicit GPU-job CPU/memory request is added. SSH host-key checks are not disabled.
