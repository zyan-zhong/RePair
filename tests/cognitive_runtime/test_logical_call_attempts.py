from pchsi.cognitive_runtime.identity import build_transport_attempt_record

def test_ambiguous_post_send_is_explicit_and_nonretrying():
 x=build_transport_attempt_record(
  logical_call_id="l",transport_attempt_id="l:0",transport_attempt_index=0,
  bytes_transmission_state="MAY_HAVE_BEEN_SENT",retry_class="NO_RETRY",
  retry_reason="connection_lost",retry_authority="FROZEN_RUNTIME_POLICY",
  provider_response_id=None,terminal_attempt_status="AMBIGUOUS_POST_SEND",
  ambiguous_post_send_disposition_id=None,raw_request_sha256="a"*64,
  raw_response_sha256=None,input_tokens=None,output_tokens=None,
  reasoning_tokens=None,latency_ms=1.0,cost_usd=None)
 assert x["terminal_attempt_status"]=="AMBIGUOUS_POST_SEND"
