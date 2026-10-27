"""Paired recovery/retention and independent arithmetic verification of complete runs."""
import argparse
import json
import math
from pathlib import Path
from statistics import mean


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def load_complete(folder):
    manifest = read(folder/'manifest.json')
    c = manifest['config']
    expected = {(rep, strategy, version, idx) for rep in range(c['repeats'])
                for strategy in c['strategies'] for version in c['versions'] for idx in manifest['task_ids']}
    rows = {}
    for path in folder.glob('repeat-*/*/*/*/result.json'):
        row = read(path)
        key = (row['repeat'], row['strategy'], row['version'], row['idx'])
        if key in rows or key not in expected:
            raise ValueError(f'Duplicate or unexpected row: {key}')
        if row.get('status') != 'evaluated' or not row.get('eval_result', {}).get('valid'):
            raise ValueError(f'Unscored/invalid row: {key}; do not analyze partial results as final')
        rows[key] = row
    if set(rows) != expected:
        raise ValueError(f'Missing {len(expected-set(rows))} required rows')
    return manifest, rows


def tf(row):
    return row['eval_result']['aggregate']['task_fulfillment_mean']


def pe(row):
    return row['eval_result']['aggregate']['planning_and_efficiency_mean']


def mean_or_none(values):
    return mean(values) if values else None


def change_categories(early, current):
    before = {t['name']: t for t in early['evaluation_tools']}
    after = {t['name']: t for t in current['evaluation_tools']}
    common = before.keys() & after.keys()
    categories = []
    if before.keys() != after.keys():
        categories.append('Tool')
    if any(before[n].get('inputSchema', {}) != after[n].get('inputSchema', {}) for n in common):
        categories.append('Parameter')
    if any((before[n].get('description') or '') != (after[n].get('description') or '') for n in common):
        categories.append('Description')
    return categories


