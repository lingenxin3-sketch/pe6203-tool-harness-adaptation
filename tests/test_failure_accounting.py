"""Synthetic trace fixtures verify failure preservation; never benchmark scores."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.finalize_failed_episodes import assemble, finalize


class FailureAccountingTests(unittest.TestCase):
    def setUp(self):
        self.temp_parent = (Path(__file__).resolve().parents[1]/'runtime'/'test-fixtures').resolve()
        self.temp_parent.mkdir(parents=True, exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=self.temp_parent, prefix='failure-')
        self.addCleanup(self.safe_cleanup)
        self.root = Path(self.directory.name)
        self.run = self.root/'runs/synthetic-test'
        self.episode = self.run/'repeat-0/full_rewrite/iter5/1'
        (self.episode/'workspace').mkdir(parents=True)
        (self.root/'artifacts/inventory').mkdir(parents=True)
        for version in ['original', 'iter5']:
            self.write(self.root/f'artifacts/inventory/{version}.json', {})
        self.write(self.run/'manifest.json', {'config': {'versions': ['original', 'iter5'], 'max_steps': 12}})
        message = {'role': 'assistant', 'content': '', 'tool_calls': [
            {'id': 'synthetic-call', 'type': 'function', 'function': {'name': 'test_tool', 'arguments': '{"unfinished":'}}]}
        usage = {'total_tokens': 20, 'wall_seconds': 0.1, 'api_usd': 0}
        self.record = {'idx': 1, 'repeat': 0, 'strategy': 'full_rewrite', 'version': 'iter5',
                       'question': 'Synthetic fixture only', 'servers': {}, 'status': 'infrastructure_error',
                       'error': 'Synthetic template error', 'knowledge': {}, 'adaptation': {},
                       'model_calls': {'update': [], 'judge': [], 'agent': [{
                           'request': {'messages': [{'role': 'system', 'content': 'Synthetic system'},
                                                     {'role': 'user', 'content': 'Synthetic fixture only'}]},
                           'response': {'choices': [{'message': message, 'finish_reason': 'length'}]}, 'usage': usage}]}}
        self.path = self.episode/'result.json'
        self.write(self.path, self.record)
        self.events = [{'kind': 'start', 'payload': {'initial_files': {}}},
                       {'kind': 'model_response', 'payload': {'step': 0, 'message': message, 'usage': usage}},
                       {'kind': 'tool_result', 'payload': {'step': 0, 'call': message['tool_calls'][0],
                                                         'result': {'isError': True, 'content': [{'type': 'text', 'text': 'Invalid JSON'}]}}}]
        self.write_events()
        self.root_patch = patch('scripts.finalize_failed_episodes.ROOT', self.root)
        self.scope_patch = patch('scripts.finalize_failed_episodes.scoped_tools', return_value=[])
        self.root_patch.start(); self.scope_patch.start()
        self.addCleanup(self.root_patch.stop); self.addCleanup(self.scope_patch.stop)

    def safe_cleanup(self):
        target = Path(self.directory.name).resolve()
        if not target.is_relative_to(self.temp_parent) or target == self.temp_parent:
            raise ValueError('Refusing cleanup outside the dedicated test-fixture directory')
        self.directory.cleanup()

    def write(self, path, value):
        path.write_text(json.dumps(value), encoding='utf-8')

    def write_events(self):
        (self.episode/'events.jsonl').write_text('\n'.join(json.dumps(e) for e in self.events)+'\n', encoding='utf-8')

    def test_failed_attempt_preserved_and_not_converted_to_success(self):
        original = self.path.read_bytes()
        result = finalize(self.run, apply=True)
        self.assertEqual(len(result), 1)
        self.assertEqual((self.episode/'failure-record.json').read_bytes(), original)
        recovered = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertEqual(recovered['model_calls'], self.record['model_calls'])
        self.assertEqual(recovered['execution_status'], 'infrastructure_error')
        self.assertFalse(recovered['stop'])
        self.assertEqual(recovered['answer'], '')
        self.assertIsNone(recovered['wall_seconds'])
        self.assertNotIn('eval_result', recovered)
        self.assertEqual(recovered['failure_evidence_recovery']['original_record_sha256'], hashlib.sha256(original).hexdigest())
        self.assertEqual(finalize(self.run, apply=True), [])

    def test_inconsistent_event_cannot_be_promoted_or_overwrite_evidence(self):
        original = self.path.read_bytes()
        self.events[1]['payload']['message'] = {'role': 'assistant', 'content': 'Invented completion'}
        self.write_events()
        with self.assertRaisesRegex(ValueError, 'differs from saved model response'):
            finalize(self.run, apply=True)
        self.assertEqual(self.path.read_bytes(), original)
        self.assertFalse((self.episode/'failure-record.json').exists())


if __name__ == '__main__':
    unittest.main()
