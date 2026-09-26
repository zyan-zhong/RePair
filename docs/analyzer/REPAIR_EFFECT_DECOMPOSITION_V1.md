# REPAIR_EFFECT_DECOMPOSITION_V1

## 1. Scientific question

A0–A3 determines whether a registered intervention has total downstream value.
It does not determine whether value came from one pivotal action, a multi-step
option, additional observations, route disruption, or history context.

This protocol decomposes 8–12 distinct verified Benefit candidates without
expanding the A0–A3 main condition table.

## 2. Eligibility

A candidate is eligible only if:

- it has a frozen formal Benefit outcome;
- it binds a unique task/gamefile and source state;
- its full action/option bytes and termination are frozen;
- the policy, prompt, budget, seed schedule, and state reconstruction are frozen;
- it has not been selected based on a desired mechanism story.

If more than 12 candidates are eligible, select mechanically by candidate-ID
hash order. Fewer than six candidates yields a case-study-only result.

## 3. Conditions

### D0 — Baseline continuation

Resume the same policy from the exact source state without intervention.

### D1 — Full registered repair

Execute the entire exact action or bounded option, then return control to the
same policy.

### D2 — Tested prefixes

For an option of length `k`, execute prefixes `1..j` for every `j ∈ [1,k]`,
returning control immediately after each prefix. Primitive actions have one D2
condition identical in action length to D1.

### D3 — Registered matched perturbation

Select a control mechanically from the same source menu using a frozen rule:

```text
same action count
same admissibility status
same total environment-step budget
matched novelty class
matched observation opportunities
matched option-termination budget
same high-level action class where possible
different registered target/mechanism
first qualifying option in original menu/order
```

The control cannot be human-selected after outcomes are visible.

### D4 — History attenuation

Execute the same full D1 intervention and preserve the real post-intervention
environment state, observation, and menu. Replace detailed intervention history
visible to the continuing policy with the fixed marker:

```text
[REGISTERED_INTERVENTION_EXECUTED]
```

This tests dependence on intervention-history detail, not a general natural
mediation effect.

## 4. Common controls

All conditions share:

```text
same reconstructed source state
same policy and adapter
same decoding configuration
same continuation seed
same total environment-step budget
same source menu and action validation
same termination and success definition
same infrastructure retry contract
```

Every intervention action counts against the common budget.

## 5. Mechanical repair-effect decomposition trace

```text
REPAIR_EFFECT_DECOMPOSITION_TRACE_V1
```

records:

```text
location change
inventory change
container state change
goal visibility change
take/open/move availability change
admissible-menu hash change
observation novelty
progress-event change
history tokens added
intervention action count
remaining budget
post-intervention success and terminal class
```

These are descriptive channels, not automatically identified causal mediators.

## 6. Mechanism labels

```text
SPECIFIC_SINGLE_ACTION_EFFECT
MINIMAL_PREFIX_EFFECT  # only when all shorter prefixes are definitively non-Benefit
COMPOSITIONAL_OPTION_EFFECT
HISTORY_CONTEXT_DEPENDENT
NONSPECIFIC_PERTURBATION_EFFECT
BUDGET_OR_EXTRA_OBSERVATION_CONFOUNDED
UNRESOLVED_MULTI_CHANNEL_EFFECT
```

Only the first two permit strong action-level language. A compositional option is
reported as a short controlled option, not as one critical action.

## 7. Metrics

```text
D1 total Benefit retention
shortest tested sufficient prefix length
D3 matched-control success/Benefit
D4 history-attenuated success/Benefit
intervention actions and observations
budget consumed
post-intervention policy calls
mechanical progress-event changes
```

Report all candidate-level outcomes, including decomposition failures and
infrastructure incidents.


## 8. Claim-language and training boundary

Paper-facing language is `specificity-confirmed repair yield` or
`specificity-confirmed subset of EVRY`; `CSVRY` may remain an internal artifact
identifier. D0–D4 does not identify full natural direct/indirect causal effects.

A D2 prefix may be called `minimal sufficient` only when every shorter prefix
was tested, every shorter prefix is definitively non-Benefit, and none is
Uncertain. Otherwise use `shortest tested sufficient prefix`.

D3 only supports specificity relative to the preregistered matched controls. A
formal D1 Benefit remains eligible for verified-training consideration even if
specificity is unresolved or fails; the decomposition governs mechanism claim
strength, not formal Benefit authority.
