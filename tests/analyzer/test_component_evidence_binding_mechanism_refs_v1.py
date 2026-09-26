from pchsi.analyzer.component_attribution import _component_evidence_universe


def test_component_evidence_universe_accepts_registered_mechanism_refs_only():
    group={
        "group_id":"9"*64,
        "group_manifest_sha256":"a"*64,
        "group_result_sha256":"b"*64,
        "source_conditioned_repair_sha256s":["c"*64],
        "mechanism_hypotheses":[
            {
                "hypothesis_id":"h0",
                "statement":"registered mechanism",
                "evidence_sha256s":["d"*64,"e"*64],
                "uncertainty":"u",
            }
        ],
        "unrelated_nested":{"sha256":"f"*64},
    }
    known=_component_evidence_universe(group)
    assert known=={"a"*64,"b"*64,"c"*64,"d"*64,"e"*64}
    assert "9"*64 not in known
    assert "f"*64 not in known


def test_component_evidence_universe_preserves_existing_coarse_authorities():
    group={
        "group_manifest_sha256":"a"*64,
        "group_result_sha256":"b"*64,
        "source_conditioned_repair_sha256s":[],
        "mechanism_hypotheses":[],
    }
    assert _component_evidence_universe(group)=={"a"*64,"b"*64}
