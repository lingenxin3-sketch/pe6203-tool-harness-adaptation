"""Export scientific figures from complete, independently verified results only."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from analyze_comparisons import compare, read


def plot(run, output, development=False):
    data = compare(run)
    manifest = read(run/'manifest.json')
    versions = manifest['config']['versions']
    labels = {'original': 'Early', 'iter3': 'Middle', 'iter5': 'Late'}
    styles = {'no_update': ('No update', '#555555', 'o', '--'),
              'full_rewrite': ('Full rewrite', '#B85C00', 's', ':'),
              'selective_patch': ('Selective patch', '#006CB5', '^', '-')}
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False,
                         'axes.spines.right': False, 'svg.fonttype': 'none'})
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.5))
    points = []
    for row in data['independent_arithmetic']:
        name, color, marker, line = styles[row['strategy']]
        for ax, metric, title in zip(axes, ['tf', 'pe'], ['Task fulfillment (TF)', 'Planning effectiveness (PE)']):
            scores = [row[v+'_'+metric] for v in versions]
            ax.plot(range(len(versions)), scores, label=name, color=color,
                    marker=marker, linestyle=line, linewidth=1.7,
                    markersize={'no_update': 9, 'full_rewrite': 7, 'selective_patch': 4}[row['strategy']],
                    markerfacecolor='none', clip_on=False)
            ax.set(xticks=range(len(versions)), xticklabels=[labels[v] for v in versions],
                   ylim=(1, 10), yticks=[1, 3, 5, 7, 9, 10], title=title, ylabel='Mean score (1–10)')
            ax.grid(axis='y', alpha=0.2)
            points.append({'strategy': row['strategy'], 'metric': metric, 'versions': versions, 'values': scores})
    prefix = 'DEVELOPMENT ONLY — ' if development else ''
    fig.suptitle(prefix+'Performance across environment versions', fontsize=12)
    fig.legend(*axes[0].get_legend_handles_labels(), loc='lower center', ncol=3, bbox_to_anchor=(0.5, 0.055), frameon=False)
    fig.text(0.5, 0.015, f"{len(manifest['task_ids'])} tasks per policy/version; {manifest['config']['repeats']} repetition(s); descriptive means, no significance claim.", ha='center', fontsize=8)
    fig.tight_layout(rect=(0, 0.14, 1, 0.95))
    for extension in ['png', 'svg']:
        fig.savefig(output/f'performance.{extension}', dpi=220)
    plt.close(fig)
    (output/'figure-data.json').write_text(json.dumps({'run': str(run), 'development_only': development, 'points': points}, indent=2), encoding='utf-8')
    return output/'performance.png'


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--development', action='store_true')
    args = parser.parse_args()
    if args.run.name.startswith('dev') and not args.development:
        parser.error('Development runs require --development labeling')
    print(plot(args.run.resolve(), args.output.resolve(), args.development))
