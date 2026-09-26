# REFERENCE_LOOP_WORKFLOW_COORDINATION_V1

## 1. Current state

```text
Failure Memory final seal                 complete
Reference-loop evidence protocols         complete
π1 exact identity                         complete
12 full trajectory rebindings             complete
12 Analyzer Evidence Packs                complete
Mechanical evidence panel                 complete
Formal Analyzer execution                 not authorized
```

The next stage is Analyzer V2 design implementation, gold annotation and
A0–A3 pilot. Evidence plumbing is frozen unless a concrete blocker is found.

## 2. Component handoff graph

```text
Task Policy
→ five-file attempt bundle
→ Reference-loop validator/rebinding
→ Mechanical Evidence
→ Common Analyzer Evidence Pack
→ Analyzer Local Result
→ Group Manifest
→ Analyzer Group Result
→ Projected Repair Candidate
→ Human Researcher portfolio
→ Repair Registration
→ Existing F0/F1 runner
→ Verifier outcome
→ Verified Training Evidence
→ Existing trainer
→ π2 candidate
→ Memory OFF + Harness OFF evaluator
→ programmatic promotion/rollback
→ round evidence / Research Memory
```

## 3. Identity flow

Every downstream artifact retains:

```text
policy identity
task/gamefile
source attempt bundle
source state/prefix
Analyzer condition/run
Memory snapshot/packet
candidate repair
F0/F1 pair
training sample
result manifest
```

No component reconstructs identity from directory names or prose.

## 4. Authority flow

| Component | May create | Cannot create |
|---|---|---|
| Evidence layer | exact facts and lineage | mechanism or utility |
| Mechanical extractor | deterministic derived facts | causal explanation |
| Analyzer | hypotheses and repair proposals | Benefit/Harm or training labels |
| Memory | governed historical packets | reasoning or promotion |
| Human Researcher | priorities and experiment plan | effect labels or promotion authority |
| Verifier | F0/F1 effect authority | research preference |
| Training builder | eligible chosen/rejected examples | unverified labels |
| Trainer | candidate checkpoint | promotion |
| Promotion gate | GO/NO-GO from frozen evidence | new hypotheses |

## 5. Workstreams

### A — Evidence and Verifier

Immediate:

- evidence-foundation final seal;
- repair registration contract implementation;
- one exact-state F0/F1 smoke;
- pair-equality audit;
- candidate/result ledgers.

Parallel paper work:

- evidence schema appendix;
- verification method;
- candidate funnel scripts.

### B — Analyzer and Researcher

Immediate:

- implement Analyzer V2 typed schemas/parser;
- gold-panel annotation tooling/guideline;
- A0/A1 prompts;
- grouped synthesis;
- A3 Memory packet renderer;
- Human Researcher V2 records.

Parallel paper work:

- Analyzer method;
- research-prioritization method;
- related work;
- qualitative case template.

### C — Training and Evaluation

Immediate without real training:

- verified-data dummy dry-run;
- T0–T5 config reuse audit;
- π1/π2 identity slots;
- OFF/OFF evaluator smoke;
- statistical analysis scripts.

Parallel paper work:

- learning method;
- experimental protocol;
- empty result tables.

### D — Paper and Artifacts

Immediate:

- Figure 1 update;
- Introduction/claim wording;
- artifact index;
- cost ledger;
- AI-use ledger;
- anonymized release checklist.

## 6. Parallelism

### During Analyzer implementation

Run in parallel:

```text
gold annotation
F0/F1 synthetic tests
candidate dedup tooling
Researcher template tooling
verified-data dummy dry-run
paper Method draft
```

### During Analyzer API execution

Run in parallel:

```text
mechanical metric aggregation
candidate projector validation
verifier queue construction
cost ledger
local Analyzer dataset builder
plotting scripts
```

### During F0/F1 execution

Run in parallel:

```text
training config audit
verified-data builder
candidate funnel
case-study preparation
OFF/OFF evaluator smoke
```

### During π2 training

Run in parallel:

```text
local Analyzer shadow
API Researcher shadow
task-family plots
regression analysis
Limitations and Appendix
```

## 7. Hard dependencies

```text
Evidence foundation sealed
→ Analyzer implementation

gold guideline + output schema frozen
→ gold annotation completion

pilot complete + prompt frozen
→ formal A0–A3 run

formal candidate manifest frozen
→ F0/F1

F0/F1 result manifest sealed
→ policy training

π2 checkpoint sealed
→ OFF/OFF benchmark

π1→π2 independently audited GO
→ autonomous Planner control
```

## 8. Server/HPC operating constraints

- large outputs live under `/data/run01`;
- do not use `/data/home/.../run` aliases as authority paths;
- do not manually override Slurm CPU or memory allocations;
- use stage-appropriate walltime rather than a multi-day default;
- preserve outputs and worktrees on disconnect;
- all runners are resume-safe and fail closed on unexpected dirty paths;
- no-clobber outputs; previous attempts move to incident directories;
- Analyzer model/API calls require exact approval tokens;
- ambiguous post-send failures do not silently retry a scientific call;
- Git publication occurs only after tests and fixed-head review.

## 9. Module closure

Each completed submodule receives:

```text
focused tests
full relevant regression
artifact/evidence summary
single-purpose commit
remote push
local/remote equality
parent-module Markdown update
```

Major stages additionally receive:

```text
final seal artifact
tag
main merge
post-merge regression
```

## 10. Next implementation order

```text
1. seal current evidence foundation
2. implement Analyzer V2 schemas/parser/run manifests
3. build gold annotation tooling
4. run three schema fixtures
5. annotate gold panel
6. run A0/A1 localization evaluation
7. implement grouped A2/A3
8. run 12-state pilot
9. freeze formal prompt
10. run 30-state repair discovery
11. Human Researcher prioritization
12. formal F0/F1
13. verified training evidence
14. T0–T5 training/evaluation
15. π2 OFF/OFF GO/NO-GO
```

## 11. Claim coordination

```text
C1
← A0–A3 verified-repair yield and cost

C2
← F0/F1 candidate funnel and false-promotion analysis

C3
← T0–T5 training comparison

C4
← π2 OFF/OFF versus π1 OFF/OFF
```

Localization accuracy is supporting evidence, not the primary C1 endpoint.
