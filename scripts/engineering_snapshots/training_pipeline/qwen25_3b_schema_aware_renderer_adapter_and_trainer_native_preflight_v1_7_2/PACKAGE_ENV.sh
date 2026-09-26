#!/usr/bin/env bash

PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
export PACKAGE_ROOT

export BADCASE_ROOT="${BADCASE_ROOT:-/data/run01/scwb204/sdar_repro/badcase}"
export ROUND_ROOT="${ROUND_ROOT:-$BADCASE_ROOT/experiments/human_reference_round_pi1_pi2_v1}"

# ---------- V1.6 frozen renderer census / Human→Strong normative bridge ----------
export V16_OUTPUT_ROOT="${V16_OUTPUT_ROOT:-$ROUND_ROOT/qwen25_3b_frozen_renderer_interface_census_and_reference_takeover_bridge_v1_6}"
export V16_CENSUS_PATH="$V16_OUTPUT_ROOT/renderer_interface_census/FROZEN_Q2_RENDERER_INTERFACE_CENSUS_V1.json"
export V16_MATERIALIZER_EXCERPT_PATH="$V16_OUTPUT_ROOT/renderer_interface_census/MATERIALIZER_RELEVANT_SOURCE_EXCERPTS_V1.txt"
export V16_NORMATIVE_BRIDGE_PATH="$V16_OUTPUT_ROOT/reference_takeover_bridge/REFERENCE_TO_TAKEOVER_NORMATIVE_BRIDGE_V1.json"
export V16_REVIEW_ZIP="$V16_OUTPUT_ROOT/review.zip"

export EXPECTED_V16_CENSUS_SHA256="cd1fb294bc048a3b4e73d642a633c8cef0a8698664214a87ad54af280299a297"
export EXPECTED_V16_NORMATIVE_BRIDGE_SHA256="be1fc703a34453b048dec62989bd558c72e647f820c09ef44b0771c1247c3c8c"
export EXPECTED_V16_REVIEW_ZIP_SHA256="7e6bc94a3305154790788b6a9860941670b8092f224d2ce2fb44581f919a1dde"

# ---------- Historical π1 / Q2 renderer oracle ----------
export PI1_SOURCE_TRAINING_EXAMPLES_PATH="${PI1_SOURCE_TRAINING_EXAMPLES_PATH:-/data/run01/scwb204/pchsi/p2/d_q2_bad_v1_frozen/training_examples.jsonl}"
export EXPECTED_PI1_SOURCE_TRAINING_EXAMPLES_SHA256="9cd758bc6ee6bde268282a19c0c580884c1643a4c0588fe4886e6a0a4810b561"

export PI1_REFERENCE_MATERIALIZED_EXAMPLES_PATH="${PI1_REFERENCE_MATERIALIZED_EXAMPLES_PATH:-/data/run01/scwb204/pchsi/p2/d_q2_bad_training_materialization_v1_frozen/materialized_examples.jsonl}"
export EXPECTED_PI1_REFERENCE_MATERIALIZED_EXAMPLES_SHA256="c4f593604208485fe6a35405acc47d56e97bcaf98705bcb292a260a3147e2895"

export PI1_FINAL_MATERIALIZATION_MANIFEST_PATH="${PI1_FINAL_MATERIALIZATION_MANIFEST_PATH:-/data/run01/scwb204/pchsi/p2/d_q2_bad_training_materialization_v1_frozen/final_materialization_manifest.json}"
export EXPECTED_PI1_FINAL_MATERIALIZATION_MANIFEST_SHA256="868c434bc519b14fb2f870fefd500526807581f4fb5b22b73eaa69e4e46db1e4"

export PI1_ROW_RENDERER_PATH="${PI1_ROW_RENDERER_PATH:-/data/run01/scwb204/pchsi/p2/d_q2_bad_training_materialization_v1_frozen/provenance/materialize.py}"
export EXPECTED_PI1_ROW_RENDERER_SHA256="5f323e437ea70d0e54fd33a21d382df26a0188c7273418acc3c91387433e0820"

