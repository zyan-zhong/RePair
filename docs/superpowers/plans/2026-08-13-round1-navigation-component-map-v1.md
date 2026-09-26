# Round-1 Navigation and Component Map V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development or superpowers:executing-plans
> to implement this plan task-by-task. Steps use checkbox syntax for
> tracking.

**Goal:** Create the canonical Round-1 overview and component registry
that explain the completed first single-round validation from policy
rollout through Harness-OFF NO-GO, post-hoc analysis and provenance
closure.

**Architecture:** The Round-1 overview is the human-readable navigation
entry point. The Component Registry is the authoritative role map for
builders, runners, collectors, analyzers, verifiers, trainers,
evaluators and registries. Neither document moves or replaces raw
evidence; both link downward to existing ledgers and audits.

**Tech Stack:** GitHub-flavored Markdown, repository-relative links,
Python 3.12 read-only documentation audits, Git.

## Global Constraints

- Work only on branch:
  `docs/round1-research-assets-v1`.
- Implementation base:
  `4d1d3553f762a9b171a9672da0b9f34951195ed2`.
- Do not rerun a model or ALFWorld.
- Do not modify scientific evidence.
- Do not move existing evidence files.
- Do not change any existing SHA-256 identity.
- Do not change the Round-1 `NO-GO` conclusion.
- Do not call provenance closure `Level 0`.
- Hierarchical analysis levels remain Level 1 through Level 6.
- Do not label Level 5 as complete.
- Do not label Level 6 as complete.
- Failure Memory remains `HOLD`.
- Exact server asset paths not yet independently registered must be
  marked as pending Module 3 asset binding rather than guessed.
- Root `README.md`, `docs/experiments/EXPERIMENT_LEDGER.md` and
  `docs/code_map.md` remain unchanged in this module.
- Use repository-relative Markdown links only for repository files.
- Do not create links to Module 2 or Module 3 files before those files
  exist.
- The module closes in one single-purpose commit.
- The closure commit is identified through Git history and is not
  self-embedded in the same commit.

---

## File Structure

### Create

`docs/rounds/round1/README.md`

Responsibility:

- provide the canonical human-readable overview of Round 1;
- distinguish workflow stages from hierarchical-analysis levels;
- expose current scientific status and conclusion boundaries;
- link to the Component Registry and existing authoritative documents.

### Create

`docs/rounds/round1/COMPONENT_REGISTRY.md`

Responsibility:

- identify every major Round-1 component;
- distinguish component type, role and authority;
- show producer-to-consumer relationships;
- show current execution or scientific status;
- avoid inventing unresolved server paths or hashes.

### Modify

`docs/rounds/round1/ASSET_CONSOLIDATION_LEDGER.md`

Responsibility:

- close the design-freeze row;
- bind the approved design commit;
- record Module 1 implementation and documentation-sync state;
- identify Module 2 as the next small module after closure.

### Unchanged in this module

- `README.md`
- `docs/experiments/EXPERIMENT_LEDGER.md`
- `docs/code_map.md`
- `docs/audits/ROUND1_CANONICAL_GAP_AUDIT.md`
- all files under `docs/audits/evidence/`
- scientific source, configuration, result and model files.

---

### Task 1: Build and Close the Round-1 Navigation and Component Map

**Files:**

- Create: `docs/rounds/round1/README.md`
- Create: `docs/rounds/round1/COMPONENT_REGISTRY.md`
- Modify: `docs/rounds/round1/ASSET_CONSOLIDATION_LEDGER.md`

**Interfaces:**

- Consumes:
  - the frozen asset-consolidation design;
  - the current Experiment Ledger;
  - the current Code Map;
  - the current canonical-gap audit;
  - existing repository code and Git history;
  - frozen Round-1 scientific status.
- Produces:
  - one Round-1 navigation entry point;
  - one component role registry;
  - one updated consolidation ledger.
- Does not produce:
  - scientific results;
  - a new taxonomy;
  - a new analysis result;
  - a Memory record;
  - an asset migration.

- [ ] **Step 1: Verify the fixed implementation base**

Run:

