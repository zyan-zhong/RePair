def next_round_action(governance,next_parent_policy_id):
    if governance.get('stop') is True:return {'launch':False,'terminal_reason':governance.get('reason'),'human_decision_required':False}
    if governance.get('stop') is False:return {'launch':True,'next_parent_policy_id':next_parent_policy_id,'human_decision_required':False}
    raise ValueError('GOVERNANCE_STOP_BOOLEAN_REQUIRED')
