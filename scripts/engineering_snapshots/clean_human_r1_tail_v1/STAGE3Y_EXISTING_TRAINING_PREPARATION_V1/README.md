# Existing training-chain preparation (Stage3Y)

This is an offline preparation adapter, not a new trainer and not training authorization.
Run `python -B RUN_PREPARE.py` from the active project environment. No API key,
Slurm job, model weights, environment step, commit or push is used.

## Existing code reused

- `post_round.validate_shadow()` and `post_round.compare_posts()` from the exact
  Stage3X delivery, identified by file hashes in `current_round.json`.
- Current `PolicyCallEvidenceV1`, source-replay/candidate contracts, branch hash,
  original manifest/binding factory and original RAW prompt builder.
- v1.7.2 `build_t2_source_adapter_row`, `make_messages`, `mask_prompt_prefix`,
  and `build_native_row`. The old 12-row command-line wrapper is not invoked.
- Generic Training Stage V2.1 artifact-index format; the actual trainer remains
  `round_training.stage_runner.run_training_stage` and is NOT called here.

## What this preparation does

1. Validate the exact fixed repository bytes.
2. Read the existing accepted Stage3X POST archive by its exact reported SHA.
   Keep Human/Strong decisions unchanged; recompute only the existing mechanical
   comparison, never semantic adjudication and never another model call.
3. Read only the first F0 source context in each existing paired repetition.
   Require identical source prompt/menu/token IDs across repetitions. Deduplicate
   to one original registered state/action per state, not five training copies.
4. Construct renderer-compatible diagnostic previews, preserving original
   Neutral/Uncertain labels and all diagnostic/non-promotion flags.
5. Use the locally available clean tokenizer and frozen chat-template hash to
   prepare native preview rows. Assert the prompt token IDs equal live evidence.
   No truncation, prompt rewriting, retokenization during training, or padding.
6. Produce a DRAFT, NOT APPROVED selected-portfolio T0/T2 proposal. Epoch/seed/
   accumulation choices live in configuration as a proposal, not in generic code.
7. Capture only the exact hash-bound historical training implementation source
   needed to reuse its training loop, not old examples, adapters or checkpoints.

The proposed selected-portfolio diagnostic control is not automatically the
full 'all unverified Analyzer repairs' T2 arm. Its scope must be stated separately.
The original frozen Human POST and scientific labels are never overwritten.

## Still required before training

- Read and adjudicate the actual accepted Strong POST against Human POST.
- Separately freeze/approve the diagnostic arm and recipe. The current Human
  POST does not authorize immediate training or substitution of other arms.
- Bind train-update access and disjoint selection identities using existing
  authorities. A path containing `train` is not sufficient authorization.
- Bind clean-base seeded new-LoRA initialization without loading the pilot
  adapter. The existing parent-adapter-only runtime cannot be misrepresented
  as that clean initializer.
- Produce/validate the original round-local contract, sample order, model-init
  evidence and execution authorization before invoking the original trainer.

Exit 0 means preparation outputs were written. It never means training started,
finished, or a new pi1 checkpoint exists. Any tokenizer blocker is saved rather
than silently replaced by a different tokenizer; other missing original authority
or input hash mismatch fails closed with exit 21.

`TRAINING_PREPARATION_REVIEW.zip` contains actual Human/Strong values, comparison,
source previews/proofs, local tokenization results when available, proposed
parameters and explicit remaining admission blockers. Repeating the same inputs
reuses byte-identical outputs without rerunning models or training.
