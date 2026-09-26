import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from stage4e import GateError, write_exact, semantic_sha
from stage4e import array_jobs

class ArrayDriverTests(unittest.TestCase):
    def impl(self):
        self.assertIsNotNone(importlib.util.find_spec('stage4e.array_driver'),'ARRAY_DRIVER_MISSING')
        from stage4e import array_driver
        return array_driver
    def test_marker_binds_native_status_and_array_task(self):
        a=self.impl()
        native={'schema_id':'STAGE4D_PARALLEL_SHARD_STATUS_V1','schema_version':1,'slurm_job_id':'905','shard_id':2,
          'completed_prefix_count_at_start':102,'assigned_pair_count':419,'t0_cell_count':419,'t2_cell_count':419,
          'total_condition_cell_count':838,'complete':True,'graceful_partial':False,
          'result_interpretation_authorized':False,'promotion_authorized':False}
        plan={'completed_prefix_count':102,'total_pair_count':1775}
        a.validate_native_status(native,plan,2,'905')
        for key,value in [('shard_id',1),('complete',False),('t2_cell_count',418),('promotion_authorized',True),('completed_prefix_count_at_start',0)]:
            with self.assertRaises(ValueError):a.validate_native_status({**native,key:value},plan,2,'905')
    def test_ambiguous_submission_intent_never_resubmits(self):
        a=self.impl()
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);plan={'plan_sha256':'a'*64,'authorization_sha256':'b'*64}
            write_exact(r/'SUBMISSION_0.intent.json',{'anything':'existing'})
            with patch('stage4e.array_driver.subprocess.run') as mock:
                with self.assertRaisesRegex(GateError,'INTENT_WITHOUT_RECEIPT'):
                    a.submit_generation(r,Path('/root'),Path('/pkg'),Path('/logs'),plan,0,(0,1,2,3))
                mock.assert_not_called()
    def test_existing_submission_is_reused_without_sbatch(self):
        a=self.impl()
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);plan={'plan_sha256':'a'*64,'authorization_sha256':'b'*64}
            obj={'job_id':'900','shards':[0,1,2,3],'generation':0,'plan_sha256':'a'*64}
            write_exact(r/'SUBMISSION_0.json',obj)
            with patch('stage4e.array_driver.subprocess.run') as mock:
                self.assertEqual(a.submit_generation(r,r,Path('/pkg'),Path('/logs'),plan,0,(0,1,2,3)),obj)
                mock.assert_not_called()
    def test_pending_cancellation_is_specific_and_state_filtered(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);calls=[]
            cfg={'full_package':'/approved','authorization_sha256':'a'*64}
            def scheduler(cmd):
                calls.append(cmd)
                if cmd[0]=='scontrol':return 'JobId=156834 UserId=test(123) JobState=PENDING Restarts=0 WorkDir=/approved JobName=st4d_select_4gpu'
                if cmd[0]=='scancel':return ''
                return '156834|CANCELLED by 123|0:0|Unknown|0\n'
            with patch('stage4e.array_jobs.scheduler',side_effect=scheduler),patch('stage4e.array_jobs.os.getuid',return_value=123):
                array_jobs.cancel_pending_once(job='156834',cfg=cfg,state_root=root)
                array_jobs.cancel_pending_once(job='156834',cfg=cfg,state_root=root)
            self.assertEqual([x for x in calls if x[0]=='scancel'],[['scancel','--state=PENDING','156834']])
    def test_running_job_never_cancelled(self):
        with tempfile.TemporaryDirectory() as d:
            calls=[]
            def scheduler(cmd):
                calls.append(cmd);return 'JobId=156834 UserId=test(123) JobState=RUNNING Restarts=0 WorkDir=/approved JobName=st4d_select_4gpu'
            with patch('stage4e.array_jobs.scheduler',side_effect=scheduler),patch('stage4e.array_jobs.os.getuid',return_value=123):
                with self.assertRaises(ValueError):array_jobs.cancel_pending_once(job='156834',cfg={'full_package':'/approved','authorization_sha256':'a'*64},state_root=Path(d))
            self.assertFalse(any(x[0]=='scancel' for x in calls))
    def test_no_evaluator_reimplementation_or_failed_job_retry(self):
        a=self.impl();text=Path(a.__file__).read_text()
        self.assertIn('consolidate_shards(',text);self.assertIn('shard_worker.main(',text)
        self.assertNotIn('env.step(',text);self.assertNotIn('EpisodeEvaluator(',text)
        self.assertIn('ARRAY_ELEMENT_FAILED_NO_AUTOMATIC_RETRY',text)

