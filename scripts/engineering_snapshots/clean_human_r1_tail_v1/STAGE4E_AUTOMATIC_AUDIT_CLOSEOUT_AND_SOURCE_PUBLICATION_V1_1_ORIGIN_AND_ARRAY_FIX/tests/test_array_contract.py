import importlib.util
from pathlib import Path
import unittest

class ArrayContractTests(unittest.TestCase):
    def impl(self):
        self.assertIsNotNone(importlib.util.find_spec('stage4e.array_jobs'),'ARRAY_ADAPTER_MISSING')
        from stage4e import array_jobs
        return array_jobs
    def test_accounting_waits_for_all_four_not_parent(self):
        a=self.impl();raw='900|COMPLETED|0:0\n900_0|COMPLETED|0:0\n900_1|RUNNING|0:0\n'
        self.assertEqual(a.classify_accounting(raw,'900',(0,1,2,3)),'WAIT')
    def test_all_four_completed_zero_is_required(self):
        a=self.impl();raw='\n'.join(f'900_{i}|COMPLETED|0:0' for i in range(4))
        self.assertEqual(a.classify_accounting(raw,'900',(0,1,2,3)),'COMPLETE')
    def test_failed_or_nonzero_element_stops(self):
        a=self.impl()
        for state,code in [('FAILED','1:0'),('COMPLETED','1:0'),('TIMEOUT','0:0'),('CANCELLED','0:0')]:
            self.assertEqual(a.classify_accounting(f'900_1|{state}|{code}','900',(0,1)),'STOP')
    def test_duplicate_accounting_is_not_silently_selected(self):
        a=self.impl()
        with self.assertRaises(ValueError):a.classify_accounting('900_0|COMPLETED|0:0\n900_0|FAILED|1:0','900',(0,))
    def test_task_steps_not_counted_as_completed_elements(self):
        a=self.impl()
        self.assertEqual(a.classify_accounting('900_0.batch|COMPLETED|0:0','900',(0,)),'WAIT')
    def test_only_never_started_pending_job_is_migratable(self):
        a=self.impl();p='/approved/pkg'
        raw=f'JobId=156834 UserId=test(123) JobState=PENDING Restarts=0 WorkDir={p} JobName=st4d_select_4gpu'
        a.validate_pending_job(raw,'156834',p,123)
        for changed in [raw.replace('PENDING','RUNNING'),raw.replace('Restarts=0','Restarts=1'),raw.replace(p,'/other'),raw.replace('test(123)','test(124)')]:
            with self.assertRaises(ValueError):a.validate_pending_job(changed,'156834',p,123)
    def test_array_template_one_gpu_and_no_parent_directory_guess(self):
        a=self.impl();text=(Path(a.__file__).resolve().parents[1]/'array_shard.sh').read_text()
        self.assertIn('#SBATCH --gpus=1',text);self.assertIn('#SBATCH --array=0-3%4',text)
        for token in ('--mem=','--mem-per','--cpus-per-task','--gpus=4','${USER}','dirname "$0"'):
            self.assertNotIn(token,text)
        self.assertIn('PACKAGE_ROOT="$1"',text);self.assertIn('SLURM_ARRAY_TASK_ID',text)
    def test_submission_uses_single_array_and_no_requeue(self):
        a=self.impl();cmd=a.submission_command(Path('/pkg'),Path('/execution'),'p'*64,(0,1,2,3),Path('/logs'))
        self.assertIn('--array=0,1,2,3%4',cmd);self.assertIn('--export=NIL',cmd);self.assertIn('--no-requeue',cmd)
        self.assertEqual(cmd.count('sbatch'),1)
    def test_partial_resume_only_registered_incomplete_shards(self):
        a=self.impl()
        rows={i:{'complete':i!=2,'t0_cell_count':10 if i!=2 else 4,'t2_cell_count':10 if i!=2 else 4,'assigned_pair_count':10} for i in range(4)}
        self.assertEqual(a.incomplete_shards(rows),(2,))
        with self.assertRaises(ValueError):a.incomplete_shards({0:{**rows[0],'t2_cell_count':9}})
    def test_plan_partition_reuses_absolute_ordinal(self):
        a=self.impl();plan=a.partition_from_prefix(102,1775)
        self.assertEqual([len(x) for x in plan],[418,418,419,418])
        self.assertEqual(sorted(x for row in plan for x in row),list(range(102,1775)))
    def test_bad_prefix_rejected(self):
        a=self.impl()
        for n in (-1,1776,True):
            with self.assertRaises(ValueError):a.partition_from_prefix(n,1775)
    def test_submit_output_ambiguity_rejected(self):
        a=self.impl();self.assertEqual(a.parse_parsable_job('123;cluster\n'),'123')
        for raw in ('','123\n124','Submitted batch job 123'):
            with self.assertRaises(ValueError):a.parse_parsable_job(raw)

class ArrayQueryTests(unittest.TestCase):
    def test_partial_accounting_with_no_queue_is_unknown_not_infinite_wait(self):
        from unittest.mock import patch
        from stage4e import array_jobs as a
        with patch('stage4e.array_jobs.scheduler',side_effect=['900_0|COMPLETED|0:0\n','']):
            self.assertEqual(a.query_array('900',(0,1,2,3))[0],'UNKNOWN')
