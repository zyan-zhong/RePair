# Failure Memory FM1/FM2 Decoupling Audit V1

Date: 2026-08-19

## Status

This audit records the real pre-A9 observation that motivated a narrowly
scoped representation-availability fix.

It does **not** change the FM1 token budget, FM1 safety policy, FM2 safety
policy, source-integrity gate, effect authority, or Package-A exposure
authority.

## Real pre-A9 evidence

All three human-approved source candidates passed source integrity and FM2
Policy-view safety, but their independently constructed FM1 raw episodic views
exceeded the frozen 256-token ceiling.

| Candidate | Source integrity | FM1 disposition | FM1 tokens | FM1 safety | FM2 disposition | FM2 tokens | FM2 safety |
|---|---|---|---:|---|---|---:|---|
| `a3d1a1d25629724e712632b3527278d779fb48c388a4b397b7554e3b4e4d617f` | VERIFIED | `PROJECTION_INELIGIBLE_TOKEN_BUDGET` | 514 / 256 | PASS | ELIGIBLE | 180 / 256 | PASS |
| `793e4aaa87d7caf9152aab797ccf5a30e6babdeacfc183be12a9de181e652201` | VERIFIED | `PROJECTION_INELIGIBLE_TOKEN_BUDGET` | 357 / 256 | PASS | ELIGIBLE | 186 / 256 | PASS |
| `408fca406a563eaff9cd813572bd0f3dd8b85a7f736ecb913d00e9aad3c24899` | VERIFIED | `PROJECTION_INELIGIBLE_TOKEN_BUDGET` | 323 / 256 | PASS | ELIGIBLE | 184 / 256 | PASS |

Diagnostic closure:

```text
CANDIDATE_COUNT=3
FM1_UNAVAILABLE_COUNT=3
UNEXPECTED_BLOCKER_COUNT=0
FM1_FM2_DECOUPLING_ROOT_CAUSE_CONFIRMED
PRE_A9_FM1_DIAGNOSTIC_RC=0
```

## Scientific interpretation

`FM1_MATCHED_RAW_EPISODIC_VIEW_V1` and the FM2 structured descriptive
projection are independent Policy-view representations of one governed record.

For these three candidates:

- FM1 is **unavailable** under its frozen raw-view token contract;
- FM1 is not unsafe;
- FM1 is not silently truncated;
- FM2 remains independently safe and within budget;
- source integrity remains verified;
- descriptive record eligibility should therefore not be destroyed solely by
  FM1 token overflow.

The fix permits exactly this FM1 disposition to be non-blocking:

```text
PROJECTION_INELIGIBLE_TOKEN_BUDGET
```

The following remain blocking:

- FM1 Policy-view safety failure;
- FM1 source ambiguity;
- FM1 source/governance/access/lifecycle failure;
- any other unrecognized FM1 failure;
- any FM2 ineligibility.

FM2 remains mandatory for Package-A descriptive eligibility.

## Frozen non-changes

```text
FM1 hard ceiling = 256
FM2 hard ceiling = 256
FM1 truncation = forbidden
FM1 synthetic replacement = forbidden
Policy-view safety = unchanged
source-integrity gate = unchanged
effect authority = UNTESTED
Package-A exposure = NOT_EXPOSED_PACKAGE_A
Benefit/Harm authority = not created by this fix
FM3 prescriptive authority = not created by this fix
```

## Snapshot semantics

`MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_V1` may contain a canonical FM1 artifact whose
build disposition is `PROJECTION_INELIGIBLE_TOKEN_BUDGET`, provided FM2 is
ELIGIBLE and all other Package-A gates pass.

The FM1 artifact remains in the snapshot so downstream Package B can observe
the true representation availability state. Package B must not fabricate,
truncate, rewrite, or increase the FM1 budget.

A later B-DIRECT M1 cell requires an actually ELIGIBLE FM1 view. An FM1
token-ineligible record may be used for FM2-based development but cannot be
silently treated as an M1 cell.

## Authority boundary

This audit is a representation-coupling correction only.

It creates no real A9 execution evidence and does not itself authorize
environment replay.
