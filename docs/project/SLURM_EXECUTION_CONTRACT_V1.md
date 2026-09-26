# Cluster / Slurm Execution Contract V1

```text
STATUS = CANONICAL_PROJECT_EXECUTION_BACKGROUND
CHANGE_POLICY = EXPLICIT_USER_DIRECTIVE_OR_NEW_SITE_EVIDENCE_REQUIRED
```

Date frozen: 2026-08-19

This document records the site-specific HPC execution contract established by
real PCHSI runs. It is not a universal Slurm prescription.

## 1. Shell failure-handling policy

Project shell snippets and runners use explicit return-code handling:

```bash
set +e
set +u
set +o pipefail
```

Do not use:

```bash
set -euo pipefail
```

unless the researcher explicitly changes this project rule.

For an important pipeline:

```bash
command 2>&1 | tee log
RC="${PIPESTATUS[0]}"
```

`$?` after `tee` must not be used as a substitute for the primary command's
exit status.

## 2. A800 submission shape

The default A800 shape is:

```bash
#SBATCH -J <job-name>
#SBATCH -p gpu_a800
#SBATCH --gpus=<N>
#SBATCH -t <realistic-walltime>
#SBATCH -o <log-path>
#SBATCH -e <log-path>
```

Do not explicitly request the following by default:

```text
--nodes
--ntasks
--cpus-per-task
--cpus-per-gpu
--mem
--mem-per-cpu
--gres
```

The site policy allocates node/CPU/memory from the GPU request.

The observed `gpu_a800` site defaults used during this project include:

```text
DefCpuPerGPU = 8
DefMemPerCPU = 15700
```

These values are execution evidence, not a cross-cluster assumption.

## 3. GPU syntax

Prefer:

```bash
--gpus=N
```

rather than:

```bash
--gres=gpu:N
```

on this cluster unless a future tested workload demonstrates a different
site-approved requirement.

## 4. Submission preflight

For a new resource shape, run:

```bash
sbatch --test-only <script>
```

before real submission.

A successful project preflight with `--gpus=1` demonstrated that the site
automatically assigned 8 processors.

The cluster uses a site `job_submit.lua` policy; explicit resource fields that
are normally legal Slurm syntax may still be rejected by that site policy.

## 5. Walltime

Use a realistic walltime rather than a large default.

For short PCHSI GPU work, start from approximately 45–60 minutes when the
measured workload supports it. Increase only when runtime evidence requires it.

Shorter realistic walltime may improve scheduling opportunities; do not reduce
it so far that normal execution repeatedly dies at the time limit.

## 6. tmux and Slurm

Use `tmux` for long interactive preparation and audit work.

Use Slurm for GPU workloads and other long scheduled jobs.

SSH disconnection is an operational event and must not be confused with a
scientific/code failure.

## 7. Job evidence and resumability

Long jobs should record:

- submitted job ID;
- output/error log;
- success/DONE marker;
- state inspection path;
- immutable or hashed scientific evidence;
- enough state to resume without re-running already sealed scientific cells.

Do not submit a duplicate job merely because the SSH client disconnected.

## 8. Scientific freeze precedes operational tuning

Scientific identities must be frozen before model execution when the protocol
requires it:

- task/panel identity;
- policy/checkpoint identity;
- prompt/runtime identity;
- source evidence;
- scientific manifest;
- stopping rule.

A later operational correction to Slurm resource headers may be made only when
it does not change the scientific authority or sampled cases.

## 9. Network failures

Git fetch/push or SSH transport failures are operational failures.

They must not automatically trigger rerunning a scientific experiment.

First determine whether the remote state already equals the local intended
commit/evidence state.

## 10. Change control

A change to this contract requires either:

- an explicit researcher/user directive; or
- new concrete site-policy evidence showing that a rule is no longer valid.

The change and its evidence must be recorded before future runners adopt it.
