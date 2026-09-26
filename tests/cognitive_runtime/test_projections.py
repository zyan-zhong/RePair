from pathlib import Path
from pchsi.cognitive_runtime.projections import local_projection
from pchsi.reference_loop.canonical import write_new_json

def test_local_projection_reuses_evidence_pack_identity(tmp_path:Path):
 p=tmp_path/"pack.json";write_new_json(p,{"evidence_pack_sha256":"a"*64})
 out=local_projection(p)
 assert out["evidence_pack_sha256"]=="a"*64 and out["memory_pack_sha256"] is None
