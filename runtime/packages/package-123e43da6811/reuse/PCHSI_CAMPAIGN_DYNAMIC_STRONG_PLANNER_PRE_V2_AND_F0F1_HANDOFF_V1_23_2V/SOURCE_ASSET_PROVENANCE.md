# V1232V Source Asset Provenance

This package is a continuation adapter. It does not replace the fixed scientific checkout or create a second Planner/F0F1 implementation.

## Durable reused scientific contracts

- Dynamic PRE V2 staging source authority: `integration/strong-primary-dynamic-pre-v2` at durable historical head `6b9f270016213393993494314b4b0be8f6b2c49a`.
- Fixed live runtime authority remains discovered from `ROLE_SCOPED_STRONG_PRIMARY_FRESH_ROUND_AUTHORITY_V1.json`; no repository path or current HEAD is hard-coded.
- Reused Dynamic PRE helpers:
  - `src/pchsi/research_intelligence/dynamic_primary_pre_v2.py`
  - `src/pchsi/research_intelligence/current_round_researcher_memory_v1.py`
  - `src/pchsi/cognitive_runtime/dynamic_pre_v2_semantic_normalization.py`
  - `prompts/cognitive_runtime/RESEARCHER_PRE_PRIMARY_V2.txt`
  - `configs/cognitive_runtime/schemas/strong_researcher_pre_primary_v2.json`
- Role-neutral F0/F1 protocol is read from the live fixed repository at runtime:
  `configs/research_intelligence/planner_bound_f0f1_replication_protocol_v2.json`.

## Representation seam closed by this package

V1232U scientifically freezes the current dynamic A2/A3 pair universe but its package-local row wrapper does not explicitly carry the older PRE-V2 adapter fields `pair_status=COMPLETE_A2_A3` and top-level per-condition `source_state_sha256`.

V1232V therefore writes `V1232V_DYNAMIC_PRE_PAIR_UNIVERSE_VIEW_V1`: an immutable representation-only view bound to the exact V1232U pair-universe SHA. It does not add/remove/re-rank candidates, does not change K<=1 outcomes, and carries `scientific_selection_changed=false`.

## Provider/runtime reuse

The live PRE call reuses the fixed checkout's `execute_one()`, request renderer, P2 transport, call ledger, transport-attempt ledger, provider response parser, and no-hidden-retry behavior. The package overlays only the versioned `R-PRE-PRIMARY-V2` prompt/schema/semantic validator in-process; the fixed checkout is not modified.

## Authority boundary

PRE may choose a bounded verification portfolio but cannot assign Benefit/Harm/Neutral/Uncertain. Effect authority remains `INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY`. Training remains `HOLD_PENDING_VERIFIED_F0F1_MANIFEST`.

## Vendored asset SHA-256s in this delivery

```text
dynamic_primary_pre_v2.py
fa0d2c34915fac9e77a71b37eed67eb45de7eff8bf9bbdd816d86dbae5a25ff0

dynamic_pre_v2_semantic_normalization.py
1214cc8c298ed319e159e35edd0980cb1909e91787ef8ea27a3f47839d28d695

current_round_researcher_memory_v1.py
b163202d95bc899d177653ff598a25655b6c3fbf3716ecb6f6a751019c7c4128

RESEARCHER_PRE_PRIMARY_V2.txt
1cc1ee3eb7c1cbd946e84bdd3f0a230d787503ba8ed605e8a8ecb8d8716869d0

strong_researcher_pre_primary_v2.json
c15fbc2fc618cb7660a5ddb6500d1b478b591f72ddfbb160c10d4127fda6bea5

planner_bound_f0f1_replication_protocol_v2.json (reference copy only; production reads live fixed-repo authority)
c8f135c4396e54dc925123a078ff228a1901b85422a1aeaab8304a11bb97304d
```
