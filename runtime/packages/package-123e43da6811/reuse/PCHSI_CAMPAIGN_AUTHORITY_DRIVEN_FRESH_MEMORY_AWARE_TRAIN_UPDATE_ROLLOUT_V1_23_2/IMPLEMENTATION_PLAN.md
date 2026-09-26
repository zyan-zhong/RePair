# V1.23.2 implementation plan

1. Pin the exact V123133 input capsule SHA.
2. Derive one deterministic activation identity.
3. Create one state root under the current lineage.
4. Write durable submission reservation.
5. Submit one held, non-requeue Slurm job using the sealed resource plan.
6. Persist/adopt the job id before release.
7. Release the exact held job.
8. Inside allocation:
   - validate exact partition and GPU cardinality;
   - verify implementation HEAD and clean worktree;
   - redirect all runtime caches to run storage;
   - reject a pre-existing bound endpoint;
   - launch exact current vLLM in an owned process group;
   - wait for exact model/version readiness.
9. Revalidate all TRAIN_UPDATE bytes.
10. Materialize schedule/access/gamefile/environment/protocol provenance.
11. Build `ROUND_ROLLOUT_COLLECTION_REQUEST_V1` and authorized execution binding.
12. Run all frozen TRAIN_UPDATE cells through:
    - `SpawnedAlfworldAdapter`;
    - `RoundMemoryPolicyAttemptAdapterV1`;
    - current standard `run_single_episode`;
    - one crash-consistent `ArtifactPublisher`.
13. Classify each terminal as:
    - SCIENTIFIC_SUCCESS
    - SCIENTIFIC_FAILURE
    - INFRASTRUCTURE_INVALID
    - PROTOCOL_INVALID
14. Freeze complete universe.
15. Publish failure cohort only if the whole rollout is scientifically valid.
16. Emit `ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1`.
17. Tear down owned vLLM process group.
18. No training / Memory writeback / next-round transition in this package.
