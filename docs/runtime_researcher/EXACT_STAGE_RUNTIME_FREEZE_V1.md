# Exact Stage Runtime Freeze V1

Base deterministic head: `e64bc5efdcfd436bab807cd8519a3ffb7dd38746`.

The machine-readable authority is
`configs/cognitive_runtime/unified_cognitive_runtime_manifest_v1.json`.

| Stage | Role | Unit | Memory | Max output | Logical calls/unit | Output |
|---|---|---|---:|---:|---:|---|
| L-A0 | Analyzer | episode | OFF | 12,288 | 1 | `ANALYZER_LOCAL_RESULT_V2` |
| L-A1 | Analyzer | episode | OFF | 12,288 | 1 | `ANALYZER_LOCAL_RESULT_V2` |
| G-A2 | Analyzer | group | OFF | 16,384 | 1 | `ANALYZER_GROUP_RESULT_V1` |
| G-A3 | Analyzer | group | ON, higher-level only | 16,384 | 1 | `ANALYZER_GROUP_RESULT_V1` |
| C | Analyzer | group | condition-bound | 4,096 | 1 | `ANALYZER_COMPONENT_ATTRIBUTION_V1` |
| P | deterministic | policy profile | OFF | 0 | 0 | deterministic profile |
| X | Analyzer cross-check | target | condition-bound | 8,192 | 1 | `ANALYZER_CROSSCHECK_RESULT_V1` |
| Researcher PRE shadow | Researcher | round | Researcher pack | 16,384 | 1 | `API_RESEARCHER_PRE_SHADOW_V1` |
| Researcher POST shadow | Researcher | round | Researcher pack | 12,288 | 1 | `API_RESEARCHER_POST_SHADOW_V1` |

The historical P2 ceiling of 32,768 remains a global cap; stage budgets are
smaller. ACT1 must revalidate current provider acceptance. No silent model,
reasoning, truncation, schema, or budget fallback is allowed.

All L/G/C/X rows bind the exact existing Analyzer schema file SHA from base head `e64bc5e`; Researcher rows bind package-local schema SHA.
