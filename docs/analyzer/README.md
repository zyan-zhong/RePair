# Analyzer Documentation Entry Point

For the finalized π1 Formal Analyzer V2 system, start here:

1. `FORMAL_ANALYZER_V2_CANONICAL_ARCHIVE_V1.md` — complete scientific design/runtime/reference summary.
2. `FORMAL_ANALYZER_V2_ARCHITECTURE_CODE_MAP_V1.md` — design layer -> implementation -> schema -> prompt -> test -> server artifact map.
3. `FORMAL_ANALYZER_V2_FIELD_SCHEMA_REFERENCE_V1.md` — field/schema scientific meaning, producer/consumer and identity rules.
4. `FORMAL_ANALYZER_V2_EXPERIMENT_PROTOCOL_RESULTS_V1.md` — complete Formal π1 protocol, treatment definitions, execution order, results and claim boundaries.
5. `FORMAL_ANALYZER_V2_MAINTENANCE_INVARIANTS_V1.md` — non-silent-change rules.
6. `FORMAL_ANALYZER_V2_BRANCH_CONSOLIDATION_V1.md` — branch/main/archive/release policy.
7. `../../experiments/formal_analyzer/pi1_reference_v1/README.md` — Formal reference-run archive entry point.
8. `../../experiments/formal_analyzer/pi1_reference_v1/EXPERIMENT_MANIFEST.json` — machine-readable run identity/results.
9. `../../experiments/formal_analyzer/pi1_reference_v1/CODE_ASSET_MANIFEST.json` — machine-readable code/schema/prompt/test inventory.
10. `../../experiments/formal_analyzer/pi1_reference_v1/DATA_ASSET_MANIFEST.json` — machine-readable server scientific-asset provenance/archive requirements.
11. `../../experiments/formal_analyzer/pi1_reference_v1/RESULT_MANIFEST.json` — machine-readable final result/claim-boundary summary.
12. `../../experiments/formal_analyzer/pi1_reference_v1/ARTIFACT_INDEX.md` — detailed server artifact paths/provenance.
13. `../../experiments/formal_analyzer/pi1_reference_v1/REMOTE_ARCHIVE_COMPLETENESS_V1.md` — exact definition of when the reference is independent of the current HPC filesystem.

## Final reference identities

- Actual Formal Main execution code head: `0529efa4b4c896f3855a4634c7daa3a3559e3a89`
- Canonical post-experiment Analyzer head: `17201a462d24985e195a5bb225e388bd9cb9089e`
- Formal DAG V2 SHA: `71b42e8c2a3641c3740978b0598fe30ac7a5ad7b02706b9ed80f42e01abb01a5`
- Round Evidence SHA: `d38806705cff6a4cc302fad2682d4505ec01f1df1196838120930dadb1be0a83`
- Next scientific gate: `HUMAN_TRAINING_RESEARCHER_PRE`

## Authoritative implementation roots

- Analyzer: `src/pchsi/analyzer/`
- Cognitive runtime: `src/pchsi/cognitive_runtime/`
- Reused Failure Memory consumer interface: `src/pchsi/memory/`
- Analyzer schemas: `configs/analyzer/schemas/`
- Runtime schemas: `configs/cognitive_runtime/schemas/`
- Runtime stage/prompt/schema binding: `configs/cognitive_runtime/unified_cognitive_runtime_manifest_v1.json`
- Prompts: `prompts/cognitive_runtime/`
- Analyzer tests: `tests/analyzer/`
- Runtime tests: `tests/cognitive_runtime/`

Older design, audit, implementation-plan, protocol, metric, and prompt-version documents remain historical/canonical supporting material. Do not infer the current system by choosing the numerically largest filename; use the canonical archive and the frozen runtime manifest as the maintenance authority.

## Archival status rule

Git is the authority for readable code/design/schema/prompt/protocol/manifests. The exact V1.1 orchestration source must also be imported into the experiment archive. Large/raw generated scientific artifacts must additionally be packaged as a content-addressed release asset. Do not call the reference server-independent until `REMOTE_ARCHIVE_COMPLETENESS_V1.md` is satisfied.
