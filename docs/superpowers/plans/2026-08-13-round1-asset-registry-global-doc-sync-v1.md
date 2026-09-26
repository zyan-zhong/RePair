# Round-1 Historical Asset Registry and Global Documentation Sync V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development or superpowers:executing-plans
> to implement this plan task-by-task. Steps use checkbox syntax for
> tracking.

**Goal:** Create the canonical Round-1 asset and identity registry, then
synchronize all project-level documentation to the completed Round-1
scientific state without modifying historical evidence.

**Architecture:** Module 3 is documentation, identity registration and
repository-navigation consolidation only. It first performs a read-only
inventory of the major Round-1 workflow assets and verifies their actual
server paths, existing cryptographic identities, producers, consumers and
retention roles. Only verified identities may enter
`docs/rounds/round1/ASSET_REGISTRY.md`. After the asset registry is
closed, the root README, Experiment Ledger, Code Map, Round-1 navigation,
Component Registry, Module Closure Policy and parent consolidation ledger
are synchronized to that same state.

**Tech Stack:** GitHub-flavored Markdown, Python 3.12 read-only inventory
and deterministic documentation-audit scripts, POSIX shell, Git.

## Global Constraints

- Work only on branch:
  `docs/round1-research-assets-v1`.
- Module-2 closure base:
  `a51fb7a62f0581c9090f6982075000c22130bcaf`.
- Module 3 implementation may begin only after this implementation plan
  has been committed, pushed, verified against the remote branch and the
  worktree is clean.
- At implementation start, derive the frozen plan commit from Git history
  for this exact plan path rather than embedding the plan's own unknown
  future commit SHA inside itself.
- Do not run OpenAI, Anthropic, Gemini or any other semantic model.
- Do not run ALFWorld.
- Do not retrain pi0, pi1, an Analyzer or any other model.
- Do not generate pi2.
- Do not regenerate historical semantic outputs.
- Do not regenerate historical environment results.
- Do not move historical server evidence.
- Do not overwrite historical server evidence.
- Do not replace an existing historical SHA-256 identity.
- Do not manufacture a new historical package seal to hide the absence
  of an old one.
- A verification hash computed by Module 3 may be used to check current
  bytes, but it must not be misrepresented as an original historical
  seal.
- Do not infer an asset path from a remembered package name.
- Do not infer a producer or consumer solely from filename similarity.
- Do not infer an authoritative result from a derived summary if a lower
  source-of-truth artifact exists.
- Preserve the Round-1 Harness-OFF policy result as `COMPLETE_NO_GO`.
- Preserve hierarchical Levels 1-4 as `COMPLETE`.
- Preserve Level 5 as `REJECTED`.
- Preserve Level 6 as `INCOMPLETE`.
- Preserve canonical evidence and provenance closure as `IN_PROGRESS`.
- Preserve Failure Memory as `HOLD`.
- Canonical evidence and provenance closure is not a hierarchical-analysis
  level.
- Hierarchical-analysis Levels remain numbered 1 through 6.
- Semantic hypotheses do not become environment truth.
- Candidate directional relations do not become causal edges.
- Harness-assisted or Memory-assisted behavior does not become policy
  internalization.
- The current v3.1/E0-E20 roadmap must remain distinguishable from the
  completed historical Round-1 scientific event.
- Do not relabel the historical Round-1 run as one of E0-E20 unless an
  original frozen experiment identity explicitly establishes that
  mapping.
- Module 3 closes in one single-purpose implementation commit after its
  plan-freeze commit has already been closed.

---

## Source-of-Truth Order

When documentation disagrees, resolve it in this order:

1. original server-side raw evidence;
2. original manifest, ledger or cryptographic seal;
3. deterministic audit output;
4. Round-1 Asset Registry;
5. Component Registry or Hierarchical Analysis Ledger;
6. Experiment Ledger;
7. root README.

A higher-level summary may not override lower-level evidence.

---

## File Structure

### Create

`docs/rounds/round1/ASSET_REGISTRY.md`

Responsibility:

- register every major Round-1 asset family;
- bind logical role to verified server path;
- bind repository mirror where one exists;
- record producer and downstream consumer;
- record population or file count;
- record existing SHA-256 or package/root seal;
- distinguish historical identity from Module-3 verification hash;
- record status;
- record retention rule;
- classify each asset as authoritative, derived or navigational.

### Modify

`README.md`

Responsibility:

- preserve the canonical research protocol;
- replace stale top-level research-status statements;
- expose the completed Round-1 `NO-GO`;
- expose provenance closure as `IN_PROGRESS`;
- expose Failure Memory as `HOLD`;
- link to the Round-1 overview, Asset Registry, Experiment Ledger,
  current provenance audit, protocol and Code Map;
- distinguish completed Round-1 from the current/future E0-E20 roadmap.

### Modify

`docs/rounds/round1/README.md`

Responsibility:

- add the Asset Registry to the Round-1 Documentation Map;
- remove the stale statement that Module 2 is the next small module;
- record historical-asset consolidation as complete after Module 3
  closes;
- retain provenance closure as the unresolved scientific/evidence
  workstream;
- retain Failure Memory as `HOLD`.

### Modify

`docs/rounds/round1/COMPONENT_REGISTRY.md`

Responsibility:

- replace the statement that exact asset identity is still awaiting
  Module 3;
- link exact identities to `./ASSET_REGISTRY.md`;
- preserve component roles, authority boundaries and statuses;
- update its Documentation Sync State.

### Modify

`docs/experiments/EXPERIMENT_LEDGER.md`

Responsibility:

- add a project-wide completed Round-1 scientific-event record;
- do not falsely map the completed Round-1 event onto E0-E20;
- distinguish the completed historical Round-1 event from the active
  v3.1/E0-E20 roadmap;
- record Round-1 training completion and Harness-OFF `NO-GO`;
- record hierarchical Levels 1-4 complete, Level 5 rejected and Level 6
  incomplete;
- record provenance closure `IN_PROGRESS`;
- record Failure Memory `HOLD`;
- remove or qualify any global wording that incorrectly implies no
  Harness-OFF Round-1 evaluation was ever executed.

### Modify

`docs/code_map.md`

Responsibility:

- place the current Round-1 research/component navigation before older
  Runtime Core and S1 engineering history;
- link to Component Registry, Asset Registry, Hierarchical Analysis
  Ledger and current provenance audit;
- retain historical Runtime Core and S1 implementation details;
- do not claim that documentation components execute scientific work.

### Modify

`docs/protocol/MODULE_CLOSURE_POLICY.md`

Responsibility:

- add the frozen Documentation Sync Check;
- require each small-module closure to check the parent ledger,
  Round-1 README when applicable, Component Registry, Asset Registry,
  Hierarchical Analysis Ledger, Experiment Ledger, Code Map and root
  README;
- record each checked item as `UPDATED`,
  `CHECKED_NO_CHANGE_REQUIRED` or `NOT_APPLICABLE`;
- preserve the existing small-module commit/push/remote-equality rules.

### Modify

`docs/rounds/round1/ASSET_CONSOLIDATION_LEDGER.md`

Responsibility:

- close Module 3;
- close the Round-1 Research Asset Consolidation major module;
- record the Module-3 read-only asset audit;
- record Documentation Sync Check results;
- identify remaining provenance closure as a separate workstream;
- preserve Failure Memory `HOLD`.

### Check, normally unchanged

`docs/rounds/round1/HIERARCHICAL_ANALYSIS.md`

Responsibility:

- verify relative links and status consistency;
- do not rewrite its frozen Level 1-6 scientific content unless a
  deterministic broken-link or identity defect is found.

`docs/audits/ROUND1_CANONICAL_GAP_AUDIT.md`

Responsibility:

- remains the current provenance-closure entry point;
- no scientific audit content changes in Module 3.

---

# Task 1: Verify Module-3 Execution Preconditions

## Purpose

Bind implementation to the pushed plan and a clean repository state.

## Step 1.1: Resolve the frozen plan commit

Run:

```bash
export BRANCH="docs/round1-research-assets-v1"

export MODULE3_PLAN_PATH="docs/superpowers/plans/2026-08-13-round1-asset-registry-global-doc-sync-v1.md"

export MODULE3_PLAN_COMMIT="$(
  git log \
    -1 \
    --format='%H' \
    -- "$MODULE3_PLAN_PATH"
)"

test -n "$MODULE3_PLAN_COMMIT"

echo \
  "MODULE3_PLAN_COMMIT=$MODULE3_PLAN_COMMIT"
```

The resolved commit must be the dedicated plan-freeze commit.

## Step 1.2: Verify branch, ancestry, remote and clean worktree

Run:

```bash
test "$(
  git branch --show-current
)" = "$BRANCH"

git merge-base \
  --is-ancestor \
  "a51fb7a62f0581c9090f6982075000c22130bcaf" \
  HEAD

git merge-base \
  --is-ancestor \
  "$MODULE3_PLAN_COMMIT" \
  HEAD

git fetch \
  origin \
  "$BRANCH"

git merge-base \
  --is-ancestor \
  "$MODULE3_PLAN_COMMIT" \
  "origin/$BRANCH"

test -z "$(
  git status --porcelain
)"
```

All commands must succeed before Task 2.

---

# Task 2: Read-Only Major Asset Inventory

## Purpose

Identify the actual major Round-1 server assets before creating the
canonical registry.

This task modifies no repository file.

Temporary outputs may be written only under `/tmp`.

## Representative server root

Module 2 proved that the corresponding candidate paths beneath:

```text
/data/home/scwb204/run/pchsi
/data/run01/scwb204/pchsi
```

refer to the same underlying filesystem objects for the audited
hierarchical candidate set.

Module 3 uses:

```text
/data/run01/scwb204/pchsi
```

as the representative inspection root while retaining the mirror result
in the parent ledger.

This is a de-duplication choice, not a claim that `/data/home` is a
different scientific copy.

## Major workflow asset classes

The inventory must cover:

```text
A. governance and runtime foundation
B. pi0 trajectory / development evidence
C. strong-model proposal / R132
D. Q2 environment validation
E. training-data construction
F. pi1 training
G. Harness-OFF evaluation
H. mechanical post-hoc analysis
I. hierarchical semantic analysis
J. canonical evidence and provenance closure
K. Failure Memory handoff boundary
```

Future Memory, local Analyzer and Research Planner artifacts are not
treated as completed Round-1 assets.

## Step 2.1: Generate bounded candidate inventory

Run:

```bash
export ROUND1_ROOT="/data/run01/scwb204/pchsi"

export MODULE3_CANDIDATES="/tmp/round1_module3_major_asset_candidates_v1.txt"

: > "$MODULE3_CANDIDATES"

find "$ROUND1_ROOT" \
  -maxdepth 9 \
  \( \
    -iname '*round1*' -o \
    -iname '*pi0*' -o \
    -iname '*trajectory*' -o \
    -iname '*strong*proposer*' -o \
    -iname '*offline*proposer*' -o \
    -iname '*r132*' -o \
    -iname '*primary117*' -o \
    -iname '*q2*' -o \
    -iname '*training*data*' -o \
    -iname '*train17*' -o \
    -iname '*train31*' -o \
    -iname '*train47*' -o \
    -iname '*pi1*' -o \
    -iname '*harness*off*' -o \
    -iname '*select*v2*' -o \
    -iname '*mechanical*' -o \
    -iname '*posthoc*' -o \
    -iname '*hierarchical*' -o \
    -iname '*matched_group*' -o \
    -iname '*mechanism*' -o \
    -iname '*task_family*' -o \
    -iname '*cross_capability*' -o \
    -iname '*global*synthesis*' -o \
    -iname '*canonical*gap*' -o \
    -iname '*provenance*' \
  \) \
  -print \
  2>/dev/null \
  | sort \
  > "$MODULE3_CANDIDATES"

echo \
  "ROUND1_MODULE3_CANDIDATE_INVENTORY_WRITTEN"

wc -l \
  "$MODULE3_CANDIDATES"
```

This discovery list is not itself canonical evidence.

## Step 2.2: Build structured verified inventory

Create only:

```text
/tmp/round1_module3_verified_major_assets_v1.jsonl
```

