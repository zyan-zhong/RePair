from pathlib import Path
import ast
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parent


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def main():
    rows=[]
    for line in (ROOT/"PACKAGE_FILES.sha256").read_text().splitlines():
        if not line:
            continue
        digest,rel=line.split("  ",1)
        path=ROOT/rel
        if not path.is_file() or path.is_symlink():
            raise SystemExit("STOP=PACKAGE_FILE_MISSING:"+rel)
        if sha(path)!=digest:
            raise SystemExit("STOP=PACKAGE_SHA_MISMATCH:"+rel)
        rows.append(rel)
    print("PACKAGE_SHA256_VERIFY_PASS files="+str(len(rows)))

    authority=json.loads(
        (ROOT/"V1232_INPUT_CAPSULE_AUTHORITY_V1.json").read_text(encoding="utf-8")
    )
    capsule=ROOT/authority["capsule_filename"]
    if sha(capsule)!=authority["capsule_sha256"]:
        raise SystemExit("STOP=V123133_CAPSULE_PIN")
    print("V123133_CAPSULE_PIN_PASS")

    for rel in rows:
        if rel.endswith(".py"):
            ast.parse((ROOT/rel).read_text(encoding="utf-8"),filename=rel)
    print("PACKAGE_PYTHON_AST_PASS")

    production="\n".join(
        (ROOT/name).read_text(encoding="utf-8")
        for name in (
            "submit_v1232.py",
            "submission_contract.py",
            "live_rollout_job.py",
        )
    )
    for token in (
        "STRONG-PRIMARY-R1-PI0-I1",
        "PI0_CLEAN",
        "gpu_a800",
        "2843",
        "07221cbfa374e5ac",
        "8ebdf8feaa3f5287",
        "309a2441f31d210f",
        "Qwen2.5-3B-Instruct",
    ):
        if token in production:
            raise SystemExit("STOP=CURRENT_EXPERIMENT_LITERAL:"+token)
    print("NO_CURRENT_ROUND_MODEL_DATA_RESOURCE_HARDCODE_PASS")

    if "branch_bindings_v2" in production or "PRIVATE_UPDATE_BINDING" in production:
        raise SystemExit("STOP=DEPRECATED_DISCOVERY_SURFACE_REINTRODUCED")
    print("NO_PREVIOUS_DISCOVERY_SURFACE_PASS")

    policy=json.loads(
        (ROOT/"V1232_LIVE_ROLLOUT_OPERATIONAL_POLICY_V1.json")
        .read_text(encoding="utf-8")
    )
    if policy.get("task_retry_count")!=0:
        raise SystemExit("STOP=SCIENTIFIC_TASK_RETRY_NOT_ZERO")
    if policy.get("job_requeue_authorized") is not False:
        raise SystemExit("STOP=JOB_REQUEUE_AUTHORIZED")
    print("NO_TASK_RETRY_NO_JOB_REQUEUE_PASS")

    env=dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"]="1"
    cp=subprocess.run(
        [sys.executable,"-m","pytest","-q","-p","no:cacheprovider",str(ROOT/"tests")],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=False,
        env=env,
    )
    print(cp.stdout,end="")
    if cp.returncode:
        raise SystemExit("STOP=PACKAGE_PYTEST")
    print("PACKAGE_PYTEST_PASS")

    for shell_name in ("RUN_V1232.sh","STATUS_V1232.sh"):
        shell=(ROOT/shell_name).read_text(encoding="utf-8")
        if re.search(r"(^|\\s)set\\s+-[A-Za-z]*[eu]",shell) or "pipefail" in shell:
            raise SystemExit("STOP=STRICT_SHELL:"+shell_name)
        cp=subprocess.run(
            ["bash","-n",str(ROOT/shell_name)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=False,
        )
        if cp.returncode:
            raise SystemExit("STOP=BASH_SYNTAX:"+shell_name)
    print("OPERATOR_STRICT_SHELL_DISABLED_PASS")
    print("BASH_SYNTAX_PASS")

    if "openai.OpenAI" in production or "requests.post" in production:
        raise SystemExit("STOP=EXTERNAL_PROVIDER_CLIENT")
    print("NO_EXTERNAL_PROVIDER_CLIENT_PASS")

    if "--hold" not in (ROOT/"submission_contract.py").read_text():
        raise SystemExit("STOP=HELD_SUBMISSION_CONTRACT_MISSING")
    if "scontrol" not in (ROOT/"submit_v1232.py").read_text():
        raise SystemExit("STOP=HELD_JOB_RELEASE_PATH_MISSING")
    print("HELD_SUBMISSION_DURABLE_RELEASE_CONTRACT_PASS")

    print("V1232_PACKAGE_VERIFY_PASS")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
