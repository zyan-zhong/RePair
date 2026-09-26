# Internal Analyzer source-binding constructor

This fills the source-binding constructor consumed by V1.6 `build_from_rollout_result`. It is an internal component of the existing first-round and resident operations. It does not launch providers, environments, training, or another controller, and adds no scientific decision or startup gate.

```python
from analyzer_binding.source_binding import SourceLayout, build_source_binding
from exact_bindings import build_from_rollout_result

source = build_source_binding(
    rollout_result,
    layout=SourceLayout.bundle(installed_bundle_root),
    current_index=current_typed_index,
    output_root=round_output / "memory_projection",
    # Optional: native objects already produced by the Memory operation.
    source_partition_by_lineage=native_partition_bindings,
)
binding = build_from_rollout_result(
    rollout_result, source_binding=source,
    current_index=current_typed_index, output_root=round_output / "analyzer",
)
```

The entry chooses the installed layout mechanically. `SourceLayout.project(project_root)` addresses the existing development capture; `SourceLayout.bundle(installed_bundle_root)` addresses `registered_sources/`, `reuse/<original-package-name>/`, and `reuse/h44/`. There are no per-package path, runner, parser, policy, or snapshot choices for the operator. Package relocation changes only local locators, preserving the registered source identity. All finite `PACKAGE_FILES.sha256` members are checked. A modified source file or manifest fails before loading.

The project layout also recognizes the exact complete current capture registered by `work/v17/NATIVE_BBA_FULL_SOURCE_RECEIPT_V2.json`, but only when the materializer itself addresses that receipt's `extracted_root`. It verifies the registered commit/tree, archive SHA and individual file bytes against the already-fetched `registered_git_cache`. The earlier capture with newline-transformed files is rejected. It does not search for checkouts or rewrite the registered Linux repo locator. The live bundle continues to use the original registered checkout.

| Field | Existing authoritative source |
| --- | --- |
| `packages.q/u/x` | SHA-bound SOURCE_PLAN entries, cross-checked against the V14 source-capture historical package registration; original package manifests |
| `packages.h44` | Gate2 `/manifest` row `exact_package:h44`, cross-checked with V14 registration; original H4.4 manifest |
| `scientific_repo_root` | Gate2 `/manifest` row `git_relevant_sources_archive` `/source_path` |
| Current repository source identity | V14 source capture `/repo/head`, currently bba400; not the historical Gate2 61c9 source identity |
| `runtime_manifest` | Registered repo `configs/cognitive_runtime/unified_cognitive_runtime_manifest_v1.json` |
| `experiment_contract` | Q's existing repo-relative protocol path `configs/analyzer/analyzer_a0_a3_experiment_contract_v1.json` |
| `role_authority` | Q/U's existing repo-relative protocol path `docs/project/strong_primary_takeover_v1/stage6ao/ROLE_SCOPED_STRONG_PRIMARY_FRESH_ROUND_AUTHORITY_V1.json` |
| `train_root` | Manifest-checked H4.4 `assets/deployment_authorities.json#/train_root` |
| `f0f1_protocol` | Manifest-checked X `assets/configs/planner_bound_f0f1_replication_protocol_v2.json` |
| `analyzer_snapshot_directory` | This rollout's exact `input_member_manifest.memory` member `/active_snapshot_directory` |
| `analyzer_token_contract` | The same current Memory authority `/token_budget_contract_path`; domain identity compared with the current request |
| `researcher_view` | Native `build_researcher_memory_view_v1` from the current immutable loaded snapshot; initial source partitions come automatically from the tracked native role-view producer; updated source partitions or views come from the existing current Memory operation |

The three repo-relative JSON sources and two native Memory producer modules are compared byte-for-byte with `git cat-file blob <captured-head>:<exact-relative-path>`. This is a read of individual registered objects, without a directory or Git status census. Repository bytes are never assembled by merging H4.4 historical modules into the current partial `native_bba` capture. Other native dependencies remain the deployed checkout's responsibility, as in V1.6.

The current rollout request file hash, round identity, request identity, Memory runtime raw file hash, active snapshot hash and token contract hash must all agree. Promoted rounds obtain their snapshot and token locators from their own capsule member; initial Memory defaults never override them.

