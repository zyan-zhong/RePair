# V1232Q Implementation Plan

1. Reuse the already valid V1232M/V1232K rollout terminal, universe, failure cohort and handoff. Never rerun rollout.
2. Discover the unique Strong-primary fixed-head repository through the frozen Stage6AO authority and run the existing import/signature preflight before output creation or provider calls.
3. Reuse V1232P bounded shard-terminal bundle-location reconciliation and validate selected bundle bytes before output creation.
4. Materialize a deterministic current-round failure-universe JSONL from the already frozen failure cohort and recovered receipt/episode authorities.
5. Reuse existing `select_failure_only_u_reg()` and `build_local_u_reg_manifest()` to freeze `CLEAN_ANALYZER_LOCAL_U_REG_V1`; no manual source count or failure/success ratio.
6. Materialize each selected source's existing `CLEAN_ANALYZER_TASK_ACCESS_RECORD_V1`.
7. Freeze `CLEAN_ANALYZER_TASK_ACCESS_MANIFEST_V1` from those exact records and bind `RUNTIME_INPUT_REGISTRY_V1.task_access_manifest_sha256` to the SHA-256 of the manifest file bytes, exactly as the existing clean Analyzer materializer does.
8. Bind each `SCIENTIFIC_UNIT_IDENTITY_V1.task_set_manifest_sha256` to `CLEAN_ANALYZER_LOCAL_U_REG_V1.u_reg_sha256`.
9. Run the existing Strong L-A0/L-A1 registry with zero automatic retry/replacement.
10. Reuse historical `load_attempt_directory_v1`, ACT3 signature materialization, `build_group_manifests`, and `build_group_synthesis_inputs` on accepted A1 artifacts.
11. Preserve complete deterministic group denominator and explicit source-closure census; no top-up/Human group selection.
12. Stop at the existing G-A2/G-A3/C/P/X → Dynamic PRE V2 continuation boundary.

Release verification additionally AST-scans every package-local `domain_hash(...)` call and rejects literal sequence/list-comprehension payloads, so the V128/V1232P compatibility class cannot recur inside this package.
