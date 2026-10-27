"""Narrow, deterministic persistence checks for the two reviewed case studies.

These checks are supplementary facts, not replacements for TF or PE and not a
representative accuracy estimate. Task wording/content still needs inspection.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re


def inspect(folder):
    rows = []
    for path in sorted(folder.glob('repeat-*/*/*/*/result.json')):
        record = json.loads(path.read_text(encoding='utf-8'))
        if record['idx'] not in {28, 113}:
            continue
        workspace = (path.parent/'workspace').resolve()
        changes = record.get('artifact_changes', {})
        changed = set(changes.get('created', [])) | set(changes.get('modified', []))
        artifacts, task_count = [], 0
        for relative in sorted(changed):
            file = (workspace/relative).resolve()
            if not file.is_relative_to(workspace) or not file.is_file():
                raise ValueError('Recorded artifact missing or outside workspace: '+relative)
            count = 0
            if record['idx'] == 28 and file.name == 'tasks.md':
                content = file.read_text(encoding='utf-8')
                count = len(re.findall(r'^\s*-\s+\[[ xX]\]\s+\S', content, flags=re.MULTILINE))
            elif record['idx'] == 113 and relative in {'tasks.json', '.agentic-tools-mcp/tasks/tasks.json'}:
                content = json.loads(file.read_text(encoding='utf-8'))
                direct = content.get('tasks', [])
                count = len(direct) if isinstance(direct, list) else 0
                count += sum(len(request.get('tasks', [])) for request in content.get('requests', []))
            if count:
                task_count += count
                artifacts.append({'file': relative, 'stored_tasks': count})
        scores = record.get('eval_result', {}).get('aggregate', {})
        rows.append({'idx': record['idx'], 'strategy': record['strategy'], 'version': record['version'],
                     'repeat': record['repeat'], 'required_task_persistence_observed': bool(task_count),
                     'stored_task_entries': task_count, 'artifacts': artifacts,
                     'local_tf': scores.get('task_fulfillment_mean'),
                     'tf_10_without_observed_required_persistence': None if scores.get('task_fulfillment_mean') is None
                         else scores['task_fulfillment_mean'] == 10 and not task_count,
                     'source': path.relative_to(folder).as_posix()})
    totals = defaultdict(lambda: {'episodes': 0, 'scored_episodes': 0, 'persistence_observed': 0, 'tf_10_without_persistence': 0})
    for row in rows:
        group = totals[(row['idx'], row['strategy'])]
        group['episodes'] += 1
        group['scored_episodes'] += row['local_tf'] is not None
        group['persistence_observed'] += row['required_task_persistence_observed']
        group['tf_10_without_persistence'] += row['tf_10_without_observed_required_persistence'] is True
    for values in totals.values():
        if values['scored_episodes'] != values['episodes']:
            values['tf_10_without_persistence'] = None
    report = {'selection': 'Tasks28 and113 were chosen as diagnostic failure case studies after inspecting execution, before judge scores. Not a random sample.',
              'criteria': {'28': 'Created/modified tasks.md contains at least one Markdown task entry.',
                           '113': 'Created/modified known task-manager state contains at least one saved task, not just an empty project.'},
              'limitations': 'Persistence does not prove task-content correctness, actual implementation or human approval. '
                             'Multiple stored entries may describe overlapping tasks. No general benchmark success rate is inferred.',
              'judge_comparison_complete': len(rows) == 18 and all(row['local_tf'] is not None for row in rows),
              'rows': rows, 'totals': [{'idx': idx, 'strategy': strategy, **values}
                                     for (idx, strategy), values in sorted(totals.items())]}
    output = folder/'analysis/artifact-review.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    args = parser.parse_args()
    result = inspect(args.run_directory.resolve())
    print(json.dumps({'reviewed': len(result['rows']), 'totals': result['totals'],
                      'limitations': result['limitations']}, indent=2))
