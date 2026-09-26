# Failure Memory Package B — Direct Memory Exposure and Retrieval Development Implementation Plan V1.1.1

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** First make a clean matched-record frozen-π1 representation experiment possible without live retrieval; then complete the deterministic retrieval, applicability, blind-gold, threshold and Stage-0 chain.

**Architecture:** Package B reads only an immutable `MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_V1` from Package A. It has two internal lanes. `B-DIRECT` freezes which record is shown and changes only representation. `B-RETRIEVAL` develops live retrieval on disjoint train-DEV roles. The two lanes share snapshot/projection contracts but do not contaminate each other's scientific variable.

**Tech Stack:** Python 3.12, pytest, canonical JSON, existing Runtime Core, existing Policy tokenizer contract, deterministic BM25, optional frozen E5, deterministic RRF, existing ALFWorld/policy evaluator surfaces under explicit execution approval.

**Spec:** `docs/superpowers/specs/2026-08-18-failure-memory-two-package-v1_1-design-amendment.md`

## Global constraints

- Starts only from a remotely equal Package-A closure head.
- Dedicated branch: `implementation/failure-memory-package-b-policy-exposure-v1`.
- Dedicated worktree: `/data/run01/scwb204/sdar_repro/badcase/github_exports/pchsi-wt-failure-memory-package-b-v1`.
- External scripts/ZIP/logs root: `/data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts`.
- `RAW_POLICY_PROMPT_V1` is untouched.
- `MEMORY_M0_V1` is untouched.
- Runtime Core parser, exact membership and budgets remain authority.
- Complete admissible menu remains original-order, unfiltered, unsorted and untruncated.
- No online Analyzer.
- No live LLM reranker.
- No evaluation-time learning.
- No `valid_seen` or `valid_unseen` for development/selection.
- Active snapshots are immutable.
- B-DIRECT arms never retrieve separately.
- Every internal task closes by independent commit/push/equality.

---

# Part I — B-DIRECT

## Task B0 — Package-A dependency binding

Verify:
- Package-A closure marker;
- exact Package-A commit;
- DEV descriptive snapshot ID/SHA;
- all referenced artifact hashes;
- no Package-A effect beyond `UNTESTED`.

Create Package-B branch/worktree from Package-A closure head.

Commit:

`Bind Package B to Failure Memory Package A`

Marker:

`PACKAGE_B_TASK_B0_DEPENDENCY_CLOSED`

---

## Task B1 — DEV descriptive snapshot loader

**Create**
- `src/pchsi/memory/dev_snapshot_loader.py`
- focused tests

Loader requires:
- expected full snapshot SHA;
- content-addressed directory;
- no symlink;
- no mutable `latest`;
- exact registered files only;
- rehash record/retrieval-key/FM1/FM2 artifacts;
- no FM3 membership.

Commit:

`Load immutable Failure Memory DEV snapshots`

Marker:

`PACKAGE_B_TASK_B1_DEV_SNAPSHOT_LOADER_CLOSED`

---

## Task B2 — Whole-projection packing

**Create**
- `projection_packing.py`
- focused tests

Two fixed modes:

```text
DIRECT_SINGLE_RECORD
record_count = exactly 1
max Memory tokens = 256

LIBRARY
record_count = 0..3
max Memory tokens = 384
```

Rules:
- whole record only;
- stop at first non-fitting record;
- no partial truncation;
- deterministic order;
- preserve release/non-applicability cues;
- actual token count stored.

Commit:

`Pack Failure Memory projections without truncation`

Marker:

`PACKAGE_B_TASK_B2_PACKING_CLOSED`

---

## Task B3 — Common Memory-aware prompt

**Create**
- `memory_augmented_prompt.py`
- focused tests

Frozen order:

```text
TASK_GOAL_JSON
CURRENT_OBSERVATION_JSON
EXECUTED_TRANSITIONS_JSON
RETRIEVED_FAILURE_EXPERIENCES_JSON
VISIBLE_ADMISSIBLE_COMMANDS_JSON
INTERFACE_FEEDBACK_JSON
OUTPUT_REQUIREMENT
```

M0:
`RETRIEVED_FAILURE_EXPERIENCES_JSON=[]`

Memory ON:
one or more frozen Policy projections.

Tests prove:
- M0 and ON share all non-Memory bytes;
- complete menu exact sequence;
- recent executed transitions unchanged;
- no change to historical prompt builder;
- deterministic bytes.

