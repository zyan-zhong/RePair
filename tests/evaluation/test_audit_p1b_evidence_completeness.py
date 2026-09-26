from pchsi.evaluation.evidence_completeness import audit_current_evidence_contract

def test_report_has_explicit_requirements():
    r=audit_current_evidence_contract(); assert r.requirement_count>=10 and all(x.justification for x in r.requirements)
