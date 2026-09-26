# Round-1 Hierarchical Analysis Asset Map V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development or superpowers:executing-plans
> to implement this plan task-by-task. Steps use checkbox syntax for
> tracking.

**Goal:** Create one canonical repository-level map of Round-1
hierarchical semantic analysis Levels 1-6, binding every level to its
actual evidence universe, builders, analyzers, validators, verifiers,
requests, results, status and conclusion boundary.

**Architecture:** Module 2 is documentation and provenance
consolidation only. It first performs a read-only inventory of existing
historical analysis assets on the server and in Git history. Only
verified assets and counts may then enter
`docs/rounds/round1/HIERARCHICAL_ANALYSIS.md`. The module does not rerun
any model, regenerate any analysis result or repair missing historical
evidence.

**Tech Stack:** GitHub-flavored Markdown, Python 3.12 read-only
inventory/audit scripts executed inline, POSIX shell read-only file
inspection, Git.

## Global Constraints

- Work only on branch:
  `docs/round1-research-assets-v1`.
- Module 1 closure base:
  `e0351af647ae4480d87f1ee0353d3c99137f0835`.
- Frozen Module 2 plan commit:
  `b99d54424a513fdf019056595f58d5d0b605d3d5`.
- Before Module 2 implementation begins, the frozen plan commit must be
  an ancestor of the current HEAD and the worktree must be clean.
- Do not run OpenAI, Claude, Gemini or any other semantic model.
- Do not run ALFWorld.
- Do not retrain pi0, pi1 or any analyzer.
- Do not regenerate Level 1-6 outputs.
- Do not move or rename historical server artifacts.
- Do not overwrite historical artifacts.
- Do not replace existing SHA-256 identities.
- Do not infer an asset path from a remembered package name.
- Do not infer a population or denominator from an output row count.
- Observed-zero claims must remain distinct from missing evidence.
- Semantic hypotheses remain distinct from environment truth.
- Hierarchical analysis Levels remain numbered 1 through 6.
- Canonical evidence/provenance closure is not a hierarchical-analysis
  level.
- Level 1 remains `COMPLETE`.
- Level 2 remains `COMPLETE`.
- Level 3 remains `COMPLETE`.
- Level 4 remains `COMPLETE`.
- Level 5 remains `REJECTED`.
- Level 6 remains `INCOMPLETE`.
- Module 2 may clarify asset identities and execution structure, but it
  may not upgrade or downgrade those frozen scientific dispositions.
- Failure Memory remains `HOLD`.
- Root `README.md`, project `EXPERIMENT_LEDGER.md` and
  `docs/code_map.md` remain unchanged in this module.
- Exact comprehensive path/SHA registration across all Round-1 assets
  remains Module 3 responsibility.
- Module 2 closes in one single-purpose implementation commit.

---

## File Structure

### Create

`docs/rounds/round1/HIERARCHICAL_ANALYSIS.md`

Responsibility:

- define the Level 1-6 semantic-analysis hierarchy;
- distinguish each level's research question and role;
- record verified populations and denominators;
- record builders, analyzers, validators and verifiers;
- record request/execution structure;
- record authoritative output identities when verified;
- record status and conclusion boundaries;
- explicitly preserve missingness and rejection semantics.

### Modify

`docs/rounds/round1/README.md`

Responsibility:

- replace the current statement that the detailed hierarchy is deferred;
- add a relative link to `./HIERARCHICAL_ANALYSIS.md`;
- preserve all existing scientific statuses.

### Modify

`docs/rounds/round1/COMPONENT_REGISTRY.md`

Responsibility:

- replace Module-2-pending references in the Level 1-6 summary rows;
- link the hierarchical section to the new canonical hierarchy ledger;
- do not duplicate the full Level-specific asset inventory.

### Modify

`docs/rounds/round1/ASSET_CONSOLIDATION_LEDGER.md`

Responsibility:

- close Module 2 after implementation;
- preserve Module 1 closure;
- set Module 3 as the next small module;
- update Documentation Sync Check.

### Unchanged

The following remain untouched:

- root `README.md`;
- `docs/experiments/EXPERIMENT_LEDGER.md`;
- `docs/code_map.md`;
- `docs/audits/ROUND1_CANONICAL_GAP_AUDIT.md`;
- files below `docs/audits/evidence/`;
- source code;
- model artifacts;
- raw semantic outputs;
- evaluation artifacts.

---

# Task 1: Read-Only Hierarchical Analysis Asset Inventory

## Purpose

Before writing the hierarchy ledger, discover and verify the actual
historical Level 1-6 assets.

