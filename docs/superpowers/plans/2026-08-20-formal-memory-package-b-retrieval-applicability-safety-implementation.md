# Formal Memory Package B — Retrieval & Applicability Safety Implementation Plan

Parent scientific authority: `577ee618a334dc08d73dd6fa31c7afa152b9afd5`

Branch: `science/memory-package-b-retrieval-v1`

## Scientific question

Package B answers Q3:

> Can the system retrieve the right historical Failure Experience at the right
> time, abstain when retrieval/applicability is uncertain, and avoid exposing
> wrong or non-applicable Memory?

Package B does not estimate causal Benefit/Harm of Memory. Applicability gold is a
diagnostic/safety authority only.

## Frozen three-stage protocol

The grouping unit is exact `TASK_GAMEFILE_GROUP`.

The three pools are mutually exclusive:

1. `RETRIEVER_CALIBRATION_DEV`
2. `RETRIEVER_SELECTION_VALIDATION`
3. `REGISTERED_SAFETY_STRESS`

`valid_seen` and `valid_unseen` are forbidden from retriever tuning/selection.

No query may appear in more than one pool by task/gamefile group identity.

## Independent gold authority

Every Formal-B query row must bind:
- a query ID;
- task/gamefile group ID used only for partition/isolation;
- policy-visible query state;
- independently registered correct Memory lineage, or independently registered
  abstention/no-applicable-Memory truth;
- independent gold authority artifact SHA.

The retriever, Memory record, applicability gate, Analyzer, or downstream policy
must not self-label the gold used to evaluate the same row.

## Query visibility

Retriever scoring may use only:
- current public observation;
- recent executed transitions;
- current interface feedback.

The scoring query must not include:
- source task/attempt identity;
- gamefile identity;
- seed;
- effect/promotion status;
- verified recovery procedure;
- oracle path or correct action;
- hidden state;
- Analyzer-generated post-hoc interpretation.

The public task goal is intentionally excluded from retrieval scoring so that
selection is driven by current failure/state evidence rather than task-name matching.

## Frozen ranking family

Formal B uses one transparent deterministic ranking function:

`CASEFOLD_WORD_JACCARD_V1`

Tokenization:
- Unicode text is casefolded;
- maximal alphanumeric/underscore word tokens are retained;
- token sets are compared with Jaccard similarity;
- no stemming, fuzzy matching, embedding model, LLM, or external retriever is used.

Each candidate Memory record must already pass the existing governance hard filter.

Score:
`|query_tokens ∩ record_tokens| / |query_tokens ∪ record_tokens|`.

A tie for top score is not resolved by record order: it produces abstention.

## Calibration and selection

The ranking function is frozen. Only the exposure threshold is calibrated.

Candidate threshold grid:

`0.00, 0.05, 0.10, ..., 0.50`.

Calibration DEV:
- evaluate all frozen thresholds;
- rank thresholds lexicographically by:
  1. lower wrong-Memory exposure rate;
  2. higher correct-Memory exposure rate;
  3. higher selective accuracy;
  4. higher coverage;
  5. higher threshold as the conservative deterministic tie-break;
- retain the best three threshold candidates.

Selection Validation:
- evaluate only those three calibration-selected candidates;
- use the same frozen lexicographic rule;
- freeze exactly one selected threshold/config.

Safety Stress:
- selected config only;
- no threshold/ranker changes;
- no calibration on stress outcomes.

## Applicability gate

Ranking never directly exposes Memory.

The top candidate must pass the existing mechanical direct applicability gate.

Only `APPLICABLE` permits exposure.

`NOT_APPLICABLE`, `CONFLICTING`, and `UNCERTAIN` all produce abstention.

The gate remains exact/case-sensitive and does not use semantic paraphrase,
Analyzer inference, or hidden state.

## Primary Q3 safety/utility measurements

Report at minimum:
- wrong Memory exposure rate;
- non-applicable Memory exposure rate;
- correct Memory exposure rate;
- abstention rate;
- coverage;
- selective accuracy among exposures;
- pre-gate top-1 retrieval hit rate;
- disposition counts for APPLICABLE / NOT_APPLICABLE / CONFLICTING / UNCERTAIN.

Selection is safety-first: wrong exposure is lexicographically primary.

## Null/adverse result handling

A0 outcome is frozen as Benefit=0, Harm=0, Neutral=9. It does not alter this B
protocol.

B null/adverse results do not authorize redesign of Package C.

Only registered amendment triggers remain:
`PROTOCOL_DEFECT`, `CONTAMINATION`, `CRITICAL_SAFETY_FAILURE`,
`INVALID_SCIENTIFIC_IDENTITY`.

## Implementation sequence after plan review

1. pure Formal-B query/gold/pool/config/result contracts;
2. deterministic lexical scorer + tie-abstention;
3. existing applicability gate integration;
4. calibration/selection/stress evaluator and metrics;
5. independent-gold panel materializer + contamination/isolation audit;
6. fixed-head review;
7. offline Formal-B scientific execution;
8. result audit/seal.

No model/GPU execution is required for the core B retrieval experiment.
