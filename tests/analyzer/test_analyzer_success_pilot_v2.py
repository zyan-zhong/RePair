from pchsi.analyzer.success_optimization import register_success_pilot
def test_success_pilot_is_secondary_and_execution_closed():
 r=register_success_pilot([{"candidate_sha256":"a"*64,
   "gamefile_sha256":"b"*64,"requires_environment_verification":True}])
 assert r["execution_role"]=="SECONDARY_NON_BLOCKING"
 assert r["live_execution_authorized"] is False
