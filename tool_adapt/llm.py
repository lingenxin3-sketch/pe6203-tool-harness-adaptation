"""OpenAI-compatible local inference, with complete usage and explicit failures."""
from __future__ import annotations
import json
from copy import deepcopy
import time
import urllib.request
from urllib.parse import urlparse


class LocalModel:
    def __init__(self, base_url='http://127.0.0.1:8081/v1', model='qwen3-4b', *, temperature=0.0,
                 max_tokens=2048, seed=6203, timeout=300):
        if urlparse(base_url).hostname not in {'127.0.0.1', 'localhost', '::1'}:
            raise ValueError('This project is configured for free local inference only')
        self.base_url, self.model = base_url.rstrip('/'), model
        self.temperature, self.max_tokens, self.seed, self.timeout = temperature, max_tokens, seed, timeout
        self.calls = []

    def _local_post(self, endpoint, body):
        server = self.base_url.removesuffix('/v1')
        request = urllib.request.Request(server + endpoint, data=json.dumps(body).encode(),
                                         headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.load(response)

    def fit_context(self, body, context_size=16384):
        """Exact local tokenizer; drop only complete old assistant/tool groups.

        The system instructions, original task and most recent interaction remain.
        Raw trajectories are kept separately by the agent; pruning is logged here.
        """
        body = deepcopy(body)
        removed = 0
        while True:
            rendered = self._local_post('/apply-template', body)['prompt']
            count = len(self._local_post('/tokenize', {'content': rendered, 'add_special': False})['tokens'])
            if count + self.max_tokens + 128 <= context_size:
                return body, {'prompt_tokens_checked': count, 'dropped_messages': removed}
            messages = body['messages']
            # Preserve the system and first user task, then find a complete older turn.
            start = next((i for i in range(2, len(messages)-1) if messages[i]['role']=='assistant'), None)
            if start is None:
                raise ValueError('Task and tool contracts exceed local context capacity')
            end = start + 1
            while end < len(messages) and messages[end]['role']=='tool':
                end += 1
            if end == len(messages):
                raise ValueError('Latest tool interaction exceeds local context capacity')
            removed += end-start
            del messages[start:end]

    def complete(self, messages, *, tools=None, json_mode=False):
        body = {'model': self.model, 'messages': messages, 'temperature': self.temperature,
                'max_tokens': self.max_tokens, 'seed': self.seed}
        if tools:
            body['tools'] = tools
            body['tool_choice'] = 'auto'
        if json_mode:
            body['response_format'] = {'type': 'json_object'}
        body, context_audit = self.fit_context(body)
        req = urllib.request.Request(self.base_url + '/chat/completions',
            data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
        started = time.perf_counter()
        # No silent retries: each request has one accountable trace record.
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            payload = json.load(response)
        usage = dict(payload.get('usage', {}))
        usage['wall_seconds'] = time.perf_counter() - started
        usage['api_usd'] = 0.0
        usage['cost_scope'] = 'local inference; electricity and hardware not monetized'
        self.calls.append({'request': body, 'response': payload, 'usage': usage, 'context': context_audit})
        return payload['choices'][0]['message'], usage

    def generate_notes(self, instruction, data):
        message, usage = self.complete([{'role': 'system', 'content': instruction},
                                       {'role': 'user', 'content': data}], json_mode=True)
        return json.loads(message['content']), usage
