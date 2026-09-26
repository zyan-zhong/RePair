# Current TRAIN_UPDATE to native Memory

This adapter supplies the previously missing producer identified in
`../analyzer_binding/MEMORY_SOURCE_BOUNDARY_REVIEW.md`. It adds no provider call,
independent Memory store, classifier, promotion rule, or human configuration.
The immutable bba400 native sources and historical V1 source restrictions remain
unchanged on disk. Seven exact native modules receive documented in-memory
compatibility changes; `overlay_receipt()` records their base and adapted hashes.

## Minimal API and schema changes

1. `SequenceSourceTaskAccessBindingV2` records the actual current native request,
   parent policy, TRAIN_UPDATE manifest and exact unique row, task/gamefile,
   attempt and sealed bundle identities. It does not use V1's protected-manifest
   hash or claim `TRAIN_MEMORY_SOURCE`. Existing V1 validation remains strict.
2. Existing L-A0/L-A1 output has required `memory_boundary_registrations`, keyed
   one-to-one to actual errors. The same response carries supported literal
   native applicability conditions, or explicit `UNRESOLVED`. Standard accepted
   local-result bytes keep their original schema; the raw response and logical
   call are retained and revalidated as authority for the extra registration.
3. Native source deserialization accepts the explicit nested V2 schema. The
   three native source-partition enums additionally accept `TRAIN_UPDATE`;
   consumer views require full source provenance for that value. Existing
   reconstruction, assembly, source audit, eligibility, FM1/FM2, five-pair
   classifier, shadow-event disposition, closure and snapshot publisher remain
   their original functions.

Before any native import in the owner:

```python
from memory_binding.worker_bootstrap import bootstrap_current_and_children
bootstrap_current_and_children(registered_scientific_repo)
```

After the original independent H4.4 `verify_plan` replay:

```python
from memory_binding.api import materialize_round_memory
result = materialize_round_memory(
    binding=operation_binding,
    analyzer_output_root=analyzer_root,
    execution_plan_ref=plan_ref,
    verifier_ref=verifier_ref,
    output_root=memory_output,
)
```

All input and returned references use `{path, file_sha256}`. The operation
binding already contains exact request, handoff, TRAIN_UPDATE manifest, Memory
runtime and token-contract references. The tokenizer defaults to the original
native local counter, selected exclusively by the request-bound Memory runtime's
source-runtime authority and token contract. No download or fallback tokenizer
is used. The optional tokenizer argument is for native fixture integration.

Returned `event_refs` are actual typed native shadow events.
`additional_member_refs` contains record/retrieval-key/FM1/FM2 references only for
native eligible `PROMOTE_NEXT_ROUND` records. `new_partition_ref` contains only
those newly promoted lineage bindings. The closure owner merges this map with
`binding.refs.memory_source_partitions`, filters the active lineages using
native closure, and transports the merged map to the next constructor.
`receipt_ref` binds all results and the exact overlay receipt.

UNRESOLVED applicability preserves the actual factual experience and accepted
response/origin references, without inventing a procedural record or event.
Ineligible native assemblies preserve native failure codes and an incomplete
event. Harm, Neutral and Uncertain use the original classifier; they do not gain
active member references. Distinct F0 and F1 evidence projections retain every
registered pair repetition and the complete original verifier reference.
This operation never writes into the active current-round Memory snapshot.

## Worker propagation

`worker_bootstrap.py` exports `worker_environment(repo, base_environment=...)`
for explicit subprocess environments. Its two exact PYTHONPATH entries are this
package's `worker_startup` directory and its parent directory; the exact native
repo is carried in `PCHSI_CURRENT_MEMORY_NATIVE_REPO`. The supplied
`sitecustomize.py` checks the fixed source hashes before any worker code and pins
the `pchsi` namespace to that registered checkout. A rejected startup exits;
Python's normal silent continuation after a sitecustomize exception is avoided.

Normal child/grandchild Python calls inherit this setup. Preserve these variables
when launching Slurm workers (the original calls preserve the inherited
environment); interpreters using `-I`, `-E` or `-S` must explicitly bootstrap.
This changes neither launch resources nor provider/environment execution count.

Exact native consumers:

- Rollout shard calls `pchsi.evaluation.policy_attempt_adapter`:
  `RoundMemoryPolicyAttemptAdapterV1.__init__` loads the calibrated snapshot.
  `dev_snapshot_loader.py` reads governed record/key/FM1/FM2, not raw source
  experience files. These published artifact schemas remain unchanged.
- H4.4 worker/controller children likewise load the current Memory runtime's
  snapshot through the policy attempt adapter. They must inherit the same native
  namespace instead of silently importing a captured older checkout.
- Local/group Analyzer consume native snapshot and consumer views; PRE consumes
  the native Researcher view with the true `TRAIN_UPDATE` partition.
- Materialization/replay parses nested V2 source access through
  `SequenceFailureExperienceV1.from_json`; closure parses native shadow events
  with the added exact source enum. These are the V2-specific reading boundaries.

## Verification and limits

Run from the project root:

```
python -B -m pytest work/v17/memory_binding/tests/test_binding.py work/v17/analyzer_binding/tests/test_source_binding.py work/v16/analyzer_adapter/tests/test_exact_bindings.py -q -p no:cacheprovider
python -B work/v17/memory_binding/tests/run_native_compatibility.py
```

Latest Windows result: **31 passed** (including complete native reconstruction,
accepted same-call output, original five-pair verifier, native record/event,
nonempty retained snapshot plus new member, next Researcher view, process and
grandchild inheritance, negative source/round/pair checks); **123 unchanged
native tests passed, 8 deselected**. The compatibility runner uses binary file
writes and omits POSIX directory-fsync/symlink cases only on Windows. On Linux it
runs all six native suites without those compatibility substitutions. Linux
durability, server execution, actual model tokenizer and live provider outputs
have not been exercised by these local fixture tests.

The source fixture uses native policy condition `P4-R0-PI0`; this does not relabel
production metadata. Production requires the actual episode policy condition.
No new record or applicability text was obtained from a model during these
tests. Owner integration, scheduled execution and candidate runtime publishing
remain separate work owned by the campaign entry.
