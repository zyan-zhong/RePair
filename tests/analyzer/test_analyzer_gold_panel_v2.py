from pchsi.analyzer.gold_panel import select_gold_panels
def test_panels_are_unique_and_multi_error_annotation_is_supported():
 rows=[{"task_id":"a","gamefile_sha256":"1"*64,"outcome":"FAILURE","frozen_order":0},
       {"task_id":"b","gamefile_sha256":"1"*64,"outcome":"SUCCESS","frozen_order":1},
       {"task_id":"c","gamefile_sha256":"2"*64,"outcome":"SUCCESS","frozen_order":2}]
 p=select_gold_panels(rows,failure_count=1,success_count=1)
 assert p["failure"][0]["task_id"]=="a" and p["success"][0]["task_id"]=="c"
 assert p["annotation_contract"]["supports_multiple_error_instances"]
