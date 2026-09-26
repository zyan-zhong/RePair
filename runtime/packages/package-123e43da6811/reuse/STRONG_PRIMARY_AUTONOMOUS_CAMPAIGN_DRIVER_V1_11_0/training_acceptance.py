def validate_training_terminal(x):
    if type(x.get('optimizer_steps')) is not int or x['optimizer_steps']<=0:raise ValueError('OPTIMIZER_STEPS_NOT_POSITIVE')
    if x.get('initial_checkpoint_sha256')==x.get('final_checkpoint_sha256'):raise ValueError('CHECKPOINT_UNCHANGED')
    if x.get('candidate_reload_pass') is not True:raise ValueError('CANDIDATE_RELOAD_NOT_PASS')
    return {'accepted':True}
