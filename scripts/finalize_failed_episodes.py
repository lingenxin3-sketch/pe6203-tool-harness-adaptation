"""Recover recorded partial trajectories for scoring, never retry an episode.

The original infrastructure-failure record is retained verbatim. Only evidence
already present in incremental events/model requests is assembled for the judge.
An empty or inconsistent trace is refused, not synthesized or assigned a score.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tool_adapt.agent import file_snapshot, file_changes
from tool_adapt.experiment import scoped_tools, save


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def assemble(path):
    raw = read(path)
    if raw.get('status') != 'infrastructure_error':
        return None
    events_path = path.with_name('events.jsonl')
    events = [json.loads(line) for line in events_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    calls = raw.get('model_calls', {}).get('agent', [])
    starts = [event['payload'] for event in events if event['kind'] == 'start']
    responses = [event for event in events if event['kind'] == 'model_response']
    if len(starts) != 1 or not calls or len(responses) != len(calls):
        raise ValueError(f'Insufficient or inconsistent raw evidence: {path}')
    first_messages = calls[0]['request']['messages']
    if len(first_messages) != 2 or [m['role'] for m in first_messages] != ['system', 'user']:
        raise ValueError('Initial context is not the recorded system/task pair')
    if first_messages[1]['content'] != raw['question']:
        raise ValueError('Recorded question mismatch')
    messages = deepcopy(first_messages)
    added_users = set()
    errors, known_calls = [], {}
    for event in events:
        payload = event['payload']
        if event['kind'] == 'model_response':
            step = payload['step']
            call = calls[step]
            if payload['message'] != call['response']['choices'][0]['message']:
                raise ValueError('Incremental event differs from saved model response')
            # A runtime verification message is not separately logged as an event,
            # but is present verbatim in the subsequent recorded model request.
            for message in call['request']['messages'][2:]:
                if message['role'] == 'user' and message['content'] not in added_users:
                    messages.append(deepcopy(message))
                    added_users.add(message['content'])
            messages.append(deepcopy(payload['message']))
            for tool_call in payload['message'].get('tool_calls', []):
                known_calls[tool_call['id']] = tool_call
        elif event['kind'] == 'tool_result':
            tool_call = payload['call']
            if known_calls.get(tool_call['id']) != tool_call:
                raise ValueError('Tool result has no matching recorded call')
            messages.append({'role': 'tool', 'tool_call_id': tool_call['id'],
                             'content': json.dumps(payload['result'], ensure_ascii=False, sort_keys=True, separators=(',', ':'))})
            if payload['result'].get('isError'):
                errors.append({'step': payload['step'], 'tool': tool_call['function']['name'], 'result': payload['result']})
    manifest = read(path.parents[4]/'manifest.json')
    inventories = {v: read(ROOT/'artifacts/inventory'/f'{v}.json') for v in manifest['config']['versions']}
    result = deepcopy(raw)
    observed_answers = [m.get('content') or '' for m in messages if m['role'] == 'assistant' and not m.get('tool_calls')]
    if 'trajectory_messages' in raw and raw['trajectory_messages'] != messages:
        raise ValueError('Recovered events disagree with already saved trajectory')
    result.update({'trajectory_messages': messages, 'answer': raw.get('answer', observed_answers[-1] if observed_answers else ''),
                   'stop': raw.get('stop', False), 'exceeded': raw.get('exceeded', len(calls) >= manifest['config']['max_steps']),
                   'tool_errors': errors, 'agent_usage': [c['usage'] for c in calls],
                   'wall_seconds': raw.get('wall_seconds'),
                   'artifact_changes': raw.get('artifact_changes') or file_changes(starts[0]['initial_files'], file_snapshot(path.parent/'workspace')),
                   'evaluation_tools': scoped_tools(raw, inventories[raw['version']], inventories['original']),
                   'status': 'awaiting_judge', 'execution_status': 'infrastructure_error',
                   'terminal_reason': raw['error'],
                   'failure_evidence_recovery': {
                       'method': 'Recorded incremental events plus recorded model-request user messages; no rerun or invented action.',
                       'original_record_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                       'events_sha256': hashlib.sha256(events_path.read_bytes()).hexdigest(),
                       'original_record': 'failure-record.json',
                       'wall_time_limitation': 'Whole-episode timer was not returned after the exception; request timings remain recorded.'}})
    return result


def finalize(folder, apply=False):
    handled = []
    for path in sorted(folder.glob('repeat-*/*/*/*/result.json')):
        result = assemble(path)
        if result is None:
            continue
        receipt = path.with_name('failure-record.json')
        if apply:
            if receipt.exists():
                if receipt.read_bytes() != path.read_bytes():
                    raise ValueError('Existing failure receipt differs; refusing overwrite')
            else:
                receipt.write_bytes(path.read_bytes())
            save(path, result)
        handled.append({'idx': result['idx'], 'strategy': result['strategy'], 'version': result['version'],
                        'messages': len(result['trajectory_messages']), 'answer_present': bool(result['answer']),
                        'artifact_changes': result['artifact_changes'], 'applied': apply,
                        'execution_status': result['execution_status']})
    return handled


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    print(json.dumps(finalize(args.run_directory.resolve(), apply=args.apply), indent=2))
