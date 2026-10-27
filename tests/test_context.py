import unittest
from tool_adapt.llm import LocalModel


class ContextTests(unittest.TestCase):
    def test_prunes_complete_old_turn_preserving_task(self):
        model=LocalModel(max_tokens=10)
        def local(endpoint, body):
            if endpoint=='/apply-template':
                return {'prompt':str(len(body['messages']))}
            return {'tokens':[1] * (int(body['content'])*100)}
        model._local_post=local
        messages=[{'role':'system','content':'rules'},{'role':'user','content':'original task'},
                  {'role':'assistant','tool_calls':[{'id':'old'}]},
                  {'role':'tool','tool_call_id':'old','content':'old output'},
                  {'role':'assistant','tool_calls':[{'id':'new'}]},
                  {'role':'tool','tool_call_id':'new','content':'new output'}]
        body,audit=model.fit_context({'messages':messages},context_size=550)
        self.assertEqual(audit['dropped_messages'],2)
        self.assertEqual(body['messages'][:2],messages[:2])
        self.assertEqual(body['messages'][2:],messages[4:])
        self.assertEqual(len(messages),6)

    def test_cannot_silently_truncate_original_task(self):
        model=LocalModel(max_tokens=10)
        model._local_post=lambda endpoint,body: {'prompt':'x'} if endpoint=='/apply-template' else {'tokens':[1]*1000}
        with self.assertRaises(ValueError):
            model.fit_context({'messages':[{'role':'user','content':'large original task'}]},context_size=500)


if __name__=='__main__':
    unittest.main()
