# V1.23.2W implementation plan

## Reused authorities
- V1.23.2V Dynamic PRE V2 representation, Researcher Memory, prompt/schema, request renderer and `execute_one()` transport.
- Historical `infra_recovery_disposition.py` at commit `1ea4647443d4a9140bb6712c7f92f1538c896b8b`, blob `d8b3d3332120b5efff1f53207e2bb5ec423e9d76`.
- Historical V1.21.23 autonomous partial-POST recovery architecture: classify from durable ledgers; same-call no-resend; bounded new remediation logical call; no Human scientific decision.

## State machine
1. Re-render exact PRE request and recompute original logical-call identity.
2. If accepted already: adopt only.
3. If non-accepted: read `method_result.json`, `attempt_000.json`, `transport_http_meta.json`; classify using the frozen historical source.
4. Ineligible/ambiguous/method failure: fail closed, no provider call, no Human disposition.
5. Eligible SAFE_PRE_SEND / SAFE_PROVIDER_REJECTION and invocation-start authority present: write bounded recovery authority and create a new deterministic remediation scientific unit/logical call with exactly the same projection/request/model/round/policy/Memory.
6. At most one remediation provider call. Never resend the original logical call. Never run a second recovery.
7. If accepted: reuse V Dynamic PRE finalization and freeze the same planner-bound F0/F1 handoff.

## Current-round counts
No live denominator (24, 34, 39, 68, 76, etc.) is a production authority. All state/branch counts remain mechanically derived.
