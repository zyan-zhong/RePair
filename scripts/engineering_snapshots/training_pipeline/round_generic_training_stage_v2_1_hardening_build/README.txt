Round Generic Training Stage V2.1 Hardening Build

The generic core contains no current-round identity. Current Human-T2 values live in a replaceable profile and content-addressed stage binding. The runner adds STARTED/terminal stage receipts and input/output artifact indexes. This package does not load a model, submit Slurm, execute training, or authorize training. A separate model-initialization smoke is required after fixed-head review.

Run: sha256sum -c PACKAGE_FILES.sha256 && chmod 700 RUN_BUILD_REVIEW.sh && bash ./RUN_BUILD_REVIEW.sh 2>&1 | tee build_review_driver.log

Hardening changes
-----------------
- Pre-execution validation completes before any attempt root is created.
- Runtime failures close the STARTED receipt chain conservatively.
- Direct dataset, parent adapter, parent trainer, training config, and base-model manifest inputs are indexed.
- Sample-order optimizer groups are closed against row/state lineage and token accounting.
- The frozen parent runtime adapter rejects unsupported optimizer, precision, objective, and PEFT contract drift.
- The parent adapter config is checked against the round-local PEFT contract.
