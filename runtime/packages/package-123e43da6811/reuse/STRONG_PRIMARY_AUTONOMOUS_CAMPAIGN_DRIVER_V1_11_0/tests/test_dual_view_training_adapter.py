from __future__ import annotations
import json
from pathlib import Path
import pytest
from dual_view_training_adapter import load_dual_view_records, validate_dual_view_census


def row(ord_, state, view, ex, rowsha, loss=3):
    return {"schema_id":"POLICY_STRATEGY_DUAL_VIEW_NATIVE_ROW_V1","schema_version":1,
            "ordinal":ord_,"view_kind":view,
            "source_identity":{"source_example_sha256":ex,"source_state_sha256":state},
            "tokenization":{"input_ids":[1,2,3,4],"labels":[-100,2,3,4],
                            "sequence_token_count":4,"prompt_masked_token_count":1,
                            "completion_loss_token_count":loss,
                            "input_ids_sha256":"1"*64,"labels_sha256":"2"*64},
            "deployment_i1_execution_view": view=="I1_EXECUTION_ACTION",
            "training_auxiliary_strategy_view": view=="STRATEGY_AUXILIARY",
            "promotion_eligible":False,"trainer_native_row_sha256":rowsha}


def write_rows(tmp_path, rows):
    p=tmp_path/'d.jsonl'; p.write_text('\n'.join(json.dumps(x) for x in rows)+'\n',encoding='utf-8'); return p


def test_same_source_state_pair_is_legal(tmp_path:Path):
    s='a'*64
    p=write_rows(tmp_path,[row(0,s,'I1_EXECUTION_ACTION','b'*64,'c'*64),row(1,s,'STRATEGY_AUXILIARY','d'*64,'e'*64)])
    records=load_dual_view_records(p,prompt_label_value=-100)
    assert len(records)==2
    assert {r['view_kind'] for r in records}=={'I1_EXECUTION_ACTION','STRATEGY_AUXILIARY'}
    assert len({r['source_state_sha256'] for r in records})==1
    assert len({r['source_example_sha256'] for r in records})==2


def test_duplicate_source_example_is_rejected(tmp_path:Path):
    s='a'*64; ex='b'*64
    p=write_rows(tmp_path,[row(0,s,'I1_EXECUTION_ACTION',ex,'c'*64),row(1,s,'STRATEGY_AUXILIARY',ex,'e'*64)])
    with pytest.raises(ValueError,match='SOURCE_EXAMPLE_DUPLICATE'):
        load_dual_view_records(p,prompt_label_value=-100)


def test_missing_strategy_member_is_rejected(tmp_path:Path):
    s='a'*64
    p=write_rows(tmp_path,[row(0,s,'I1_EXECUTION_ACTION','b'*64,'c'*64)])
    with pytest.raises(ValueError,match='PAIR_INCOMPLETE'):
        load_dual_view_records(p,prompt_label_value=-100)


def test_action_only_or_zero_strategy_loss_is_rejected():
    good={"STRATEGY_ROW_COUNT":1,"VERIFIED_BENEFIT_ROW_COUNT":1,"STRATEGY_TARGET_TOKEN_COUNT":3,
          "STRATEGY_LOSS_BEARING_TOKEN_COUNT":3,"ACTION_TARGET_TOKEN_COUNT":2,"ACTION_LOSS_BEARING_TOKEN_COUNT":2,
          "PROMPT_MASKED_TOKEN_COUNT":2,"TOTAL_LOSS_BEARING_TOKEN_COUNT":5,"ACTION_ONLY_STRATEGY_ROW_COUNT":0,
          "NON_VERIFIED_STRATEGY_ROW_COUNT":0}
    assert validate_dual_view_census(good)["authorized"] is True
    bad=dict(good); bad["STRATEGY_LOSS_BEARING_TOKEN_COUNT"]=0
    with pytest.raises(ValueError,match='STRATEGY_LOSS'):
        validate_dual_view_census(bad)
