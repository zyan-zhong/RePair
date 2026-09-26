# Strong Researcher Blind Evidence Hydration V1

## Problem

The Human Research Planner adjudication is approved as a scientific decision
candidate, and its blind Strong input correctly hides Human selection. However,
several round-level lanes still expose only immutable SHA references:

```text
policy lineage/config/task set
rollout census
mechanical failure census
Formal result manifest
Analyzer metric report
code/config diff
resource budget
optional historical F0/F1 / GO-NO-GO / training / prior decisions
```

A hash is sufficient for provenance but not for model reasoning.

## Design

This stage hydrates only evidence already bound by the current Round Evidence.

```text
Round-Evidence SHA
        ↓
search approved frozen roots
        ↓
exact file SHA or matching non-reference artifact identity
        ↓
validate no ambiguity
        ↓
full JSON object if small
or deterministic compact view if large
        ↓
STRONG_RESEARCHER_BLIND_PRE_INPUT_V2
```

Null history remains null. The system does not import missing evidence from chat
history, memory, or a later experiment.

The policy checkpoint remains identity-only: the Researcher needs the frozen
checkpoint identity, not model-weight bytes.

## Why this is needed

Human and Strong PRE are intended as a controlled comparison. The Strong
Researcher must be able to read the same evidence content that informed the
Human reference, while still being unable to see the Human decision.

The hydrated input therefore preserves:

```text
all 30 A2/A3 candidate pairs
round-level Researcher Memory
policy scorecard content
Analyzer aggregate evidence content
available experiment-history content
resource/budget content
```

and still forbids:

```text
Human selection / rationale / PRE hash
current F0/F1 outcomes
future π2 evaluation
strong-model benchmark per-task results
success-trajectory optimization
```

## Resolution behavior

A required bound artifact is accepted when the highest-authority match is
unique by scientific content identity. Multiple copied files are allowed when
the content is identical.

The stage fails closed into a review state when:

```text
required evidence is missing
required evidence is not readable
two distinct artifacts claim the same bound identity
```

It does not silently pick one.

## Outputs

```text
STRONG_RESEARCHER_EVIDENCE_HYDRATION_MANIFEST_V1.json
STRONG_RESEARCHER_BLIND_PRE_INPUT_V2.json            # only if ready
RESEARCH_PLANNER_REFERENCE_TRACE_V3.json             # only if ready
STRONG_RESEARCHER_EVIDENCE_HYDRATION_BUILD_REPORT_V1.json
bound_readable_evidence/<slot>/...
```

The Human 12-state adjudication and repair portfolio are unchanged.

## Future gated flow

After review:

```text
push feature branch
→ freeze approved Human PRE + portfolio + reviewed hydrated blind input
→ run Strong Researcher blind PRE shadow V5
→ Human/Strong field-level adjudication
→ F0/F1 handoff
```


## Authority-recovery addendum

The first live hydration run exposed an authority-ranking defect rather than
missing scientific evidence.

Observed live result:

```text
required bound slots = 9
resolved = 3
unresolved = 6
```

The six unresolved slots were `QUERY_REQUIRED_AMBIGUOUS`, not proven missing.
For five of them the scan already contained one dedicated
`05_round_evidence_seal/support/*` artifact, but it tied with schema-less
hash-reference maps copied through Researcher input and review artifacts.

The three slots initially marked resolved (`policy_config`, Formal result
manifest, Analyzer metric report) also selected schema-less nested reference
maps rather than the underlying readable evidence.

The corrected authority rules are:

1. a schema-less map that only contains SHA references and authority/status
   metadata is provenance, not readable evidence;
2. `SCIENTIFIC_UNIT_IDENTITY_V1` is an identity carrier, not task-set content;
3. an identity-field match is eligible as readable content only when the
   artifact filename/schema fully matches the semantic slot name;
4. sealed Round-Evidence support artifacts receive priority among eligible
   identity-field matches;
5. an exact file SHA remains the strongest authority;
6. UTF-8 text/config files bound by exact file SHA may be exposed as text;
7. distinct highest-authority leaf artifacts still fail closed.

This changes only evidence resolution. Human adjudication, the 12-state
portfolio, budgets, visibility boundaries, and effect-label authority remain
unchanged.
