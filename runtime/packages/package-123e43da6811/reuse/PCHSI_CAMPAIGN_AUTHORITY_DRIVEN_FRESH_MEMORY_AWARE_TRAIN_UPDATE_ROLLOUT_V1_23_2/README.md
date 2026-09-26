# PCHSI V1.23.2 — Authority-driven Fresh Memory-aware TRAIN_UPDATE Rollout

This is the first package in the V1.23 line that intentionally returns to live
scientific execution.

It consumes only the sealed V1.23.1.3.3 source capsule and the implementation
worktree already proven by the full repository regression.

The live scientific unit is:

```text
current parent policy
+
immutable round-start Failure Memory
+
frozen TRAIN_UPDATE universe
        ↓
standard episode evaluator
        ↓
standard AttemptBundle / policy-call evidence / transitions
        ↓
complete rollout-universe seal
        ↓
deterministic scientific-failure cohort
```

No training, Memory writeback, promotion, rollback, benchmark evaluation or
external strong-model Provider call is authorized in V1.23.2.

## Exactly-once-ish Slurm submission boundary

The login-node launcher derives one deterministic activation id from the sealed
capsule/binding/resource authorities.

Submission is:

```text
durable reservation
→ sbatch --hold --parsable --no-requeue
→ durable job-id receipt
→ scontrol release
```

A job name/comment derived from the activation id is used only for
reconciliation after an interrupted login-node launcher.

The launcher never performs an automatic second `sbatch` after an ambiguous
submission state.

## Resource authority

The login node does not choose a partition or GPU count.

It consumes the sealed resource plan:

```text
partition = frozen site-policy authority
GPU count = engine-profile tensor-parallel-size authority
```

The compute job then validates the real Slurm/CUDA topology before launching
vLLM.

## Runtime ownership

The compute job refuses to adopt a pre-existing service on the bound localhost
endpoint.

It launches the exact service command from the sealed execution binding in its
own process group and tears down only that owned process group.

No Human PID selection exists.

## Rollout semantics

The schedule is the complete frozen TRAIN_UPDATE manifest in deterministic
schedule order.

There are no per-task scientific retries in this first live canary.

If an infrastructure/protocol-invalid cell occurs:

- no new environment task is executed after it;
- all remaining scheduled cells receive synthetic infrastructure-invalid
  terminals;
- the complete universe denominator remains explicit;
- no scientific failure cohort is published from the invalid rollout.

If the whole universe is protocol-valid, all scientific failures are published
as the deterministic failure cohort.

The final handoff is ready for the existing automatic Analyzer path, but this
package does not invent an Analyzer executable command that has not yet been
live-bound.
