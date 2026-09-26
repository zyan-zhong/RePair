# V1.23.2T — Git object-ID authority recovery + Strong Analyzer group tail + dynamic Planner pair universe

Consumes only a successful `V1232R1` output root. It reuses existing Strong Analyzer, Memory, G/C/P/X, candidate and K<=1 assets. It does **not** rerun L-A0/L-A1, ALFWorld, F0/F1, training, SELECT, or promotion.

Scientific route:

`39-ish machine-derived SOURCE_CLOSED groups -> exact Analyzer Memory -> G-A2/G-A3 -> C -> deterministic P -> X -> source-context execution equivalence -> candidate projection -> K<=1 -> dynamic Planner pair universe`.

All counts are read/derived from upstream authorities. No current group count, pair count, job ID, state root, Memory SHA, model path, or legacy 30/12 cardinality is compiled into production code.

Transport governance: one logical call / one transport attempt; terminal logical calls are reused; partial call directories fail closed; `AMBIGUOUS_POST_SEND` is never resent. G ambiguity quarantines that group; C/X ambiguity preserves target missingness and continues unrelated targets. Other hard stops fail closed.


## Git repository identity recovery

V1232T retains the V1232S scientific scope but corrects one pre-provider control-plane defect:
V1232S treated `git rev-parse HEAD` as a 64-hex SHA-256 artifact digest. Git commit IDs instead live in the repository object-ID domain.

V1232T reads `git rev-parse --show-object-format=storage`, verifies `HEAD^{commit}`, validates the OID length from the reported hash algorithm through `hashlib`, and confirms `git cat-file -t <oid> == commit`.
No 40-hex or 64-hex Git OID length is compiled as current-run authority.