class ArrayFollowIntegrationTests(unittest.TestCase):
    def put_status(self, root, state_root, plan, master, shard, job, partial=False):
        from stage4e import array_driver as a, file_sha
        count=len(array_jobs.partition_from_prefix(102,1775)[shard]);done=count-1 if partial else count
        native=root/'parallel_v1'/f'shard_{shard}'/f'SHARD_STATUS_{job}_V1.json'
        write_exact(native,{'schema_id':'STAGE4D_PARALLEL_SHARD_STATUS_V1','schema_version':1,
            'slurm_job_id':job,'shard_id':shard,'completed_prefix_count_at_start':102,'assigned_pair_count':count,
            't0_cell_count':done,'t2_cell_count':done,'total_condition_cell_count':2*done,
            'complete':not partial,'graceful_partial':partial,'result_interpretation_authorized':False,'promotion_authorized':False})
        write_exact(a.marker_path(state_root,master,shard),{'array_job_id':master,'shard_id':shard,
            'slurm_job_id':job,'plan_sha256':plan['plan_sha256'],'native_status_file_sha256':file_sha(native)})
    def test_real_status_files_and_partial_subset_submission(self):
        from stage4e import array_driver as a
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'exec';root.mkdir();state=root/a.STATE_REL;state.mkdir(parents=True)
            plan={'completed_prefix_count':102,'total_pair_count':1775,'plan_sha256':'a'*64,'authorization_sha256':'b'*64}
            cfg={'execution_root':str(root),'execution_log_root':str(Path(d)/'logs'),'poll_seconds':0,
                 'array_policy':{'max_partial_resumptions':1}}
            for i in range(4):self.put_status(root,state,plan,'900',i,str(900+i),partial=i==2)
            self.put_status(root,state,plan,'910',2,'911')
            with patch('stage4e.array_driver.subprocess.run',side_effect=[SimpleNamespace(returncode=0,stdout='900\n',stderr=''),SimpleNamespace(returncode=0,stdout='910\n',stderr='')]) as submit,patch('stage4e.array_driver.query_array',return_value=('COMPLETE','completed elements')):
                result=a.follow_arrays(cfg,state,plan)
                self.assertEqual(len(result),4)
                self.assertTrue(all(s['complete'] for s in result.values()))
                self.assertIn('--array=2%4',submit.call_args_list[1].args[0])
                self.assertEqual(read_json_local(state/'SUBMISSION_1.json')['shards'],[2])
    def test_failed_array_does_not_submit_second_generation(self):
        from stage4e import array_driver as a
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);state=root/'state';state.mkdir()
            plan={'plan_sha256':'a'*64,'authorization_sha256':'b'*64}
            cfg={'execution_root':str(root),'execution_log_root':str(root/'logs'),'poll_seconds':0,
                 'array_policy':{'max_partial_resumptions':1}}
            with patch('stage4e.array_driver.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='900\n',stderr='')) as submit,patch('stage4e.array_driver.query_array',return_value=('STOP','900_1|FAILED|1:0')):
                with self.assertRaisesRegex(GateError,'ARRAY_ELEMENT_FAILED_NO_AUTOMATIC_RETRY'):
                    a.follow_arrays(cfg,state,plan)
                self.assertEqual(submit.call_count,1)
                self.assertFalse((state/'SUBMISSION_1.intent.json').exists())

def read_json_local(path):
    return json.loads(path.read_text())
