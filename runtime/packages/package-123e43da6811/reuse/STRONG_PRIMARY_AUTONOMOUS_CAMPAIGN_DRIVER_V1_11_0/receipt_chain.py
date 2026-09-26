from safe_io import domain_hash
def append_receipt(prev,stage,payload):
    out={'schema_id':'AUTONOMOUS_CAMPAIGN_RECEIPT_V1','schema_version':1,'stage':stage,'previous_receipt_sha256':None if prev is None else prev['receipt_sha256'],'payload':payload,'receipt_sha256':'0'*64}
    out['receipt_sha256']=domain_hash('AUTONOMOUS_CAMPAIGN_RECEIPT_V1',out)
    return out
