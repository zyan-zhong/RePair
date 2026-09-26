"""Governed strong-model runtime and Training Researcher data chain."""

from .identity import (
    build_scientific_unit_identity,
    build_logical_call_record,
    build_transport_attempt_record,
)
from .manifest import load_runtime_manifest, stage_spec
from .request_renderer import render_stage_request
from .round_evidence import freeze_round_evidence_package
