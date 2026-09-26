# V1.23.2Q — Runtime Registry Authority Reconciliation

Recovery successor to V1232P. V1232P stopped before any Strong provider call while constructing `RUNTIME_INPUT_REGISTRY_V1`:

```text
ValueError: dictionary update sequence element #0 has length 64; 2 is required
```

Exact cause:

```text
domain_hash(domain, payload)
→ pchsi.reference_loop.canonical.domain_hash
→ body = dict(payload)
```

V1232P passed a `list[str]` of 64-character source-unit SHAs as `payload`. That helper is Mapping-specific. This is the same compatibility class already recorded historically in V128 for `SOURCE_EXECUTED_PREFIX_V1`: sequence-valued payloads must not be routed through the Mapping-only `domain_hash` helper.

For the current registry field, the correct fix is not another ad-hoc sequence hash. Existing `materialize_clean_analyzer_local_inputs_v1.py` already freezes the canonical authority chain:

```text
per-source CLEAN_ANALYZER_TASK_ACCESS_RECORD_V1
→ CLEAN_ANALYZER_TASK_ACCESS_MANIFEST_V1
→ SHA256(file bytes)
→ RUNTIME_INPUT_REGISTRY_V1.task_access_manifest_sha256
```

V1232Q restores this existing chain. It also reuses `build_local_u_reg_manifest()` so source scientific-unit identities bind the deterministic selected U_reg rather than using the rollout handoff SHA as a substitute task-set identity.

No rollout/environment/training execution is added. V1232P made zero Strong provider calls before failing, so V1232Q uses a fresh downstream output root and safely rematerializes only deterministic pre-provider Analyzer input artifacts.

The canonical downstream flow remains:

```text
valid rollout handoff
→ deterministic failure-only selection
→ CLEAN_ANALYZER_LOCAL_U_REG_V1
→ task-access records + task-access manifest
→ existing RUNTIME_INPUT_REGISTRY_V1
→ existing Strong L-A0/L-A1
→ historical ACT3 loader/signatures
→ build_group_manifests
→ build_group_synthesis_inputs
→ existing G-A2/G-A3/C/P/X continuation
```

No manual state count, parser selection, retry, group selection, bundle path selection, benchmark feedback, or Human scientific decision is introduced.
