from pathlib import Path
from pchsi.reference_loop.canonical import strict_json_loads
def load_metric_registry(path=None):
 p=path or Path(__file__).resolve().parents[3]/"configs/analyzer/analyzer_metric_registry_v1.json"
 v=strict_json_loads(p.read_bytes())
 if v["weighted_composite_scores_forbidden"] is not True: raise ValueError("weighted composite forbidden")
 return v
