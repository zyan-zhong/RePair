"""The existing PRE call supplies executable semantics for future rounds."""
from contextlib import contextmanager
from unittest.mock import patch
from copy import deepcopy
from typed_options import annex_schema,validate_annex

PROMPT='''
Also return execution_contracts for EVERY selected EXECUTABLE_SHORT_OPTION, and none for exact actions.
This is the executable representation of the SAME complete selected candidate, not a new experiment or a shortened repair.
Copy source_candidate_sha256, source_state_sha256 and termination_condition exactly. Preserve all ordered option_actions.
Every contract has mandatory environment-done, next-action-not-in-live-menu and action-exhaustion stops, per-step native budget accounting, and return to frozen policy.
stop_predicates are OR-ed. MENU_COMMAND_PREFIX takes one exact command prefix ending with a space (e.g. a take command naming the target type).
OBSERVATION_ALL_SUBSTRINGS takes one or more literal substrings, ALL required in the current public observation; task-instruction lines are excluded. Do not use generic words that also match negative feedback.
PUBLIC_TARGET_VISIBLE and PUBLIC_TARGET_CARRIED take one lowercase object type, using the existing public observation/menu detectors.
PUBLIC_GOAL_COMPLETION takes the exact public_task_goal and uses the public environment-done boundary; use only when the termination objective is exactly the full task goal.
Live admissible commands enforce native action preconditions. No hidden environment state, reward, verifier output, future result or arbitrary code is available to the contract.
Set semantic_coverage FULL only when every termination clause is represented faithfully; explain the mapping in coverage_explanation.
Use UNREPRESENTABLE if the declared predicates cannot represent the complete option; never silently weaken or rewrite the candidate, and never claim partial semantics as FULL.
This annex is generated in this same PRE response and executed deterministically; there is no human runtime parser.
'''

@contextmanager
def install(authority):
    import adapter
    from training_binding import strategy_source
    native_pre=adapter.run_pre
    def pre(binding,values,core,tail,universe,out):
        if binding['round_id'] in authority['frozen_pre_round_ids']:return native_pre(binding,values,core,tail,universe,out)
        native_schema,native_prompt,native_finalize=strategy_source.extend_pre_schema,strategy_source.extend_pre_prompt,core.x.finalize_dynamic_primary_pre_v2
        def schema(base):
            value=native_schema(base);value['properties']['execution_contracts']=annex_schema()
            value['required'].append('execution_contracts');return value
        def finalize(*,value,**kwargs):
            value=deepcopy(value);rows=value.pop('execution_contracts',None)
            accepted=native_finalize(value=value,**kwargs)
            if rows is not None:
                from pre_stage import selected_candidates
                selected=selected_candidates(accepted,{'pair_table':kwargs['pair_rows']})
                validate_annex(rows,selected)
            return accepted
        with patch.object(strategy_source,'extend_pre_schema',schema),patch.object(strategy_source,'extend_pre_prompt',lambda text:native_prompt(text)+PROMPT),patch.object(core.x,'finalize_dynamic_primary_pre_v2',finalize):
            return native_pre(binding,values,core,tail,universe,out)
    with patch.object(adapter,'run_pre',pre):yield