```bash
test "$(
  git branch --show-current
)" = \
"docs/round1-research-assets-v1"

test "$(
  git rev-parse HEAD
)" = \
"4d1d3553f762a9b171a9672da0b9f34951195ed2"

test -z "$(
  git status --porcelain
)"
```

Expected:

- all commands return `0`;
- the worktree is clean.

- [ ] **Step 2: Verify required source documents exist**

Run:

```bash
python - <<'PY'
from pathlib import Path


required = (
    Path("README.md"),
    Path("docs/code_map.md"),
    Path(
        "docs/experiments/"
        "EXPERIMENT_LEDGER.md"
    ),
    Path(
        "docs/audits/"
        "ROUND1_CANONICAL_GAP_AUDIT.md"
    ),
    Path(
        "docs/protocol/"
        "MODULE_CLOSURE_POLICY.md"
    ),
    Path(
        "docs/superpowers/specs/"
        "2026-08-13-round1-research-asset-"
        "consolidation-v1-design.md"
    ),
    Path(
        "docs/rounds/round1/"
        "ASSET_CONSOLIDATION_LEDGER.md"
    ),
)

missing = [
    path.as_posix()
    for path in required
    if not path.is_file()
]

assert not missing, missing

print(
    "ROUND1_MODULE1_SOURCE_DOCUMENTS_PASS"
)
PY
```

Expected:

```text
ROUND1_MODULE1_SOURCE_DOCUMENTS_PASS
```

- [ ] **Step 3: Establish the expected RED state**

Run before creating the two Module 1 documents:

```bash
python - <<'PY'
from pathlib import Path


expected = (
    Path(
        "docs/rounds/round1/"
        "README.md"
    ),
    Path(
        "docs/rounds/round1/"
        "COMPONENT_REGISTRY.md"
    ),
)

missing = [
    path.as_posix()
    for path in expected
    if not path.exists()
]

print({
    "expected_missing":
        missing,
})

assert len(missing) == 2

print(
    "ROUND1_MODULE1_RED_CONFIRMED"
)
PY
```

Expected:

```text
ROUND1_MODULE1_RED_CONFIRMED
```

This RED proves that the required navigation and registry documents do
not yet exist.

- [ ] **Step 4: Create the Round-1 README**

Create:

`docs/rounds/round1/README.md`

The exact top-level heading is:

```markdown
# Round 1 — Single-Round Policy Improvement Validation
```

It must contain these headings in this order:

```markdown
## Status at a Glance
## Research Question
## Round Identity and Policy Boundary
## End-to-End Workflow
## Workflow Stage Status
## Main Result and Interpretation
## Mechanical and Hierarchical Post-hoc Analysis
## Canonical Evidence and Provenance Closure
## Failure Memory Handoff
## Component Map
## Documentation Map
## Claim Boundary
## Current Next Step
```

### Required status facts

The `Status at a Glance` section must state:

```text
Round identity:
ROUND1_SINGLE_ROUND_POLICY_IMPROVEMENT_VALIDATION

Round execution:
COMPLETE

Policy-improvement result:
COMPLETE_NO_GO

Hierarchical analysis:
LEVELS_1_TO_4_COMPLETE
LEVEL_5_REJECTED
LEVEL_6_INCOMPLETE

Canonical evidence and provenance closure:
IN_PROGRESS

Failure Memory:
HOLD
```

### Required research interpretation

The README must state in plain language:

- the first pi0-to-pi1 training round was executed;
- the final Harness-OFF evaluation did not establish successful policy
  improvement;
- the round therefore ended in `NO-GO`;
- interface behavior improved, but this cannot be presented as
  successful long-horizon task competence;
- post-hoc analysis is diagnostic evidence, not causal truth;
- provenance closure is being completed before those analyses become
  sources for Memory or new training claims.

### Required policy boundary

The README must distinguish:

- pi0 task policy;
- pi1 trained task policy;
- external strong proposer/analyzer;
- environment/Q2 verifier;
- Harness-OFF evaluator;
- future local analyzer;
- future Research Planner.

It must explicitly state:

```text
semantic analyzer output
≠
environment truth
```

and:

```text
Harness-assisted or Memory-assisted behavior
≠
policy internalization
```

