from pathlib import Path
import os

from stage0.authorization import prepare_authorization
from stage0.common import load_json_object, sha256_file
from stage0.constants import AUTHORIZATION_ROOT, PREFLIGHT_ROOT


if __name__ == "__main__":
    package_root = Path(__file__).resolve().parent
    preflight_path = PREFLIGHT_ROOT / "OFFLINE_PREFLIGHT_RECEIPT_V1.json"
    preflight = load_json_object(preflight_path)
    authorization = prepare_authorization(
        output_path=(
            AUTHORIZATION_ROOT / "STAGE0_EXECUTION_AUTHORIZATION_V1.json"
        ),
        supplied_token=os.environ.get(
            "HUMAN_PILOT_STAGE0_EXECUTION_APPROVAL", ""
        ),
        package_inventory_sha256=sha256_file(
            package_root / "PACKAGE_FILES.sha256"
        ),
        preflight_receipt_sha256=preflight[
            "preflight_receipt_sha256"
        ],
    )
    print("HUMAN_PILOT_STAGE0_EXECUTION_AUTHORIZATION_READY")
    print("AUTHORIZATION_SHA256=" + authorization["authorization_sha256"])
    print("AUTHORIZED_TOTAL_CONDITION_CELL_COUNT=170")
    print("PAPER_EFFICACY_EVIDENCE=false")
    print("PROMOTION_ELIGIBLE=false")
