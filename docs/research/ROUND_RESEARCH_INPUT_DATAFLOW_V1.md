# Round Research Input Dataflow V1

## 1. Purpose

This is the reusable dataflow that supplies the round-level Training
Researcher. It replaces manual JSON assembly. The current π1→π2 Human
Reference Round is a legacy-asset adapter into the same dataflow used by later
Strong-API and Local Research Planner rounds.

It does not replace:

- Round Evidence;
- Hierarchical Analyzer;
- Persistent Failure Experience;
- Human/API/Local Researcher implementations;
- F0/F1;
- trainer, evaluator or promotion gate.

## 2. Five required input lanes

Every `RESEARCHER_ROUND_INPUT_PACKAGE_V1` contains:

1. **Current policy scorecard**
   - policy lineage, checkpoint and config;
   - task-set identity;
   - rollout census;
   - mechanical failure census.

2. **Analyzer evidence**
   - Formal Analyzer result manifest;
   - metric report;
   - candidate, abstention and missingness authority through the Formal archive.

3. **Historical Failure Experience**
   - one governed `RESEARCHER_MEMORY_VIEW_V1`;
   - purpose `ROUND_RESEARCH_PLANNING`;
   - train-side records only;
   - held-out data aggregate-only.

4. **Experiment history**
   - historical F0/F1;
   - GO/NO-GO;
   - prior Researcher decisions;
   - training/evaluation/regression history;
   - code/config changes.

5. **Resource and cost**
   - resource budget manifest;
   - Human PRE selects exact verification/API/environment/GPU budgets.

## 3. Automatic round flow

```text
ROUND_TRANSITION_RECEIPT_V1
→ SELF_IMPROVEMENT_ROUND_MANIFEST_V1
→ fresh rollout / scorecard
→ Formal Analyzer seal
→ ROUND_EVIDENCE_PACKAGE_V1
→ governed Failure/Research Memory snapshot
→ build_researcher_memory_view_v1(
      purpose=ROUND_RESEARCH_PLANNING
  )
→ RESEARCHER_ROUND_INPUT_PACKAGE_V1
→ Human / Strong API / Local Researcher adapter
→ RESEARCHER_PRE_DECISION_V1
```

Future rounds must consume explicit `ROUND_ARTIFACT_INDEX_V1` bindings. They
must not recursively search the filesystem or ask a human to concatenate
evidence.

The current π1→π2 adapter performs a one-time import from already frozen legacy
assets. Once the current binding is sealed, subsequent rounds use stage
receipts and artifact indices.

## 4. Role parity

Human Reference, Strong-API shadow and future Local shadow receive the same:

```text
ROUND_EVIDENCE_PACKAGE_V1
RESEARCHER_MEMORY_VIEW_V1
RESEARCHER_ROUND_INPUT_PACKAGE_V1
```

The shadow cannot see Human PRE bytes, Human PRE hash or Human rationale.

## 5. Authority

The Researcher may identify the principal bottleneck, discover or synthesize a
key repair hypothesis, freeze one principal change, allocate a portfolio and
define training, evaluation and stop rules.

It may not:

- create mechanical facts;
- execute task actions;
- assign Benefit/Harm/Neutral/Uncertain;
- alter sealed Analyzer outputs;
- read strong-model benchmark per-task results;
- promote its own candidate policy.

## 6. Current-round prerequisite boundary

This implementation materializes:

```text
RESEARCHER_ROUND_INPUT_PACKAGE_V1
HUMAN_REFERENCE_EVIDENCE_BINDING_V1_CANDIDATE
HUMAN_RESEARCHER_PRE_WORKSHEET_V5
HUMAN_PRE_PREREQUISITE_REPORT_V1
```

It does not freeze the Human PRE decision. Human scientific selection remains a
separate reviewed artifact.
