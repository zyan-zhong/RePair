"""Compatibility exports for the hardened Analyzer sampling scheduler."""

from .analysis_sampling import (
    AnalysisUnit,
    MechanicalPolicySignals,
    allocate_analysis_sampling,
    load_sampling_approval,
    select_analysis_regime,
)

allocate_analysis_budget = allocate_analysis_sampling
load_budget_policy = load_sampling_approval

__all__ = [
    "AnalysisUnit", "MechanicalPolicySignals", "allocate_analysis_sampling",
    "allocate_analysis_budget", "load_sampling_approval", "load_budget_policy",
    "select_analysis_regime",
]
