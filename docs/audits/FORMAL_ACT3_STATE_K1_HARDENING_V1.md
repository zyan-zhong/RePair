# Formal ACT3 state-level K≤1 materialization hardening V1

## Scope

This is a pre-F0/F1 protocol-compliance hardening of the already frozen
`candidate_limit_per_condition_per_state = 1` contract.

It does not modify Analyzer prompts, grouping, Memory, X, the 30-state
registered universe, or any already observed Analyzer artifact.

## Incident

The grouped G-stage contract correctly limits proposals per error member.
The Formal scientific budget is per condition × source state.  The current
30-state cohort contains 37 source-closed error memberships, including seven
states with two memberships.

`candidate_sha256` is an artifact identity and includes proposal provenance.
Therefore it is not sufficient as an execution-equivalence identity.

## Frozen correction

1. Project and validate candidates exactly as before.
2. Remove non-executable candidates from the environment budget.
3. Canonicalize execution semantics:
   source state, menu, exact action or ordered short-option actions, and
   termination condition.
4. Deduplicate artifacts that have identical execution semantics.
5. If zero unique executable interventions remain, preserve an explicit
   no-candidate disposition.
6. If one remains, register it. Equivalent artifact/proposal identities are
   all preserved.
7. If more than one genuinely different intervention remains, select none and
   record `METHOD_INVALID_K1_STATE_BUDGET_COLLISION`.
8. Never select a winner using confidence, rank, SHA ordering across
   non-equivalent interventions, prose quality, or later environment outcome.

`abstained=true` remains a legacy/registry compatibility field for zero
candidate rows. Scientific reporting MUST consult `formal_disposition` and
`voluntary_abstention`; a K1 collision is not voluntary/model abstention.

## Reporting

Primary registered denominator remains 30 states. Method source-binding
failure is not reclassified as infrastructure unavailability. Full raw
Analyzer/X/proposal/candidate evidence is retained.

This hardening was introduced before current Formal F0/F1 Benefit/Harm
outcomes were observed. It must not be described as if the implementation
itself had been preregistered earlier.
