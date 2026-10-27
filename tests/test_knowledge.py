import unittest
from copy import deepcopy
from tool_adapt.knowledge import Knowledge, adapt, detect_changes, normalize_tools


def tool(name, description='', **properties):
    return {'name': name, 'description': description,
            'inputSchema': {'type': 'object', 'properties': properties}}


def fake_notes(instruction, payload):
    # Test-only stub. Never produces claimed benchmark outcomes.
    import json
    obj = json.loads(payload)
    return {name: 'Updated ' + name for name in obj['requested_tools']}, {'test_stub': True}


class AdaptationTests(unittest.TestCase):
    def setUp(self):
        self.old = Knowledge.initial([tool('read'), tool('write', 'Use read before write'), tool('sum')])

    def test_parameter_change_and_dependency(self):
        current = [tool('read', path={'type': 'string'}), tool('write', 'Use read before write'), tool('sum')]
        result, audit = adapt(self.old, current, 'selective_patch', fake_notes, version='Middle')
        self.assertEqual(audit['regenerated'], ['read', 'write'])
        self.assertEqual(result.notes['sum'], self.old.notes['sum'])

    def test_description_only_change(self):
        changes = detect_changes(self.old, normalize_tools([tool('read', 'Returns ISO dates'), tool('write', 'Use read before write'), tool('sum')]))
        self.assertIn('read', changes.modified)

    def test_rename_as_delete_and_add(self):
        result, audit = adapt(self.old, [tool('fetch'), tool('write', 'Use fetch before write'), tool('sum')], 'selective_patch', fake_notes, version='Late')
        self.assertNotIn('read', result.tools)
        self.assertNotIn('read', result.notes)
        self.assertIn('fetch', audit['changes']['added'])

    def test_no_update_is_byte_equivalent(self):
        result, _ = adapt(self.old, [tool('new')], 'no_update', None, version='Late')
        self.assertEqual(result.to_dict(), self.old.to_dict())

    def test_full_rewrite_includes_unchanged(self):
        _, audit = adapt(self.old, list(self.old.tools.values()), 'full_rewrite', fake_notes, version='Middle')
        self.assertEqual(audit['regenerated'], ['read', 'sum', 'write'])

    def test_no_change_avoids_model_call(self):
        result, audit = adapt(self.old, list(self.old.tools.values()), 'selective_patch', None, version='Middle')
        self.assertEqual(audit['updated_note_count'], 0)

    def test_invalid_update_does_not_mutate_input(self):
        before = deepcopy(self.old.to_dict())
        with self.assertRaises(ValueError):
            adapt(self.old, [tool('new')], 'full_rewrite', lambda *a: ({'wrong': 'x'}, {}), version='Middle')
        self.assertEqual(before, self.old.to_dict())

    def test_dependency_closure_is_transitive(self):
        old = Knowledge.initial([tool('one'), tool('two', 'uses one'), tool('three', 'uses two')])
        changes = detect_changes(old, normalize_tools([tool('one', 'changed'), tool('two', 'uses one'), tool('three', 'uses two')]))
        self.assertEqual(changes.impacted, ['one', 'three', 'two'])

    def test_ablation_disables_dependency_closure(self):
        changes = detect_changes(self.old, normalize_tools([tool('read', 'changed'), tool('write', 'Use read before write'), tool('sum')]), dependency_closure=False)
        self.assertEqual(changes.impacted, ['read'])

    def test_duplicate_names_rejected(self):
        with self.assertRaises(ValueError):
            Knowledge.initial([tool('read'), tool('read')])


if __name__ == '__main__':
    unittest.main()
