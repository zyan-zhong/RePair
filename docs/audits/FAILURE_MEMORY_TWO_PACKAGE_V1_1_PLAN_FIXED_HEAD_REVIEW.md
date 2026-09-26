# Failure Memory Two-Package V1.1 Fixed-Head Plan Review

## Reviewed identity

Repository:

`zyan-zhong/phase-critical-harness-guided-self-improvement`

Reviewed plan head:

`db755bb57f9e23668df1940c0b30d230ec44e0e9`

Reviewed parent:

`0332971d88f1592575ba6b8197c9db5b54472a13`

Observed graph:

```text
parent 0332971
  ↓
plan db755bb
```

The plan branch is exactly one documentation commit ahead and zero behind.

## Decision

`PLAN_CHANGES_REQUIRED_FAILURE_MEMORY_TWO_PACKAGE_V1_1`

The two-package architecture remains approved. No scientific redesign is required.

The current implementation plans require narrow hardening before production code begins.

## Blocker 1 — implementation authority base mismatch

The Package-A plan names `0332971...` as its implementation base while the spec and implementation plans themselves exist only at descendant `db755bb...`.

Production implementation must not branch from a commit that does not contain its approved plan.

Correction:

```text
Unit-4 code authority = 0332971...
final plan authority = final plan-hardening head
implementation base = final plan authority after fast-forward to main
```

The Unit-4 code bytes remain reviewed against `0332971...`.

## Blocker 2 — Package-A real candidate flow omitted the real eligibility transition

The code plan implements source-integrity and descriptive-eligibility logic before real materialization, but the real execution task did not explicitly require applying those gates to every materialized candidate before snapshot membership.

Correction:

```text
real candidate
→ source-integrity audit
→ descriptive-eligibility audit
→ new governed record version
→ DEV snapshot membership
```

No in-place mutation is allowed.

## Blocker 3 — Package-A snapshot type was too close to formal library authority

The formal `MEMORY_LIBRARY_SNAPSHOT_V1` requires retriever/index/threshold configuration that does not exist until Package B.

Correction:

Package A publishes:

`MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_V1`

It is immutable, content-addressed and sufficient as a Package-B source, but it is not a formal evaluation/library snapshot.

Package B later publishes a retrieval-bound Stage-1 DEV library snapshot after retriever and threshold selection.

## Blocker 4 — code and real ALFWorld execution were mixed in Task A8

The execution contract says build/code approval precedes real environment execution, but the Package-A task text mixed them.

Correction:

```text
A0–A8 = code / tests / static qualification only
CODE_APPROVED_FAILURE_MEMORY_PACKAGE_A_V1
PACKAGE_A_EXECUTION_APPROVED
A9 = real environment-only replay + real materialization/gates/snapshot
A10 = cumulative closure
```

## Blocker 5 — ledger timestamps were underspecified

A deterministic constructor must not call current wall-clock time internally.

Correction:

Event time, if recorded, is caller-supplied evidence metadata. Canonical constructors and identity recomputation never invoke `datetime.now()`, `time.time()` or equivalent.

## Blocker 6 — Package-B early representation result was unnecessarily delayed by full retriever development

The approved V1.1 design already separates retrieval development from matched representation ablation.

Correction:

Package B now has two internal lanes:

```text
B-DIRECT
snapshot → packing → prompt/runtime → applicability → matched representations
→ PI1_MATCHED_MEMORY_REPRESENTATION_ABLATION_READY

B-RETRIEVAL
train-DEV partition → query panel → lexical/dense/hybrid
→ blind gold → threshold/retriever selection → retrieval-bound snapshot
→ Stage-0 audit
→ PI1_MEMORY_ON_STAGE1_DEV_READY
```

The first matched-record scientific study still requires separate execution approval.

## Blocker 7 — retrieval candidates and gold-label workflow were underspecified

The previous plan said to “freeze” lexical scoring, hybrid weights and thresholds without specifying exact preregistered algorithms, and omitted the blind gold-label materialization/ledger required by the approved design.

Correction:

Lexical candidate:

```text
BM25
k1 = 1.2
b = 0.75
IDF = ln(1 + (N - df + 0.5) / (df + 0.5))
no stemming
no stop-word removal
casefold before regex tokenization
regex tokens = (?u)\b\w+\b
query duplicate tokens count once
```

Dense candidate:

```text
intfloat/e5-base-v2
revision = f52bf8ec8c7124536f0efb74aca902b2995e5bcd
query prefix = "query: "
passage prefix = "passage: "
attention-mask mean pooling
L2 normalization
cosine = normalized dot product
CPU float32 reference embedding execution
```

Hybrid candidate:

```text
equal-weight Reciprocal Rank Fusion
rank starts at 1
RRF k = 60
score = 1/(60 + lexical_rank) + 1/(60 + dense_rank)
```

Threshold configuration search is deterministic and calibration-only:

```text
top_k ∈ {1, 2, 3}
threshold candidates =
  +infinity abstain sentinel
  + every distinct observed calibration candidate score
selection uses the frozen safety-first lexicographic objective
```

Per-retriever configuration is frozen on calibration. Retriever choice then uses selection-validation without threshold retuning.

Blind applicability gold receives no score, rank or retriever identity and preserves two independent passes plus registered adjudication.

## Blocker 8 — one-sentence reflection generator was not defined

A new live LLM call would add a generator-quality confound.

Correction:

The compact baseline is renamed:

`SINGLE_CUE_FAILURE_SUMMARY_V1`

It is deterministic and uses exactly the first canonical FM2 `failure_pattern` item from the same record version. There is no rewrite, no new Analyzer call and no additional semantic authority.

This is the operational simple-summary baseline for the first representation study.

## Overall disposition

After the corrections in the revised plans are committed and remotely equal:

```text
Package A plan = APPROVABLE
Package B plan = APPROVABLE
two-package architecture = UNCHANGED
production code = STILL NOT AUTHORIZED until plan approval token
```
