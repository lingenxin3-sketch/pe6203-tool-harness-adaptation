"""Replay saved real evidence without invoking a model or claiming a live run."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def demo(run, task, version):
    manifest = read(run/'manifest.json')
    if task not in manifest['task_ids'] or version not in manifest['config']['versions']:
        raise ValueError('Task or version is outside this saved experiment')
    print('SAVED EVIDENCE REPLAY - not a new live experiment')
    print(f'Task {task} | {version} | source: {run}')
    print('Scores are displayed only when the recorded judge has completed.\n')
    for strategy in manifest['config']['strategies']:
        path = run/'repeat-0'/strategy/version/str(task)/'result.json'
        print(f'--- {strategy} ---')
        if not path.exists():
            print('This episode has not been recorded yet.\n')
            continue
        record = read(path)
        print('Question:', record['question'].strip())
        adaptation = record['adaptation']
        print('Update status:', adaptation['status'])
        print('Regenerated notes:', ', '.join(adaptation.get('regenerated', [])) or '(none)')
        call_count = 0
        for message in record['trajectory_messages']:
            for call in message.get('tool_calls', []):
                call_count += 1
                function = call['function']
                print(f'  Call {call_count}: {function["name"]}')
                arguments = function['arguments']
                if not isinstance(arguments, str):
                    arguments = json.dumps(arguments, ensure_ascii=False)
                print('   ', arguments[:400] + (' ... [see raw record]' if len(arguments) > 400 else ''))
        for error in record.get('tool_errors', []):
            print('  TOOL ERROR:', json.dumps(error['result'], ensure_ascii=False)[:500])
        print('Actual file changes:', json.dumps(record['artifact_changes'], ensure_ascii=False))
        if record.get('status') == 'evaluated':
            scores = record['eval_result']['aggregate']
            print('Local rubric scores: TF', scores['task_fulfillment_mean'], 'PE', scores['planning_and_efficiency_mean'])
        else:
            print('Recorded status:', record.get('status'), '(no final score)')
        update_calls = record['model_calls']['update']
        print('Update tokens:', sum(c['usage'].get('total_tokens', 0) for c in update_calls))
        print('Evidence:', path)
        print()
    print('Read actual artifact content before judging semantic success; file creation alone is insufficient.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, default=ROOT/'runs/final-v1')
    parser.add_argument('--task', type=int, default=28)
    parser.add_argument('--version', choices=['original', 'iter3', 'iter5'], default='iter3')
    args = parser.parse_args()
    demo(args.run.resolve(), args.task, args.version)
