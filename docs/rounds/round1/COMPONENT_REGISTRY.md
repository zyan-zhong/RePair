# Round-1 Component Registry

## Purpose

This registry maps the major scientific and engineering components used
during the first single-round policy-improvement validation.

Its purpose is to answer, for each component:

- what it does;
- what evidence it consumes;
- what artifact it produces;
- what authority it has;
- where its implementation or evidence can currently be found;
- what downstream component consumes it;
- whether it is complete, rejected, incomplete or on hold.

This registry is navigational.

It does not replace raw evidence, deterministic audits, cryptographic
seals or the project Experiment Ledger.

## How to Read This Registry

The first column gives the human-readable component name.

`Historical/internal ID` preserves the engineering or experimental name
when one exists.

`Type` describes the component role.

`Authority` is intentionally separate from implementation status.

A component can be complete while having no authority to make a
scientific decision outside its registered role.

This Component Registry owns component roles, authority boundaries,
inputs, outputs and downstream relationships.

The exact major historical path, population, cryptographic identity and
retention binding is maintained separately in the
[Round-1 Asset Registry](./ASSET_REGISTRY.md).

Component-level rows do not duplicate every low-level historical file
when the Asset Registry already supplies the authoritative major-asset
entry point.

## Authority Boundaries

The registry uses the following authority descriptions.

| Authority | Meaning |
|---|---|
| `protocol / access authority` | Defines or enforces frozen protocol or data-access conditions |
| `byte / identity authority` | Establishes exact file, request, package or artifact identity |
| `deterministic mechanical-fact authority` | Computes reproducible non-semantic facts from frozen evidence |
| `environment-execution validity authority` | Establishes whether a registered candidate is valid under actual environment execution/evidence |
| `semantic hypothesis only` | Produces interpretations that require independent evidence before becoming causal or environment truth |
| `training-data transformation only` | Constructs training examples but does not determine whether the trained policy improved |
| `model-training execution only` | Updates model parameters but does not judge scientific success |
| `evaluation aggregation only` | Aggregates registered evaluation evidence |
| `no independent scientific authority` | Performs support work without independently establishing a scientific claim |

Two boundaries are especially important:

```text
strong-model semantic proposal
≠
environment validity
```

and:

```text
training completion
≠
policy improvement
```

## Component Types

Only the following component types are used:

```text
GOVERNANCE
BUILDER
RUNNER
COLLECTOR
PUBLISHER
MECHANICAL_ANALYZER
SEMANTIC_ANALYZER
VERIFIER
TRAINER
EVALUATOR
AGGREGATOR
REGISTRY
```

When a historical component genuinely served more than one inseparable
role, types are joined using `+`.

## Round-1 Component Flow

```text
Governance / Runtime
        ↓
pi0 Evidence Production
        ↓
Strong-Model Proposal Pipeline
        ↓
Q2 Environment Validation
        ↓
Training Data
        ↓
pi1 Training
        ↓
Harness-OFF Evaluation
        ↓
NO-GO
        ↓
Mechanical Post-hoc Analysis
        ↓
Hierarchical Semantic Analysis
        ↓
Canonical Evidence / Provenance Closure
        ↓
Future Failure Memory Handoff
```

## A. Governance and Runtime Foundation

