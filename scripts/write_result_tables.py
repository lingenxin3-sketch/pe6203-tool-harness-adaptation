"""Produce report tables only from complete, independently checked results."""
import argparse
import json
from pathlib import Path

from analyze_comparisons import compare

NAMES = {'no_update': 'No update', 'full_rewrite': 'Full rewrite', 'selective_patch': 'Selective patch'}
VERSIONS = {'original': 'Early', 'iter3': 'Middle', 'iter5': 'Late'}


def number(value, signed=False):
    if value is None:
        return 'n/a'
    return f'{value:+.2f}' if signed else f'{value:.2f}'


def table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |', '| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(map(str, row))+' |' for row in rows])


def write_tables(main, destination, ablation=None):
    data = compare(main, ablation)
    manifest = json.loads((main/'manifest.json').read_text(encoding='utf-8'))
    c = manifest['config']
    count = len(manifest['task_ids'])
    split = manifest['split']
    lines = ['# Verified result tables', '',
             f'Source: `{main.name}`; split: **{split}**; {count} tasks; {c["repeats"]} repetition per configuration.', '',
             'Local rubric scores. TF and PE range from 1 to 10; higher is better. ECS is the original cross-version formula. '
             'Single-run differences are descriptive and do not establish statistical significance.', '']
    if split != 'test':
        lines.extend(['**DEVELOPMENT DATA ONLY - do not substitute these values for formal test results.**', ''])
    lines.extend(['## Main results', '', table(['Policy', 'Early TF / PE', 'Middle TF / PE', 'Late TF / PE', 'ECS'],
        [[NAMES[r['strategy']]]+[number(r[v+'_tf'])+' / '+number(r[v+'_pe']) for v in c['versions']]+[number(r['ecs'])]
         for r in data['independent_arithmetic']]), '',
        f'Each stage mean uses {count*c["repeats"]} episodes per policy. ECS aligns the same tasks across all three versions.', '',
        'All policies use identical initial knowledge at Early, with no adaptation. Any Early score gap is execution '
        'or judging variation, not an update benefit. One repetition cannot separate every source of variation '
        'from later policy differences.', ''])
    for version in c['versions'][1:]:
        group = [r for r in data['recovery_retention'] if r['version'] == version]
        lines.extend([f'## {VERSIONS[version]} recovery and retention', '',
            table(['Cohort', 'Policy', 'n', 'TF', 'Delta vs Early', 'Delta vs no update'],
                  [[r['cohort'], NAMES[r['strategy']], r['episodes'], number(r['tf']),
                    number(r['delta_from_own_early'], True), number(r['delta_from_same_version_no_update'], True)] for r in group]), '',
            'Changed = scoped contracts differ from Early. Recovery compares changed tasks with same-version no-update. '
            'Retention compares unaffected tasks with the same policy at Early. Negative differences are losses; '
            'cohorts and denominators are stage-specific.', ''])
    lines.extend(['## Results by change category', '',
        table(['Version', 'Change', 'Policy', 'n', 'TF / PE', 'Delta vs no update'],
              [[VERSIONS[r['version']], r['category'], NAMES[r['strategy']], r['episodes'],
                number(r['tf'])+' / '+number(r['pe']), number(r['delta_from_same_version_no_update'], True)]
               for r in data['change_category_results']]), '',
        data['definitions']['change_categories'], '',
        'A lower score identifies a harder observed cohort, not the causal effect of that change type. '
        'Empty categories have no score. Category counts must not be summed as unique episodes.', ''])
    if not data['change_category_evidence_available']:
        lines.extend(['Category results unavailable: this older development run did not capture authoritative evaluation tools. '
                      'No categories or scores have been inferred from incomplete evidence.', ''])
    update = [r for r in data['costs'] if r['component'] == 'update']
    full_tokens = next(r['total_tokens'] for r in update if r['strategy'] == 'full_rewrite')
    lines.extend(['## Adaptation cost', '', table(['Policy', 'Calls', 'Total tokens', 'Request seconds', 'Token saving vs full'],
        [[NAMES[r['strategy']], r['calls'], f'{r["total_tokens"]:,}', number(r['model_request_seconds']),
          f'{100*(1-r["total_tokens"]/full_tokens):.1f}%' if full_tokens else 'n/a'] for r in update]), '',
        'Totals include both environment transitions and rejected update calls. No-update has no adaptation generation, '
        'but that alone says nothing about task quality. Token savings are relative to full rewrite, not an overall utility score.', '',
        '## Execution and judging cost', '',
        table(['Policy', 'Component', 'Calls', 'Total tokens', 'Request seconds'],
              [[NAMES[r['strategy']], r['component'], r['calls'], f'{r["total_tokens"]:,}', number(r['model_request_seconds'])]
               for r in data['costs'] if r['component'] != 'update']), '',
        'All recorded API charges are USD 0 because inference is local. Hardware and electricity are not monetized. '
        'Request time is not whole-experiment duration; cache reuse, hardware and execution order affect timing.', ''])
    if ablation is not None:
        lines.extend(['## Dependency-expansion component comparison', '',
            table(['Task', 'Version', 'TF on / off', 'Delta TF', 'PE on / off', 'Notes on / off'],
                  [[r['idx'], VERSIONS[r['version']], number(r['on_tf'])+' / '+number(r['off_tf']), number(r['delta_tf'], True),
                    number(r['on_pe'])+' / '+number(r['off_pe']), str(r['on_updated_notes'])+' / '+str(r['off_updated_notes'])]
                   for r in data['dependency_ablation']]), '',
            'On = the main selective method; off = the predeclared selective variant without reference expansion. '
            'Early performs no updates. The six pairs are supplementary, with two predeclared tasks and one repetition; '
            'they are not a second full benchmark.', ''])
    failures = data['terminal_execution_failures']
    lines.extend(['## Fixed-budget execution diagnostics', '',
        table(['Policy', 'Step-limit episodes', 'Length-limited replies', 'Calls with pruning', 'Rejected updates'],
              [[NAMES[r['strategy']], r['step_budget_exhausted'], r['length_limited_actor_responses'],
                r['actor_calls_with_context_pruning'], r['rejected_updates']] for r in data['execution_diagnostics']]), '',
        'Episode counts and model-response counts have different denominators. An output reaching its length limit '
        'does not always abort an episode. Context pruning keeps original instructions and the task; full raw histories '
        'remain saved. These common resource limits can mediate observed policy differences.', ''])
    lines.extend(['## Recorded execution exceptions', '',
                  f'{len(failures)} terminal execution exception(s) remain included in the scored grid.'])
    if failures:
        lines.extend(['', table(['Task', 'Policy', 'Version', 'TF', 'PE'],
                               [[r['idx'], NAMES[r['strategy']], VERSIONS[r['version']], number(r['tf']), number(r['pe'])]
                                for r in failures]), '',
                      'Original failure receipts and incremental traces are preserved. Scoring a failed trace is not a retry '
                      'or a claim that task execution completed successfully.'])
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('main_run', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--ablation', type=Path)
    args = parser.parse_args()
    print(write_tables(args.main_run.resolve(), args.output.resolve(), args.ablation.resolve() if args.ablation else None))
