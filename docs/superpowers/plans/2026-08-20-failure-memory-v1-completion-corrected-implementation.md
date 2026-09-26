# Failure Memory V1 Completion — Corrected Implementation Plan

## Module 0 — Scope and protocol freeze

Freeze corrected scope, consumer access, round maintenance and scientific-program
contracts. Commit with one purpose.

## Module 1 — Consumer exports

TDD `consumer_views.py`:

- fixed test-helper file loading;
- strict Policy projection;
- Policy abstention does not suppress Analyzer candidates;
- Analyzer top-k without Policy threshold;
- Researcher full-record access only with train-side authority;
- held-out aggregate-only.

## Module 2 — Mechanical round maintenance

TDD `round_maintenance.py`:

- immutable active snapshot;
- append-only shadow ledger;
- no same-round readback;
- Benefit/Harm/Neutral/Uncertain/infra dispositions;
- retrieval-dev shadow-only;
- evaluation writeback forbidden;
- next-round content-addressed snapshot plan.

## Module 3 — External component ports

TDD `component_ports.py`:

- Analyzer proposal ingress;
- same-state verifier ingress;
- Researcher evidence export;
- optional verified training-evidence port;
- no external component implementation or execution.

## Module 4 — Scientific program and truthful Q1–Q5 matrix

TDD `scientific_program.py`:

- Stage 0/1A/1B/2/3 cell identities and freeze rules;
- bind existing A0/B authorities;
- Q4/Q5 remain open/deferred absent real external authorities;
- optional Stage1B/C/OFF-OFF authorities upgrade only their registered questions.

## Fixed-head validation

Run focused tests, all Memory tests, full repository tests, compileall, native clean
build, static scope/leakage audit, current active-snapshot role-view smoke, current
Q1–Q5 matrix and Git bundle verification. No push.
