# Formal Analyzer -> Human PRE Boundary Orchestration Package V1.1

This file records the exact orchestration delivery used to complete the Formal Analyzer π1 reference run from the already-frozen A2/A3 projections to the Human Training Researcher PRE boundary.

## Package identity

File:

`formal_analyzer_to_human_researcher_pre_boundary_v1_1.zip`

SHA-256:

`18a165518d498138853dc04b20f1d03ebddd9552797d3301eba2d6aee1750f52`

Package contents:
- `00_VERIFY_PACKAGE.sh`
- `README.txt`
- `RUN_TO_HUMAN_PRE_BOUNDARY.sh`
- `SHA256SUMS.txt`
- `tests/test_master_helpers.py`
- `tools/master.py`
- `tools/verify_package.py`

The exact successful source files are now also archived byte-for-byte in Git under:

`experiments/formal_analyzer/pi1_reference_v1/orchestration_v1_1/`

The Git copy was created from the successful server package only after `sha256sum -c SHA256SUMS.txt` passed at the source and again after copying into the archive worktree. Its embedded `SHA256SUMS.txt` therefore remains the direct file-level identity authority for the seven source files. The original ZIP remains a distinct release artifact and must retain its own SHA-256 identity above.

Package self-tests before execution:
- SHA256 package verification PASS;
- Python AST PASS;
- no environment/ALFWorld execution surface PASS;
- no direct synchronous Responses execution surface PASS;
- no `set -euo pipefail` PASS;
- boundary semantic marker audit PASS;
- helper tests: 6 passed.

## V1.1 correction relative to V1

V1 incorrectly promoted `confirmatory_permitted=true` into an Analyzer live-call gate.

V1.1 uses the repository's actual authority:
- `teacher_call_permitted=true` is the live teacher-call gate;
- `confirmatory_permitted` remains a recorded task-access/data-use field;
- every group member still requires exact task/gamefile provenance match.

V1.1 also consumes the current `ANALYZER_GROUP_RESULT_V2` field:

`source_conditioned_proposals`

rather than the stale name `source_conditioned_repairs`.

## Execution stages

1. materialize group runtime registry and `FORMAL_ANALYZER_DAG_REGISTRY_V2`;
2. submit and import the 60 Formal G-A2/A3 Batch requests;
3. build and execute 60 Formal X requests using existing `crosscheck_projection_v2`;
4. run deterministic candidate projection and source-state x condition K<=1 gate;
5. freeze Formal Analyzer support manifests and `ROUND_EVIDENCE_PACKAGE_V1`;
6. stop before Human Training Researcher PRE.

## Successful reference run

Stage 1:
- `FORMAL_MAIN_GROUP_RUNTIME_REGISTRY_AND_DAG_V2_PASS`
- registered local units: 30;
- group runtime units: 60;
- Formal DAG SHA: `71b42e8c2a3641c3740978b0598fe30ac7a5ad7b02706b9ed80f42e01abb01a5`.

Stage 2 G Batch:
- Batch ID: `batch_6a9118638eac8190a431ddfbab4f7f0a`;
- 60 completed, 0 failed;
- 60/60 VALIDATED.

Stage 3 X Batch:
- Batch ID: `batch_6a91192f92508190a60f88d8780fb7ea`;
- 60 completed, 0 failed;
- 60/60 VALIDATED.

Stage 4:
- Formal source states: 30;
- K1 collisions: 0;
- selected candidate counts: A2=30, A3=30.

Stage 5:
- `FORMAL_ANALYZER_TO_HUMAN_PRE_BOUNDARY_PASS`;
- Round Evidence SHA: `d38806705cff6a4cc302fad2682d4505ec01f1df1196838120930dadb1be0a83`;
- Human PRE created: false;
- API Researcher PRE shadow created: false;
- environment call performed: false;
- F0/F1 performed: false;
- automatic scientific retry performed: false;
- next gate: `HUMAN_TRAINING_RESEARCHER_PRE`.

## Archival policy

The orchestration package is a historical reference execution harness, not a new production Analyzer module. The production/canonical algorithms remain in `src/pchsi/analyzer` and `src/pchsi/cognitive_runtime`.

Git archival now includes the exact readable source under `orchestration_v1_1/`. Release archival must additionally attach the original ZIP named above so the historical delivery artifact itself remains downloadable and independently verifiable.

Recommended release archival:
- attach the exact ZIP named above as a release asset;
- attach the full Formal Analyzer scientific artifact archive and release checksum inventory;
- verify SHA-256 values before publication;
- bind the release to the archive/main commit containing this manifest;
- if immutable releases are enabled, upload all assets to a draft before publishing.

Do not reconstruct this ZIP from later files and reuse the same identity. A rebuilt package is a new artifact even if its intent is the same.