This task writes no repository file.

Temporary inventory output may be written only under `/tmp`.

## Known scientific anchors

The following are expected historical anchors derived from previously
frozen analysis records.

They are audit expectations, not permission to manufacture the final
ledger.

### Level-1 / Level-2 input universe anchor

Expected:

```text
authorized matched groups = 85

semantic available groups = 73
semantic unavailable groups = 12

complete-core groups = 50
partial-validated groups = 23
```

The implementation must verify these values against actual historical
artifacts before recording them as canonical.

If the existing artifacts disagree, stop Module 2 and report the
disagreement.

### Level-2 mechanism anchor

Expected:

```text
canonical mechanisms = 30
```

Final missingness-status breakdown must come from the actual Level-2
result artifact rather than memory.

### Level-3 projection anchors

Expected:

```text
frozen tasks = 17
task families = 6
Level-2 mechanisms = 30
mechanism × family cells = 180
semantic family requests = 6
```

All must be verified from the actual Level-3 deterministic census and
execution/result assets.

### Level-4 interaction anchors

Expected historical summary:

```text
evaluated cross-capability relation pairs = 148
candidate directional relations = 29
```

These relations remain semantic candidate directions.

They are not causal edges.

The implementation must verify both values from the actual Level-4
result/audit before writing them into the canonical ledger.

### Level-5 status anchor

Expected:

```text
status = REJECTED
```

The exact rejection reason and evidence-closure blocker must be copied
from the actual Level-5 audit or rejection artifact.

Do not reconstruct the reason from conversation history.

### Level-6 status anchor

Expected:

```text
status = INCOMPLETE
```

The implementation must determine only what the historical evidence
supports about Level-6 execution state.

Do not guess whether it was never called, partially built, partially
executed or merely not sealed.

If that distinction cannot be established, record:

```text
Final completed Level-6 result is not registered.
Exact execution-state binding deferred until source evidence is located.
```

---

## Step 1.1: Verify the fixed Git state

Run:

```bash
test "$(
  git branch --show-current
)" = \
"docs/round1-research-assets-v1"

git merge-base \
  --is-ancestor \
  "b99d54424a513fdf019056595f58d5d0b605d3d5" \
  HEAD

test -z "$(
  git status --porcelain
)"
```

All must return `0`.

---

## Step 1.2: Verify current Round-1 navigation assets

Run:

```bash
python - <<'PY'
from pathlib import Path


required = (
    Path(
        "docs/rounds/round1/"
        "README.md"
    ),
    Path(
        "docs/rounds/round1/"
        "COMPONENT_REGISTRY.md"
    ),
    Path(
        "docs/rounds/round1/"
        "ASSET_CONSOLIDATION_LEDGER.md"
    ),
    Path(
        "docs/audits/"
        "ROUND1_CANONICAL_GAP_AUDIT.md"
    ),
)

missing = [
    path.as_posix()
    for path in required
    if not path.is_file()
]

assert not missing, missing

assert not Path(
    "docs/rounds/round1/"
    "HIERARCHICAL_ANALYSIS.md"
).exists()

print(
    "ROUND1_MODULE2_SOURCE_STATE_PASS"
)
PY
```

Expected:

```text
ROUND1_MODULE2_SOURCE_STATE_PASS
```

---

## Step 1.3: Generate a bounded read-only candidate inventory

The first inventory is discovery only.

Run:

```bash
export HIERARCHY_INV="/tmp/round1_hierarchy_asset_candidates_v1.txt"

: > "$HIERARCHY_INV"

for root in \
  /data/run01/scwb204/pchsi \
  /data/home/scwb204/run/pchsi
do
  if test -d "$root"
  then
    echo \
      "===== ROOT: $root =====" \
      >> "$HIERARCHY_INV"

    find "$root" \
      -maxdepth 8 \
      \( \
        -iname '*level1*' -o \
        -iname '*level_1*' -o \
        -iname '*matched_group*' -o \
        -iname '*level2*' -o \
        -iname '*level_2*' -o \
        -iname '*mechanism*' -o \
        -iname '*level3*' -o \
        -iname '*level_3*' -o \
        -iname '*task_family*' -o \
        -iname '*level4*' -o \
        -iname '*level_4*' -o \
        -iname '*cross_capability*' -o \
        -iname '*level5*' -o \
        -iname '*level_5*' -o \
        -iname '*global_synthesis*' -o \
        -iname '*level6*' -o \
        -iname '*level_6*' -o \
        -iname '*challenge*' \
      \) \
      -print \
      2>/dev/null \
      | sort \
      >> "$HIERARCHY_INV"
  fi
done

echo \
  "ROUND1_MODULE2_CANDIDATE_INVENTORY_WRITTEN"

wc -l \
  "$HIERARCHY_INV"
```

