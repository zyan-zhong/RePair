# Failure Memory Two-Package Acceleration Design Amendment V1.1

## 1. Status and authority

Design decision:

`DESIGN_APPROVED_FAILURE_MEMORY_TWO_PACKAGE_ACCELERATION_V1_1`

Approval date:

`2026-08-18`

Repository:

`zyan-zhong/phase-critical-harness-guided-self-improvement`

Authoritative base:

`0332971d88f1592575ba6b8197c9db5b54472a13`

This amendment is subordinate to, and must be read with:

- `docs/superpowers/specs/2026-08-14-failure-memory-v1-design.md`;
- `docs/memory/FAILURE_MEMORY_V1_IMPLEMENTATION_ROADMAP.md`;
- `docs/memory/FAILURE_MEMORY_V1_LEDGER.md`;
- the project-level v3.3 research protocol and the 2026-08-13 route correction.

The amendment changes implementation packaging and experiment ordering. It does not rewrite closed Unit-1 through Unit-4 scientific contracts.

## 2. Project-level scientific position

Persistent Failure Memory is an auxiliary historical-experience layer inside a research-guided policy self-improvement system.

The project-level evidence chain remains:

```text
failure evidence
→ Researcher / Analyzer
→ historical Failure Experience support
→ candidate repair
→ same-state environment verification
→ Benefit / Harm / Neutral / Uncertain
→ verified training evidence
→ πk+1
→ Memory-OFF + Harness-OFF evaluation
→ promote / rollback
```

A positive frozen-policy Memory result establishes only tool/system value. The final policy self-improvement authority remains:

```text
π2 + Memory OFF + Harness OFF
>
π1 + Memory OFF + Harness OFF
```

The independent Failure Memory V1 study retains its own frozen-policy scientific scope, but that scope must not replace the project-level canonical story.

## 3. Why two implementation packages

The remaining pre-ablation work is compressed into two packages to reduce interaction and transfer overhead while preserving per-module auditability.

Every internal module still closes through:

```text
RED
→ GREEN
→ focused tests
→ applicable full regression
→ static/scope/no-touch audit
→ ledger update
→ single-purpose commit
→ push
→ local/remote equality
→ clean worktree
```

No package may hide several scientific decisions inside one commit.

## 4. Package A — Write / Identity / Causal-Test Infrastructure

Package A owns:

```text
Unit-4 cumulative fixed-head review evidence
source-state reconstruction contracts
ALFWorld environment-only replay qualification
Memory-specific OFF/ON branch identity
append-only event/effect/exposure/promotion ledgers
real candidate materialization into staging
source-integrity audit
descriptive eligibility and DEV access transition
immutable DEV descriptive snapshot
full-artifact hash binding
rollback-by-pointer
```

Package A may run ALFWorld only for environment-only prefix replay qualification.

Package A must not:

- call π1 or any task policy;
- execute a Memory-OFF/Memory-ON continuation;
- create Benefit/Harm evidence;
- mark an effect `POSITIVE`;
- grant prescriptive eligibility;
- claim that Memory is useful;
- publish a formal evaluation snapshot.

Package A final marker:

`MEMORY_CAUSAL_TEST_INFRASTRUCTURE_READY`

This means the infrastructure is qualified to run causal tests. It does not mean causal evidence exists.

## 5. Package B — Read / Retrieval / Policy Exposure

Package B owns:

```text
TRAIN_RETRIEVAL_DEV three-way deterministic partition
immutable snapshot loading and verification
retrieval-development lane
lexical / dense / hybrid candidates
threshold and abstention selection
applicability / release / conflict evaluation
whole-record packing
common Memory-aware prompt
Memory-aware runtime integration
Policy-exposure evidence
Stage-0 quality / safety / retrieval audit
matched-record representation-ablation manifest
```

Package B contains two experimentally separate lanes.

### 5.1 Retrieval-development lane

```text
current Policy-visible query state
→ hard filters
→ candidate scoring
→ deterministic ranking
→ threshold / conflict / release checks
→ APPLICABLE / UNCERTAIN / NOT_APPLICABLE
→ projection or abstain
```

This lane develops retrieval and abstention on the authorized train retrieval-development roles.

### 5.2 Representation-ablation lane

```text
one pre-frozen source-record identity
→ FM1 matched raw view
→ one-sentence reflection
→ FM2 structured descriptive view
```

