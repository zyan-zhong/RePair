"""Scheduling adapter for four independent one-GPU jobs; no scientific evaluator."""
from __future__ import annotations
import os
from pathlib import Path
import re
import subprocess
import time
from . import GateError, read_json, write_exact, semantic_sha

ACTIVE = {'PENDING','RUNNING','COMPLETING','CONFIGURING','SUSPENDED','REQUEUED','RESIZING'}


def partition_from_prefix(prefix: int, total: int) -> tuple[tuple[int, ...], ...]:
    if type(prefix) is not int or type(total) is not int or not 0 <= prefix <= total:
        raise GateError('ARRAY_PREFIX_INVALID')
    return tuple(tuple(i for i in range(prefix, total) if i % 4 == shard) for shard in range(4))


def parse_accounting(raw: str, master: str, shards: tuple[int, ...]) -> dict[int, tuple[str,str]]:
    if not master.isdigit() or not shards or any(type(i) is not int or i not in range(4) for i in shards):
        raise GateError('ARRAY_ACCOUNTING_IDENTITY_INVALID')
    found = {}
    for line in raw.splitlines():
        v = line.split('|')
        if len(v) < 3:
            continue
        match = re.fullmatch(re.escape(master) + r'_(\d+)', v[0].strip())
        if match is None:
            continue  # A parent or .batch/.extern record is not an array element.
        shard = int(match.group(1))
        if shard not in shards:
            raise GateError('ARRAY_UNEXPECTED_ACCOUNTING_ELEMENT')
        if shard in found:
            raise GateError('ARRAY_DUPLICATE_ACCOUNTING_ELEMENT')
        state = v[1].strip().split()[0].rstrip('+')
        found[shard] = state, v[2].strip()
    return found


def classify_accounting(raw: str, master: str, shards: tuple[int, ...]) -> str:
    found = parse_accounting(raw, master, shards)
    for state, code in found.values():
        if state not in ACTIVE and (state != 'COMPLETED' or code != '0:0'):
            return 'STOP'
    if len(found) == len(shards) and all(x == ('COMPLETED','0:0') for x in found.values()):
        return 'COMPLETE'
    return 'WAIT'


def validate_pending_job(raw: str, job: str, package: str, uid: int) -> None:
    fields = dict(re.findall(r'(?:^|\s)([A-Za-z][A-Za-z0-9_]*)=(\S+)', raw))
    owner = re.fullmatch(r'.+\((\d+)\)', fields.get('UserId',''))
    if (fields.get('JobId') != job or fields.get('JobState') != 'PENDING'
            or fields.get('Restarts') != '0' or fields.get('WorkDir') != package
            or fields.get('JobName') != 'st4d_select_4gpu' or owner is None
            or int(owner.group(1)) != uid):
        raise GateError('OLD_JOB_NOT_OWNED_NEVER_STARTED_PENDING_STAGE4D')


def parse_parsable_job(raw: str) -> str:
    value = raw.strip()
    if re.fullmatch(r'[0-9]+(?:;[A-Za-z0-9_.-]+)?', value) is None:
        raise GateError('ARRAY_SUBMISSION_AMBIGUOUS_NO_RETRY')
    return value.split(';',1)[0]


def submission_command(package: Path, root: Path, plan_sha: str, shards: tuple[int,...], logs: Path) -> list[str]:
    if not shards or len(set(shards)) != len(shards) or any(type(i) is not int or i not in range(4) for i in shards):
        raise GateError('ARRAY_SHARD_SET_INVALID')
    return ['sbatch','--parsable','--export=NIL','--no-requeue',
            '--array=' + ','.join(map(str,shards)) + '%4',
            '--chdir='+str(package), '--output='+str(logs/'full_select_array_%A_%a.out'),
            '--error='+str(logs/'full_select_array_%A_%a.err'),str(package/'array_shard.sh'),
            str(package),str(root),plan_sha]


