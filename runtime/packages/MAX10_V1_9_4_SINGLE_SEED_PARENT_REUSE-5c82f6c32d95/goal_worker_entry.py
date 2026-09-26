from pathlib import Path
import argparse,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))

def main():
    from promotion_entry import load
    load()
    from goal_runtime import installed
    from reuse_runtime import installed as reuse_installed
    from entry.offoff_job import worker
    p=argparse.ArgumentParser();p.add_argument('--worker',required=True);p.add_argument('--request-sha256',required=True);args=p.parse_args()
    with installed(),reuse_installed():worker(args.worker,args.request_sha256)

if __name__=='__main__':main()
