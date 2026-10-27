"""Fixed agent loop: all strategies differ only in their tool knowledge."""
from __future__ import annotations
import asyncio
import json
import time
import hashlib
from .knowledge import Knowledge, canonical


def file_snapshot(workspace):
    result = {}
    for path in workspace.rglob('*'):
        if path.is_file() and not path.name.endswith('.stderr.log'):
            try:
                result[str(path.relative_to(workspace)).replace('\\', '/')] = hashlib.sha256(path.read_bytes()).hexdigest()
            except OSError:
                # Original very-long fixture names may exceed legacy Windows APIs.
                continue
    return result


def file_changes(before, after):
    return {'created': sorted(set(after)-set(before)), 'deleted': sorted(set(before)-set(after)),
            'modified': sorted(name for name in before.keys() & after.keys() if before[name] != after[name])}


async def run_agent(model, runtime, knowledge: Knowledge, question: str, *, max_steps=12, event_path=None):
    def event(kind, payload):
        if event_path is not None:
            with event_path.open('a',encoding='utf-8') as handle:
                handle.write(canonical({'kind':kind,'payload':payload})+'\n')
    files = sorted(str(p.relative_to(runtime.workspace)).replace('\\', '/')
                   for p in runtime.workspace.rglob('*') if p.is_file() and not p.name.endswith('.log'))
    system = (
        'You are an AI agent using MCP tools. Complete the user request by calling tools. '
        'Do not ask the user questions. Do not claim actions you have not performed. '
        'All file operations must stay within the experiment workspace. '
        f'The workspace is {runtime.workspace}. Relative paths refer to this workspace. '
        'Use the tool contracts and usage notes below. On a tool failure, inspect the error before retrying. '
        'Before your final answer, check every explicit user requirement. If a file, task, project or memory '
        'must be created, actually call the corresponding tool and check its result; describing it is not completion. '
        'When finished, give a concise evidence-grounded answer.\n'
        'Existing resource files (use these exact paths, never guess filenames):\n' + '\n'.join(files) +
        '\nUsage notes:\n' + canonical(knowledge.notes))
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': question}]
    before = file_snapshot(runtime.workspace)
    event('start', {'question':question, 'initial_files':before})
    tools = [{'type': 'function', 'function': {'name': t['name'], 'description': t['description'],
              'parameters': t['inputSchema']}} for t in knowledge.tools.values()]
    start, usages, errors = time.perf_counter(), [], []
    finished, answer, verified = False, '', False
    for step in range(max_steps):
        message, usage = await asyncio.to_thread(model.complete, messages, tools=tools)
        usages.append(usage)
        messages.append(message)
        event('model_response', {'step':step,'message':message,'usage':usage})
        calls = message.get('tool_calls') or []
        if not calls:
            if not verified and step < max_steps - 1:
                verified = True
                changes = file_changes(before, file_snapshot(runtime.workspace))
                messages.append({'role': 'user', 'content':
                    'Runtime verification before accepting your final answer. Actual file changes since task start: '
                    + canonical(changes) + '. A claim that you saved or created something is not execution evidence. '
                    'Recheck the ORIGINAL request. If any required action is missing, use the available tools now. '
                    'If it is impossible, explain the unmet requirement honestly. Do not ask the user to act.'})
                continue
            answer = message.get('content') or ''
            finished = True
            break
        for call in calls:
            function = call['function']
            try:
                arguments = json.loads(function['arguments']) if isinstance(function['arguments'], str) else function['arguments']
                if not isinstance(arguments, dict):
                    raise ValueError('Tool arguments must be a JSON object')
                result = await runtime.call(function['name'], arguments)
            except (ValueError, TypeError) as exc:
                result = {'isError': True, 'content': [{'type': 'text', 'text': str(exc)}]}
            if result.get('isError'):
                errors.append({'step': step, 'tool': function['name'], 'result': result})
            messages.append({'role': 'tool', 'tool_call_id': call['id'], 'content': canonical(result)})
            event('tool_result', {'step':step,'call':call,'result':result})
    return {'question': question, 'answer': answer, 'trajectory_messages': messages,
            'stop': finished, 'exceeded': not finished, 'tool_errors': errors,
            'agent_usage': usages, 'wall_seconds': time.perf_counter() - start,
            'artifact_changes': file_changes(before, file_snapshot(runtime.workspace))}