def incomplete_shards(statuses: dict[int,dict]) -> tuple[int,...]:
    missing = []
    for shard, value in sorted(statuses.items()):
        n=value.get('assigned_pair_count'); t0=value.get('t0_cell_count');t2=value.get('t2_cell_count')
        if any(type(x) is not int for x in (n,t0,t2)) or not (0 <= t0 == t2 <= n):
            raise GateError('ARRAY_SHARD_PAIR_COUNT_INVALID')
        if type(value.get('complete')) is not bool or value['complete'] != (t0 == n):
            raise GateError('ARRAY_SHARD_COMPLETENESS_INVALID')
        if not value['complete']:
            missing.append(shard)
    return tuple(missing)


def scheduler(args: list[str]) -> str:
    p=subprocess.run(args,text=True,capture_output=True,timeout=60)
    if p.returncode:
        raise GateError('SCHEDULER_COMMAND_FAILED:'+args[0]+':'+p.stderr[-2000:])
    return p.stdout


def query_array(master: str, shards: tuple[int,...]) -> tuple[str,str]:
    raw=scheduler(['sacct','-n','-P','-X','-j',master,'--format=JobID%50,State%40,ExitCode'])
    result=classify_accounting(raw,master,shards)
    if result == 'WAIT':
        # Query uncertainty is not completion. Preserve compact queue state for diagnosis.
        queue=scheduler(['squeue','--array','-h','-j',master,'-o','%i|%T'])
        if not queue.strip():return 'UNKNOWN',raw
    return result,raw


def cancel_pending_once(*, job: str, cfg: dict, state_root: Path) -> None:
    """Cancel only this owned pending job, with a durable intent and terminal recheck."""
    receipt=state_root/'PENDING_REPLACEMENT.json';intent=state_root/'PENDING_REPLACEMENT.intent.json'
    if receipt.exists():
        value=read_json(receipt)
        if value.get('old_job_id') != job or value.get('cancelled_before_start') is not True:
            raise GateError('PENDING_REPLACEMENT_LINEAGE_CHANGED')
        return
    if not intent.exists():
        raw=scheduler(['scontrol','--oneliner','show','job',job])
        validate_pending_job(raw,job,cfg['full_package'],os.getuid())
        write_exact(intent,{'old_job_id':job,'owned_pending_verified':True,
            'job_record_sha256':semantic_sha({'scontrol':raw}),
            'authorization_sha256':cfg['authorization_sha256'],
            'cancellation_scope':'THIS_JOB_ONLY_PENDING_STATE_FILTER'})
        # Atomic state filter: never kill this workload if it has started meanwhile.
        scheduler(['scancel','--state=PENDING',job])
    elif read_json(intent).get('old_job_id') != job:
        raise GateError('PENDING_REPLACEMENT_INTENT_CHANGED')
    for _ in range(30):
        raw=scheduler(['sacct','-n','-P','-X','-j',job,'--format=JobIDRaw,State%40,ExitCode,Start,ElapsedRaw'])
        rows=[x.split('|') for x in raw.splitlines() if x.split('|')[0].strip()==job]
        if len(rows)>1:raise GateError('OLD_JOB_ACCOUNTING_AMBIGUOUS')
        if rows:
            row=rows[0];state=row[1].strip().split()[0]
            if state=='CANCELLED':
                if len(row)<5 or row[3].strip() not in ('Unknown','None','N/A','') or row[4].strip()!='0':
                    raise GateError('OLD_JOB_MAY_HAVE_STARTED_NO_MIGRATION')
                write_exact(receipt,{'old_job_id':job,'cancelled_before_start':True,
                    'state':'CANCELLED','accounting_record':row,
                    'authorization_sha256':cfg['authorization_sha256']})
                print('STAGE4D_OLD_PENDING_JOB_CANCELLED='+job,flush=True)
                return
            if state not in ('PENDING','CANCELLED'):
                raise GateError('OLD_JOB_STARTED_OR_FINISHED_NO_MIGRATION:'+state)
        time.sleep(2)
    raise GateError('PENDING_CANCELLATION_UNCONFIRMED_NO_ARRAY_SUBMISSION')