## Native Researcher projection

The producer already exists: `pchsi.memory.dev_snapshot_loader.load_calibrated_dev_snapshot_v2` verifies the immutable snapshot and records; `pchsi.memory.consumer_views.build_researcher_memory_view_v1` produces `ROUND_RESEARCH_PLANNING` with the records unchanged. This constructor calls both and writes its result immutably. It supplies no old round evidence; the existing PRE adapter later binds the actual current-round evidence. It does not replace a missing snapshot with an empty record list.

The native producer's `source_partition_by_lineage` input contains `MemorySourcePartitionBindingV1` objects. They can come directly from the parent Memory operation. For a persisted current typed index, `refs.memory_source_partitions` may hold an exact file ref to a mapping of lineage keys to the existing native objects' `to_dict()` representations. The constructor parses those native fields, invokes their original validators, and checks lineage equality. This is transport of the existing native argument, not a newly invented scientific authority. The constructor does not author a partition based on the directory name, `train` root, access contract, or record presence.

The complete registered bba400 source resolves the initial map automatically. `scripts/memory/run_role_view_smoke_v1.py:157-173` already constructs `MemorySourcePartitionBindingV1` for each loaded member using `TRAIN_MEMORY_SOURCE` and the frozen snapshot's SHA as partition authority. `scripts/memory/run_memory_live_cell_executor_v1.py:365-394` uses the same rule. The constructor reuses the exact partition assignment from the tracked role-view script, after matching the loaded snapshot and token contract against tracked `configs/memory/package_b_failure_memory_dependency_v1.json`. It executes neither the script's unrelated Policy/Analyzer query logic nor its CLI. The original `ACCESS_DIAGNOSTIC_ONLY` scope is preserved for `ROUND_RESEARCH_PLANNING`; no full training provenance is conferred.

Consequently the captured initial `FINAL_RUNTIME_IDENTITY_V1.json` need not contain a prebuilt partition map or historical view. It already supplies the snapshot/token locators required by the existing initial producer. The earlier conclusion that absent map/view refs blocked initialization was too broad and is superseded by this automatic route.

For a changed Memory snapshot, the constructor will not silently transplant the original dependency's partition authority. The existing current Memory operation supplies its native per-lineage bindings or exact views as described above. Missing updated bindings are reported at `source_partition_by_lineage` with the current snapshot identity; the constructor does not ask the user to author scientific data.

Ledger V93-10/V94-3 records the reusable native Memory and Researcher input producers. An absent historical view alone is not an error. No human-filled JSON, server search, or new collection/review round is requested.

## Verification and limits

`python -B -m pytest work/v17/analyzer_binding/tests/test_source_binding.py work/v16/analyzer_adapter/tests/test_exact_bindings.py -q -p no:cacheprovider`

Verified result: **25 passed in 6.59s** (16 constructor tests and 9 unchanged V1.6 exact-binding tests). The constructor is frozen at this verified scope. [Memory source boundary review](MEMORY_SOURCE_BOUNDARY_REVIEW.md) records the separate current TRAIN_UPDATE writeback contract, exact missing type/semantic fields and unimplemented integration proposal.

Tests cover actual registered Q/U/X/H4.4 bytes and locators, relocated installations and changed-source rejection, current promoted Memory selection, round/request/snapshot/token mismatch rejection, capsule path containment, actual native Researcher projection, automatic initial partitions, and full-current-source constructor integration with native snapshot builders and loaders. The real native test helper publishes a complete nonempty test snapshot containing governed record, retrieval key, FM1 and FM2. Only the initial test snapshot authority is substituted in the bootstrap integration case; the published scientific objects, snapshot audit/loader, Git object checks and view producer are real.

On Windows, the native test publisher's POSIX-only directory fsync and text-mode low-level file writer are replaced only in the test fixture with binary writes; canonical bytes and native scientific validation are preserved. This does not establish Linux durability. The original server snapshot data is not mounted locally, so the test snapshot remains fixture evidence and the actual initial server view has not been materialized. No provider execution, complete scientific round, or Max10 run is claimed. Existing V1.6 artifacts and ZIPs remain unchanged.
