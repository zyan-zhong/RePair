# Reference-Loop Evidence Materialization V1 — Implementation Plan

> **Execution base:** `design/reference-loop-evidence-foundation-v1` at
> `1b34c188ef906091c5d3d1674692f45514f54e01`.

## Goal

Implement the evidence foundation required before any formal Hierarchical
Analyzer call:

1. concrete, content-addressed π1 identity materialization;
2. read-only task/gamefile access revalidation;
3. exact five-file attempt-bundle validation;
4. immutable trajectory rebinding sidecar;
5. deterministic episode-level mechanical facts;
6. deterministic paired mechanical facts;
7. bounded read-only discovery over historical run assets.

This plan does **not** authorize Analyzer execution, Research Planner
implementation, environment branch execution, policy training, OFF/OFF
promotion, or reinterpretation of the sealed Failure Memory results.

## Reuse commitments

- Reuse `PolicyCallEvidenceV1.from_json`.
- Reconstruct and revalidate existing `ActionTrace` bytes without modifying
  historical trace objects.
- Reuse `PublicTransitionRecordV1.from_json`.
- Reuse `EpisodeArtifactV1.from_json`.
- Reuse `validate_policy_call_trace_alignment`.
- Reuse `build_attempt_bundle_bytes` to require exact byte and semantic-hash
  reproduction of the source bundle.
- Write Analyzer-era lineage only through new content-addressed sidecars.
- Preserve existing task-access assignments; revalidation may confirm,
  downgrade or block, never upgrade to sealed.
- Mechanical evidence emits deterministic facts or explicit `UNKNOWN`, never
  mechanism hypotheses or Benefit/Harm labels.

## Batch B1 — π1 identity and task access

### Files

- `src/pchsi/reference_loop/canonical.py`
- `src/pchsi/reference_loop/types.py`
- `src/pchsi/reference_loop/identity.py`
- `src/pchsi/reference_loop/task_access.py`
- `scripts/reference_loop/materialize_pi1_reference_identity_v1.py`
- `scripts/reference_loop/revalidate_task_access_v1.py`
- `tests/reference_loop/test_identity.py`
- `tests/reference_loop/test_task_access.py`

### RED

Copy only B1 tests and require failure because
`pchsi.reference_loop` is absent.

### GREEN

Implement:

- explicit `PI1_IDENTITY_SOURCE_REGISTRATION_V1`;
- file/directory-manifest SHA verification;
- symlink rejection;
- exactly one matching checkpoint registration inside the sealed runtime
  manifest;
- `PI1_REFERENCE_IDENTITY_V1`;
- existing task-access row ingestion;
- gamefile-level consistency checks;
- exact allowed dispositions;
- no `UPGRADED_TO_SEALED`.

### Commit

`Materialize pi1 identity and revalidate task access`

## Batch B2 — exact attempt bundle and trajectory sidecar

### Files

- `src/pchsi/reference_loop/bundle_reader.py`
- `src/pchsi/reference_loop/rebinding.py`
- `scripts/reference_loop/rebind_and_extract_episode_v1.py`
- `tests/reference_loop/_helpers.py`
- `tests/reference_loop/test_bundle_reader.py`
- `tests/reference_loop/test_rebinding.py`

### RED

Copy B2 tests and require failure because bundle/rebinding modules are absent.

### GREEN

Implement exact validation of:

- required five-file bundle shape;
- no symlinked file or parent;
- `SHA256SUMS` exact frozen order;
- canonical JSON/JSONL roundtrip;
- policy-call ↔ ActionTrace alignment;
- executed ActionTrace ↔ PublicTransition alignment;
- contiguous call indices;
- unique/increasing environment-step indices;
- executed-history reconstruction;
- observation/menu continuity;
- five-counter budget continuity;
- episode count/final-state binding;
- exact `build_attempt_bundle_bytes` reproduction.

Implement `TRAJECTORY_REBINDING_MANIFEST_V1` as a new sidecar. Formal
Analyzer release requires an explicit π1 checkpoint match and a full-trajectory
development-visible access decision. Future Analyzer/repair/training IDs remain
null until those stages exist.

### Commit

`Implement immutable trajectory evidence rebinding`

## Batch B3 — deterministic mechanical evidence and discovery

### Files

- `src/pchsi/reference_loop/alfworld_events.py`
- `src/pchsi/reference_loop/mechanical.py`
- `src/pchsi/reference_loop/paired.py`
- `src/pchsi/reference_loop/discovery.py`
- `src/pchsi/reference_loop/__init__.py`
- `scripts/reference_loop/compare_mechanical_pair_v1.py`
- `scripts/reference_loop/discover_reference_loop_inputs_v1.py`
- `tests/reference_loop/test_mechanical_and_paired.py`
- `tests/reference_loop/test_discovery.py`

### RED

Copy B3 tests and require failure because mechanical/discovery modules are
absent.

### GREEN

Implement generic mechanical facts:

- calls/steps/protocol failures/inadmissible/nonexecuted/environment error;
- exact repeats, consecutive repeats, max run, ABAB oscillation;
- observation/menu unchanged;
- exact `Nothing happens.` count;
- registered no-effect rule;
- budget exhaustion;
- time to first/last public state change;
- terminal done/won/success.

Implement conservative ALFWorld rules:

- destination/source/source-family revisits;
- inventory observations;
- goal visibility/take availability where the goal object can be parsed;
- effective acquisition/treatment/placement events;
- registered-progress timing;
- explicit `UNKNOWN` for unsupported/ambiguous parsing.

Implement paired facts:

- shared call and environment-step prefix;
- first pre-state/action/executed-action/observation/menu/budget divergence;
- hard invalidation for F0/F1 divergence before the registered intervention;
- no causal outcome label.

Implement bounded discovery:

- complete five-file bundle inventory;
- π1 development-visible candidates;
- runtime-manifest candidates indexed by exact SHA;
- no automatic checkpoint selection;
- no model or environment execution.

### Commit

`Extract deterministic episode and paired evidence`

## Verification

Run, in this order:

```bash
make -C native/s1_backend_probe clean all unit
python -m pytest -q tests/reference_loop
python -m pytest -q
python -m compileall -q src scripts tests
git diff --check
```

Then audit exact branch scope and four-commit topology:

1. plan;
2. B1;
3. B2;
4. B3.

Only after all checks pass, push
`implementation/reference-loop-evidence-materialization-v1`.

## Read-only real-asset discovery

After code publication, run a separate no-write/no-model/no-environment
discovery command over bounded `/data/run01` evidence roots. Discovery may
produce:

- `READY_FOR_EXPLICIT_REGISTRATION`; or
- `BLOCKED_NO_PI1_DEV_COMPLETE_TRAJECTORY`.

A blocked discovery is a valid scientific result. It must not be bypassed by
using SELECT-summary evidence, guessing Train17, or choosing a `latest`
directory.
