# Stage 0 Implementation Plan V1

1. Verify the package and prior fixed-head/twin-review authorities.
2. Re-run focused generic-SELECT and evaluation regression tests in the detached worktree.
3. Materialize a no-model preflight receipt and explicit execution authorization.
4. Submit one resumable GPU job with no explicit CPU or memory request.
5. Start one shared vLLM server with the parent and candidate LoRAs statically registered.
6. Execute the frozen 85-cell schedule for each policy using the existing `run_single_episode`.
7. Audit every published attempt and append-only receipt, aggregate paired results by unique task, and publish a nonzero CRC-validated review ZIP atomically.
8. Seal the round as `PILOT_ENGINEERING_ROUND_V1`; prohibit paper efficacy and promotion claims; emit the Stage 1 automation handoff.
