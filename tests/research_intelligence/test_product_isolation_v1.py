from pathlib import Path
import pytest
from pchsi.research_intelligence.product_isolation import HUMAN,BENCHMARK,assert_artifact_domain,assert_separate_roots

def test_roots_must_be_disjoint(tmp_path):
 with pytest.raises(ValueError): assert_separate_roots(tmp_path,tmp_path/'nested')

def test_human_rejects_benchmark_result():
 with pytest.raises(ValueError,match='leakage'): assert_artifact_domain({'schema_id':'STRONG_MODEL_REFERENCE_CELL_RESULT_V1'},HUMAN)

def test_benchmark_rejects_human_pre():
 with pytest.raises(ValueError,match='leakage'): assert_artifact_domain({'schema_id':'HUMAN_RESEARCHER_PRE_V1'},BENCHMARK)
