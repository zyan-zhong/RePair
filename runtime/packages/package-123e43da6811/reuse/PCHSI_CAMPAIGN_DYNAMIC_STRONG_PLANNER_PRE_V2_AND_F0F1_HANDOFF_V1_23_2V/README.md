# PCHSI V1.23.2V — Dynamic Strong Planner PRE V2 + F0/F1 Handoff

Input: one successful V1232U output root.

Output on success:
- `V1232V_DYNAMIC_PRE_PAIR_UNIVERSE_VIEW_V1.json`
- `STRONG_RESEARCHER_PRE_PRIMARY_DYNAMIC_CONTRACT_V2.json`
- `RESEARCHER_MEMORY_VIEW_V1.json`
- `STRONG_RESEARCHER_BLIND_PRE_INPUT_V3.json`
- durable `strong_pre_runtime/<logical_call_id>/...`
- `V1232V_PLANNER_BOUND_F0F1_LAUNCH_HANDOFF_V1.json`
- `PCHSI_V1232V_TERMINAL_V1.json`

The package performs zero environment calls and zero training executions. It may perform one new Strong PRE provider logical call, or zero if the exact accepted terminal is safely reused.

Normal-path Human scientific decisions: zero.
