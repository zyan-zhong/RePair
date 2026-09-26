# V1.23.2 package validation

Package-level tests and static gates cover:

- exact capsule SHA pin;
- no current round/model/task-count/A800/GPU literal in generic production code;
- resource argv comes entirely from the sealed Slurm plan;
- held submission + no-requeue + deterministic job comment/name;
- deterministic activation identity;
- no strict-shell flags;
- no external OpenAI/Provider client;
- no training invocation;
- task retry count is zero in versioned operational policy;
- compute runner owns and signals only its own service process group;
- classification keeps infrastructure/protocol failures out of scientific
  task-failure counts.

The server-side live run additionally checks allocation topology, exact service
readiness, all TRAIN_UPDATE bytes and immutable Memory authority.
