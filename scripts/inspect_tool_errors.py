"""Index explicit MCP and structured payload errors without changing scores.

An errored call can be recovered later; this is not a task-failure classifier.
Text log lines mentioning errors are not automatically classified as tool errors.
"""
import argparse
from collections import Counter
import json
from pathlib import Path


def indicators(result):
    found = []
    if result.get('isError') is True:
        found.append('mcp_isError')
    for block in result.get('content', []):
        if block.get('type') != 'text':
            continue
        try:
            payload = json.loads(block.get('text', ''))
        except (ValueError, TypeError):
            continue
        if not isinstance(payload, dict):
            continue
        if str(payload.get('status', '')).lower() in {'error', 'failed', 'failure'}:
            found.append('payload_status_error')
        if payload.get('success') is False:
            found.append('payload_success_false')
        if payload.get('error'):
            found.append('payload_error_field')
    return sorted(set(found))


def inspect(folder):
    failures, episodes, count = [], [], 0
    for path in sorted(folder.glob('repeat-*/*/*/*/result.json')):
        record = json.loads(path.read_text(encoding='utf-8'))
        calls, flagged, hidden = {}, 0, 0
        for position, message in enumerate(record.get('trajectory_messages', [])):
            for call in message.get('tool_calls', []):
                calls[call['id']] = call['function']
            if message.get('role') != 'tool':
                continue
            count += 1
            try:
                result = json.loads(message['content'])
            except (ValueError, TypeError):
                continue
            if not isinstance(result, dict):
                continue
            signs = indicators(result)
            if not signs:
                continue
            flagged += 'mcp_isError' in signs
            hidden += 'mcp_isError' not in signs
            failures.append({'idx': record['idx'], 'strategy': record['strategy'], 'version': record['version'],
                             'repeat': record['repeat'], 'message_index': position, 'indicators': signs,
                             'call': calls.get(message.get('tool_call_id')), 'result': result,
                             'source': path.relative_to(folder).as_posix()})
        episodes.append({'idx': record['idx'], 'strategy': record['strategy'], 'version': record['version'],
                         'repeat': record['repeat'], 'mcp_flagged_calls': flagged,
                         'additional_structured_error_calls': hidden})
    report = {'episodes_inspected': len(episodes), 'tool_results_inspected': count,
              'indicator_counts': dict(Counter(sign for failure in failures for sign in failure['indicators'])),
              'episodes': episodes, 'calls': failures,
              'scope': 'Explicit error flags and top-level structured status only; may miss prose errors. '
                       'Errored calls do not imply final task failure. Scores are unchanged.'}
    destination = folder/'analysis/tool-error-review.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    args = parser.parse_args()
    result = inspect(args.run_directory.resolve())
    print(json.dumps({key: value for key, value in result.items() if key not in {'episodes', 'calls'}}, indent=2))
