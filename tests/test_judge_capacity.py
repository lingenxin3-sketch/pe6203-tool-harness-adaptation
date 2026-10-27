"""The judge-only amendment must not truncate evidence or change actor capacity."""
import unittest
from copy import deepcopy
from scripts.judge_with_capacity import expand_capacity
from tool_adapt.llm import LocalModel


class CapacityTests(unittest.TestCase):
    def model(self, tokens):
        model = LocalModel()
        model._local_post = lambda endpoint, body: ({'prompt': 'rendered'} if endpoint == '/apply-template'
                                                   else {'tokens': [1]*tokens})
        return model

    def test_long_judge_prompt_preserved_and_actor_limit_unchanged(self):
        body = {'messages': [{'role': 'user', 'content': 'Full official rubric and trajectory'}]}
        original = deepcopy(body)
        with self.assertRaises(ValueError):
            self.model(17885).fit_context(body)
        fitted, evidence = expand_capacity(self.model(17885), 24576).fit_context(body)
        self.assertEqual(fitted, original)
        self.assertEqual(body, original)
        self.assertEqual(evidence['dropped_messages'], 0)
        self.assertEqual(evidence['context_limit'], 24576)

    def test_amended_guard_still_rejects_an_oversized_single_prompt(self):
        body = {'messages': [{'role': 'user', 'content': 'Too long'}]}
        with self.assertRaises(ValueError):
            expand_capacity(self.model(24000), 24576).fit_context(body)


if __name__ == '__main__':
    unittest.main()
