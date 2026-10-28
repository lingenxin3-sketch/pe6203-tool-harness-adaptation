"""Synthetic protocol tests, with no model calls or benchmark score claims."""
from pathlib import Path
import json
import tempfile
import unittest
import sys
from unittest.mock import patch
from scripts.repeat_common import inspect,metrics,merge_views,save,compatibility
from scripts.repeat_runner import resume_record,build_runner,validate_manifest_save
from tool_adapt.knowledge import digest
import scripts.repeat_campaign as campaign
import scripts.repeat_publish as publisher

class RepeatTests(unittest.TestCase):
    def setUp(self):
        parent=Path(__file__).resolve().parents[1]/'runtime/test-fixtures';parent.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=parent);self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.m={'config':{'repeats':1,'strategies':['no_update','full_rewrite','selective_patch'],'versions':['original','iter3','iter5']},'task_ids':list(range(18)),
            'coverage':[{'idx':i,'version':v,'affected':v!='original'} for i in range(18) for v in ['original','iter3','iter5']],'source_hashes':{},'inventory_hashes':{},'split':'test'}
    def make(self,name):
        folder=self.root/name;save(folder/'manifest.json',self.m)
        for pol in self.m['config']['strategies']:
            for v in self.m['config']['versions']:
                for i in self.m['task_ids']:
                    r={'repeat':0,'strategy':pol,'version':v,'idx':i,'question':'synthetic','manifest_hash':digest(self.m),'knowledge':{'tools':{},'notes':{'a':'unchanged'}},
                       'status':'evaluated','eval_result':{'valid':True,'aggregate':{'task_fulfillment_mean':7,'planning_and_efficiency_mean':8}},'model_calls':{'update':[],'agent':[{'request':{'messages':[{'role':'system','content':'Existing resource files (use these exact paths, never guess filenames):\na.txt\nUsage notes: synthetic'}]},'usage':{'total_tokens':10,'wall_seconds':1,'api_usd':0}}],'judge':[]}}
                    save(folder/f'repeat-0/{pol}/{v}/{i}/result.json',r)
        return folder
    def test_complete_three_round_identity_and_sources(self):
        fs=[self.make(n) for n in ['old','r2','r3']];result=merge_views(fs)
        self.assertEqual(result['total_records'],486);self.assertEqual(len(result['rounds']),3)
        self.assertEqual([r['name'] for r in result['rounds']],['old','r2','r3'])
        self.assertEqual(len({r['source_manifest_sha256'] for r in result['rounds']}),1)
        self.assertEqual(result['strategies'][0]['stages']['original']['task_count'],18)
        self.assertEqual(result['strategies'][0]['stages']['original']['observations'],54)
    def test_missing_and_unscored_refuse_final(self):
        f=self.make('r2');p=f/'repeat-0/no_update/original/0/result.json';r=json.loads(p.read_text());r['status']='awaiting_judge';save(p,r)
        self.assertEqual(inspect(f)['scored'],161)
        with self.assertRaises(ValueError):metrics(f)
        p.unlink();self.assertEqual(inspect(f)['missing'],1)
    def test_duplicate_and_path_mismatch_rejected(self):
        f=self.make('r2');r=json.loads((f/'repeat-0/no_update/original/0/result.json').read_text());save(f/'repeat-0/no_update/original/999/result.json',r)
        self.assertFalse(inspect(f)['complete']);self.assertTrue(inspect(f)['issues'])
    def test_failed_execution_remains_in_complete_scored_grid(self):
        f=self.make('r2');p=f/'repeat-0/no_update/original/0/result.json';r=json.loads(p.read_text());r['execution_status']='infrastructure_error';save(p,r)
        self.assertTrue(inspect(f)['complete']);self.assertEqual(inspect(f)['failures'],1)
    def test_incompatible_and_duplicate_round_sources_refused(self):
        a=self.make('old');b=self.make('r2');m=json.loads((b/'manifest.json').read_text());m['config']['seed']=999;save(b/'manifest.json',m)
        with self.assertRaises(ValueError):merge_views([a,b])
        with self.assertRaises(ValueError):merge_views([a,a])
    def test_resume_restores_knowledge_and_preserves_bytes(self):
        f=self.make('r2');p=f/'repeat-0/no_update/original/0/result.json';raw=p.read_bytes()
        k=resume_record(f,0,'no_update','original',{'idx':0,'question':'synthetic'},self.m)
        self.assertEqual(k.notes,{'a':'unchanged'});self.assertEqual(p.read_bytes(),raw)
        self.assertIsNone(resume_record(f,0,'no_update','original',{'idx':18,'question':'synthetic'},self.m))
        (f/'repeat-0/no_update/original/18/workspace').mkdir(parents=True)
        with self.assertRaisesRegex(ValueError,'no committed result'):resume_record(f,0,'no_update','original',{'idx':18,'question':'synthetic'},self.m)
    def test_resume_manifest_never_overwritten(self):
        p=self.root/'manifest.json';save(p,self.m);raw=p.read_bytes();validate_manifest_save(p,self.m)
        self.assertEqual(raw,p.read_bytes())
        with self.assertRaises(ValueError):validate_manifest_save(p,{'different':True})
    def test_resume_adapter_builds_against_frozen_runner(self):self.assertTrue(callable(build_runner()))
    def test_first_round_failure_or_upload_failure_stops_second(self):
        from unittest.mock import MagicMock
        with patch.object(campaign,'ROOT',self.root),patch.object(campaign,'RUNTIME',self.root/'runtime'),patch.object(campaign,'acquire',return_value=MagicMock()),patch.object(campaign,'read',return_value={'compatible_preconditions':True,'passed':True,'actual_resume_skip_verified':True,'audit':{'complete_and_evaluated':True}}),patch.object(campaign,'state'),patch.object(campaign,'verified_status'),patch.object(campaign.threading,'Thread'),patch.object(campaign.ctypes.windll.kernel32,'SetThreadExecutionState',return_value=1),patch.object(campaign,'run_round',side_effect=RuntimeError('upload failed')) as run,patch.object(sys,'argv',['repeat_campaign.py']):
            with self.assertRaisesRegex(RuntimeError,'upload failed'):campaign.main()
            run.assert_called_once_with(1,False)
        campaign.STOP.clear()
    def test_success_without_verified_gate_still_cannot_start_second(self):
        from unittest.mock import MagicMock
        with patch.object(campaign,'ROOT',self.root),patch.object(campaign,'RUNTIME',self.root/'runtime'),patch.object(campaign,'acquire',return_value=MagicMock()),patch.object(campaign,'read',return_value={'compatible_preconditions':True,'passed':True,'actual_resume_skip_verified':True,'audit':{'complete_and_evaluated':True}}),patch.object(campaign,'state'),patch.object(campaign,'verified_status'),patch.object(campaign.threading,'Thread'),patch.object(campaign.ctypes.windll.kernel32,'SetThreadExecutionState',return_value=1),patch.object(campaign,'run_round') as run,patch.object(sys,'argv',['repeat_campaign.py']):
            with self.assertRaisesRegex(RuntimeError,'publication gate missing'):campaign.main()
            run.assert_called_once_with(1,False)
        campaign.STOP.clear()
    def test_publish_whitelist_and_sensitive_check(self):
        self.assertFalse(publisher.allowed('dashboard/server.py'));self.assertFalse(publisher.allowed('runs/final-v1/manifest.json'))
        self.assertTrue(publisher.allowed('docs/追加实验/状态.md'))
        self.assertTrue(publisher.sensitive(b'ghp_'+b'a'*36));self.assertFalse(publisher.sensitive(b'http://127.0.0.1:8081/v1'))
    def test_transient_metadata_lock_retries_same_bytes_only(self):
        original=Path.replace;calls=[]
        def replace(path,target):
            calls.append(path)
            if len(calls)==1:raise PermissionError('Synthetic temporary reader lock')
            return original(path,target)
        target=self.root/'metadata.json'
        with patch.object(Path,'replace',new=replace):save(target,{'phase':'testing'})
        self.assertEqual(len(calls),2);self.assertEqual(calls[0],calls[1])
        self.assertEqual(json.loads(target.read_text()),{'phase':'testing'})
    def test_same_manifest_but_changed_resource_visibility_refuses_merge(self):
        a=self.make('old');b=self.make('r2');p=b/'repeat-0/full_rewrite/original/0/result.json';r=json.loads(p.read_text());r['model_calls']['agent'][0]['request']['messages'][0]['content']='Existing resource files (use these exact paths, never guess filenames):\nb.txt\nUsage notes: synthetic';save(p,r)
        with self.assertRaisesRegex(ValueError,'resource lists differ'):merge_views([a,b])
    def test_second_round_path_must_be_predeclared_before_model_switch(self):
        with patch.object(campaign,'read',return_value={'output_name':'unapproved-directory'}),patch.object(campaign,'model') as model:
            with self.assertRaisesRegex(RuntimeError,'predeclaration not verified'):campaign.run_round(2)
            model.assert_not_called()
    def test_evidence_package_retains_failure_and_closed_phase_logs(self):
        import zipfile
        folder=self.root/'runs/synthetic-scored';m={'config':{'repeats':1,'strategies':['no_update'],'versions':['original']},'task_ids':[1]};save(folder/'manifest.json',m)
        episode=folder/'repeat-0/no_update/original/1';row={'repeat':0,'strategy':'no_update','version':'original','idx':1,'status':'evaluated','execution_status':'infrastructure_error','eval_result':{'valid':True,'aggregate':{'task_fulfillment_mean':2,'planning_and_efficiency_mean':3}}}
        for name in ['result.json','agent-record.json','failure-record.json']:save(episode/name,row)
        (episode/'events.jsonl').write_text('{}\n');(episode/'workspace').mkdir();(episode/'workspace/abc.stderr.log').write_text('synthetic server error')
        runtime=self.root/'runtime'/publisher.CAMPAIGN;runtime.mkdir(parents=True);(runtime/'synthetic-scored-execution.log').write_text('synthetic execution error')
        with patch.object(publisher,'ROOT',self.root),patch.object(publisher,'RECEIPTS',self.root/'receipts'):
            archive=publisher.package(folder)
        with zipfile.ZipFile(archive) as z:
            self.assertIn('runs/synthetic-scored/repeat-0/no_update/original/1/workspace/abc.stderr.log',z.namelist())
            self.assertIn(f'runtime/{publisher.CAMPAIGN}/synthetic-scored-execution.log',z.namelist())

if __name__=='__main__':unittest.main()