### Required workflow

The workflow must be shown as:

```text
governance and runtime foundation
→ pi0 development trajectories
→ strong-model candidate proposals
→ Q2 environment validation
→ training-data construction
→ pi1 training
→ Harness-OFF evaluation
→ NO-GO
→ mechanical analysis
→ hierarchical semantic analysis
→ canonical provenance closure
→ Failure Memory handoff
```

### Required workflow-stage table

The table must contain these rows and statuses:

| Stage | Required status |
|---|---|
| Governance and runtime foundation | `COMPLETE` |
| pi0 trajectory collection | `COMPLETE` |
| Strong-model proposal | `COMPLETE` |
| Q2 environment validation | `COMPLETE` |
| Training-data construction | `COMPLETE` |
| pi1 training | `COMPLETE` |
| Harness-OFF evaluation | `COMPLETE_NO_GO` |
| Mechanical post-hoc analysis | `COMPLETE` |
| Hierarchical semantic analysis Levels 1-4 | `COMPLETE` |
| Global mechanism synthesis, Level 5 | `REJECTED` |
| Independent challenge, Level 6 | `INCOMPLETE` |
| Canonical evidence and provenance closure | `IN_PROGRESS` |
| Failure Memory | `HOLD` |

### Required hierarchy clarification

The README must explicitly say:

```text
Canonical evidence and provenance closure is a sibling workstream to
hierarchical semantic analysis. It is not Level 0 and does not renumber
Levels 1-6.
```

### Required current links

Use working relative links to:

- `./COMPONENT_REGISTRY.md`
- `./ASSET_CONSOLIDATION_LEDGER.md`
- `../../audits/ROUND1_CANONICAL_GAP_AUDIT.md`
- `../../experiments/EXPERIMENT_LEDGER.md`
- `../../code_map.md`
- `../../protocol/MODULE_CLOSURE_POLICY.md`
- `../../superpowers/specs/2026-08-13-round1-research-asset-consolidation-v1-design.md`

Do not link to `HIERARCHICAL_ANALYSIS.md` or `ASSET_REGISTRY.md` until
those files are created in Modules 2 and 3.

- [ ] **Step 5: Create the Component Registry**

Create:

`docs/rounds/round1/COMPONENT_REGISTRY.md`

The exact top-level heading is:

```markdown
# Round-1 Component Registry
```

It must contain these headings:

```markdown
## Purpose
## How to Read This Registry
## Authority Boundaries
## Component Types
## Round-1 Component Flow
## A. Governance and Runtime Foundation
## B. pi0 Evidence Production
## C. Strong-Model Proposal Pipeline
## D. Q2 Environment Validation
## E. Training and Checkpoint Production
## F. Harness-OFF Evaluation
## G. Mechanical Post-hoc Analysis
## H. Hierarchical Semantic Analysis
## I. Canonical Evidence and Provenance Closure
## J. Future Memory, Local Analyzer and Planner
## Registry Limitations
## Documentation Sync State
```

### Required component-table columns

Every component table must use:

```text
Component
Historical/internal ID
Type
Scientific role
Consumes
Produces
Authority
Repository entry
Server evidence
Status
Downstream consumer
```

### Required component types

Use only:

```text
GOVERNANCE
BUILDER
RUNNER
COLLECTOR
PUBLISHER
MECHANICAL_ANALYZER
SEMANTIC_ANALYZER
VERIFIER
TRAINER
EVALUATOR
AGGREGATOR
REGISTRY
```

Multiple types may be joined with `+`.

### Required authority vocabulary

Use these explicit authority descriptions:

```text
protocol / access authority
byte / identity authority
deterministic mechanical-fact authority
environment-execution validity authority
semantic hypothesis only
training-data transformation only
model-training execution only
evaluation aggregation only
no independent scientific authority
```

### Required component inventory

The registry must include at least the following components.

#### Governance and Runtime Foundation

- task-access and condition governance;
- Runtime Core;
- strict raw-policy parser;
- prompt and M0 history builder;
- immutable dual-budget accounting;
- ALFWorld evaluator;
- ActionTrace and trajectory evidence collector;
- artifact publisher.

