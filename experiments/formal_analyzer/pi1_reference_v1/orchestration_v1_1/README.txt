Formal Analyzer -> Human Training Researcher PRE Boundary V1.1
================================================================

Purpose
-------
This is a resumable orchestration package for the already-built and already-
validated Formal Analyzer stack. It starts from the CURRENT frozen Main assets:

- 30 accepted Formal Main A0 results;
- 30 accepted Formal Main A1 results;
- 30 source-closed Formal groups / 37 memberships;
- 30 exact Post-Main A1 file bindings;
- 30 restored A3 Analyzer Memory packs;
- 30 A2 + 30 A3 offline projections with 30/30 common-input equality.

It DOES NOT rebuild or redesign:
- Failure Memory;
- Analyzer grouping;
- Analyzer prompts/schemas;
- group projection semantics;
- X semantics;
- candidate projection;
- environment verification.

What the single runner does
---------------------------
1. Materializes one Formal group runtime registry and FORMAL_ANALYZER_DAG_REGISTRY_V2.
   Multi-source groups are represented by a group scientific identity plus a
   memberwise task-access witness; no fake single task/gamefile is invented.
2. Re-renders the already-frozen 30 A2 + 30 A3 requests and submits them as ONE
   OpenAI Batch job through the same generic Batch protocol used elsewhere.
3. Waits/polls the Batch and imports every terminal unit without hidden retry.
4. Builds X from each validated G target using existing crosscheck_projection_v2.
5. Submits X as ONE Batch job, waits/polls, and imports results.
6. Applies the existing deterministic candidate projector and condition/state K=1
   guard. Distinct execution-semantic collisions are METHOD_INVALID; no winner is
   selected.
7. Freezes a formal Analyzer result manifest, pre-verification metrics, resource
   census, and ROUND_EVIDENCE_PACKAGE_V1.
8. STOPS BEFORE Human Training Researcher PRE.

No F0/F1, ALFWorld, environment, trainer, Human PRE, API Researcher shadow, or
Researcher decision is created by this package.

Important asynchronous/resume behavior
--------------------------------------
A single invocation can wait through both Batch jobs and run to the Human PRE
boundary. Run it in tmux.

If the process/session dies, run THE SAME command again. Existing immutable
receipts and files are reused. Completed stages are not resubmitted.

A Batch submission is protected by a pre-send submission-intent file. If the
process dies after the create request may have been sent but before a receipt is
written, the package STOPs instead of automatically resubmitting. Only if you
independently recover the exact Batch ID may you resume with:

  PCHSI_RECOVER_G_BATCH_ID=<batch_id>
or
  PCHSI_RECOVER_X_BATCH_ID=<batch_id>

The recovered Batch must bind the exact previously uploaded input_file_id.

Live authorization
------------------
The two Formal live Batch jobs require an explicit one-time environment flag:

  export PCHSI_AUTHORIZE_FORMAL_ANALYZER_LIVE=YES

This flag does not authorize environment/F0F1 execution; those are not present.

Recommended server location
---------------------------
Upload the ZIP to:

  /data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/

Then safely extract it there.

Run
---
Recommended:

  tmux new -As formal-analyzer-to-human-pre

Inside tmux:

  export PCHSI_AUTHORIZE_FORMAL_ANALYZER_LIVE=YES
  export PCHSI_BATCH_POLL_SECONDS=60

  cd /data/home/scwb204/run/sdar_repro/badcase/pchsi_scripts/formal_analyzer_to_human_researcher_pre_boundary_v1

  bash ./00_VERIFY_PACKAGE.sh

  bash ./RUN_TO_HUMAN_PRE_BOUNDARY.sh

If disconnected:
  reconnect to tmux, or run the same RUN_TO_HUMAN_PRE_BOUNDARY.sh command again.

Expected final boundary
-----------------------
FORMAL_ANALYZER_TO_HUMAN_PRE_BOUNDARY_PASS
HUMAN_RESEARCHER_PRE_CREATED=false
API_RESEARCHER_PRE_SHADOW_CREATED=false
ENVIRONMENT_CALL_PERFORMED=false
F0F1_PERFORMED=false
AUTOMATIC_SCIENTIFIC_RETRY_PERFORMED=false
NEXT_GATE=HUMAN_TRAINING_RESEARCHER_PRE

Scientific boundary
-------------------
The package does NOT assign Benefit/Harm/Neutral/Uncertain. Those remain the
later independent Environment/Verifier authority.

It also does not invent a new C/P live provider sequence. The CURRENT registered
reference path is Formal A0-A3 -> X -> deterministic candidate projection ->
ROUND_EVIDENCE_PACKAGE_V1 -> Human Researcher PRE. Adding unregistered C/P live
calls here would alter the frozen experiment rather than reuse it.


V1.1 access-gate correction
---------------------------
V1 incorrectly required confirmatory_permitted=True for every group member.
That is not the repository runtime contract. The authoritative live teacher-call
gate is teacher_call_permitted=True; confirmatory_permitted remains preserved as
a data-use field but is not promoted into a live Analyzer authorization bit.

V1.1 also fixes the deterministic candidate stage to consume the current
ANALYZER_GROUP_RESULT_V2 field `source_conditioned_proposals`.

V1.1 uses a new default state root:
  /data/run01/scwb204/sdar_repro/badcase/pchsi_scripts/
  formal_analyzer_to_human_researcher_pre_boundary_v1_1_state

Therefore a V1 Stage-1 partial directory cannot collide with V1.1. No V1 live
Batch was submitted before the reported stop, so no live receipt migration is
needed.