This command:

- does not alter any historical file;
- does not execute any model;
- does not follow a candidate by inference;
- produces only a discovery list under `/tmp`.

---

## Step 1.4: Search repository Git history for hierarchy identifiers

Run:

```bash
git log \
  --all \
  --oneline \
  --decorate \
  --regexp-ignore-case \
  --grep='matched.group\|mechanism\|task.family\|cross.capability\|global.synthesis\|independent.challenge' \
  > \
  /tmp/round1_hierarchy_git_history_v1.txt

echo \
  "ROUND1_MODULE2_GIT_HISTORY_INVENTORY_WRITTEN"

wc -l \
  /tmp/round1_hierarchy_git_history_v1.txt
```

This is provenance support only.

Commit messages cannot override raw evidence.

---

## Step 1.5: Classify candidate assets

For every candidate that appears to belong to Levels 1-6, record in a
temporary inventory:

```text
level
logical role
absolute path
file type
size
sha256
producer script if identifiable
input identity if identifiable
output identity if identifiable
status artifact
audit artifact
request artifact
raw semantic output
deterministic census
verifier output
```

Do not invent a value that cannot be established.

The temporary structured file is:

```text
/tmp/round1_hierarchy_verified_inventory_v1.jsonl
```

Every row must include:

```json
{
  "level": 1,
  "logical_role": "example",
  "path": "/absolute/path",
  "exists": true,
  "kind": "file",
  "size_bytes": 123,
  "sha256": "lowercase-hex",
  "authority": "source-or-derived",
  "verification_note": "verified from filesystem"
}
```

No repository file is created in this step.

---

## Step 1.6: Freeze Level-specific evidence bundles

For each Level 1-6, identify when available:

```text
design / protocol
deterministic census
input evidence pack
request manifest
provider request
provider response
semantic output
local shadow output
schema
semantic validator
deterministic verifier
aggregation result
audit result
seal / checksum
rejection artifact
```

Not every level is required to contain every artifact class.

The final ledger must record absent classes explicitly rather than
inventing them.

---

# Task 2: Construct the Canonical Hierarchical Analysis Ledger

## File

Create:

```text
docs/rounds/round1/HIERARCHICAL_ANALYSIS.md
```

## Required top-level structure

The exact heading is:

```markdown
# Round-1 Hierarchical Semantic Analysis
```

Required headings:

```markdown
## Purpose
## Scientific Authority Boundary
## Hierarchy at a Glance
## Shared Evidence and Missingness Rules
## Level 1 — Matched-Group Analysis
## Level 2 — Capability-Scoped Mechanism Discovery
## Level 3 — Task-Family Projection
## Level 4 — Cross-Capability Interaction / Coverage Synthesis
## Level 5 — Global Mechanism Synthesis
## Level 6 — Independent Challenge
## Cross-Level Data Flow
## What the Hierarchy Establishes
## What the Hierarchy Does Not Establish
## Relationship to Canonical Provenance Closure
## Relationship to Future Failure Memory
## Authoritative Asset Index
## Remaining Historical Gaps
```

---

## Shared Level template

Each Level 1-6 section must contain:

```markdown
### Research Question
### Scientific Role
### Frozen Inputs
### Population and Denominator
### Internal Components
### Semantic Execution
### Deterministic Validation
### Outputs
### Status
### Conclusion Boundary
### Downstream Consumer
### Authoritative Assets
```

Do not omit a subsection just because a historical artifact is missing.

Use an explicit unresolved statement instead.

---

# Level 1 Requirements

## Name

```text
Level 1 — Matched-Group Analysis
```

## Status

```text
COMPLETE
```

## Role

Explain that Level 1 compares matched policy/trajectory evidence at the
local grouped level.

It separates local semantic interpretation from higher-level reusable
mechanism discovery.

## Required internal-component inventory

When verified, record:

```text
matched evidence-pack builder
deterministic matched-group census
request builder
external semantic analyzer
local shadow analyzer if actually executed
scientific schema
semantic validator
deterministic verifier
claim/result aggregator
```

Do not claim a local shadow execution if it was only planned.

## Population

Record the actual matched-group universe from the frozen artifacts.

If the verified universe is:

```text
85 groups
73 semantic available
12 semantic unavailable
50 complete-core
23 partial-validated
```

record all five numbers and definitions.

If not, stop and investigate before closure.

