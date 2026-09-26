# Formal Analyzer π1 Reference — Remote Archive Completeness V1

Status: **ARCHIVAL CONTRACT / RELEASE GATE**

This document defines what must exist remotely before the Formal Analyzer π1 reference can be considered independent of the current HPC filesystem.

## 1. Git remote — required readable/maintainable assets

The repository must contain the complete human-maintainable method definition:

### Design and scientific protocol
- `docs/analyzer/HIERARCHICAL_ANALYZER_V2_DESIGN.md`
- `docs/analyzer/HIERARCHICAL_ANALYZER_V2_OUTPUT_CONTRACT_V1.md`
- `docs/analyzer/FORMAL_ANALYZER_V2_CANONICAL_ARCHIVE_V1.md`
- `docs/analyzer/FORMAL_ANALYZER_V2_ARCHITECTURE_CODE_MAP_V1.md`
- `docs/analyzer/FORMAL_ANALYZER_V2_FIELD_SCHEMA_REFERENCE_V1.md`
- `docs/analyzer/FORMAL_ANALYZER_V2_EXPERIMENT_PROTOCOL_RESULTS_V1.md`
- `docs/analyzer/FORMAL_ANALYZER_V2_MAINTENANCE_INVARIANTS_V1.md`
- `docs/analyzer/FORMAL_ANALYZER_V2_BRANCH_CONSOLIDATION_V1.md`
- associated metric, audit, paper-evidence, protocol, and runtime-researcher documents.

### Final implementation
- complete `src/pchsi/analyzer/` implementation;
- complete `src/pchsi/cognitive_runtime/` runtime used by the reference chain;
- the relevant `src/pchsi/memory/` consumer interface reused by A3;
- executable/reference scripts under `scripts/analyzer/` and `scripts/cognitive_runtime/`.

### Schemas and frozen contracts
- `configs/analyzer/schemas/`;
- `configs/cognitive_runtime/schemas/`;
- relevant `configs/memory/` role/consumer contracts;
- `configs/cognitive_runtime/unified_cognitive_runtime_manifest_v1.json`;
- Analyzer experiment/budget/metric contracts.

### Prompts
At minimum the exact final prompt files bound by the runtime manifest:
- `ANALYZER_L_A0_PROMPT_V3.txt`;
- `ANALYZER_L_A1_PROMPT_V3.txt`;
- `ANALYZER_G_A2_PROMPT_V4.txt`;
- `ANALYZER_G_A3_PROMPT_V4.txt`;
- `ANALYZER_C_PROMPT_V1.txt`;
- `ANALYZER_X_PROMPT_V2.txt`;
- Researcher shadow prompts used by the downstream runtime contract.

Historical prompt versions remain useful lineage and should not be deleted from Git merely because a later version is final.

### Tests/hardening lineage
- Analyzer unit/contract tests;
- cognitive runtime contract tests;
- ACT3 registration/source-binding tests;
- Formal DAG V2 tests;
- K1 tests;
- request renderer/output validation/retry-hard-stop tests;
- historical audit documents.

### Experiment metadata
- `EXPERIMENT_MANIFEST.json`;
- `CODE_ASSET_MANIFEST.json`;
- `DATA_ASSET_MANIFEST.json`;
- `RESULT_MANIFEST.json`;
- `ARTIFACT_INDEX.md`;
- `ORCHESTRATION_PACKAGE_V1_1.md`;
- `RELEASE_NOTES.md`.

## 2. Exact reference orchestration source — must also be in Git

The successful V1.1 boundary package is part of the reproducible experiment implementation, even though it is not a production `src/pchsi/...` module.

Required exact source import location:

`experiments/formal_analyzer/pi1_reference_v1/orchestration_v1_1/`

Required files copied byte-for-byte from the server package:
- `00_VERIFY_PACKAGE.sh`
- `README.txt`
- `RUN_TO_HUMAN_PRE_BOUNDARY.sh`
- `SHA256SUMS.txt`
- `tests/test_master_helpers.py`
- `tools/master.py`
- `tools/verify_package.py`

Source authority directory on the server:

`/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/formal_analyzer_to_human_researcher_pre_boundary_v1_1`

The Git copy must be verified against that package's `SHA256SUMS.txt` before commit.

The original ZIP remains a separate release asset and must keep SHA256:

`18a165518d498138853dc04b20f1d03ebddd9552797d3301eba2d6aee1750f52`

## 3. GitHub Release — required byte-level scientific snapshot

Git alone is not the correct storage for every generated/raw execution artifact. A release bound to an immutable tag should carry a compact full scientific snapshot archive.

Recommended tag:

`formal-analyzer-pi1-reference-v1.0`

The tag must point to the final archive/main commit after the exact orchestration source import and all archive manifests are committed.

Recommended release assets:

1. `formal-analyzer-pi1-reference-v1-artifacts.tar.zst`
2. `formal_analyzer_to_human_researcher_pre_boundary_v1_1.zip`
3. `FORMAL_ANALYZER_PI1_RELEASE_SHA256SUMS.txt`
4. optional machine-readable archive inventory/manifest if also included inside the tarball.

## 4. Required contents of the full artifact archive

The archive should contain the exact canonical scientific artifacts needed to re-audit the reference run, while excluding redundant caches and non-scientific temporary files.

### Fresh π1 / local evidence
- frozen fresh-π1 selection/collection manifests and required trajectory evidence;
- Formal Main A0/A1 runtime registry and accepted normalized execution manifest;
- exact validated A1 artifact authority/bindings.

### Source closure
- `FORMAL_ACT3_REGISTRATION_CLOSURE_V2.json`;
- `FORMAL_ACT3_SOURCE_CLOSURE_ROWS_V2.json`;
- `FORMAL_EXACT_SOURCE_BINDINGS_V1.json`;
- `FORMAL_SOURCE_CONTEXTS_V1.json`;
- `ANALYZER_SOURCE_CLOSED_GROUPS_V1.json`;
- `ANALYZER_SOURCE_CLOSED_GROUP_SYNTHESIS_INPUTS_V1.json`.

### A3 Memory
- frozen snapshot manifest/contract files required to identify the snapshot;
- sealed historical materializer source used as algorithm reference;
- `RESTORE_SUMMARY_V1.json`;
- `ANALYZER_MEMORY_RETRIEVAL_MANIFEST_V1.json`;
- member-view JSONL;
- all 30 group bundles;
- all 30 A3 Memory role packs.

### A2/A3 treatment projections
- all 30 A2 projections;
- all 30 A3 projections;
- group manifests/synthesis inputs used by the projections;
- `A2_A3_PAIR_AUDIT.json`;
- `REQUEST_PREFLIGHT.json`;
- rendered request bundles or their exact content-addressed equivalents.

### Formal DAG/runtime registry
- Formal DAG V2 artifact;
- group/local runtime registry artifacts;
- memberwise task-access witness manifests used for the multi-source groups.

### Formal G Batch
- Batch input manifest/JSONL;
- upload/submission/terminal receipts;
- output/error JSONL when applicable;
- exact imported validated G artifacts/status manifests;
- transport provenance needed to bind `batch_6a9118638eac8190a431ddfbab4f7f0a`.

### Formal X Batch
- same categories as G;
- exact imported validated X artifacts/status manifests;
- transport provenance needed to bind `batch_6a91192f92508190a60f88d8780fb7ea`.

### Candidate and Round Evidence
- `FORMAL_ANALYZER_CANDIDATE_POOL_V1.json`;
- all support manifests used by the Round Evidence freezer;
- `ROUND_EVIDENCE_PACKAGE_V1.json` whose semantic SHA is `d38806705cff6a4cc302fad2682d4505ec01f1df1196838120930dadb1be0a83`;
- final boundary manifest proving Human PRE/F0F1 had not yet occurred.

### Logs and execution harness
- final V1.1 master log or an exact forensic log subset sufficient to audit all stage transitions;
- exact V1.1 ZIP;
- archive-level SHA256 manifest.

## 5. What is explicitly not enough

The reference is **not** server-independent merely because Git contains:
- code;
- result numbers;
- Batch IDs;
- server paths;
- semantic SHAs.

Those are necessary but do not replace the byte-level scientific artifacts needed to independently re-audit the run after the server paths disappear.

## 6. Release integrity policy

Recommended publication procedure:
1. finish exact orchestration source import into Git;
2. sync/fetch and verify archive branch/main ancestry;
3. build the full artifact archive from the authoritative server paths in `DATA_ASSET_MANIFEST.json`;
4. generate archive-level SHA256 sums;
5. extract/verify the archive in a clean temporary directory;
6. create the release as draft;
7. upload all assets;
8. verify asset hashes;
9. publish the release;
10. enable/use immutable release protection when available;
11. verify the published release/asset integrity;
12. only then mark `server_independent_archive_complete=true` in a future explicit archive-completion commit.

## 7. Current completion state at creation of this document

Already remote in Git:
- design/protocol documentation: yes;
- final Analyzer implementation: yes;
- cognitive runtime: yes;
- schemas/contracts: yes;
- final and historical prompts: yes;
- tests/hardening lineage: yes;
- machine-readable experiment result metadata: yes;
- server artifact path/SHA map: yes.

Still required before declaring complete server-independent archival:
- exact V1.1 orchestration source import: pending server-side copy/commit;
- full byte-level scientific artifact archive: pending;
- tag/release: pending;
- immutable/release-asset verification: pending.

This pending status is intentional and must not be silently upgraded to COMPLETE before those actions are verified.
