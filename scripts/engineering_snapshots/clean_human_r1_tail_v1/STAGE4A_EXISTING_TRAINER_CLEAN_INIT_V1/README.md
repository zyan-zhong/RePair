# Existing Trainer clean initialization and binding

This adapter consumes the already-approved Stage3Z NEXT_STAGE_BINDING and plan.
It does not select an arm, rewrite a Planner decision, retokenize, relabel Neutral,
change I1, load pilot training data, or promote a policy.

## Current run

Input review: `ec4b2396208f71dad21bc3b2bdb4b29d05a3c2d3ecdf17ab14695a6ac99d8596`.
The request carries the fixed repository and artifact locations. Scientific
parameters are read from the approved plan, not from this program.

1. `bash RUN_ALL.sh --submit-smoke` verifies the packet, live input references,
   inherited code tree, formal source and model-byte-manifest identity, then
   submits ONE single-GPU initialization job. It does not authorize training.
2. `bash RUN_ALL.sh --status` reads scheduler state and produced receipts.
3. Once the initialization and compiled binding are reviewed, the SAME package
   supports `bash RUN_ALL.sh --submit-training --approve-binding <exact SHA>`.
   This is a distinct execution authorization, not implicit in the plan.

All commands should be invoked as child commands, never sourced into the login
shell. No shell fail-fast options are set. No CPU or memory resources are
explicitly requested; the bound wall time is 20 minutes. Submit retries are not
automatic. An intent with no receipt requires reconciliation.

## Reuse map

- Fixed `629895d8...` Generic Training Stage V2.1, contracts and receipts.
- Existing formal_train.py SHA `4709c32d...` seeded fresh initializer, optimizer,
  loss, grouping, training loop, final ledger and checkpoint writer.
- Original frozen_formal_train_peft adapter: record/order validation and PEFT
  reload path. Its parent is an initialization-only, step-zero adapter created
  from the clean snapshot in this job, not a trained pilot adapter.
- Existing full-tree verifier from Stage3V.
- Exact upstream native data, masks, sample order, budget, optimizer and LoRA
  config. The runtime contract adds initialization/adapter evidence only.

The fixed model-byte manifest is read as model-only metadata from the original
engineering provenance location. Every listed file is checked at the CLEAN
snapshot path. No pilot samples, training recipe or trained adapter are read.

## Smoke

Use the original seeded initializer. Verify frozen base parameters, finite LoRA
A, zero LoRA B, a finite enabled-versus-disabled numeric probe, repeat-seed
parameter equality and saved-adapter reload equality. Export only an untrained
initialization adapter and receipts. No optimizer is constructed or stepped.

The 16-token prefix is an engineering numeric probe from the bound native input;
it is not a task evaluation or a training sample selection rule.

## One necessary compatibility boundary

The older formal_train.verify_formal_schedule function contains an exact
`effective_batch == 4` pilot assertion. The approved clean plan uses a different
batch. The isolated module adapter delegates schedule validation to the existing
Generic Stage validate_training_contract and original _verify_order, with an
explicit in-memory batch/contract equality check. This is NOT a skipped check,
no-op, padding, row deletion, or a change to the optimization loop. Original
files remain unchanged.

## Automation boundary

`prepare(request)` consumes artifact references; `compile_binding` produces the
existing stage binding; `authorize_training` validates exact caller authority;
`train` invokes the ORIGINAL stage_runner.run_training_stage. Future registered
Primary actors can feed the same artifact API. This package does not deploy the
entire Strong-primary orchestrator or archive/no-training lifecycle. Unsupported
plans fail without automatic fallback. Archive provenance remains incomplete.

Initialization success != trained pi1; training success != promotion. The T2
candidate remains diagnostic and awaits the separately bound TRAIN_SELECT,
I1/RAW, Memory-OFF/Harness-OFF evaluation route.
