from pathlib import Path
from pchsi.cognitive_runtime.manifest import load_runtime_manifest
from pchsi.reference_loop.canonical import sha256_file

def test_existing_analyzer_schema_hashes_are_frozen():
 root=Path(__file__).resolve().parents[2]
 manifest=load_runtime_manifest()
 for row in manifest["stage_rows"]:
  path=row.get("output_schema_relative_path")
  digest=row.get("output_schema_sha256")
  if path:
   assert sha256_file(root/path)==digest
