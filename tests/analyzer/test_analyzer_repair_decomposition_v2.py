from pchsi.analyzer.repair_decomposition import register_decomposition,interpret_decomposition
def test_decomposition_is_post_benefit_and_does_not_revoke_benefit():
 t=register_decomposition("a"*64)
 r=interpret_decomposition(t,{
   "D0":"Failure","D1":"Benefit","D3":"Neutral","D4":"Benefit",
   "prefix_results":[
     {"prefix_length":1,"effect_label":"Neutral"},
     {"prefix_length":2,"effect_label":"Benefit"},
   ]})
 assert t["execution_role"]=="POST_BENEFIT_SECONDARY"
 assert r["formal_benefit_unchanged"] is True
 assert r["mechanism_label"]=="SHORTEST_TESTED_SUFFICIENT_PREFIX"