Commit:

`Build the Failure Memory augmented Policy prompt`

Marker:

`PACKAGE_B_TASK_B3_MEMORY_PROMPT_CLOSED`

---

## Task B4 — Memory-aware Runtime bridge and exposure record

**Create**
- `memory_runtime_bridge.py`
- `policy_exposure.py`
- schemas
- focused tests

The bridge may:
- build new prompt;
- record snapshot/projection exposure;
- call existing Runtime Core decision functions.

The bridge may not:
- repair/canonicalize actions;
- filter/reorder menu;
- alter BudgetState rules;
- call Analyzer/retriever unless explicitly passed frozen results;
- mutate snapshot;
- infer internal Memory utilization.

Exposure evidence binds:
- source/non-source decision identity;
- snapshot;
- retrieval mode;
- Memory lineage/version;
- projection class/full SHA;
- token count;
- insertion anchor;
- final prompt SHA;
- branch/condition role.

Commit:

`Bridge Failure Memory exposure to Runtime Core`

Marker:

`PACKAGE_B_TASK_B4_RUNTIME_EXPOSURE_CLOSED`

---

## Task B5 — Deterministic compact-summary baseline

**Create**
- `single_cue_failure_summary.py`
- strict schema
- focused tests

Authority:

`SINGLE_CUE_FAILURE_SUMMARY_V1`

For a record/FM2 pair, its only semantic text is:

```text
the first canonical FM2 failure_pattern item
```

No rewriting.
No new LLM call.
No new Analyzer call.
No source change.

The summary:
- carries source lineage/version and FM2 descriptive payload SHA;
- passes the same Policy-view static identity/oracle/spoof safety checks;
- uses one string field only.

If FM2 has no failure-pattern item or the single cue fails safety, the record is ineligible for the compact-summary arm.

Commit:

`Build deterministic single-cue Failure Memory summaries`

Marker:

`PACKAGE_B_TASK_B5_SINGLE_CUE_SUMMARY_CLOSED`

---

## Task B6 — Direct applicability and negative-control gate

**Create**
- `applicability_gate.py`
- focused tests

For B-DIRECT it evaluates only mechanically checkable registered cues against the current Policy-visible state.

Possible results:

```text
APPLICABLE
NOT_APPLICABLE
CONFLICTING
UNCERTAIN
```

No LLM inference.
No unobserved phase/subgoal inference.

`NOT_APPLICABLE|CONFLICTING|UNCERTAIN` normally abstain.

The explicit `NEG` stress arm may force-expose only a record with a registered `NOT_APPLICABLE` disposition. That forced exposure is separately labeled and never counted as normal retrieval.

Commit:

`Gate direct Failure Memory applicability`

Marker:

`PACKAGE_B_TASK_B6_DIRECT_APPLICABILITY_CLOSED`

---

## Task B7 — Matched representation-cell materializer

**Create**
- `representation_ablation.py`
- CLI/materializer
- schemas
- focused tests

For each registered matched cell, bind one exact record version.

Produce:

```text
M0 = common empty slot
M1 = FM1 matched raw view
M2 = SINGLE_CUE_FAILURE_SUMMARY_V1
M3 = FM2 structured descriptive view
NEG = forced known-NOT_APPLICABLE FM2, when registered
D1 = longer executed-history diagnostic
D2 = random-FM2 secondary stress diagnostic
```

Rules:
- M1/M2/M3 same record lineage/version;
- no per-arm retrieval;
- no live generation;
- M3 is FM2, never prescriptive FM3;
- D1 is not an FM arm;
- NEG requires registered NOT_APPLICABLE evidence;
- random control is secondary only.

Commit:

`Materialize matched Failure Memory representation cells`

Marker:

`PI1_MATCHED_MEMORY_REPRESENTATION_ABLATION_READY`

This marker authorizes only a later separately approved train-development scientific execution.

---

# Part II — B-RETRIEVAL

## Task B8 — Three-way retrieval-development partition

Consumes exactly:

`TRAIN_RETRIEVAL_DEV = 1186`

Within each frozen task family, compute:

```text
role_score =
SHA256(
  "MEMORY_RETRIEVAL_DEV_ROLE_V1\0"
  + task_gamefile_group_id
)
```

Sort `(role_score, task_gamefile_group_id)`.

