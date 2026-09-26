# Research Planner Asset Reuse Map V2

## Reuse first

| Need | Existing asset | Action |
|---|---|---|
| Human PRE/POST | `cognitive_runtime/researcher.py` + schemas | Direct reuse |
| Strong API shadow | API PRE/POST shadow schemas/runtime | Direct reuse |
| Local supervision | local researcher supervision schemas | Direct reuse |
| Reference-round identity | old `research_intelligence/reference_round.py` | Port and compatibility-test |
| Demonstration compilation | old `demonstrations.py` | Port |
| Distillation chain | old `distillation.py` | Port and update final target |
| Takeover gate | old `takeover.py` | Port and keep fail-closed |
| Research paradigm | old `paradigm.py` | Port; add repair-program responsibility |
| Generic loop hardening | design branch spec | Selectively encode role-neutral/identity/next-round constraints |
| Analyzer | Formal Analyzer V2 archive/runtime | No redesign |
| Failure Experience | Memory role packs/snapshots | No redesign |
| F0/F1 | Existing source-state replay/verifier | No reimplementation |
| Trainer/evaluator | Round-1 training and OFF/OFF assets | No reimplementation |

## New minimal additions

- `repair_portfolio.py`;
- `role_neutral.py`;
- `benchmark_registry.py`;
- reference-round readiness materializer;
- corrected research/localization/benchmark documents.

## Explicitly forbidden in this continuation

- new Analyzer hierarchy;
- new Memory schema or retriever;
- second F0/F1 engine;
- second training stack;
- second evaluator;
- live model/environment/training execution;
- silent migration of historical strong-model results into the primary benchmark.