| Component | Historical/internal ID | Type | Scientific role | Consumes | Produces | Authority | Repository entry | Server evidence | Status | Downstream consumer |
|---|---|---|---|---|---|---|---|---|---|---|
| Task-access and condition governance | P1 governance / condition manifests | `GOVERNANCE + REGISTRY` | Freeze task use, condition identity and access boundaries | task manifests, protocol state | access/condition records | `protocol / access authority` | Server-side historical assets; repository binding pending Module 3 | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | pi0 evidence production |
| Strict raw-policy parser | RAW_POLICY_PARSER_V1 | `VERIFIER` | Enforce the literal action-envelope contract without repairing actions | raw model response | parse result / literal action | `deterministic mechanical-fact authority` | `src/pchsi/evaluation/raw_policy_parser.py` | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | Runtime Core |
| Prompt and M0 history builder | RAW_POLICY_PROMPT_V1 / MEMORY_M0_V1 | `BUILDER` | Build deterministic policy input and recent executed-transition history | task goal, observation, executed history, menu | policy prompt and M0 identity | `no independent scientific authority` | `src/pchsi/evaluation/raw_policy_prompt.py` | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | task-policy calls |
| Immutable dual-budget accounting | 60/30/3 budget | `GOVERNANCE` | Enforce policy-attempt, environment-step and consecutive-nonexecuted limits | current budget state, execution result | next immutable budget state | `protocol / access authority` | `src/pchsi/evaluation/budget.py` | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | Runtime Core / evaluator |
| Runtime Core | E1 Runtime Core V1 | `GOVERNANCE + VERIFIER` | Validate menu/preconditions, parse responses, check exact membership and reserve/finalize environment steps | prompt result, menu identities, model response, budget | execution decision and budget lineage | `protocol / access authority` | `src/pchsi/evaluation/runtime_core.py` | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | ALFWorld evaluator |
| ALFWorld environment adapter / evaluator boundary | E1 ALFWorld evaluator | `EVALUATOR + RUNNER` | Connect the approved runtime contract to ALFWorld execution | registered task, Runtime Core decision | observations, environment results, episode evidence | `environment-execution validity authority` | `src/pchsi/evaluation/alfworld_adapter.py` and related evaluation package | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | pi0/pi1 episode evidence |
| ActionTrace evidence collector | ActionTrace | `COLLECTOR` | Record model-call, parser, budget, action and environment provenance | policy/runtime/environment events | immutable trace evidence | `byte / identity authority` | `src/pchsi/evaluation/action_trace.py` | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | episode evidence / audits |
| Artifact publisher | E1 artifact publication | `PUBLISHER` | Publish registered evidence bundles without turning publication into scientific judgment | completed attempt/episode artifacts | published evidence bundles | `no independent scientific authority` | `src/pchsi/evaluation/artifact_publisher.py` | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | downstream audits |

## B. pi0 Evidence Production

