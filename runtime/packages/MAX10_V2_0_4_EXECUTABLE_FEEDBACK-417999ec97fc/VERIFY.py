from pathlib import Path
import sys,subprocess
from closure_entry import verify
ROOT=Path(__file__).resolve().parent
if __name__=='__main__':
    identity=verify()
    tests=['test_semantic_adoption.py','test_repair_feedback.py','test_trajectory_facts.py','test_pre_context.py','test_group_prompt.py','test_x_prompt.py','test_closed_history.py','test_environment_deadline.py']
    p=subprocess.run([sys.executable,'-B','-m','pytest','-q',*[str(ROOT/n) for n in tests]],cwd=ROOT)
    if p.returncode:raise SystemExit(p.returncode)
    if '--server' in sys.argv:
        from repair_verify import server
        server()
    print('REGISTERED_REPAIR_FEEDBACK_VERIFY_PASS',identity)