Every row must contain:

```text
logical_name
workflow_stage
scientific_role
server_path
repository_path
producer
downstream_consumer
population_or_file_count
historical_identity_kind
historical_identity_value
verification_sha256
status
retention_rule
authority_class
source_evidence
verification_note
```

Rules:

- `repository_path` is null when no repository mirror exists.
- `historical_identity_kind` must describe the original identity source,
  such as `FILE_SHA256`, `ROOT_SEAL`, `PACKAGE_FREEZE_ROOT`,
  `COMMIT_SHA` or `NO_ORIGINAL_ROOT_SEAL_REGISTERED`.
- `historical_identity_value` must be copied from actual evidence.
- `verification_sha256` may be recomputed from a file during Module 3.
- A verification hash must not replace an original package/root seal.
- Unknown producer/consumer/path fields must not be guessed.
- A major executed workflow stage without a defensible authoritative
  identity is a STOP condition for final Module-3 closure.

## Step 2.3: Verify previously established fixed anchors

At minimum, verify against the actual files:

### R132 primary proposer

Expected historical anchors:

```text
primary cases = 117
teacher outputs = 91
rejections = 26
Q2 bindings = 351
package freeze root =
794727df6157715d3c8e04156f97e53300ef9107ca793d215caec447cab964b5
```

Representative known paths to verify, not blindly trust:

```text
/data/run01/scwb204/pchsi/p2/p2_strong_offline_proposer_openai_v1_r1_3_2

/data/run01/scwb204/pchsi/p2/p2_strong_offline_proposer_openai_v1_run_r1_3_2

/data/run01/scwb204/pchsi/p2/logs/p2_r132_primary117/primary117.log

/data/run01/scwb204/pchsi/p2/p2_pre_model_call_package_v1/contracts/q2_state_bindings.jsonl
```

### Harness-OFF evaluation

Verify the actual locations and SHA-256 identities of:

```text
P4_SELECT_V2_FINAL_ANALYSIS_RESULT_V1.json
P4_SELECT_V2_FINAL_ANALYSIS_SEAL_V1.json
P4_SELECT_V2_SINGLE_ROUND_FINAL_EVIDENCE.sha256
P4_SELECT_V2_TASK_LEVEL_RESULTS_V1.json
P4_select_v2_final_unblind.py
```

Expected SHA-256 values:

```text
865b2f33b36226a52031b2e764ec0de5728d217c8da2247701ecc34c5cc48246

a5068c4be4d468ab70dd75b6690042bfc34b2f33b2da2c78e30d92b3b6a03e83

74229fc35058d790509c5de62632db3f8a2441e595621351b4496e49006d7e09

17aaef25bc093bb38f1b587e8a9fe835c8472721032dca9af5f5087d9cdc4ad7

1f43f898dbaacb2bc891b66a8eeab2877c612e60db6a978db0abfea369131f02
```

A mismatch is a STOP condition.

### Hierarchical analysis

Use the authoritative paths and identities already registered in:

```text
docs/rounds/round1/HIERARCHICAL_ANALYSIS.md
```

but re-check existence and current bytes against the server files.

Do not use the Markdown ledger to override a conflicting raw artifact.

### Provenance closure

Repository entry point:

```text
docs/audits/ROUND1_CANONICAL_GAP_AUDIT.md
```

Registered R132 evidence under:

```text
docs/audits/evidence/round1_canonical_gap/r132_primary117_identity_v1/
```

The provenance-closure workstream remains `IN_PROGRESS`.

## Task-2 acceptance

Task 2 passes only when:

- every executed major workflow stage has at least one defensible
  authoritative asset identity;
- all known fixed anchors match;
- no path is accepted only because its filename looked plausible;
- authoritative versus derived versus navigational assets are separated;
- unresolved canonical identity for an executed major stage causes STOP.

---

# Task 3: Create the Canonical Round-1 Asset Registry

## Purpose

Create:

```text
docs/rounds/round1/ASSET_REGISTRY.md
```

from the verified Task-2 inventory only.

## Required top-level sections