#### pi0 Evidence Production

- development schedule builder;
- pi0 episode runner;
- policy-call evidence builder;
- episode evidence validator;
- attempt-bundle publisher.

#### Strong-Model Proposal Pipeline

- strong-proposer source-package builder;
- provider request builder and request freeze;
- OpenAI provider adapter;
- scientific schema validator;
- deterministic semantic validator;
- R132 PRIMARY117 ledger.

The R132 ledger row must record:

```text
117 source cases
117 frozen requests
91 teacher outputs
26 rejections
351 Q2 state bindings
```

It must not claim that all terminal semantic provenance is closed.

#### Q2 Environment Validation

- Q2 state-binding builder;
- state/binding identity validator;
- environment-execution validator;
- accepted/rejected correction registry.

The environment validator is the validity authority for environment
execution. The strong model is not.

#### Training and Checkpoint Production

- accepted-example builder;
- training-dataset builder;
- training-sample ledger;
- pi1 trainer;
- pi1 checkpoint registry.

The trainer must be described as an execution component, not as the
judge of whether pi1 improved.

#### Harness-OFF Evaluation

- evaluation schedule builder;
- pi0/pi1 episode runner;
- task-level result builder;
- final result aggregator;
- final result seal and audit.

The overall status is:

```text
COMPLETE_NO_GO
```

#### Mechanical Post-hoc Analysis

- termination/profile builder;
- action and state-revisit analyzer;
- loop-fingerprint analyzer;
- cross-checkpoint or cross-seed matrix builder;
- mechanical result aggregator.

These components have deterministic mechanical-fact authority only.

#### Hierarchical Semantic Analysis

Include one summary row for each level:

- Level 1 — Matched-Group Analysis:
  `COMPLETE`
- Level 2 — Capability-Scoped Mechanism Discovery:
  `COMPLETE`
- Level 3 — Task-Family Projection:
  `COMPLETE`
- Level 4 — Cross-Capability Interaction / Coverage Synthesis:
  `COMPLETE`
- Level 5 — Global Mechanism Synthesis:
  `REJECTED`
- Level 6 — Independent Challenge:
  `INCOMPLETE`

Each is `SEMANTIC_ANALYZER` or
`SEMANTIC_ANALYZER + AGGREGATOR`.

Each has:

```text
semantic hypothesis only
```

as its authority boundary.

The detailed assets, denominators, request counts and internal
builders/verifiers are deferred to Module 2.

#### Canonical Evidence and Provenance Closure

Include:

- R132 file/log identity census;
- R132 PRIMARY117 identity-chain auditor:
  `COMPLETE`;
- R132 terminal semantic-provenance auditor:
  `INCOMPLETE`;
- Q2 semantic binding closure:
  `INCOMPLETE`;
- Harness-OFF canonical artifact closure:
  `INCOMPLETE`;
- final canonical-gap seal:
  `INCOMPLETE`.

The registry must link the completed R132 identity audit to:

```text
../../audits/ROUND1_CANONICAL_GAP_AUDIT.md
```

and:

```text
../../audits/evidence/round1_canonical_gap/
r132_primary117_identity_v1/
```

The Markdown link itself must be on one line.

#### Future Components

Include:

- Persistent Failure Memory builder:
  `HOLD`;
- Memory retriever/injector:
  `HOLD`;
- local hierarchical analyzer:
  `HOLD`;
- analyzer-supervision dataset builder:
  `HOLD`;
- Research Planner:
  `HOLD`;
- promotion/rollback gate:
  `HOLD`.

These rows must not imply that the components have been implemented or
validated.

### Server evidence rule

Where a server path and identity have already been independently
verified, record them.

Where they have not yet been registered, use:

```text
Exact binding deferred to Module 3 Asset Registry
```

Do not infer a path from a package name, conversation summary or commit
message.

### Repository-entry rule

Use actual current repository paths when known.

When the historical implementation or result is server-only, use:

```text
Server-side historical asset; repository binding pending Module 3
```

Do not fabricate a repository path.

- [ ] **Step 6: Update the Asset Consolidation Ledger**

Modify:

