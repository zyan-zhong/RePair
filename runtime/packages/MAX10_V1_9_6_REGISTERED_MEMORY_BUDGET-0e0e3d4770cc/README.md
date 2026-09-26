# Registered calibrated Memory budget reuse

The ledger registers FailureMemoryTokenBudgetContractV1 (semantic identity
613166c9f092795cb03c892ee0046f0af5bf7fc13ba44f7fccb950027c329262):
single record 4096 tokens, retrieved library pack 512 tokens, at most 3 records.
These are distinct constraints. The prior claim that 256 was the current
registered single-record ceiling was wrong: it came from a legacy Package-A
governance helper still used by current-round materialization.

This small bridge verifies the current request's exact contract and runtime
identity, reuses all native source-integrity/procedural/safety/causal gates,
and supplies the registered single-record ceiling to FM1/FM2/FM3 construction.
It does not change the library budget, truncate evidence, perform LLM
compression, introduce new labels, or bypass eligibility checks.

R1/R2 immutable closure and R3 round-start snapshot remain unchanged. New
materializations are written beneath a contract-addressed directory. R2's six
records are re-materialized only in a validation directory to prove the fix;
this is not a claim that R2's corrected candidate was inserted into R3 memory.
Future production memory closure uses the corrected bridge automatically.

VERIFY.py validates the package and unit regressions. VERIFY.py --server also
uses the six exact registered R2 records and the registered local tokenizer,
with zero provider/environment/Slurm/Git calls. RUN.sh verifies before launch;
a live resident must first be handed off by the registered controller procedure.
The existing unified status command remains unchanged.

The running campaign contains the previously authorized single R2 promotion
exception, disclosed in V1.9.5. Future selection stays success count first,
goal fraction on ties, one paired seed with identity-checked parent reuse.
Final benchmark tasks remain isolated. No research loop is added.
