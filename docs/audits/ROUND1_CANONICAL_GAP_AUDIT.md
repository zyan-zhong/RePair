# Round-1 Canonical Gap Audit

## Purpose

Close the remaining byte-identity, semantic-identity and provenance
gaps for the frozen first-round evidence before Failure Memory records
or new scientific claims are generated.

## Global constraints

- Do not rerun the strong model to repair historical evidence.
- Do not rerun ALFWorld to repair historical evidence.
- Do not overwrite historical R132 case ledgers.
- Preserve original missingness and rejection states.
- Failure Memory generation remains on hold until the canonical
  evidence chain is closed.

## R132 PRIMARY117 identity-chain audit

### Question

Can the recovered R132 execution be bound deterministically to the
117 frozen source cases, 117 frozen requests, actual case directories
and the existing Q2 state-binding population?

### Frozen identities

- R132 package freeze root:
  `794727df6157715d3c8e04156f97e53300ef9107ca793d215caec447cab964b5`
- R132 primary log SHA-256:
  `315236e71249dc9f8fd37617b9f426356dfc2c810ad5d3dafb2769aed92652e9`

### Result

Status: `PASS`

Observed:

- primary case manifest rows: 117
- primary request manifest rows: 117
- run case directories: 117
- Q2 state bindings: 351
- Q2 cases: 117
- Q2 bindings per case: exactly 3 for all 117 cases
- teacher outputs: 91
- rejections: 26
- call-evidence files: 117
- raw response bodies: 99
- transport-attempt metadata records: 135
- blockers: 0
- warnings: 0

### Interpretation

The source-case, frozen-request, run-directory and Q2-binding identity
sets are closed for R132.

The 91 / 26 teacher-output-versus-rejection partition also matches the
previously sealed R132 population.

`terminal.json` exists for every case, but the generic V1 label
extractor reported `UNRESOLVED_TERMINAL_LABEL` for all 117 cases.
This is not treated as an identity-audit failure. It is the next
independent semantic-provenance audit target.

No terminal disposition is inferred or repaired in this module.

### Evidence

Repository evidence directory:

`docs/audits/evidence/round1_canonical_gap/r132_primary117_identity_v1/`

Original audit identities:

- audit script:
  `e493ef7a0151a41adaa2c208c0701431a20954b2908d6f0c4df114c913aab8c5`
- 117-row case identity table:
  `89e513cbf758bf12df6c66050e4093f3f538dcc61f6cfc411b5b4e6b183724f3`
- summary:
  `c8d5125d47512d88542751262daf95096ffd43941acfc56ed444469f163768c8`

### Remaining gap

Next small module:

**R132 terminal disposition and semantic provenance audit.**

It must read the actual final R1.3.2 terminal schema and bind terminal
disposition, rejection/teacher output and Q2 references without
rerunning or rewriting any historical case.
