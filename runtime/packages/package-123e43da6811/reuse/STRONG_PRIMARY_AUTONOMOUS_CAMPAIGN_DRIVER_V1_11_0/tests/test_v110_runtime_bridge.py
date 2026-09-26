from pathlib import Path
from v110_runtime_bridge import load_verifier_gate


def test_reuses_v110_receipt_gate_in_isolated_process(tmp_path:Path):
    pkg=tmp_path/'v110'; pkg.mkdir()
    (pkg/'receipt_gate.py').write_text('''def validate_verifier_receipts(a,b,c):\n return {"schema_id":"STRONG_PRIMARY_R1_VERIFIER_RECEIPT_GATE_V1","round_id":"R1","result_package_sha256":"b"*64,"stable_effect_counts":{"BENEFIT":0,"HARM":1,"NEUTRAL":0,"UNCERTAIN":0}}\n''',encoding='utf-8')
    up=tmp_path/'up'; (up/'verifier').mkdir(parents=True)
    for name in ('CLEAN_REFERENCE_F0F1_RESULT_PACKAGE_V1.json','FINAL_TERMINAL_V2.json','ACCEPTED_PRE_BINDING_V3.json'):
        (up/'verifier'/name).write_text('{}',encoding='utf-8')
    out=load_verifier_gate(v110_package_root=pkg,upstream_root=up)
    assert out['round_id']=='R1' and out['stable_effect_counts']['HARM']==1
