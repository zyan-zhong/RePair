import pytest
from training_acceptance import validate_training_terminal

def test_optimizer_must_change_checkpoint():
    with pytest.raises(ValueError,match='CHECKPOINT_UNCHANGED'):
        validate_training_terminal({'optimizer_steps':1,'initial_checkpoint_sha256':'a'*64,'final_checkpoint_sha256':'a'*64,'candidate_reload_pass':True})

def test_training_terminal_requires_steps_reload_and_changed_checkpoint():
    x=validate_training_terminal({'optimizer_steps':2,'initial_checkpoint_sha256':'a'*64,'final_checkpoint_sha256':'b'*64,'candidate_reload_pass':True})
    assert x['accepted'] is True