For family count `n`:

```text
n_calibration = (n + 1) // 2
remaining = n - n_calibration
n_selection = (remaining + 1) // 2
n_panel = remaining - n_selection
```

Assign sequentially:
1. calibration;
2. selection validation;
3. multi-round panel.

Require each family to have nonzero membership in all three roles; otherwise stop before any label/retrieval execution.

Materialize exact counts and manifest hashes before use.

Commit:

`Partition Failure Memory retrieval development roles`

Marker:

`PACKAGE_B_TASK_B8_RETRIEVAL_PARTITION_CLOSED`

---

## Task B9 — Stage-0 Policy-visible query panel

**Create**
- `stage0_query_panel.py`
- schedule/manifest
- runner
- tests

Policy:
primary frozen Train17 checkpoint identity from existing Failure Memory policy contract.

No active-bank writeback.

Panel selection:
- calibration role: lowest role-score 10 tasks per frozen task family;
- selection role: lowest role-score 10 tasks per frozen task family;
- same task never appears in both roles.

If any role/family has fewer than 10 tasks: hard stop before execution and require a resource-contract amendment.

Per task:
- run the common Memory-aware empty-slot interface;
- fixed Stage-0 request seed = 17;
- collect the first decision state after exactly one successfully executed environment transition;
- if the task terminates before such a state, record `QUERY_STATE_UNAVAILABLE` and do not substitute a later/other task.

Query-state availability is reported, not backfilled post hoc.

Execution requires `PACKAGE_B_EXECUTION_APPROVED`.

Commit code before execution:

`Prepare Failure Memory Stage-0 query panel`

Marker after real query collection:

`PACKAGE_B_TASK_B9_STAGE0_QUERY_PANEL_CLOSED`

---

## Task B10 — Deterministic BM25 lexical candidate

Tokenization:
- Python Unicode regex `(?u)\b\w+\b`;
- casefold before tokenization;
- no stemming;
- no stop-word removal;
- duplicate query tokens count once.

Passage corpus:
exact `semantic_retrieval_text` from eligible snapshot retrieval keys.

Parameters:

```text
k1 = 1.2
b = 0.75
idf(t) = ln(1 + (N - df(t) + 0.5)/(df(t) + 0.5))
```

Score:

```text
Σ_t idf(t) *
(tf(t,d)*(k1+1)) /
(tf(t,d) + k1*(1-b+b*dl/avgdl))
```

Tie-break:
descending score, then lineage ID, then record version.

Commit:

`Implement deterministic BM25 Failure Memory retrieval`

Marker:

`PACKAGE_B_TASK_B10_BM25_CLOSED`

---

## Task B11 — Frozen E5 dense candidate

Identity:

```text
intfloat/e5-base-v2
revision f52bf8ec8c7124536f0efb74aca902b2995e5bcd
```

Reference execution:
- complete artifact hashes frozen;
- CPU;
- float32;
- tokenizer/model exact revision;
- query prefix `query: `;
- passage prefix `passage: `;
- attention-mask mean pooling;
- L2 normalization;
- score = normalized dot product;
- deterministic record-ID tie-break.

Code tests use an injected fake encoder; no download in build phase.

Real model materialization and embedding require `PACKAGE_B_EXECUTION_APPROVED`.

Commit:

`Implement frozen E5 Failure Memory retrieval`

Marker:

`PACKAGE_B_TASK_B11_DENSE_CLOSED`

---

## Task B12 — Deterministic hybrid RRF candidate

Same post-hard-filter candidate set for lexical and dense rankings.

Rank begins at 1.

```text
RRF_K = 60

hybrid_score(record)
=
1/(60 + lexical_rank)
+
1/(60 + dense_rank)
```

Equal weight only.

Tie-break:
lineage ID, record version.

No learned weights or normalization.

Commit:

`Fuse Failure Memory retrieval with fixed RRF`

Marker:

`PACKAGE_B_TASK_B12_HYBRID_CLOSED`

---

## Task B13 — Blind gold candidate pool and annotation ledger

For every available Stage-0 query state in calibration and selection roles:
- run all three candidate retrievers without labels;
- take each retriever's top 3 after hard filters;
- union and deduplicate `(query_id, memory_version)` pairs.

