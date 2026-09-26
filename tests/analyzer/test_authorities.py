from __future__ import annotations
import importlib
import pytest


def _m():
    return importlib.import_module("pchsi.analyzer.authorities")


def test_exact_authority_boundary_and_information_boundary() -> None:
    m = _m()
    assert m.ANALYZER_WRITABLE_AUTHORITIES == frozenset({
        m.AnalyzerAuthority.SEMANTIC_HYPOTHESIS,
        m.AnalyzerAuthority.REPAIR_PROPOSAL,
        m.AnalyzerAuthority.ABSTENTION,
    })
    assert m.AnalysisTimeInformationBoundary.POST_EPISODE_DEV_ONLY.value == (
        "POST_EPISODE_DEV_ONLY"
    )
    assert m.LOCAL_GENERATION_CONDITIONS == frozenset({
        m.AnalyzerCondition.A0_ONE_SHOT_LOCAL,
        m.AnalyzerCondition.A1_MULTI_HYPOTHESIS_LOCAL,
    })
    assert m.AnalysisSchedulerRole.RESEARCH_PRIORITY_AUTHORITY.value == "NOT_AUTHORIZED"


def test_canonical_identity_preserves_semantic_bytes() -> None:
    m = _m()
    assert m.canonical_analyzer_identity(
        domain="D", payload={"x": ["A", "a"]}
    ) != m.canonical_analyzer_identity(
        domain="D", payload={"x": ["a", "A"]}
    )
    assert m.canonical_analyzer_identity(
        domain="D", payload={"x": "foo"}
    ) != m.canonical_analyzer_identity(
        domain="D", payload={"x": " foo "}
    )
    assert m.canonical_analyzer_identity(
        domain="D", payload={"x": "A"}
    ) != m.canonical_analyzer_identity(
        domain="D", payload={"x": "a"}
    )


@pytest.mark.parametrize("payload", [{"x": float("nan")}, {"x": object()}])
def test_canonical_identity_rejects_noncanonical_payload(payload) -> None:
    m = _m()
    with pytest.raises((TypeError, ValueError)):
        m.canonical_analyzer_identity(domain="D", payload=payload)