```text
Purpose
Authority and Source-of-Truth Boundary
Path and Mirror Policy
Registry Field Definitions
Round-1 Workflow Asset Map
Governance and Runtime Foundation
pi0 Development Evidence
Strong-Model Proposal and R132
Q2 Environment Validation
Training-Data Construction
pi1 Training
Harness-OFF Evaluation
Mechanical Post-hoc Analysis
Hierarchical Semantic Analysis
Canonical Evidence and Provenance Closure
Failure Memory Handoff Boundary
Repository-Mirrored Evidence
Retention Rules
Known Historical Gaps
Documentation Consumers
```

## Required registry fields

Every major asset row records:

```text
Logical asset
Workflow stage
Scientific role
Server path
Repository path
Producer
Downstream consumer
Population / file count
Historical identity
Status
Retention
Authority class
```

## Authority classes

Use only:

```text
AUTHORITATIVE_RAW_OR_SEALED
AUTHORITATIVE_DETERMINISTIC_AUDIT
DERIVED_ANALYSIS
NAVIGATIONAL_REGISTRY
HISTORICAL_REFERENCE
```

Semantic model output may be authoritative as the record of what the
semantic model returned, but its scientific authority remains semantic
hypothesis generation rather than environment truth.

## Retention vocabulary

Use:

```text
PRESERVE_EXACT_BYTES
PRESERVE_WITH_ORIGINAL_SEAL
PRESERVE_AS_REPOSITORY_EVIDENCE
PRESERVE_AS_HISTORICAL_REFERENCE
NAVIGATION_ONLY
```

## Registry boundary

Do not list every low-level raw-response file merely to maximize row
count.

The registry is canonical at the major scientific asset-family and
authoritative-entry-point level.

Raw child artifacts remain reachable through their registered package,
manifest, seal or evidence root.

---

# Task 4: Synchronize Round-1 Navigation

## Files

Modify:

```text
docs/rounds/round1/README.md
docs/rounds/round1/COMPONENT_REGISTRY.md
```

## Round-1 README changes

- add `[Asset Registry](./ASSET_REGISTRY.md)` to Round-level records;
- remove the stale Module-2 next-step block;
- after Module 3 closes, state that Round-1 research-asset consolidation
  is complete;
- keep canonical provenance closure `IN_PROGRESS`;
- keep Failure Memory `HOLD`;
- identify the Asset Registry as the exact path/identity entry point.

## Component Registry changes

Replace the statement that exact asset identity is awaiting Module 3
with a relative link to:

```text
./ASSET_REGISTRY.md
```

Replace:

```text
exact asset identity still awaiting registry binding
```

with wording that states exact major-asset identity is registered in the
Asset Registry while unresolved provenance remains explicitly tracked by
the canonical-gap audit.

Do not rewrite component scientific roles.

---

# Task 5: Synchronize the Project Experiment Ledger

## File

Modify:

```text
docs/experiments/EXPERIMENT_LEDGER.md
```

## Required structure

Add near the top:

```text
## Completed Round-1 scientific event
```

This section must record:

```text
Round identity:
ROUND1_SINGLE_ROUND_POLICY_IMPROVEMENT_VALIDATION

Round execution:
COMPLETE

Harness-OFF policy-improvement result:
COMPLETE_NO_GO

Hierarchical:
Levels 1-4 COMPLETE
Level 5 REJECTED
Level 6 INCOMPLETE

Canonical provenance:
IN_PROGRESS

Failure Memory:
HOLD
```

The section must link relatively to:

```text
../rounds/round1/README.md
../rounds/round1/ASSET_REGISTRY.md
../rounds/round1/HIERARCHICAL_ANALYSIS.md
../audits/ROUND1_CANONICAL_GAP_AUDIT.md
```

## E0-E20 boundary

The existing E0-E20 roadmap remains a separate active/future protocol
ledger.

Do not claim that historical Round 1 equals E12-E16.

Where current wording globally says no credible Harness-OFF result
exists, qualify it so the scientific truth becomes:

```text
A completed Round-1 Harness-OFF evaluation exists and produced NO-GO.
No successful policy-internalization claim is supported.
```

Do not convert `NO-GO` into successful internalization.

---

# Task 6: Synchronize the Code Map

