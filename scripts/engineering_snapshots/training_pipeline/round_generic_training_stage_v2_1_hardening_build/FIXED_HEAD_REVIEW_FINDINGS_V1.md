# Generic Training Stage V2 Fixed-Head Review Findings

The V2 review package was not approved for model initialization because four
round-loop hardening gaps remained:

1. Pre-execution input or adapter validation could create an orphan attempt
   directory or an unterminated STARTED receipt.
2. The artifact index did not enumerate the direct dataset, parent adapter,
   parent trainer, parent training config, and base-model manifest inputs.
3. The runtime adapter did not reject profile values that the frozen parent
   trainer would silently ignore (optimizer betas/epsilon/scheduler, precision,
   objective, and PEFT identity).
4. The sample-order manifest token accounting was not mechanically closed
   against its pass order, row/state lineage, and optimizer groups.

V2.1 adds targeted tests and fixes for these gaps. It does not load a model,
submit Slurm, authorize training, or execute optimizer steps. The next gate
remains fixed-head review, followed by a separately authorized model-
initialization smoke.