export PI1_CHAT_TEMPLATE_PATH="${PI1_CHAT_TEMPLATE_PATH:-/data/run01/scwb204/pchsi/p2/d_q2_bad_training_materialization_v1_frozen/provenance/chat_template.jinja}"
export EXPECTED_PI1_CHAT_TEMPLATE_SHA256="cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f"

export EXPECTED_PI1_TOKENIZER_BUNDLE_SHA256="8fba154872aa8982e9556cb6cbdd35f3f6e83b8c3c41d782caf6fbf5931c8e0c"

export QWEN_BASE_MODEL_PATH="${QWEN_BASE_MODEL_PATH:-/data/run01/scwb204/.cache/huggingface/hub/models--Qwen--Qwen2.5-3B-Instruct/snapshots/aa8e72537993ba99e69dfaafa59ed015b17504d1}"
export QWEN_FOUNDATION_REPOSITORY="Qwen/Qwen2.5-3B-Instruct"
export QWEN_FOUNDATION_REVISION="aa8e72537993ba99e69dfaafa59ed015b17504d1"

# ---------- V1.3 semantic dataset authority ----------
export V13_OUTPUT_ROOT="${V13_OUTPUT_ROOT:-$ROUND_ROOT/qwen25_3b_plan_driven_dataset_materialization_and_trainer_preflight_v1_3_granularity_failclosed}"
export V13_SEMANTIC_ROOT="$V13_OUTPUT_ROOT/semantic_materialization"
export EXPECTED_V13_SEMANTIC_MATERIALIZATION_SHA256="335c8c587c96d5215821e1ad02582d19bef5bf5d5a3ee37f5b81fa2a43bda7f6"
export EXPECTED_V13_ACTUAL_MIXTURE_SHA256="2da3e81b4bef350f61f7b9cbc9d7f340bfccdced108125ddf9fe6904f81538c0"

# ---------- Strong Research Planner plan ----------
export STRONG_PLAN_PATH="${STRONG_PLAN_PATH:-$ROUND_ROOT/human_strong_post_adjudication_and_strong_training_plan_v1_1_route_scope_recovery/handoff/RESEARCH_PLANNER_TRAINING_PLAN_V1.json}"
export EXPECTED_STRONG_PLAN_SHA256="282fe712c85641c47f9c29f2b942c6b94528d22a942345d4ac57553ab95697d2"

# ---------- Parent π1 Train17 ----------
export PARENT_CHECKPOINT_SET_MANIFEST="${PARENT_CHECKPOINT_SET_MANIFEST:-/data/run01/scwb204/pchsi/p2/p4_r1_q2_bad_checkpoint_set_v1_frozen/checkpoint_set_manifest.json}"
export EXPECTED_PARENT_CHECKPOINT_SET_MANIFEST_SHA256="b374398da2f8103376f54998bc15dd35f73ad90fe5bed93742dfd23d52c7ef87"
export PARENT_POLICY_ID="PILOT_DISTILLED_PI1"
export PARENT_POLICY_TRAINING_SEED="17"
export EXPECTED_PARENT_TRAIN17_ADAPTER_BUNDLE_SHA256="b296f2254b1fa1f2e141dffd3f6b5af903f839df4790ffcb245fd8dd57773ace"

# ---------- V1.7 outputs ----------
export OUTPUT_ROOT="${OUTPUT_ROOT:-$ROUND_ROOT/qwen25_3b_schema_aware_renderer_adapter_and_trainer_native_preflight_v1_7_2}"
export REPRO_ROOT="$OUTPUT_ROOT/historical_renderer_reproduction"
export SOURCE_ADAPTER_ROOT="$OUTPUT_ROOT/schema_aware_source_adapter"
export NATIVE_ROOT="$OUTPUT_ROOT/trainer_native_dataset"
export MAINLINE_ROOT="$OUTPUT_ROOT/chinese_mainline_view"
export PREFLIGHT_ROOT="$OUTPUT_ROOT/trainer_preflight"
export REVIEW_ROOT="$OUTPUT_ROOT/review"
