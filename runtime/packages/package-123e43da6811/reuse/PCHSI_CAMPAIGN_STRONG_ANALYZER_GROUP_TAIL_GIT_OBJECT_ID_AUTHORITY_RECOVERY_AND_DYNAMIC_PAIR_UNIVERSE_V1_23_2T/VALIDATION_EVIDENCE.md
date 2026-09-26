# Validation evidence

Package verification checks:
- no current run/job/root/denominator literals;
- existing G/C/P/X, Analyzer Memory, candidate and K<=1 APIs are explicitly reused;
- no ALFWorld/training/Slurm execution path;
- no automatic retry / resend / replacement / top-up;
- durable source-context execution-equivalence behavior;
- operator shell strict-mode prohibition;
- read-only STATUS helper.

The live server run, not these package tests, is authoritative for scientific results and provider call outcomes.


- Git HEAD is validated as a Git object ID, not as an artifact SHA-256;
- repository object format is read from `git rev-parse --show-object-format=storage`;
- `HEAD^{commit}` and `git cat-file -t` provide commit-type authority;
- no fixed 40/64 Git OID length is used as current repository authority.
