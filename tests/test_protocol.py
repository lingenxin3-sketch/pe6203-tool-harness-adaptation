import json
from pathlib import Path
import tempfile
import unittest
from tool_adapt.knowledge import Knowledge, adapt
from tool_adapt.mcp_runtime import MCPRuntime, public_name
from tool_adapt.official import OfficialEvaluator
from tool_adapt.experiment import scoped_tools

ROOT = Path(__file__).resolve().parents[1]


class ProtocolTests(unittest.TestCase):
    def test_local_only_inference(self):
        from tool_adapt.llm import LocalModel
        with self.assertRaises(ValueError):
            LocalModel('https://paid-provider.example/v1')

    def test_file_boundary(self):
        runtime = MCPRuntime(ROOT, 'original', [], ROOT/'runtime'/'boundary-test')
        self.assertIsNone(runtime.path_violation({'paths': ['a.txt', 'nested/b.txt']}))
        self.assertIsNotNone(runtime.path_violation({'path': '../outside.txt'}))
        self.assertIsNotNone(runtime.path_violation({'destination': '../outside.txt'}))

    def test_task_scope_includes_new_not_unrelated_existing(self):
        def tool(name):
            return {'name': public_name('server', name), 'description': '', 'inputSchema': {}}
        early = {'server': {'status':'ok', 'tools':[tool('used'), tool('other')]}}
        current = {'server': {'status':'ok', 'tools':[tool('used'), tool('other'), tool('new')]}}
        selected = scoped_tools({'servers':{'server':['used']}}, current, early)
        self.assertEqual({t['name'] for t in selected}, {public_name('server','used'),public_name('server','new')})

    def test_updater_does_not_receive_task_answers(self):
        calls=[]
        def generator(system, payload):
            calls.append(json.loads(payload))
            return {'tool':'note'}, {}
        adapt(Knowledge.initial([]), [{'name':'tool','description':'Use this tool','inputSchema':{}}],
              'selective_patch',generator,version='Middle')
        self.assertEqual(set(calls[0]), {'requested_tools','current_contracts'})

    def test_official_ecs_formula_and_aggregation(self):
        official=OfficialEvaluator(ROOT/'upstream')
        row=official.ecs._compute_row('case',10,7,4)
        self.assertAlmostEqual(row.mean,7)
        self.assertAlmostEqual(row.stdev,6**0.5)
        result=official.functions['aggregate_eval_runs']([
            {'result': {'task_fulfillment':8,'grounding':9,'planning_and_efficiency':6}},
            {'result': {'error':'invalid'}},
            {'result': {'task_fulfillment':6,'grounding':7,'planning_and_efficiency':8}}])
        self.assertEqual(result['task_fulfillment_mean'],7)
        self.assertEqual(result['successful_runs'],2)

    def test_final_tasks_are_official_and_disjoint(self):
        config=json.loads((ROOT/'configs/experiment.json').read_text())
        chosen=json.loads((ROOT/'upstream/src/custom/data/test_cases/chosen_idx.json').read_text())
        ids={x['idx'] for x in chosen['samples']}
        self.assertTrue(set(config['test_ids']) <= ids)
        self.assertFalse(set(config['test_ids']) & set(config['development_ids']))
        self.assertEqual(len(config['test_ids']),len(set(config['test_ids'])))


if __name__=='__main__':
    unittest.main()
