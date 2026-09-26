"""Advice within the registered G/X/PRE/POST schemas and execution capabilities."""
OPTION_GUIDANCE='''
REGISTERED EXECUTABLE REPAIR CAPABILITIES:
Propose a coherent, evidence-supported dependency sequence, not a longer sequence
for its own sake. Check the public task goal, held/visible objects, already
completed phases and remaining prerequisites. Naming a goal object or reaching a
location is not evidence that the complete task becomes achievable afterward.
For short options, formulate termination using the existing runtime capabilities:
environment done; all ordered actions exhausted; next action absent from the LIVE
admissible menu; and native per-step budget accounting. Additional OR-ed public
stops may use only MENU_COMMAND_PREFIX (exact prefix ending with a space),
OBSERVATION_ALL_SUBSTRINGS (literal positive observation substrings, all required),
PUBLIC_TARGET_VISIBLE / PUBLIC_TARGET_CARRIED (one lowercase object type), or
PUBLIC_GOAL_COMPLETION (exact public task goal, environment-done boundary).
Predicates are checked BEFORE each action, including the first. Do not choose a
predicate already true at the source if further actions are required. Predicates
must not infer hidden state or match the task instruction as achieved progress.
Do not add an unexecutable termination clause such as 'observation contradicts
the plan', 'reconsider the strategy', or 'until sufficiently improved'. Express
uncertainty and possible contradictions in existing hypothesis/evidence fields.
If safety genuinely requires an unsupported stop, preserve that limitation and
do not label the option executable. Do not silently weaken a frozen candidate.
All interventions return to the same frozen policy; anticipate the remaining
dependency where that policy can repeat a completed phase or make an illegal
action. Exact one-step repair remains valid when it closes the supported gap.
No invented observations, forced A2/A3 disagreement, task-specific rules, extra
schema fields, or automatic extension beyond the registered option length.
'''
X_GUIDANCE='''
REGISTERED EXECUTABILITY AUDIT:
Audit the complete candidate against the public prerequisites and existing finite
stop predicates. A multi-step option is not invalid merely because later actions
are absent from the source menu: they are revalidated in their later live states.
Conversely, a goal-named action or a reachable location alone does not establish
task completion. Preserve unsupported dependencies as uncertainty. Distinguish
local subgoal progress from an untested terminal-success claim. Flag unsupported
termination semantics without rewriting or truncating the frozen candidate.
'''
PRE_GUIDANCE='''
REGISTERED DEPENDENCY AND CONTINUATION REVIEW:
For each reviewed candidate, use the existing rationale fields to distinguish:
publicly established prerequisites; already completed phases; the exact gap the
intervention closes; and the dependencies remaining when the frozen policy resumes.
Absence of evidence is UNKNOWN, not proof a prerequisite is satisfied or absent.
Do not prefer an action merely because it names the goal object or resembles a
terminal action. Prefer coherent supported repair coverage over speculative
longer plans or repeated navigation; do not impose a fixed number of states.
Use prior_closed_round_trajectory_facts alongside accepted prior POST lessons.
These are facts from CLOSED TRAIN rounds, not current-round causal labels or
guarantees of transfer. Repeated completed phases, invalid actions and unresolved
dependencies can falsify an explanation and inform a new testable hypothesis.
Preserve all candidate hashes/actions/termination text, FULL typed coverage,
existing review schema, and registered budgets. No human runtime adjudication.
'''
POST_GUIDANCE='''
REGISTERED PUBLIC TRAJECTORY FACTS:
Read registered_trajectory_facts together with the native verifier. Public views
and branch patterns use zero-based indices; run-length counts preserve order and
multiplicity. Distinguish intervention execution, observed local progress, later
policy continuation, and terminal outcome. Do not replace verifier effect labels.
Use actual remaining executed steps before attributing failure to insufficient
horizon; check repeated actions/observations and feedback before proposing causes.
An action absent from the live menu is observed inadmissibility, not proof of a
specific hidden prerequisite. Where public evidence establishes that an object
was visible, do not retain 'object not found there' as an equally supported cause.
Record supported mechanisms, contradictory facts and still-unknown prerequisites
in the EXISTING lesson, next_round_implication and alternative_explanations fields.
Local progress is not BENEFIT; only existing verified eligible supervision may
enter Dual-View training. Do not force TRAIN or reinterpret NEUTRAL as success.
'''
