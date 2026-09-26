# S1 Collector Backend Probe V1 — Non-Executing Candidate

## Status

- Design: frozen.
- Implementation candidate: complete through Task 15.
- Candidate status: `candidate_pending_static_and_semantic_review`.
- `BACKEND_PROBE_EXECUTION=NOT_APPROVED`.
- `READ_ONLY_INVENTORY_EXECUTION=NOT_APPROVED`.
- `COLLECTOR_BACKEND_FINAL_APPROVAL=PENDING`.

This document does not authorize namespace, mount, pivot-root, seccomp,
Landlock, P1–P20, ALFWorld, model, expert, or inventory execution.

## Candidate boundary

The implementation contains:

1. a closed native and Python command surface;
2. content-addressed contracts and strict JSON records;
3. injected system-operation interfaces;
4. source, mount, capability, resource and static seccomp contracts;
5. trusted-bootstrap ordering validators;
6. evidence-tree validation and no-clobber publication;
7. dataset-bound execution-record validation;
8. compile-only P1–P20 payload and outcome manifests;
9. pure supervisor and namespace plans with closed injected executors;
10. deterministic, readelf-based candidate artifact generation.

None of these components opens the execution gate.

## Non-executing verification

The candidate is verified with:

```bash
PYTHON=/data/home/scwb204/run/sdar_repro/conda_envs/sdar_sft_py312/bin/python
"$PYTHON" -m pytest -q
make -C native/s1_backend_probe clean all unit probe-payloads
"$PYTHON" -m compileall -q src tests scripts
```

Tests may compile and execute ordinary unit-test binaries that exercise
pure planning, parsing, hashing, validation, and injected fake-operation
behavior. Tests must not execute real security-changing probe operations.

## Reproducibility

Candidate native artifacts are built with a fixed locale, timezone,
`SOURCE_DATE_EPOCH`, deterministic archive flags, path-remapping compiler
flags, and explicit tool paths. Two clean builds must yield the same
binary SHA-256.

Runtime closure generation uses `/usr/bin/readelf` and emits a canonical
JSON manifest. Absolute checkout paths and current timestamps must not
enter candidate bytes.

## Evidence and publication

Approved output names are exactly:

- `semantic_evidence.json`
- `local_evidence.json`
- `local_evidence.json.sha256`

Validation rejects extra paths, non-regular files, symbolic links,
hardlinks, oversized files, invalid JSON, and digest mismatch. Publication
uses no-clobber semantics and fsync ordering.

## Required future approval sequence

1. complete static and semantic code review;
2. freeze source, runtime, filters, payloads, profiles and artifact hashes;
3. create an external dataset-bound execution decision record;
4. separately grant `BACKEND_PROBE_EXECUTION_APPROVED`;
5. execute P1–P20;
6. audit semantic and local evidence;
7. approve or reject the backend;
8. separately design, implement and approve the read-only inventory
   collector.

Repository labels, files, commit messages, environment variables, or
command-line arguments cannot substitute for the external execution
decision.

## Stop condition

Task 15 stops at a code-review candidate. No backend probe and no inventory
collector execution is authorized by this commit.
