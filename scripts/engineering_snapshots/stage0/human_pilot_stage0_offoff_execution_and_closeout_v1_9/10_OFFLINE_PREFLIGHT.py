from pathlib import Path

from stage0.preflight import run_preflight


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    receipt = run_preflight(package_root=root)
    print("HUMAN_PILOT_STAGE0_OFFLINE_PREFLIGHT_PASS")
    print("PREFLIGHT_RECEIPT_SHA256=" + receipt["preflight_receipt_sha256"])
    print("MODEL_EXECUTION_COUNT=0")
    print("ENVIRONMENT_EXECUTION_COUNT=0")
    print("PAPER_EFFICACY_EVIDENCE=false")