## Missingness

Explicitly distinguish:

```text
validated group with zero relevant claims
```

from:

```text
group with unavailable semantic output
```

They are not equivalent.

---

# Level 2 Requirements

## Name

```text
Level 2 — Capability-Scoped Mechanism Discovery
```

## Status

```text
COMPLETE
```

## Role

Explain that Level 2 consolidates Level-1 primary semantic claims into
capability-scoped reusable candidate mechanisms.

It does not perform causal verification.

## Mechanism taxonomy

Verify and record the exact count of canonical mechanisms.

Expected anchor:

```text
30 canonical mechanisms
```

## Deterministic denominator

The ledger must preserve:

```text
all validated denominator
complete-core denominator
observed-zero groups
semantic-unavailable groups
```

Never use only groups containing a mechanism claim as prevalence
denominator.

## Membership

Record whether the frozen output uses:

```text
exclusive primary membership
RESIDUAL
UNEXPLAINED
counterevidence references
```

only if verified in the actual Level-2 artifacts.

## Missingness status

Record the actual frozen mechanism missingness classifications.

Do not recreate those classes by re-running a new algorithm.

---

# Level 3 Requirements

## Name

```text
Level 3 — Task-Family Projection
```

## Status

```text
COMPLETE
```

## Expected verified anchors

```text
17 frozen task identities
6 ALFWorld task families
30 frozen Level-2 mechanisms
180 deterministic mechanism × family cells
6 semantic family requests
```

All must be verified.

## Family limitation

If a family contains only one frozen task, preserve the explicit
single-task limitation.

Do not convert a single-task observation into a cross-task family
generalization.

## Taxonomy boundary

Level 3 must not:

```text
create a new canonical mechanism
rename Level-2 mechanisms
merge Level-2 mechanisms
split Level-2 mechanisms
promote a global missingness status
```

It projects the frozen Level-2 taxonomy only.

---

# Level 4 Requirements

## Name

```text
Level 4 — Cross-Capability Interaction / Coverage Synthesis
```

## Status

```text
COMPLETE
```

## Role

Explain that Level 4 studies candidate relationships between frozen
capability-scoped mechanisms/components.

Possible relation semantics may include:

```text
co-occurrence
ordering
coverage
possible upstream/downstream relation
```

but only according to the frozen schema.

## Expected anchors

Verify:

```text
148 evaluated cross-capability relation pairs
29 candidate directional relations
```

before entering them into the final ledger.

## Causal boundary

Explicitly state:

```text
candidate directional relation
≠
verified causal edge
```

---

# Level 5 Requirements

## Name

```text
Level 5 — Global Mechanism Synthesis
```

## Status

```text
REJECTED
```

## Role

Describe the attempted compression of Levels 1-4 into a global
mechanism story.

## Rejection

The final ledger must quote no long source text.

It must instead accurately summarize the actual rejection artifact.

Record:

```text
attempted
audited
rejected
```

and identify the exact audit/rejection asset.

Do not label Level 5 complete merely because a candidate synthesis file
exists.

## Downstream

Rejected Level-5 output may remain historical evidence.

It may not be treated as an approved global mechanism conclusion.

---

# Level 6 Requirements

## Name

```text
Level 6 — Independent Challenge
```

## Status

```text
INCOMPLETE
```

## Role

The intended role is to challenge high-level claims using
counterevidence, alternative explanations and residual cases.

## Historical-state rule

Only describe the execution state actually established by source
artifacts.

If a final sealed challenge result cannot be found, state exactly:

```text
No final completed Level-6 result is registered.
```

Do not upgrade it based on a design or request package.

---

# Shared Authority Boundary

The document must prominently state:

```text
hierarchical semantic analysis
=
diagnostic hypothesis generation
```

and:

```text
hierarchical semantic analysis
≠
environment-execution truth
```

and:

```text
hierarchical semantic analysis
≠
fresh causal verification
```

and:

```text
hierarchical semantic analysis completion
≠
policy improvement
```

---

# Relationship to Provenance Closure

The document must state:

```text
Canonical evidence / provenance closure
is a sibling evidence-governance workstream.

It is not part of the Level 1-6 numbering.
```

The current canonical audit link is:

```text
../../audits/ROUND1_CANONICAL_GAP_AUDIT.md
```

---

# Relationship to Failure Memory

The document must state:

```text
Failure Memory = HOLD
```

and explain:

- semantic analysis may later help propose Memory records;
- unresolved provenance cannot silently become Memory truth;
- Memory records must preserve pointers to source evidence;
- no current Level-1-6 output is itself an environment-verified Memory
  record merely because the semantic analysis completed.

