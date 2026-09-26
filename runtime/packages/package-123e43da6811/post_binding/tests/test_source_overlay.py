from pathlib import Path
import ast
import hashlib
import sys

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'work/v17'))
from post_binding.source_overlay import adapt_strong_post


def test_actual_registered_h44_same_call_overlay():
    path = ROOT / 'work/reference_g2/PCHSI_PAPER_CRITICAL_CAUSAL_ROUND_EXECUTION_V1_23_3H4_4/strong_post.py'
    raw = path.read_bytes()
    out = adapt_strong_post(raw.decode('utf8'), expected_source_sha256=hashlib.sha256(raw).hexdigest())
    original = ast.parse(raw.decode('utf8'))
    adapted = ast.parse(out)
    call_count = lambda tree: sum(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                                 and n.func.attr == 'execute_one' for n in ast.walk(tree))
    assert call_count(original) == call_count(adapted) == 1
    assert 'POST_PARTIAL_NO_RESEND' in out
    assert 'POST_NOT_ACCEPTED_NO_RESEND' in out
    assert out.index('recipe_ref=adopt_recipe') > out.index('if artifact is None:')
    assert 'prompt_sha256=sha(prompt)' in out
    assert 'accepted_training_recipe_binding=recipe_ref' in out


def test_source_drift_rejected_before_edit():
    with pytest.raises(ValueError, match='SOURCE_DRIFT'):
        adapt_strong_post('print("unexpected")\n', expected_source_sha256='0' * 64)
