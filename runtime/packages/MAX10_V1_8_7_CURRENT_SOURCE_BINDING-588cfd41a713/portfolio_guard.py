"""The whole frozen portfolio must be materialized, including on resume."""
from pathlib import Path
from functools import wraps
import json

def require_complete_portfolio(plan):
    expected=[x['branch_key_sha256'] for x in plan['handoff']['branch_plan']]
    bound=[x['binding']['branch_key_sha256'] for x in plan['branch_bindings']]
    if not expected or len(set(expected))!=len(expected) or len(set(bound))!=len(bound) or set(expected)!=set(bound):
        raise ValueError('FROZEN_SELECTED_PORTFOLIO_SEMANTICS_MATERIALIZATION_INCOMPLETE')

def guard_controller(original):
    @wraps(original)
    def run(root):
        require_complete_portfolio(json.loads((Path(root)/'EXECUTION_PLAN.json').read_bytes()))
        return original(root)
    return run