---

# Task 3: Synchronize Round-Level Navigation

## README

Modify:

```text
docs/rounds/round1/README.md
```

Add:

```markdown
[Hierarchical Analysis Ledger](./HIERARCHICAL_ANALYSIS.md)
```

under Round-level records.

Replace the statement that detailed Level 1-6 assets are deferred with
a link to the new ledger.

Do not alter any status.

---

## Component Registry

Modify:

```text
docs/rounds/round1/COMPONENT_REGISTRY.md
```

In the hierarchical-analysis section add a clear link to:

```text
./HIERARCHICAL_ANALYSIS.md
```

Remove language saying the detailed hierarchy is pending Module 2.

Do not duplicate all assets into the Component Registry.

---

## Asset Consolidation Ledger

Modify:

```text
docs/rounds/round1/ASSET_CONSOLIDATION_LEDGER.md
```

At closure set:

```text
MODULE2_CLOSED_MODULE3_NOT_STARTED
```

Small-module states:

```text
Design freeze                         COMPLETE
Navigation and Component Map          COMPLETE
Hierarchical Analysis Asset Map       COMPLETE
Historical Asset Registry + Docs Sync PENDING
```

Module 2 closure commit must be recoverable through Git history.

Do not self-embed the commit SHA in the same commit.

---

# Task 4: Deterministic Module-2 Documentation Audit

Run a deterministic audit before staging.

The audit must verify:

```text
HIERARCHICAL_ANALYSIS.md exists

Level 1 name exists
Level 2 name exists
Level 3 name exists
Level 4 name exists
Level 5 name exists
Level 6 name exists

Level 1 status COMPLETE
Level 2 status COMPLETE
Level 3 status COMPLETE
Level 4 status COMPLETE
Level 5 status REJECTED
Level 6 status INCOMPLETE

provenance closure is not numbered as a level

Failure Memory remains HOLD

semantic analysis is not described as environment truth

README link resolves

Component Registry link resolves

all repository-relative links resolve

no unverified asset path is invented
```

Use split string literals for placeholder-token scanning so the audit
does not self-trigger on its own source.

Example:

```python
for prohibited in (
    "TO" + "DO",
    "TB" + "D",
    "FIX" + "ME",
    "<" + "placeholder" + ">",
):
    ...
```

---

# Task 5: Exact Change Scope

Expected repository paths for the implementation commit:

```text
M  docs/rounds/round1/ASSET_CONSOLIDATION_LEDGER.md
M  docs/rounds/round1/COMPONENT_REGISTRY.md
M  docs/rounds/round1/README.md
A  docs/rounds/round1/HIERARCHICAL_ANALYSIS.md
```

No other repository path may be staged.

---

# Task 6: Commit and Closure

Commit message:

```text
Add Round-1 hierarchical analysis asset map
```

After commit:

```text
re-run deterministic documentation audit
worktree clean
push
fetch
local HEAD == remote branch HEAD
worktree clean
```

Final marker:

```text
ROUND1_HIERARCHICAL_ANALYSIS_ASSET_MAP_CLOSED
```

---

# Acceptance Gate

Module 2 closes only if all of the following hold:

```text
actual server assets were inventoried read-only

no model/environment was rerun

Level 1-6 names are canonical

actual populations/denominators are recorded

observed-zero and missing evidence are distinct

builders/analyzers/validators/verifiers are mapped

actual request/execution structure is recorded

actual output/audit identities are recorded when verified

Level 1 = COMPLETE
Level 2 = COMPLETE
Level 3 = COMPLETE
Level 4 = COMPLETE
Level 5 = REJECTED
Level 6 = INCOMPLETE

Level-4 directional relations are not called causal edges

Level-5 candidate synthesis is not upgraded

Level-6 design/request artifacts are not treated as a final result

canonical provenance closure is not part of Level numbering

Failure Memory remains HOLD

README and Component Registry point to the hierarchy ledger

only four approved repository files change

one single-purpose closure commit is pushed

local and remote heads match
```

---

# Handoff

After Module 2 closes, the next small module is:

```text
Module 3 —
Historical Asset Registry and Global Documentation Sync
```

That module will:

```text
create ASSET_REGISTRY.md

synchronize root README

synchronize EXPERIMENT_LEDGER.md

synchronize docs/code_map.md

extend MODULE_CLOSURE_POLICY.md
with the Documentation Sync Check

bind remaining exact server paths,
SHA-256 identities and retention roles
```

Module 3 remains separate from Module 2.
