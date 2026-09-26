# Memory / Analyzer / Researcher Module Handbook V1

## Persistent Failure Experience / Memory

### Purpose
A governed historical substrate, not an effect oracle. It stores procedural
failure experience and exports bounded role-specific views.

### Input
- verified trajectory/evidence identities;
- multi-step procedural experience: relevant start, preceding actions/feedback,
  state change, wrong branch, consequence, repair, applicability/counterexample;
- later F0/F1 labels and policy version;
- Researcher round decisions and GO/NO-GO lessons.

### Output
- `POLICY_MEMORY_PACK_V1`: optional policy-facing bounded context, primarily an
  ablation/runtime mechanism;
- `ANALYZER_MEMORY_PACK_V1`: historical mechanisms, counterexamples,
  applicability and candidate support;
- `RESEARCHER_MEMORY_PACK_V1`: round-level prior hypotheses, decisions,
  experiments, results and avoid-repeat lessons.

### Critical fields
record/snapshot/pack IDs and SHA; role; source policy version; task family;
mechanism; procedural sequence; repair; applicability; counterexample;
Benefit/Harm/Neutral/Uncertain; access class; provenance; retrieval reason.

### Key parameters
pack size; retrieval K; role exposure; snapshot ID; policy-version compatibility;
access class. Existing Memory schema/thresholds remain frozen by this package.

### Metrics
retrieval coverage/precision; harmful retrieval; applicability errors; Analyzer
EVRY increment A3−A2; Researcher repeated-NO-GO avoidance; cost. Direct policy
Memory success remains an ablation, not the main claim.

## Hierarchical Analyzer V2

### Purpose
Explain what happened and why; represent multiple errors/success-quality events;
propose grounded repairs; abstain when evidence is insufficient.

### Input
- complete post-episode Evidence Pack;
- deterministic mechanical facts;
- L: episode evidence, Memory OFF;
- G-A2: A1 bytes + group/source bindings, Memory OFF;
- G-A3: exact A2 inputs + one frozen Analyzer Memory pack;
- C: validated group result;
- X: target artifact + current evidence.

### Output
L local results; error instances; critical windows; hypotheses; evidence and
counterevidence; success-quality events; G group mechanisms and source-conditioned
proposals; C component attribution; P deterministic policy profile; X immutable
sidecar; projected candidate or ABSTAIN.

### Critical fields
condition/stage; evidence SHA; task/gamefile/group IDs; error/hypothesis/repair
IDs; call indices; lifecycle; terminal footprint; evidence refs; uncertainty;
source-state/menu SHA; Memory SHA; raw/validated response SHA; model/config/cost.

### Parameters
A0 one hypothesis vs A1 up to three; K=1 candidate or ABSTAIN; short option 1–4
actions; exact stage token budgets; A1 byte reuse; A3-only Memory; X independent
request; no hidden retry; common U_reg.

### Metrics
localization exact/±1; window IoU; lifecycle agreement; evidence precision;
unsupported facts; counterevidence; abstention/uncertainty calibration;
candidate executability; EVRY_reg/avail; Harm; ProposalCoverage; VBP; verifier
steps/tokens/cost per repaired unit; paired A1−A0/A2−A1/A3−A2 statistics.

### Authority
No Benefit/Harm, training label, F0/F1 execution, or promotion authority.

## Human Training Researcher / Research Planner

### Purpose
Choose the current round's principal bottleneck and single falsifiable change;
allocate research budget; interpret measured results; preserve rejected/deferred
alternatives. The first π1→π2 round is human-primary.

### Input
Frozen `ROUND_EVIDENCE_PACKAGE_V1`: policy lineage; rollout/mechanical census;
formal Analyzer A0–A3 artifacts/metrics; Failure Experience; historical F0/F1,
GO/NO-GO and training evidence; resources and code/config differences.

### Output
Human PRE and POST; API PRE/POST shadow; field-level adjudication; researcher
training/promotion recommendations; later local Researcher supervision; after GO
and quality gates, outer Planner proposals for πk→πk+1.

### Critical PRE fields
facts/uncertainties; all candidate bottlenecks; selected/rejected/deferred;
evidence/counterevidence; expected value/cost/risk with units; hypothesis; one
principal change; baseline/intervention/fixed variables; sample/budgets; primary
endpoint/diagnostics; support/refutation/stop.

### Critical POST fields
PRE SHA; protocol audit; numerator/denominator; unexpected evidence; hypothesis
status; alternatives; training recommendation; promotion recommendation; lesson;
next-round implication.

### Parameters
candidate pool; verification/model/environment/GPU/API budgets; single-change
constraint; evidence cutoff; stop rule; round split; shadow visibility; field-level
adjudication; local shadow quality gates.

### Metrics
Benefits per verification budget; Harm/Neutral; family coverage; duplicate
mechanisms; cost per Benefit; human revision rate; single-change compliance;
repeated-NO-GO rate; evidence validity; budget compliance; downstream GO rate;
uncertainty/abstention calibration.

### Authority
Primary current-round planning role only. Environment Verifier owns effect labels;
Training Harness executes; Promotion Gate owns promote/rollback.
