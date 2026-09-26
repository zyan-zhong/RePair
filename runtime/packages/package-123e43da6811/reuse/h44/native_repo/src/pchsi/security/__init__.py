"""Security contracts for the non-executing S1 backend-probe candidate."""

from .execution_gate import (
    ExecutionNotApprovedError,
    require_execution_approval,
)

__all__ = [
    "ExecutionNotApprovedError",
    "require_execution_approval",
]