## File

Modify:

```text
docs/code_map.md
```

## Required new first major section

Add before historical Runtime Core material:

```text
## Current Round-1 research map
```

It must link to:

```text
rounds/round1/README.md
rounds/round1/COMPONENT_REGISTRY.md
rounds/round1/ASSET_REGISTRY.md
rounds/round1/HIERARCHICAL_ANALYSIS.md
audits/ROUND1_CANONICAL_GAP_AUDIT.md
```

The new section records the current scientific workflow:

```text
pi0 evidence
→ strong proposer
→ Q2 validation
→ training-data construction
→ pi1 training
→ Harness-OFF evaluation
→ NO-GO
→ post-hoc analysis
→ provenance closure
```

It must state that exact historical code/script and server-asset
identities are delegated to Component Registry and Asset Registry rather
than duplicated incompletely.

Retain the Runtime Core and S1 historical engineering sections below.

---

# Task 7: Extend the Module Closure Policy

## File

Modify:

```text
docs/protocol/MODULE_CLOSURE_POLICY.md
```

## Add section

```text
## Documentation Sync Check
```

Every later small-module closure must check, when applicable:

```text
parent major-module ledger
Round-1 README
Component Registry
Asset Registry
Hierarchical Analysis Ledger
Experiment Ledger
Code Map
root README
```

Every item must be recorded as exactly one of:

```text
UPDATED
CHECKED_NO_CHANGE_REQUIRED
NOT_APPLICABLE
```

The policy must explicitly state that:

- a documentation check does not authorize changing a scientific result;
- a higher-level document may not override lower-level raw evidence;
- relative links must resolve;
- a status-changing scientific module must synchronize the Experiment
  Ledger;
- a top-level project-state change must synchronize the root README.

Retain all existing commit/push/remote-equality closure requirements.

---

# Task 8: Synchronize the Root README

## File

Modify:

```text
README.md
```

## Boundary

Do not casually replace the canonical protocol declaration.

The root README must distinguish:

```text
active/current protocol roadmap
```

from:

```text
completed Round-1 scientific event
```

## Required current-state block

The root entry point must expose:

```text
Round-1 execution = COMPLETE
Harness-OFF policy improvement = COMPLETE_NO_GO
Hierarchical Levels 1-4 = COMPLETE
Level 5 = REJECTED
Level 6 = INCOMPLETE
Canonical evidence/provenance closure = IN_PROGRESS
Failure Memory = HOLD
```

## Required relative navigation

Link to:

```text
docs/rounds/round1/README.md
docs/rounds/round1/ASSET_REGISTRY.md
docs/experiments/EXPERIMENT_LEDGER.md
docs/audits/ROUND1_CANONICAL_GAP_AUDIT.md
docs/protocol/MODULE_CLOSURE_POLICY.md
docs/code_map.md
```

The root README is a navigation and high-level status document.

It must not duplicate the full Asset Registry.

---

# Task 9: Final Documentation and Identity Audit

## Purpose

Prove all Module-3 documents agree without modifying scientific evidence.

## Required checks

### Status agreement

Across the applicable documents:

```text
Round 1 = COMPLETE
policy improvement = COMPLETE_NO_GO
Levels 1-4 = COMPLETE
Level 5 = REJECTED
Level 6 = INCOMPLETE
provenance closure = IN_PROGRESS
Failure Memory = HOLD
```

### Numbering boundary

Reject:

```text
## Level 0
```

Canonical provenance closure must remain outside Level 1-6.

### Asset registry schema

Every major asset row must have nonempty:

```text
logical asset
workflow stage
scientific role
server path or explicit repository-only basis
producer
consumer
identity
status
retention
authority class
```

### File existence

Every registered server file path must exist at audit time.

Every repository-relative Markdown link must resolve.

### Identity checks

For each registered file with an original expected SHA-256:

```text
current bytes SHA-256
=
registered expected SHA-256
```

For each registered package/root seal:

- verify the actual seal file exists;
- verify the registry value was read from the original source;
- do not substitute a Module-3 recomputation for the historical root
  seal.

### Known scientific anchors

Verify:

```text
R132:
117 primary cases
91 accepted teacher outputs
26 rejections
351 Q2 bindings

Harness-OFF:
COMPLETE_NO_GO

Hierarchy:
Level 1 = 85 / 73 / 12 / 50 / 23
Level 2 = 30 mechanisms
Level 3 = 17 tasks / 6 families / 180 cells
Level 4 = 148 assessed / 29 directional candidates
Level 5 = REJECTED
Level 6 = INCOMPLETE
```

### Stale-text scan

Reject any unqualified project-level statement equivalent to:

```text
Harness-OFF evaluation has never occurred
Round-1 training has not occurred
Module 2 is the next consolidation module
asset identities still await Module 3
Failure Memory is complete
Level 5 is complete
Level 6 is complete
```

Context-specific statements about a particular engineering package having
no model execution may remain if their scope is explicit.

### Whitespace and conflict markers

Run:

```bash
git diff --check
```

and require success.

---

# Task 10: Close Module 3 and the Major Consolidation Module

## Parent ledger

Update:

```text
docs/rounds/round1/ASSET_CONSOLIDATION_LEDGER.md
```

Final major-module state:

```text
MODULE3_CLOSED_MAJOR_MODULE_COMPLETE
```

Record:

- Module-3 plan identity through Git history;
- verified major asset inventory;
- fixed-anchor audit;
- Asset Registry creation;
- global documentation synchronization;
- Documentation Sync Check results;
- remaining provenance closure `IN_PROGRESS`;
- Failure Memory `HOLD`;
- no scientific result changed.

## Documentation Sync Check

Final states should be:

```text
Parent major-module ledger = UPDATED
Round-1 README = UPDATED
Component Registry = UPDATED
Asset Registry = UPDATED
Hierarchical Analysis Ledger = CHECKED_NO_CHANGE_REQUIRED
Experiment Ledger = UPDATED
Code Map = UPDATED
Root README = UPDATED
Module Closure Policy = UPDATED
```

## Commit scope

The implementation commit may contain only the files required by Module
3:

```text
README.md
docs/rounds/round1/ASSET_REGISTRY.md
docs/rounds/round1/README.md
docs/rounds/round1/COMPONENT_REGISTRY.md
docs/rounds/round1/ASSET_CONSOLIDATION_LEDGER.md
docs/experiments/EXPERIMENT_LEDGER.md
docs/code_map.md
docs/protocol/MODULE_CLOSURE_POLICY.md
```

`docs/rounds/round1/HIERARCHICAL_ANALYSIS.md` must remain unchanged
unless the final deterministic audit finds a real defect that requires a
separately justified correction before Module-3 closure.

## Implementation commit

Commit message:

```text
Complete Round-1 asset registry and global documentation sync
```

## Final closure

After commit:

1. rerun the final deterministic audit;
2. verify the worktree is clean;
3. push the branch;
4. fetch the branch;
5. verify local HEAD equals remote branch HEAD;
6. verify the worktree remains clean.

Final closure marker:

```text
ROUND1_RESEARCH_ASSET_CONSOLIDATION_CLOSED
```

---

# Final Acceptance Criteria

Module 3 and the major consolidation module close only when:

- `ASSET_REGISTRY.md` exists;
- every major executed Round-1 workflow stage has a defensible
  authoritative identity entry;
- all fixed historical SHA/root-seal anchors match;
- no historical evidence was moved or changed;
- Round-1 README links to the Asset Registry;
- Component Registry no longer says asset identity is awaiting Module 3;
- Experiment Ledger records the completed Round-1 event without falsely
  renumbering it into E0-E20;
- Code Map exposes the current Round-1 research path before historical
  engineering detail;
- Module Closure Policy contains Documentation Sync Check;
- root README reflects the completed Round-1 `NO-GO`;
- Level 5 remains `REJECTED`;
- Level 6 remains `INCOMPLETE`;
- provenance closure remains `IN_PROGRESS`;
- Failure Memory remains `HOLD`;
- all relative repository links resolve;
- `git diff --check` passes;
- implementation forms one single-purpose commit;
- the implementation commit is pushed;
- local and remote HEAD are equal;
- the final worktree is clean.
