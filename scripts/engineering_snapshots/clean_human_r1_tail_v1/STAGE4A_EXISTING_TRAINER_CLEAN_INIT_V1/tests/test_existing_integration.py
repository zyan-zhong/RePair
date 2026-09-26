"""Real frozen plan/contract/adapter tests; GPU loading remains for server smoke."""
from __future__ import annotations
import ast,copy,hashlib,json,os,tempfile,types,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import sys
HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE))
import clean_adapter as a
import run_stage as r

class ExistingIntegrationTests(unittest.TestCase):
    def data(self):
        with zipfile.ZipFile(HERE/'tests/fixtures/PLAN_HANDOFF_REVIEW.zip') as z:
            return a.validate_packet({n:z.read(n) for n in z.namelist()})
    def test_original_batch_four_assumption_is_present(self):
        tree=ast.parse((HERE/'tests/fixtures/formal_train.py').read_text())
        f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='verify_formal_schedule')
        source=ast.unparse(f)
        self.assertIn('FORMAL_EFFECTIVE_BATCH != 4',source)
    def test_actual_existing_optimizer_loop_updates_cpu_parameters(self):
        import torch
        import numpy as np
        import math,random
        from collections.abc import Sequence
        source=(HERE/'tests/fixtures/formal_train.py').read_text();tree=ast.parse(source)
        names={'verify_lora_only_trainable_parameters','hash_trainable_parameters','build_formal_optimizer',
               'collate_frozen_singleton','count_shifted_prediction_targets','_positive_num_items',
               'token_normalized_causal_lm_loss','execute_training_plan','validate_completed_formal_ledger'}
        selected=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
        ns={'torch':torch,'F':torch.nn.functional,'np':np,'math':math,'hashlib':hashlib,'json':json,'Sequence':Sequence,
            'FORMAL_LEARNING_RATE':1e-4,'FORMAL_WEIGHT_DECAY':0.,'FORMAL_MAX_GRAD_NORM':1.,'FORMAL_MAX_SEQUENCE_LENGTH':4,
            'FORMAL_OPTIMIZER_STEPS':2,'FORMAL_TARGET_LOSS_TOKEN_BUDGET':4,'FORMAL_DATASET_PASSES':1}
        exec(compile(ast.Module(body=selected,type_ignores=[]),'actual_frozen_formal_functions','exec'),ns)
        class Toy(torch.nn.Module):
            def __init__(self):
                super().__init__();self.lora_A=torch.nn.Parameter(torch.randn(8,8)/100)
            def forward(self,input_ids,attention_mask):
                return {'logits':torch.nn.functional.one_hot(input_ids,8).float()@self.lora_A}
        torch.manual_seed(17);model=Toy();before=ns['hash_trainable_parameters'](model)
        rows=[{'case_id':str(i),'tokenization':{'input_ids':[0,1,2,3],'labels':[-100,-100,2,3],'completion_loss_token_count':2}} for i in range(2)]
        plan=tuple({'global_step':i+1,'pass_index':0,'step_in_pass':i+1,'example_indices':(i,),'case_ids':(str(i),),'target_loss_tokens':2} for i in range(2))
        optimizer=ns['build_formal_optimizer'](model);scheduler=torch.optim.lr_scheduler.LambdaLR(optimizer,lambda n:1-n/2)
        ledger=ns['execute_training_plan'](model=model,source_rows=rows,plan=plan,optimizer=optimizer,scheduler=scheduler,device='cpu')
        summary=ns['validate_completed_formal_ledger'](plan=plan,ledger=ledger)
        self.assertNotEqual(before,ns['hash_trainable_parameters'](model));self.assertEqual(summary['target_loss_token_count'],4)
        self.assertEqual(summary['optimizer_step_count'],2)
        self.assertEqual(ledger[-1]['learning_rate_after'],(0.,))
    def test_real_generic_binding_original_adapter_preflight_and_authorization(self):
        from round_training import contracts
        trainer=Path(contracts.__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'out';root.mkdir();up=Path(td)/'upstream';up.mkdir();data=self.data()
            for name,raw in data['files'].items():(up/name).write_bytes(raw)
            data['next']['plan_path']=str(up/'RESEARCH_PLANNER_TRAINING_PLAN_V1.json')
            data['next']['sample_order_path']=str(up/'ROUND_SAMPLE_ORDER_MANIFEST_V1.json')
            data['contract']['dataset']['path']=str(up/'POLICY_T2_TRAINER_NATIVE_V1.jsonl')
            data['contract']['dataset']['manifest_path']=str(up/'POLICY_T2_TRAINER_NATIVE_DATASET_MANIFEST_V1.json')
            base={'snapshot_path':str(root/'clean_base/aa8e72537993ba99e69dfaafa59ed015b17504d1'),'manifest_path':str(root/'base_manifest.json'),
                  'manifest_sha256':a.sha(b'{}'),'repository_id':'Qwen/Qwen2.5-3B-Instruct','revision':'aa8e72537993ba99e69dfaafa59ed015b17504d1'}
            (root/'base_manifest.json').write_bytes(b'{}')
            init=root/'seed_zero_adapter';init.mkdir();config={'peft_type':'LORA','task_type':'CAUSAL_LM',**{k:data['contract']['peft'][k] for k in ('r','lora_alpha','lora_dropout','bias','target_modules')},'base_model_name_or_path':base['snapshot_path']}
            (init/'adapter_config.json').write_bytes(a.cb(config));(init/'adapter_model.safetensors').write_bytes(b'test-placeholder-never-loaded')
            manifest={'adapter_bundle_sha256':'b'*64,'files':{p.name:{'sha256':a.file_sha(p),'size_bytes':p.stat().st_size} for p in init.iterdir()}}
            (root/'SEED_ZERO_ADAPTER_MANIFEST.json').write_bytes(a.cb(manifest))
            formal=HERE/'tests/fixtures/formal_train.py';old=trainer/'round_training/adapters/frozen_formal_train_peft.py'
            rt={'base_binding':base,'formal_source':{'path':str(formal),'sha256':a.file_sha(formal)},'legacy_adapter_source':{'path':str(old),'sha256':a.file_sha(old)},
                'source_code_root_sha256':'c'*64,'source_code_files':{},'plan_ref':{'path':data['next']['plan_path'],'sha256':a.file_sha(Path(data['next']['plan_path']))}}
            x={'output_root':str(root),'runtime':rt,'request':{}}
            receipt=r.tagged({'schema_id':'CLEAN_SEEDED_LORA_INITIALIZATION_RECEIPT_V1','status':'PASS','training_executed':False,'optimizer_step_count':0,
                'training_plan_sha256':data['plan']['training_plan_sha256'],'seed':17,'base_binding':base,'source_code_root_sha256':'c'*64,
                'lora_a_nonzero':True,'lora_b_all_zero':True,'base_parameters_frozen':True,'repeat_seed_parameter_hash_equal':True,'saved_adapter_reload_hash_equal':True,
                'enabled_vs_disabled_logits_exact_equal':True,'logits_finite':True,'initial_trainable_parameter_sha256':'d'*64,'repeat_initial_trainable_parameter_sha256':'d'*64,
                'reloaded_trainable_parameter_sha256':'d'*64,'adapter_path':str(init),'adapter_manifest_path':str(root/'SEED_ZERO_ADAPTER_MANIFEST.json'),
                'adapter_manifest_sha256':a.file_sha(root/'SEED_ZERO_ADAPTER_MANIFEST.json'),'adapter_bundle_sha256':'b'*64},'initialization_receipt_sha256')
            r.put(root/'INITIALIZATION_RECEIPT.json',receipt)
            # Only imports for APIs that cannot execute in this preflight are stubs.
            peft=types.ModuleType('peft');peft.LoraConfig=object;peft.get_peft_model=lambda *x:(_ for _ in ()).throw(AssertionError('NO_MODEL_EXECUTION'))
            transformers=types.ModuleType('transformers');transformers.AutoModelForCausalLM=object;transformers.get_linear_schedule_with_warmup=object
            with patch.dict(sys.modules,{'peft':peft,'transformers':transformers}),patch.object(r,'load_source',return_value=data),patch.object(r,'checked_request',return_value=x):
                binding=r.compile_binding(x,receipt)
                ctx=contracts.load_stage_context(root/'TRAINING_STAGE_BINDING.json')
                old_adapter=a._configured_legacy(ctx);parent=old_adapter._load_parent_module(ctx.training_contract)
                old_adapter._install_parent_adapter(parent,context=ctx)
                # Calls the full replacement validator (not a skipped assertion).
                parent.verify_formal_schedule()
                self.assertEqual(len(parent.build_formal_run_plan(seed=17)),13)
                parent.FORMAL_EFFECTIVE_BATCH=4
                with self.assertRaisesRegex(ValueError,'FORMAL_EFFECTIVE_BATCH_DRIFT'):parent.verify_formal_schedule()
                parent.FORMAL_EFFECTIVE_BATCH=1
                self.assertIsNotNone(parent.execute_training_plan.__code__)
                r.authorize_training(root,binding['stage_binding_sha256'])
                contracts.load_execution_authorization(root/'TRAINING_AUTHORIZATION.json',context=ctx,runner_freeze_root_sha256='c'*64)
                with self.assertRaisesRegex(ValueError,'EXACT_TRAINING_BINDING'):r.authorize_training(root,'f'*64)
                self.assertFalse((root/'training_outputs').exists())
                out=json.loads((root/'TRAINING_CONTRACT.json').read_bytes())
                self.assertEqual(out['budget'],data['contract']['budget'])
                self.assertEqual(out['optimization'],data['contract']['optimization'])
                self.assertFalse(out['parent']['pilot_adapter_reuse_allowed'])
                self.assertEqual(out['parent']['adapter_path'],str(init))

if __name__=='__main__':unittest.main()
