from __future__ import annotations

import json
from pathlib import Path

from .common import load_object, sha256_file


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def paradigm_path() -> Path:
    return (
        _repo_root()
        / "configs/research_intelligence/research_planner_paradigm_v1.json"
    )


def load_research_planner_paradigm() -> dict[str, object]:
    value = load_object(paradigm_path())
    if value.get("schema_id") != "RESEARCH_PLANNER_PARADIGM_V1":
        raise ValueError("Research Planner paradigm identity mismatch")
    layers = value.get("human_reference_layers")
    if not isinstance(layers, list) or len(layers) != 6:
        raise ValueError("Research Planner paradigm must have six layers")
    if len({row["layer_id"] for row in layers}) != len(layers):
        raise ValueError("Research Planner layer IDs must be unique")
    return value


def render_human_pre_worksheet(
    *,
    round_evidence: dict[str, object],
    round_evidence_path: Path,
) -> str:
    paradigm = load_research_planner_paradigm()
    lines = [
        "# Human Research Planner PRE Worksheet",
        "",
        f"Round ID: `{round_evidence['round_id']}`",
        f"Round Evidence SHA: `{round_evidence['round_evidence_package_sha256']}`",
        f"Round Evidence File SHA: `{sha256_file(round_evidence_path)}`",
        "",
        "This worksheet is a bootstrap reference artifact. It is not a formal",
        "HUMAN_RESEARCHER_PRE_V1 record until a separately completed JSON draft",
        "passes the existing V10 finalizer and is written no-clobber.",
        "",
    ]
    for layer in paradigm["human_reference_layers"]:
        lines.append(f"## {layer['layer_id']}")
        lines.append("")
        for question in layer["questions"]:
            lines.append(f"- {question}")
        lines.extend(["", "Evidence / counterevidence notes:", "", "---", ""])
    lines.extend(
        [
            "## Formal PRE commitments",
            "",
            "- Enumerate all candidate bottlenecks.",
            "- Mark each SELECTED, REJECTED, or DEFERRED.",
            "- Select exactly one bottleneck.",
            "- Freeze one falsifiable hypothesis and one principal change.",
            "- Freeze baseline, intervention, fixed variables, sample, budgets,",
            "  primary endpoint, diagnostics, support/refutation criteria, and stop.",
            "- Do not read current-round F0/F1 outcomes or future policy results.",
            "",
        ]
    )
    return "\n".join(lines)