def compare(main, ablation=None):
    manifest, rows = load_complete(main)
    config = manifest['config']
    affected = {(r['idx'], r['version']): r['affected'] for r in manifest['coverage']}
    official = {r['strategy']: r for r in read(main/'analysis/summary.json')['strategies']}
    arithmetic, strata, costs, diagnostics = [], [], [], []
    for strategy in config['strategies']:
        task_ecs = []
        for rep in range(config['repeats']):
            for idx in manifest['task_ids']:
                values = [tf(rows[rep, strategy, v, idx]) for v in config['versions']]
                average = sum(values)/len(values)
                population_sd = math.sqrt(sum((x-average)**2 for x in values)/len(values))
                task_ecs.append(average-population_sd)
        actual = mean(task_ecs)
        checks = {'ecs': actual}
        for version in config['versions']:
            group = [r for (rep, s, v, idx), r in rows.items() if s == strategy and v == version]
            checks[version+'_tf'] = mean(map(tf, group))
            checks[version+'_pe'] = mean(map(pe, group))
        for metric, value in checks.items():
            if not math.isclose(value, official[strategy][metric], abs_tol=1e-10):
                raise ValueError(f'Independent arithmetic disagrees: {strategy} {metric}')
        arithmetic.append({'strategy': strategy, **checks, 'matches_official_aggregate': True})
        for version in config['versions'][1:]:
            for changed in [True, False]:
                keys = [(rep, idx) for rep in range(config['repeats']) for idx in manifest['task_ids']
                        if affected[idx, version] == changed]
                scores = [tf(rows[rep, strategy, version, idx]) for rep, idx in keys]
                early_deltas = [tf(rows[rep, strategy, version, idx])-tf(rows[rep, strategy, 'original', idx])
                                for rep, idx in keys]
                baseline_deltas = [tf(rows[rep, strategy, version, idx])-tf(rows[rep, 'no_update', version, idx])
                                   for rep, idx in keys]
                strata.append({'strategy': strategy, 'version': version, 'cohort': 'changed' if changed else 'unaffected',
                               'episodes': len(keys), 'task_ids': sorted({idx for _, idx in keys}),
                               'tf': mean_or_none(scores), 'delta_from_own_early': mean_or_none(early_deltas),
                               'delta_from_same_version_no_update': mean_or_none(baseline_deltas),
                               'improved_vs_early': sum(x > 0 for x in early_deltas),
                               'unchanged_vs_early': sum(x == 0 for x in early_deltas),
                               'declined_vs_early': sum(x < 0 for x in early_deltas)})
        group = [r for key, r in rows.items() if key[1] == strategy]
        actor_calls = [call for r in group for call in r['model_calls']['agent']]
        diagnostics.append({'strategy': strategy, 'episodes': len(group),
                            'step_budget_exhausted': sum(bool(r['exceeded']) for r in group),
                            'terminal_execution_failures': sum(r.get('execution_status') == 'infrastructure_error' for r in group),
                            'rejected_updates': sum(r['adaptation']['status'] == 'rejected' for r in group),
                            'length_limited_actor_responses': sum(call['response']['choices'][0].get('finish_reason') == 'length' for call in actor_calls),
                            'actor_calls_with_context_pruning': sum(call.get('context', {}).get('dropped_messages', 0) > 0 for call in actor_calls),
                            'mcp_flagged_error_calls': sum(len(r.get('tool_errors', [])) for r in group)})
        for component in ['update', 'agent', 'judge']:
            calls = [call for r in group for call in r['model_calls'][component]]
            costs.append({'strategy': strategy, 'component': component, 'calls': len(calls),
                          'prompt_tokens': sum(c['usage'].get('prompt_tokens', 0) for c in calls),
                          'completion_tokens': sum(c['usage'].get('completion_tokens', 0) for c in calls),
                          'total_tokens': sum(c['usage'].get('total_tokens', 0) for c in calls),
                          'cached_prompt_tokens': sum(c['usage'].get('prompt_tokens_details', {}).get('cached_tokens', 0) for c in calls),
                          'model_request_seconds': sum(c['usage']['wall_seconds'] for c in calls),
                          'api_usd': sum(c['usage']['api_usd'] for c in calls)})
    category_results = []
    category_evidence_available = all('evaluation_tools' in r for r in rows.values())
    if not category_evidence_available and manifest['split'] == 'test':
        raise ValueError('Formal category analysis requires authoritative evaluation_tools in every record')
    for version in config['versions'][1:] if category_evidence_available else []:
        for category in ['Tool', 'Parameter', 'Description']:
            keys = [(rep, idx) for rep in range(config['repeats']) for idx in manifest['task_ids']
                    if category in change_categories(rows[rep, 'no_update', 'original', idx],
                                                     rows[rep, 'no_update', version, idx])]
            for strategy in config['strategies']:
                group = [rows[rep, strategy, version, idx] for rep, idx in keys]
                category_results.append({'version': version, 'category': category, 'strategy': strategy,
                    'episodes': len(group), 'task_ids': sorted({idx for _, idx in keys}),
                    'tf': mean_or_none([tf(r) for r in group]), 'pe': mean_or_none([pe(r) for r in group]),
                    'delta_from_same_version_no_update': mean_or_none([
                        tf(rows[rep, strategy, version, idx])-tf(rows[rep, 'no_update', version, idx])
                        for rep, idx in keys])})
    component_pairs = []
    if ablation is not None:
        ab_manifest, ab_rows = load_complete(ablation)
        for setting in ['model', 'model_sha256', 'temperature', 'seed', 'max_steps', 'agent_max_tokens',
                        'update_max_tokens', 'judge_model', 'judge_sha256', 'judge_max_tokens', 'judge_repeats', 'versions']:
            if config[setting] != ab_manifest['config'][setting]:
                raise ValueError(f'Ablation differs on uncontrolled setting: {setting}')
        if ab_manifest['config']['dependency_closure'] or not config['dependency_closure']:
            raise ValueError('Component contrast is not closure-on versus closure-off')
        for key, off in sorted(ab_rows.items()):
            on = rows[key]
            component_pairs.append({'repeat': key[0], 'version': key[2], 'idx': key[3],
                                    'on_tf': tf(on), 'off_tf': tf(off), 'delta_tf': tf(on)-tf(off),
                                    'on_pe': pe(on), 'off_pe': pe(off),
                                    'on_updated_notes': on['adaptation'].get('updated_note_count', 0),
                                    'off_updated_notes': off['adaptation'].get('updated_note_count', 0),
                                    'on_update_status': on['adaptation']['status'],
                                    'off_update_status': off['adaptation']['status']})
    result = {'independent_arithmetic': arithmetic, 'recovery_retention': strata, 'costs': costs,
              'change_category_results': category_results,
              'change_category_evidence_available': category_evidence_available,
              'execution_diagnostics': diagnostics,
              'terminal_execution_failures': [
                  {'repeat': key[0], 'strategy': key[1], 'version': key[2], 'idx': key[3],
                   'reason': row.get('terminal_reason'), 'tf': tf(row), 'pe': pe(row)}
                  for key, row in rows.items() if row.get('execution_status') == 'infrastructure_error'],
              'dependency_ablation': component_pairs,
              'definitions': {
                  'changed': 'Scoped current contracts differ from Early; this is contract exposure, not proof the changed tool is essential.',
                  'recovery': 'Paired TF difference against no-update at the same version on exposed tasks; negative values are retained.',
                  'retention': 'Paired TF difference from the same strategy at Early on tasks with unchanged scoped contracts; negative means loss.',
                  'cost': 'Measured local request tokens and seconds, including invalid/rejected calls; wall time is hardware/cache/order dependent.',
                  'uncertainty': 'One repetition; descriptive differences only, with no significance claims.'}}
    result['definitions']['change_categories'] = ('Compared with Early using captured authoritative evaluation tools: '
        'Tool = added/removed names; Parameter = changed schema on surviving names; Description = changed description '
        'on surviving names. Categories overlap; cohort difficulty is descriptive and cannot isolate a mutation effect.')
    destination = main/'analysis/paired-comparisons.json'
    destination.write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('main_run', type=Path)
    parser.add_argument('--ablation', type=Path)
    args = parser.parse_args()
    result = compare(args.main_run.resolve(), args.ablation.resolve() if args.ablation else None)
    print(json.dumps({'verified_strategies': len(result['independent_arithmetic']),
                      'recovery_retention_rows': len(result['recovery_retention']),
                      'ablation_pairs': len(result['dependency_ablation'])}))
