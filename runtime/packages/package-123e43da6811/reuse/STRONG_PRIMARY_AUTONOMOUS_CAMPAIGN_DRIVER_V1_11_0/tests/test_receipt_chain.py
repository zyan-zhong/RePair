from receipt_chain import append_receipt

def test_receipt_chain_binds_previous_sha():
    a=append_receipt(None,'A',{'x':1})
    b=append_receipt(a,'B',{'y':2})
    assert b['previous_receipt_sha256']==a['receipt_sha256']
    assert b['receipt_sha256']!=a['receipt_sha256']
