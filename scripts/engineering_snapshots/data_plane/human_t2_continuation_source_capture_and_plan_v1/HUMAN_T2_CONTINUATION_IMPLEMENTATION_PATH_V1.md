# Human T2 Continuation Implementation Path V1

> **Approval:** `APPROVE_TWO_PACKAGE_HUMAN_PRIORITY_AND_STRONG_TRACE_DATA_PLANE_CENSUS_V1`

**Goal:** Reuse the frozen Train17 trainer implementation to build a round-local, auditable Train17→T2 continuation runner without inheriting historical dataset-specific constants or old optimizer/scheduler state.

**Current authoritative facts**

- Parent policy: `PILOT_DISTILLED_PI1`
- Parent Train17 adapter bundle SHA-256: `b296f2254b1fa1f2e141dffd3f6b5af903f839df4790ffcb245fd8dd57773ace`
- Parent `formal_train.py` SHA-256: `4709c32d34b437d2884fa83d4967f4d898e4cd17d5a56ce0b9e72a250f0ad9e7`
- Parent training config SHA-256: `a860a77890e34e4cfcb38dff0acdf35db0a3605d0a494c100f2b74b9f5228f9c`
- Current T2 dataset: 12 rows, exact sequence lengths `[774,654,568,327,570,343,436,333,491,314,274,425]`
- Current one-pass completion-loss tokens: `151`
- Current training: seed/data-seed `17`, one epoch, micro-batch `1`, gradient accumulation `4`, three optimizer steps
- Current status: diagnostic-only, non-promotable, no training authorization

## Global constraints

1. Production implementation begins only after this source-capture bundle is reviewed.
2. Reuse existing completion-only loss, gradient-accumulation normalization, trainable-parameter hashing, step ledger, run manifest, adapter artifact manifest, and final-step save logic.
3. Load Train17 with `PeftModel.from_pretrained(..., is_trainable=True)`.
4. Never call `get_peft_model()` for a fresh adapter in this continuation path.
5. Never use `resume_from_checkpoint`; create fresh optimizer and scheduler state.
6. Never inherit historical `512`, `10 passes`, `210 steps`, `21 warmup steps`, old dataset path, or old output root.
7. Job environment must be clean and explicit; ambient project output variables are forbidden.
8. Package/build stages cannot authorize or execute training.
9. User-facing explanations may be Chinese; production identifiers and program output remain concise technical English.

## Planned implementation tasks after source review

### Task 1 — Reuse map and fixed source boundary
- Verify exact source SHA values.
- Decide `REUSE_DIRECT`, `REUSE_WITH_ADAPTER`, or `MISSING_REQUIRED` per historical trainer function.
- Produce a fixed-head source review before writing production code.

### Task 2 — Round-local training contract
- Define a contract that separates inherited, current-round-derived, and forbidden-inheritance fields.
- Bind parent adapter, T2 dataset, exact sample order, optimizer recipe, three-step schedule, output root, and non-promotable status.
- Add RED/GREEN tests for old `512`, old `210`, old `21`, and ambient output-path rejection.

### Task 3 — Deterministic sample-order manifest
- Materialize the 12-row order using data seed `17`.
- Store ordered row SHA and source-state SHA.
- Run training with `shuffle=false` against the frozen order.

### Task 4 — Train17 continuation loader
- Load Qwen base.
- Load frozen Train17 adapter as trainable.
- Verify initial trainable-parameter SHA equals the parent final trainable-parameter SHA.
- Verify base weights remain frozen and target-module suffixes remain exact.

### Task 5 — Round-local optimizer and schedule
- Reuse AdamW `1e-4`, betas, epsilon, zero weight decay, max-grad-norm `1.0`.
- Fresh linear scheduler, `warmup_steps=0`.
- Exactly one epoch and exactly three optimizer steps.

### Task 6 — Existing ledger and artifact seal adaptation
- Reuse the historical step ledger, formal run manifest, adapter artifact manifest, and final-step-only publication.
- Add only the missing current-round lineage references.
- Do not introduce duplicate ledgers.

### Task 7 — Minimal Human-round binding
- Add a thin binding that references existing PRE/POST, Strong shadows, F0/F1, training plan, dataset, contract, execution receipt, candidate adapter, and evaluation handoff.
- The binding stores references and hashes only, never copied payloads.

### Task 8 — Clean Slurm execution request
- Build but do not submit a single-GPU request.
- Use a clean environment and absolute paths.
- Execution remains gated by `TRAINING_EXECUTION_APPROVED_T2_HUMAN_DIAGNOSTIC_V1`.

### Task 9 — Fixed-head code and artifact review
- Focused tests, package tests, compile/static audit, source/dataset/parent identities, no-training evidence.
- Export a review bundle.
- Stop with training authorization false.

## Final package-A construction gate

Production runner construction is authorized only after:
- this source bundle is uploaded and reviewed;
- Package B reports no existing equivalent round-local continuation implementation that should be reused instead.
