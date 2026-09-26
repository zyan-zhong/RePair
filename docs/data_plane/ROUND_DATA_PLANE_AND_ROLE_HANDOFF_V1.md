# Round Data Plane and Role Handoff V1

## Round control flow

Every clean adaptive round follows one directional evidence flow:

1. parent policy produces train-side rollout evidence;
2. Evidence Package seals the selected failure evidence;
3. Hierarchical Analyzer produces structured diagnosis;
4. Persistent Failure Experience supplies historical train-side procedural
   context;
5. Research Planner PRE selects the bottleneck, principal change, candidate
   repair portfolio, verification budget, and training-plan intent;
6. same-state F0/F1 executes controlled environment verification;
7. Research Planner POST interprets F0/F1 evidence and selects lessons;
8. deterministic training-data planning/materialization produces the authorized
   training set;
9. schema-aware renderer and Generic Training Stage execute the frozen recipe;
10. internal TRAIN_SELECT evaluates parent vs candidate under Memory OFF /
    Harness OFF;
11. deterministic promotion / rollback freezes the next parent;
12. cross-round retention writes only authorized train-side Memory and role
    traces;
13. the next round is created from the frozen next parent.

No benchmark result is permitted to flow backward into steps 1-13.

## Data accounting

Every stage must preserve machine-readable counts and budgets rather than
recomputing them informally. Round artifacts should bind at minimum:

- source state count;
- unique state count;
- selected state count;
- candidate count by source/mechanism;
- verification cell count;
- Benefit / Harm / Neutral / Uncertain counts;
- policy-training example count;
- localization-supervision example count;
- token budget and realized token count;
- optimizer-step budget and realized optimizer-step count;
- environment-call budget and realized environment-call count;
- model-call budget and realized model-call count;
- task count and replicate-seed count;
- parent/candidate paired-cell count;
- retained Memory record count;
- Strong / Local role-trace count.

These values belong in the artifact chain so downstream stages consume upstream
authority rather than inventing new denominators.

## Role handoff

The supported authority progression is:

`HUMAN_PRIMARY_STRONG_SHADOW`
→ `STRONG_PRIMARY_LOCAL_SHADOW`
→ `LOCAL_PRIMARY_STRONG_AUDIT`.

Analyzer, Research Planner PRE, and Research Planner POST use the same authority
phase for a given round unless a separately frozen exception contract says
otherwise.

Strong structured outputs are retained on every applicable train-side round for
future localization. Local shadow outputs are retained for takeover audit.
Provider-private chain-of-thought is not required; structured evidence,
structured decisions, field-level adjudication, and downstream outcomes are the
supervision targets.

## Cross-round retention

Reusable across clean rounds:

- generic code / schema / contract / tests / infrastructure;
- train-side verified training evidence under its training contract;
- train-side procedural Failure Experience under Memory governance;
- train-side Strong structured traces for localization;
- train-side Local shadow traces for takeover audit;
- frozen round manifests, promotion decisions, and budget receipts.

Not reusable into a clean adaptive round:

- Stage 0 pilot task-specific repairs;
- Stage 0 pilot Memory content;
- Stage 0 pilot task trajectories as training/adaptive evidence;
- valid_seen / valid_unseen detailed trajectories;
- final benchmark outputs as adaptive feedback.