The lane does not retrieve separately for each representation. The source record and source evidence are identical across arms.

Package B early marker:

`PI1_MATCHED_MEMORY_REPRESENTATION_ABLATION_READY`

Package B final marker:

`PI1_MEMORY_ON_STAGE1_DEV_READY`

The final marker still does not establish a positive Memory effect. It authorizes a separately approved train-development scientific execution.

## 6. Candidate and snapshot authority

A newly materialized record begins as:

`STAGING_CANDIDATE`

It may enter the first DEV descriptive snapshot only after all of the following pass:

```text
source integrity
sequence fidelity
procedural completeness
authority typing
Policy-view static safety
contextual safety where applicable
development access
descriptive eligibility
versioned governance transition
```

The transition creates a new version. Candidate artifacts are never mutated in place.

The first Package-A snapshot is a DEV descriptive-access snapshot. Effect status remains `UNTESTED`. Nonempty FM3 recovery is not authorized.

## 7. Real execution approvals

The V1.1 design uses one package-level approval per package rather than a separate human round-trip for every internal module.

Package A real execution requires:

`PACKAGE_A_EXECUTION_APPROVED`

Before that token is accepted, the execution manifest must freeze:

- exact Unit-4 approved head;
- exact source episodes / experiences;
- exact gamefiles and runtime identity;
- source-state qualification cases;
- staging output root;
- no-clobber and durability rules;
- DEV-only access scope;
- snapshot class;
- the prohibition on effect/prescriptive promotion.

Package B real execution requires:

`PACKAGE_B_EXECUTION_APPROVED`

Before that token is accepted, the execution manifest must freeze:

- exact Package-A head and snapshot;
- retrieval-development partition;
- retriever candidate identities;
- tokenizer and embedding contracts;
- threshold-selection roles;
- prompt interface;
- π1 checkpoint identity;
- Stage-0 task/query cohort;
- no formal evaluation access.

Scientific ablation execution remains separate:

`STAGE1_TRAIN_DEV_MEMORY_ABLATION_APPROVED`

## 8. First π1 Memory experiment

The first experiment is a train-development representation study, not the final FM0–FM3 formal experiment.

Main arms:

```text
M0
common Memory-aware interface
+ empty Memory array

M1
FM1 matched raw episodic view

M2
frozen one-sentence reflection
derived from the same source evidence and Analyzer lineage

M3
FM2 structured descriptive multi-step Failure Experience

NEG
registered known-non-applicable FM2 forced exposure
matched as closely as possible in projection class and token length
```

Diagnostics:

```text
D1
longer executed Policy-visible recent history
(context-length diagnostic; not an FM arm)

D2
random FM2 exposure
(secondary stress control)
```

M1, M2 and M3 must use the exact same source-record identity.

The first study does not expose an unverified FM3 recovery.

## 9. Claim boundary for the first study

A positive train-development result may support:

> On train-development ALFWorld tasks, structured, applicability-bounded multi-step failure experience provides stronger decision support to a frozen policy than matched raw failure context or one-shot summaries.

It may not support:

- general improvement across long-horizon agents;
- policy-weight improvement;
- self-improvement;
- fresh OOD generalization;
- verified recovery value;
- formal FM3 superiority.

If task success is unchanged while loops or repeated errors improve, the result supports only a mechanism-level claim.

## 10. No-touch and prohibition list

Unless an explicitly approved correction plan states otherwise, Package A and Package B must not rewrite:

```text
src/pchsi/evaluation/runtime_core.py
src/pchsi/evaluation/budget.py
src/pchsi/evaluation/raw_policy_parser.py
src/pchsi/evaluation/raw_policy_prompt.py
src/pchsi/evaluation/run_schedule.py
src/pchsi/evaluation/condition_run_schedule.py
src/pchsi/evaluation/condition_execution_binding.py
src/pchsi/evaluation/select_execution_identity.py
src/pchsi/evaluation/policy_condition.py
```

`RAW_POLICY_PROMPT_V1` and `MEMORY_M0_V1` remain unchanged.

Forbidden throughout both packages:

- force push;
- history rewrite;
- best-of-seed selection;
- live LLM reranking;
- online Analyzer applicability judgment;
- evaluation-time threshold adaptation;
- test-task Memory construction;
- current-menu reordering/filtering/truncation;
- treating Analyzer hypotheses as environment truth;
- treating snapshot inclusion as positive effect evidence.