Materialize `MEMORY_RETRIEVAL_GOLD_CANDIDATE_VIEW_V1` with:
- opaque annotation pair ID;
- Policy-visible query state;
- descriptive failure boundary;
- activation/revalidation/release/non-applicability cues;
- frozen rubric.

The blind view excludes:
- recovery;
- effect;
- promotion/lifecycle;
- Analyzer confidence;
- score;
- rank;
- retriever identity;
- selected configuration;
- later result.

Every pair receives:
- independent applicability pass 1;
- independent applicability pass 2;
- registered adjudication on disagreement.

Labels:
`APPLICABLE|NOT_APPLICABLE|CONFLICTING|UNCERTAIN`.

All passes/adjudications are append-only.

Commit code/materializer before labels:

`Build blind Failure Memory retrieval gold views`

Marker after frozen labels:

`PACKAGE_B_TASK_B13_RETRIEVAL_GOLD_CLOSED`

---

## Task B14 — Calibration-only threshold configuration

For each retriever separately:

```text
top_k ∈ {1,2,3}

threshold candidates =
{ +INF_ABSTAIN }
∪
{ every distinct candidate score observed on calibration }
```

Selection condition is `score >= threshold`.

For every candidate configuration:
1. require zero critical leakage;
2. require zero access violation;
3. require zero known harmful eligibility;
4. minimize wrong-Memory exposure;
5. minimize unresolved-conflict exposure;
6. maximize applicable-Memory recall;
7. prefer higher justified abstention;
8. prefer lower measured token/latency cost;
9. prefer lower top_k;
10. deterministic final tie-break by higher threshold canonical numeric order.

Freeze one configuration for R1/R2/R3 using calibration only.

Commit:

`Calibrate Failure Memory retrieval thresholds`

Marker:

`PACKAGE_B_TASK_B14_THRESHOLD_CALIBRATION_CLOSED`

---

## Task B15 — Independent retriever selection

Apply each already-frozen R1/R2/R3 configuration to `RETRIEVER_SELECTION_VALIDATION`.

No threshold/top-k retuning.

Use the same safety-first lexicographic comparison.

If methods remain equivalent after the registered criteria:

```text
prefer simpler retriever:
R1 lexical
then R2 dense
then R3 hybrid
```

Freeze:
- selected retriever;
- exact configuration;
- manifests;
- tokenizer/embedding identities;
- index bytes/hash;
- tie-break;
- cost evidence.

Commit:

`Select the frozen Failure Memory retriever`

Marker:

`PACKAGE_B_TASK_B15_RETRIEVER_SELECTION_CLOSED`

---

## Task B16 — Retrieval-bound Stage-1 DEV library snapshot

**Create**
- `library_snapshot.py`
- schema `memory_library_snapshot_v1.json`
- focused tests

Authority:

`MEMORY_LIBRARY_SNAPSHOT_V1`

For Stage-1 DEV it binds:
- Package-A governed record versions;
- FM1/FM2 projection hashes;
- retrieval keys;
- selected retriever;
- index/embedding identity;
- thresholds/top-k;
- scoring/tie-break;
- access policy;
- tokenizer;
- 384-token/3-record ceiling;
- full snapshot SHA.

It remains DEV access, read-only and non-prescriptive.

Effect remains `UNTESTED`.

Commit:

`Bind the Failure Memory Stage-1 DEV library snapshot`

Marker:

`PACKAGE_B_TASK_B16_STAGE1_DEV_SNAPSHOT_CLOSED`

---

## Task B17 — Stage-0 cumulative audit and Package-B closure

Audit:
- provenance and snapshot integrity;
- query access;
- leakage;
- gold-label isolation;
- exact reproducibility;
- applicability;
- wrong-Memory exposure;
- conflict;
- abstention;
- historical-prompt versus empty-slot interface perturbation;
- tokens;
- latency;
- no active-bank writeback.

Identical query + snapshot + config must reproduce exact:
- candidate set;
- scores;
- ranking;
- selected records;
- packed bytes.

Run:
- focused tests;
- full Memory suite;
- full applicable regression;
- compileall;
- no-touch hashes;
- schema inventory;
- per-commit scope;
- push/equality.

Commit:

`Seal Failure Memory retrieval and Policy exposure readiness`

Final marker:

`PI1_MEMORY_ON_STAGE1_DEV_READY`

Scientific execution still requires:

`STAGE1_TRAIN_DEV_MEMORY_ABLATION_APPROVED`