| Component | Historical/internal ID | Type | Scientific role | Consumes | Produces | Authority | Repository entry | Server evidence | Status | Downstream consumer |
|---|---|---|---|---|---|---|---|---|---|---|
| Development schedule builder | P1 schedule | `BUILDER + GOVERNANCE` | Materialize registered pi0 development cells under frozen task/condition access | access records, task identities, seed/condition identity | development schedule | `protocol / access authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | pi0 episode runner |
| pi0 episode runner | P1-R0 / pi0 development execution | `RUNNER` | Execute the initial task policy on registered development cells | schedule, model/runtime/environment | complete pi0 episodes | `no independent scientific authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | strong-proposer source builder / analysis |
| Policy-call evidence builder | PolicyCallEvidenceV1 | `COLLECTOR + BUILDER` | Preserve model request/response and call-level provenance | policy requests and responses | policy-call evidence | `byte / identity authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | evidence validator / strong proposer |
| Episode evidence validator | P1 complete-trajectory evidence audit | `VERIFIER` | Check cross-file episode, call, transition and condition consistency | episode evidence bundle | validation disposition | `byte / identity authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | P2 source selection |
| Attempt-bundle publisher | P1 episode publication | `PUBLISHER` | Publish complete evidence bundles after registered checks | completed attempt bundle | immutable published bundle | `no independent scientific authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | P2 / historical audit |

## C. Strong-Model Proposal Pipeline

| Component | Historical/internal ID | Type | Scientific role | Consumes | Produces | Authority | Repository entry | Server evidence | Status | Downstream consumer |
|---|---|---|---|---|---|---|---|---|---|---|
| Strong-proposer source-package builder | P2 source package | `BUILDER` | Freeze authorized pi0 cases and evidence references for offline semantic proposal | validated pi0 development evidence | source cases / source package | `byte / identity authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | request builder |
| Provider request builder and request freeze | P2 PRIMARY117 request freeze | `BUILDER + REGISTRY` | Build and freeze exactly one provider request per registered source case | source package, provider-neutral schema | canonical provider requests and hashes | `byte / identity authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | OpenAI provider adapter |
| OpenAI provider adapter | R1.3.2 / R132 | `RUNNER` | Submit frozen one-case requests under the provider execution contract | frozen request | raw provider response / transport evidence | `no independent scientific authority` | [Major asset binding](./ASSET_REGISTRY.md) | `/data/run01/scwb204/pchsi/p2/p2_strong_offline_proposer_openai_v1_run_r1_3_2` | `COMPLETE` | schema and semantic validators |
| Scientific schema validator | strong-model scientific schema | `VERIFIER` | Check structural conformance to the frozen scientific output contract | provider semantic output | schema disposition | `deterministic mechanical-fact authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | semantic validator |
| Deterministic semantic validator | P2 semantic gate | `VERIFIER` | Enforce frozen non-LLM semantic constraints and evidence-reference validity | schema-valid teacher proposal | accept/reject disposition | `deterministic mechanical-fact authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | Q2 / training-data path |
| R132 PRIMARY117 ledger | R132 PRIMARY117 | `REGISTRY + COLLECTOR` | Preserve one-case execution identity, call evidence and terminal-ledger structure | 117 frozen source cases and requests | 117 case ledgers | `byte / identity authority` | [Current canonical audit](../../audits/ROUND1_CANONICAL_GAP_AUDIT.md) | `/data/run01/scwb204/pchsi/p2/p2_strong_offline_proposer_openai_v1_run_r1_3_2` | `COMPLETE` | Q2 and provenance audits |

R132 population currently registered at the identity-chain boundary:

```text
117 source cases
117 frozen requests
91 teacher outputs
26 rejections
351 Q2 state bindings
```

These counts do not imply that all R132 terminal semantic provenance is
already closed.

## D. Q2 Environment Validation

| Component | Historical/internal ID | Type | Scientific role | Consumes | Produces | Authority | Repository entry | Server evidence | Status | Downstream consumer |
|---|---|---|---|---|---|---|---|---|---|---|
| Q2 state-binding builder | Q2 state bindings | `BUILDER + REGISTRY` | Bind candidate critical calls/corrections to reconstructable source-state evidence | source calls, teacher references | state-binding records | `byte / identity authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | state/binding validator |
| State/binding identity validator | Q2 identity gate | `VERIFIER` | Check source-call, case, state and binding identity | Q2 binding records | deterministic binding disposition | `byte / identity authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | environment validator |
| Environment-execution validator | Q2 environment authority | `VERIFIER + RUNNER` | Determine whether a registered candidate is executable/valid under environment evidence | reconstructed state and candidate correction | environment-valid / rejected result | `environment-execution validity authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | accepted-example registry |
| Accepted/rejected correction registry | Q2/Q3 accepted signal registry | `REGISTRY` | Preserve accepted and rejected candidate dispositions without converting teacher opinion into truth | validator results | accepted/rejected correction records | `byte / identity authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | training-data construction |

## E. Training and Checkpoint Production

| Component | Historical/internal ID | Type | Scientific role | Consumes | Produces | Authority | Repository entry | Server evidence | Status | Downstream consumer |
|---|---|---|---|---|---|---|---|---|---|---|
| Accepted-example builder | P4 accepted-example construction | `BUILDER` | Convert accepted correction evidence into training examples | accepted correction records | candidate training examples | `training-data transformation only` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | training-dataset builder |
| Training-dataset builder | Round-1 SFT dataset | `BUILDER` | Materialize the frozen training dataset under the registered data-selection rule | accepted examples / registered training sources | training dataset | `training-data transformation only` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | pi1 trainer |
| Training-sample ledger | Round-1 sample ledger | `REGISTRY` | Preserve which exact examples entered training and their provenance | training dataset | sample identity ledger | `byte / identity authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | training/provenance analysis |
| pi1 trainer | Round-1 SFT | `TRAINER` | Update task-policy parameters from the frozen first-round training dataset | base policy, training dataset, training configuration | pi1 checkpoint(s) | `model-training execution only` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | Harness-OFF evaluation |
| pi1 checkpoint registry | Round-1 checkpoint registry | `REGISTRY` | Bind trained policy/checkpoint identities to evaluation conditions | training outputs | checkpoint identity records | `byte / identity authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | Harness-OFF runner / matched analysis |

The trainer is not the judge of whether pi1 improved.

That judgment belongs to the registered evaluation evidence.

## F. Harness-OFF Evaluation

| Component | Historical/internal ID | Type | Scientific role | Consumes | Produces | Authority | Repository entry | Server evidence | Status | Downstream consumer |
|---|---|---|---|---|---|---|---|---|---|---|
| Evaluation schedule builder | P4 Harness-OFF schedule | `BUILDER + GOVERNANCE` | Freeze task/checkpoint/seed evaluation cells | policy identities, task identities, evaluation contract | evaluation schedule | `protocol / access authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | episode runner |
| pi0/pi1 episode runner | P4 Harness-OFF execution | `RUNNER + EVALUATOR` | Execute registered policy conditions without treating the training teacher as online authority | evaluation schedule, task policy, environment | Harness-OFF episodes | `environment-execution validity authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | task-level result builder |
| Task-level result builder | P4 task-level results | `BUILDER + AGGREGATOR` | Convert episode outcomes into task/checkpoint-level registered results | episode evidence | task-level result table | `evaluation aggregation only` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | final aggregator |
| Final result aggregator | P4 final analysis | `AGGREGATOR` | Aggregate registered task-level evidence into the Round-1 evaluation result | task-level results | final evaluation analysis | `evaluation aggregation only` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE_NO_GO` | scientific disposition / post-hoc analysis |
| Final result seal and audit | P4 final seal | `VERIFIER + REGISTRY` | Bind final analysis to frozen evidence identities | final analysis and canonical artifacts | seal / audit disposition | `byte / identity authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | Round-1 evidence package |

Overall Round-1 Harness-OFF disposition:

```text
COMPLETE_NO_GO
```

## G. Mechanical Post-hoc Analysis

| Component | Historical/internal ID | Type | Scientific role | Consumes | Produces | Authority | Repository entry | Server evidence | Status | Downstream consumer |
|---|---|---|---|---|---|---|---|---|---|---|
| Termination/profile builder | Round-1 mechanical profile | `MECHANICAL_ANALYZER + BUILDER` | Derive termination and trajectory-profile facts | frozen Harness-OFF evidence | termination/profile tables | `deterministic mechanical-fact authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | hierarchical analysis |
| Action and state-revisit analyzer | Round-1 revisit analysis | `MECHANICAL_ANALYZER` | Compute action/state repetition and revisit facts | action traces / episodes | repeat/revisit records | `deterministic mechanical-fact authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | matched/group analysis |
| Loop-fingerprint analyzer | Round-1 loop analysis | `MECHANICAL_ANALYZER` | Identify deterministic recurring-action/state patterns | frozen trajectories | loop fingerprints | `deterministic mechanical-fact authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | semantic mechanism analysis |
| Cross-checkpoint or cross-seed matrix builder | Round-1 comparison matrix | `MECHANICAL_ANALYZER + BUILDER` | Compare recurring mechanical failure signatures across registered policy conditions | task/checkpoint evidence | comparison matrix | `deterministic mechanical-fact authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | hierarchical analysis |
| Mechanical result aggregator | Round-1 mechanical aggregation | `AGGREGATOR` | Aggregate deterministic facts without inventing semantic mechanisms | mechanical outputs | mechanical evidence package | `deterministic mechanical-fact authority` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | Level-1/2 evidence builders |

## H. Hierarchical Semantic Analysis

The detailed internal assets, denominators, request populations,
builders, validators and verifiers are maintained in the
[Hierarchical Analysis Ledger](./HIERARCHICAL_ANALYSIS.md).

| Component | Historical/internal ID | Type | Scientific role | Consumes | Produces | Authority | Repository entry | Server evidence | Status | Downstream consumer |
|---|---|---|---|---|---|---|---|---|---|---|
| Level 1 — Matched-Group Analysis | Hierarchical Level 1 | `SEMANTIC_ANALYZER + AGGREGATOR` | Compare matched policy/trajectory evidence and form local semantic claims | matched evidence groups | matched-group claims | `semantic hypothesis only` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | Level 2 |
| Level 2 — Capability-Scoped Mechanism Discovery | Hierarchical Level 2 | `SEMANTIC_ANALYZER + AGGREGATOR` | Consolidate local claims into capability-scoped candidate mechanisms | Level-1 claims and deterministic census | canonical candidate mechanisms | `semantic hypothesis only` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | Level 3 |
| Level 3 — Task-Family Projection | Hierarchical Level 3 | `SEMANTIC_ANALYZER + AGGREGATOR` | Project frozen mechanisms across registered ALFWorld task families | Level-2 mechanisms and family census | family-level projections | `semantic hypothesis only` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | Level 4 |
| Level 4 — Cross-Capability Interaction / Coverage Synthesis | Hierarchical Level 4 | `SEMANTIC_ANALYZER + AGGREGATOR` | Examine candidate interaction, ordering and coverage relationships across capability components | prior-level mechanisms/projections | cross-capability candidate relations | `semantic hypothesis only` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `COMPLETE` | Level 5 |
| Level 5 — Global Mechanism Synthesis | Hierarchical Level 5 | `SEMANTIC_ANALYZER + AGGREGATOR` | Attempt a globally compressed explanation of the Round-1 failure evidence | Levels 1-4 evidence | global synthesis candidate | `semantic hypothesis only` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `REJECTED` | retained as rejected evidence / challenge input |
| Level 6 — Independent Challenge | Hierarchical Level 6 | `SEMANTIC_ANALYZER` | Independently challenge high-level claims, counterexamples and alternative explanations | high-level semantic evidence | challenge output | `semantic hypothesis only` | [Major asset binding](./ASSET_REGISTRY.md) | [Major asset binding](./ASSET_REGISTRY.md) | `INCOMPLETE` | no final completed downstream result |

## I. Canonical Evidence and Provenance Closure

The provenance-closure workstream is independent of the numbered
hierarchical-analysis taxonomy.

| Component | Historical/internal ID | Type | Scientific role | Consumes | Produces | Authority | Repository entry | Server evidence | Status | Downstream consumer |
|---|---|---|---|---|---|---|---|---|---|---|
| R132 file/log identity census | Round-1 canonical gap census | `REGISTRY + VERIFIER` | Recover and distinguish historical R132 file/log identities | historical files and logs | byte/file census | `byte / identity authority` | [Canonical gap audit](../../audits/ROUND1_CANONICAL_GAP_AUDIT.md) | `/data/run01/scwb204/pchsi/p2/logs/p2_r132_primary117/primary117.log` | `COMPLETE` | R132 identity auditor |
| R132 PRIMARY117 identity-chain auditor | R132_PRIMARY117_IDENTITY_AUDIT_V1 | `VERIFIER + REGISTRY` | Bind 117 source cases, 117 frozen requests, run directories and 351 Q2 bindings | R132 manifests, run ledgers, Q2 bindings | 117-row identity table and audit summary | `byte / identity authority` | [R132 identity evidence](../../audits/evidence/round1_canonical_gap/r132_primary117_identity_v1/) | `/data/run01/scwb204/pchsi/p2/p2_strong_offline_proposer_openai_v1_run_r1_3_2` | `COMPLETE` | terminal/Q2 provenance closure |
| R132 terminal semantic-provenance auditor | next canonical-gap submodule | `VERIFIER` | Bind actual terminal disposition semantics to historical case evidence | 117 terminal ledgers and related evidence | terminal provenance audit | `byte / identity authority` | Current audit ledger only | [Major asset binding](./ASSET_REGISTRY.md) | `INCOMPLETE` | final R132 closure |
| Q2 semantic binding closure | pending canonical-gap submodule | `VERIFIER` | Close semantic provenance from R132 proposal/terminal evidence into registered Q2 bindings | R132/Q2 evidence | semantic-binding closure | `byte / identity authority` | Current audit ledger only | [Major asset binding](./ASSET_REGISTRY.md) | `INCOMPLETE` | canonical evidence seal |
| Harness-OFF canonical artifact closure | pending canonical-gap submodule | `VERIFIER + REGISTRY` | Bind final Harness-OFF canonical artifacts to the Round-1 evidence chain | final evaluation artifacts | artifact closure record | `byte / identity authority` | Current audit ledger only | [Major asset binding](./ASSET_REGISTRY.md) | `INCOMPLETE` | final canonical-gap seal |
| Final canonical-gap seal | Round-1 canonical closure | `VERIFIER + REGISTRY` | Seal the completed byte/semantic/provenance closure without rewriting historical evidence | completed closure audits | final gap disposition | `byte / identity authority` | Current audit ledger only | [Major asset binding](./ASSET_REGISTRY.md) | `INCOMPLETE` | Failure Memory design review |

## J. Future Memory, Local Analyzer and Planner

The following components are future research targets.

Their presence in this registry is navigational only.

| Component | Historical/internal ID | Type | Scientific role | Consumes | Produces | Authority | Repository entry | Server evidence | Status | Downstream consumer |
|---|---|---|---|---|---|---|---|---|---|---|
| Persistent Failure Memory builder | future Failure Memory | `BUILDER` | Convert closed evidence into traceable multi-step failure-experience records | future approved evidence inputs | Memory records | `no independent scientific authority` | Not implemented | Not generated | `HOLD` | Memory retrieval / future policy experiments |
| Memory retriever / injector | future Memory runtime | `BUILDER` | Retrieve applicable historical failure experience under a frozen retrieval contract | Memory library and current policy context | retrieved Memory context | `no independent scientific authority` | Not implemented | Not generated | `HOLD` | task policy |
| local hierarchical analyzer | future local Analyzer | `SEMANTIC_ANALYZER` | Replace routine external semantic diagnosis with a local analysis model | trajectory/group evidence | local semantic hypotheses | `semantic hypothesis only` | Not implemented | Not generated | `HOLD` | environment verifier / Research Planner |
| analyzer-supervision dataset builder | future analyzer distillation | `BUILDER` | Materialize approved external-reference analysis into local-analyzer supervision | approved analysis evidence | analyzer training dataset | `training-data transformation only` | Not implemented | Not generated | `HOLD` | local analyzer trainer |
| Research Planner | future cross-round Planner | `SEMANTIC_ANALYZER` | Propose the next research/training change from prior round evidence | round evidence packages and prior NO-GO/GO history | research proposal | `semantic hypothesis only` | Not implemented | Not generated | `HOLD` | future automated research loop |
| promotion / rollback gate | future policy promotion gate | `VERIFIER + AGGREGATOR` | Apply frozen performance, regression, protocol and uncertainty criteria to candidate policy versions | independent evaluation evidence | promote / retain / rollback disposition | `evaluation aggregation only` | Not implemented | Not generated | `HOLD` | next policy round |

## Registry Limitations

This registry is the canonical component-role and authority map.

Exact major historical asset paths, populations, cryptographic
identities and retention rules are maintained separately in the
[Round-1 Asset Registry](./ASSET_REGISTRY.md).

The separation is intentional:

```text
Component Registry
=
component role
+ authority
+ input/output relation
+ status

Asset Registry
=
major historical asset path
+ identity
+ population
+ retention
```

The detailed Level 1-6 populations, denominators, request populations,
semantic validation and conclusion boundaries remain registered in the
[Hierarchical Analysis Ledger](./HIERARCHICAL_ANALYSIS.md).

Unresolved historical provenance is not guessed or repaired here.
Project-level remaining provenance work continues to be tracked by the
[Round-1 Canonical Gap Audit](../../audits/ROUND1_CANONICAL_GAP_AUDIT.md).

## Documentation Sync State

For the final Round-1 historical research-asset consolidation:

| Documentation asset | State |
|---|---|
| Parent major-module ledger | `UPDATED` |
| Round-1 README | `UPDATED` |
| Component Registry | `UPDATED` |
| Asset Registry | `UPDATED` |
| Hierarchical Analysis Ledger | `CHECKED_NO_CHANGE_REQUIRED` |
| Experiment Ledger | `UPDATED` |
| Code Map | `UPDATED` |
| Root README | `UPDATED` |
| Module Closure Policy | `UPDATED` |

This synchronization changes navigation and project-level status
documentation only. It does not strengthen any historical scientific
result or semantic hypothesis.
