# Memory A0 Local Representation Probe V1 — Implementation Plan

> Required execution discipline: TDD, fixed-head review, no scientific outcome
> execution before explicit code and execution approval.

**Goal:** implement the scientific identity, 12-cell manifest, effect-scope,
infrastructure-retry, downstream isolation, and pre-freeze contracts needed to
run Package A0 without weakening the approved A/B/C scientific boundaries.

**Base authority:** `112ba5d3ccc0a3f3c3a9fdd143ec4c69fa525229`

**Implementation branch:** `science/memory-scientific-validation-v1`

**Implementation worktree:**
`/data/run01/scwb204/sdar_repro/badcase/github_exports/pchsi-wt-memory-scientific-validation-v1`

## Non-negotiable boundaries

- no model call;
- no ALFWorld reset/step;
- no vLLM launch;
- no Memory-ON scientific outcome;
- no mutation of Package-B B1–B7 production files;
- no retriever implementation;
- no Analyzer implementation;
- no policy training;
- no valid_seen/valid_unseen access;
- no force-push, rebase, amend, or history rewrite.

The batch ends at a fixed-head code-review gate.

## Task S0 — freeze the approved targeted hardening

Create:
- `docs/superpowers/specs/2026-08-19-memory-scientific-validation-v1.md`
- `configs/memory/memory_scientific_validation_v1.json`

Append design-status entries to:
- `docs/memory/FAILURE_MEMORY_V1_LEDGER.md`
- `docs/experiments/EXPERIMENT_LEDGER.md`

The entries must preserve:
- B-DIRECT base = `112ba5d3...`;
- scientific execution = false;
- effect authority = UNTESTED;
- A0 local-only authority;
- A1 optional/conditional;
- B task/gamefile-group split;
- C query-source isolation;
- frozen Package-B retrieval binding for C2;
- exact-cell retry for pre-result infrastructure failure;
- outcome-guided redesign prohibition;
- Package-C efficiency estimands;
- internalization protocol pre-freeze;
- adverse/null reporting rule.

Suggested commit:

`Freeze Memory scientific validation hardening`

Push by fast-forward only; verify local/remote equality and clean worktree.

## Task S1 — freeze this implementation plan

Create only:
- `docs/superpowers/plans/2026-08-19-memory-a0-local-representation-probe-v1-implementation.md`

Suggested commit:

`Plan Memory A0 local representation probe`

Push by fast-forward only; verify local/remote equality and clean worktree.

## Task S2 — RED: scientific-contract tests first

Create:
- `tests/memory/test_memory_scientific_validation_v1.py`

Before production implementation exists, run the focused test and verify the
expected RED is caused by the missing `pchsi.memory.scientific_validation`
module rather than a syntax/import typo.

The tests must cover at least:

1. A0 manifest is exactly 3 sources × M0/M1/M2/M3 = 12 cells.
2. The four cells of one source share the exact continuation seed and all
   source identity fields.
3. `M0` is an available empty Memory payload; `M3` is descriptive FM2, not a
   prescriptive verified arm.
4. A0 effect vocabulary stays Benefit/Harm/Neutral/Uncertain while every effect
   carries `SOURCE_STATE_LOCAL_PAIRED`.
5. terminal relation and mechanism effect are separate.
6. pre-result infrastructure failure creates no scientific effect, is excluded
   from the scientific denominator, and requires retry of the exact frozen cell.
7. post-execution unresolved identity/evidence cannot be silently retried or
   converted into Benefit/Harm/Neutral.
8. A1 is optional/conditional and does not block B/C/internalization.
9. B calibration/selection/safety-stress task-gamefile groups are disjoint.
10. C query task-gamefile groups are disjoint from A0, token calibration,
    active Memory sources, and B-development groups.
11. C2 requires frozen retriever/threshold/snapshot/applicability bindings.
12. outcome-guided redesign is rejected except through one of the four explicit
    versioned-amendment triggers.
13. internalization pre-freeze contract requires every registered field.
14. canonical IDs are deterministic and contain no current time or checkout
    path.

## Task S3 — GREEN: scientific contracts and manifest materializer

Create:
- `src/pchsi/memory/scientific_validation.py`
- `configs/memory/schemas/memory_a0_scientific_manifest_v1.json`
- `scripts/memory/materialize_a0_scientific_manifest_v1.py`

The production layer is pure/offline. It may parse explicit JSON inputs and
write a write-once manifest. It must not import or call model/environment/
retrieval execution surfaces.

### Frozen A0 source-binding input

The CLI consumes exactly three explicit source-binding JSON files. Each source
binding carries:
- source state ID;
- source task ID;
- task/gamefile-group ID;
- source fingerprint SHA;
- source bundle SHA;
- Memory lineage/version;
- active snapshot SHA;
- matched-representation-template SHA;
- pre-frozen continuation seed.

No directory auto-selection of “best” sources is allowed.

### Frozen representation-arm input

Each source binding has exactly four arms in order M0/M1/M2/M3. Each arm binds:
- availability;
- representation class;
- artifact/payload SHA where applicable;
- token count;
- retrieval mode.

M0 has no artifact SHA and zero tokens. M1/M2/M3 must be available and use the
same `DIRECT_FIXED_RECORD_NO_RETRIEVAL` mode for A0.

### Frozen manifest semantics

The 12-cell manifest records `scientific_execution_authorized=false`. A later
execution-approval artifact may authorize execution without mutating the frozen
manifest bytes.

## Task S4 — GREEN verification and static audit

Run:

```bash
python -m pytest -q tests/memory/test_memory_scientific_validation_v1.py
python -m pytest -q tests/memory
python -m pytest -q
python -m compileall -q src tests scripts/memory
git diff --check
```

Static audit the new production files for forbidden execution imports/surfaces:

```text
openai
anthropic
vllm
torch
alfworld
PolicyClient
HttpPolicyTransport
env.step
env.reset
subprocess
requests
httpx
```

The implementation commit must touch only the new scientific-contract files,
the focused test, and one clearly marked Memory-ledger status entry.

Suggested commit:

`Implement Memory A0 scientific contracts`

Push by fast-forward only; verify local/remote equality and clean worktree.

## Task S5 — fixed-head review package

At the exact implementation head, rerun focused, Memory, and full regression,
compileall, schema parsing, static forbidden-surface audit, ancestry from
`112ba5d3...`, commit-scope audit, branch/local/remote equality, and clean
worktree.

Create an external evidence root under:

`/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/memory_scientific_validation_v1/a0_code_review/<fixed_head>`

The final marker is:

```text
MEMORY_SCIENCE_A0_CODE_REVIEW_READY
SCIENTIFIC_EXECUTION_AUTHORIZED=false
NEXT_GATE=HUMAN_FIXED_HEAD_SOURCE_REVIEW
```

No scientific execution is performed in this batch.

## Post-review execution package (not executed by this plan)

Only after explicit code approval will a separate execution package:

1. bind the exact three registered source replay artifacts to the exact three
   B-DIRECT representation templates;
2. build and hash the 12-cell manifest;
3. run exact full-prompt tokenizer census with no truncation;
4. construct Slurm scientific jobs from the frozen cells;
5. replay each exact source state;
6. run M0/M1/M2/M3 continuations under the same source-bound seed;
7. retry only pre-result infrastructure failures using identical frozen inputs;
8. seal raw evidence before any aggregate interpretation;
9. classify local paired effects without making cross-task claims.