`docs/rounds/round1/ASSET_CONSOLIDATION_LEDGER.md`

At Module 1 closure, set the major-module status to:

```text
MODULE1_CLOSED_MODULE2_NOT_STARTED
```

Update the small-module table to:

| Module | Status |
|---|---|
| Design freeze | `COMPLETE` |
| Navigation and Component Map | `COMPLETE` |
| Hierarchical Analysis Asset Map | `PENDING` |
| Historical Asset Registry and Global Documentation Sync | `PENDING` |

The design-freeze closure evidence must record:

```text
4d1d3553f762a9b171a9672da0b9f34951195ed2
```

The Navigation and Component Map closure evidence must state:

```text
Closure commit identified through Git history; this ledger does not
self-embed its own commit SHA.
```

Add a `Documentation Sync Check` table:

| Document | Module 1 state |
|---|---|
| Parent major-module ledger | `UPDATED` |
| Round-1 README | `UPDATED` |
| Component Registry | `UPDATED` |
| Asset Registry | `NOT_APPLICABLE` |
| Hierarchical Analysis Ledger | `NOT_APPLICABLE` |
| Experiment Ledger | `CHECKED_NO_CHANGE_REQUIRED` |
| Code Map | `CHECKED_NO_CHANGE_REQUIRED` |
| Root README | `CHECKED_NO_CHANGE_REQUIRED` |

Set the next action to:

```text
Module 2 — Hierarchical Analysis Asset Map
```

- [ ] **Step 7: Run the deterministic documentation audit**

Run:

```bash
python - <<'PY'
from __future__ import annotations

import re
from pathlib import Path


round_readme = Path(
    "docs/rounds/round1/README.md"
)

registry = Path(
    "docs/rounds/round1/"
    "COMPONENT_REGISTRY.md"
)

ledger = Path(
    "docs/rounds/round1/"
    "ASSET_CONSOLIDATION_LEDGER.md"
)


for path in (
    round_readme,
    registry,
    ledger,
):
    assert path.is_file(), path

    text = path.read_text(
        encoding="utf-8"
    )

    for prohibited in (
        "TO" + "DO",
        "TB" + "D",
        "FIX" + "ME",
        "<" + "placeholder" + ">",
    ):
        assert prohibited not in text, (
            path,
            prohibited,
        )


readme_text = round_readme.read_text(
    encoding="utf-8"
)

required_readme_terms = (
    "# Round 1 — Single-Round Policy Improvement Validation",
    "ROUND1_SINGLE_ROUND_POLICY_IMPROVEMENT_VALIDATION",
    "COMPLETE_NO_GO",
    "LEVELS_1_TO_4_COMPLETE",
    "LEVEL_5_REJECTED",
    "LEVEL_6_INCOMPLETE",
    "Canonical evidence and provenance closure",
    "Failure Memory",
    "semantic analyzer output",
    "environment truth",
)

for term in required_readme_terms:
    assert term in readme_text, term


registry_text = registry.read_text(
    encoding="utf-8"
)

required_registry_terms = (
    "# Round-1 Component Registry",
    "R132 PRIMARY117",
    "117 source cases",
    "91 teacher outputs",
    "26 rejections",
    "351 Q2 state bindings",
    "Level 1 — Matched-Group Analysis",
    "Level 2 — Capability-Scoped Mechanism Discovery",
    "Level 3 — Task-Family Projection",
    "Level 4 — Cross-Capability Interaction / Coverage Synthesis",
    "Level 5 — Global Mechanism Synthesis",
    "Level 6 — Independent Challenge",
    "Persistent Failure Memory",
    "Research Planner",
)

for term in required_registry_terms:
    assert term in registry_text, term


assert "It is not Level 0" in readme_text
assert "Level 0" not in registry_text

assert (
    "Level 5 — Global Mechanism Synthesis"
    in registry_text
    and "`REJECTED`" in registry_text
)

assert (
    "Level 6 — Independent Challenge"
    in registry_text
    and "`INCOMPLETE`" in registry_text
)


link_pattern = re.compile(
    r"\[[^\]]+\]\(([^)]+)\)"
)

for source in (
    round_readme,
    registry,
):
    text = source.read_text(
        encoding="utf-8"
    )

    for target in link_pattern.findall(text):
        if "://" in target:
            continue

        target_without_anchor = (
            target.split("#", 1)[0]
        )

        if not target_without_anchor:
            continue

        resolved = (
            source.parent
            / target_without_anchor
        ).resolve()

        assert resolved.exists(), {
            "source":
                source.as_posix(),
            "target":
                target,
            "resolved":
                str(resolved),
        }


ledger_text = ledger.read_text(
    encoding="utf-8"
)

for term in (
    "MODULE1_CLOSED_MODULE2_NOT_STARTED",
    "4d1d3553f762a9b171a9672da0b9f34951195ed2",
    "Module 2 — Hierarchical Analysis Asset Map",
    "`UPDATED`",
    "`CHECKED_NO_CHANGE_REQUIRED`",
    "`NOT_APPLICABLE`",
):
    assert term in ledger_text, term


print(
    "ROUND1_NAVIGATION_COMPONENT_MAP_"
    "DOCUMENTATION_AUDIT_PASS"
)
PY
```

Expected:

```text
ROUND1_NAVIGATION_COMPONENT_MAP_DOCUMENTATION_AUDIT_PASS
```

- [ ] **Step 8: Confirm the exact change scope**

Run:

```bash
git diff \
  --check

git status \
  --short
```

Expected changed paths:

```text
 M docs/rounds/round1/ASSET_CONSOLIDATION_LEDGER.md
?? docs/rounds/round1/COMPONENT_REGISTRY.md
?? docs/rounds/round1/README.md
```

No other path may be modified.

- [ ] **Step 9: Stage and inspect**

Run:

```bash
git add \
  docs/rounds/round1/README.md \
  docs/rounds/round1/COMPONENT_REGISTRY.md \
  docs/rounds/round1/ASSET_CONSOLIDATION_LEDGER.md

git diff \
  --cached \
  --name-only

git diff \
  --cached \
  --check
```

Expected staged paths are exactly the three Module 1 files.

- [ ] **Step 10: Commit the completed small module**

Run:

```bash
git commit \
  -m "Add Round-1 navigation and component map"
```

Record:

```bash
export ROUND1_MODULE1_COMMIT="$(
  git rev-parse HEAD
)"
```

- [ ] **Step 11: Re-run the audit after commit**

Run the same deterministic documentation audit from Step 7.

Expected:

```text
ROUND1_NAVIGATION_COMPONENT_MAP_DOCUMENTATION_AUDIT_PASS
```

Then run:

```bash
test -z "$(
  git status --porcelain
)"
```

Expected return code:

```text
0
```

- [ ] **Step 12: Push and verify remote equality**

Run:

```bash
git push \
  origin \
  docs/round1-research-assets-v1

git fetch \
  origin \
  docs/round1-research-assets-v1

test "$(
  git rev-parse HEAD
)" = "$(
  git rev-parse \
    origin/docs/round1-research-assets-v1
)"

test -z "$(
  git status --porcelain
)"
```

Expected:

```text
local HEAD == remote branch HEAD
worktree clean
```

Print:

```bash
echo \
  "ROUND1_NAVIGATION_COMPONENT_MAP_CLOSED"

echo \
  "ROUND1_MODULE1_COMMIT=$ROUND1_MODULE1_COMMIT"
```

---

## Acceptance Gate

Module 1 is complete only when:

```text
Round-1 README exists
Component Registry exists
component roles and authorities are explicit
workflow stages and hierarchical levels are distinct
provenance closure is not called Level 0
Level 1-4 are recorded complete
Level 5 is recorded rejected
Level 6 is recorded incomplete
Failure Memory is recorded HOLD
all repository-relative links resolve
only the three approved files changed
one single-purpose commit exists
local and remote heads match
worktree is clean
```

## Handoff

After Module 1 closes, the next independently planned and committed
small module is:

```text
Module 2 — Hierarchical Analysis Asset Map
```

Module 2 will bind each hierarchical level to its builders, analyzers,
verifiers, populations, denominators, requests, outputs and conclusion
boundaries.

It will not modify the scientific results of Levels 1-6.
