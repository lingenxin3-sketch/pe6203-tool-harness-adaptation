"""Strict result aggregation: missing runs never become silent exclusions."""
from __future__ import annotations
import csv
import json
from pathlib import Path
import statistics
from .experiment import read, save
from .official import OfficialEvaluator


def aggregate(root: Path, run_dir: Path):
    manifest = read(run_dir/'manifest.json')
    config = manifest['config']
    expected = {(repeat, strategy, version, idx) for repeat in range(config['repeats'])
                for strategy in config['strategies'] for version in config['versions'] for idx in manifest['task_ids']}
    rows, seen, invalid = [], set(), []
    affected = {(r['idx'],r['version']):r['affected'] for r in manifest['coverage']}
    evaluator = OfficialEvaluator(root/'upstream')
    for file in sorted(run_dir.glob('repeat-*/*/*/*/result.json')):
        record = read(file)
        key = (record['repeat'],record['strategy'],record['version'],record['idx'])
        if key not in expected or key in seen:
            raise ValueError('Unexpected or duplicate experiment row: ' + str(key))
        seen.add(key)
        if record.get('status') != 'evaluated' or not record.get('eval_result',{}).get('valid'):
            invalid.append({'key':key,'status':record.get('status'),'error':record.get('error')})
            continue
        scores=record['eval_result']['aggregate']
        row={'repeat':key[0],'strategy':key[1],'version':key[2],'idx':key[3],
             'affected':affected[(key[3],key[2])], 'tf':scores['task_fulfillment_mean'],
             'pe':scores['planning_and_efficiency_mean'],'grounding':scores['grounding_mean'],
             'agent_stopped':record['stop'],'step_budget_exhausted':record['exceeded'],
             'created_files':len(record.get('artifact_changes',{}).get('created',[])),
             'tool_error_count':len(record.get('tool_errors',[])),
             'update_status':record['adaptation']['status']}
        for component in ['update','agent','judge']:
            calls=record['model_calls'][component]
            row[component+'_tokens']=sum(call['usage'].get('total_tokens',0) for call in calls)
            row[component+'_seconds']=sum(call['usage']['wall_seconds'] for call in calls)
            row[component+'_api_usd']=sum(call['usage']['api_usd'] for call in calls)
        rows.append(row)
        save(run_dir/'analysis'/'official_eval'/f'repeat-{key[0]}'/key[1]/key[2]/f'{key[3]}.json',record)
    missing=sorted(expected-seen)
    status={'expected':len(expected),'found':len(seen),'evaluated':len(rows),'missing':missing,'invalid':invalid,
            'complete':not missing and not invalid}
    save(run_dir/'analysis'/'completeness.json',status)
    if not status['complete']:
        raise ValueError(f'Incomplete evaluation: {len(missing)} missing; {len(invalid)} invalid. See completeness.json.')
    with (run_dir/'analysis'/'episodes.csv').open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    summaries=[]
    for strategy in config['strategies']:
        ecs_values=[]
        for repeat in range(config['repeats']):
            base=run_dir/'analysis'/'official_eval'/f'repeat-{repeat}'/strategy
            ecs_rows,meta=evaluator.ecs.compare_three_dirs(*(str(base/version) for version in config['versions']))
            if len(ecs_rows)!=len(manifest['task_ids']):
                raise ValueError('ECS task alignment is incomplete')
            ecs_values.append(statistics.mean(row.mean-row.stdev for row in ecs_rows))
        group=[row for row in rows if row['strategy']==strategy]
        summary={'strategy':strategy,'ecs':statistics.mean(ecs_values),'episodes':len(group)}
        for version in config['versions']:
            version_rows=[r for r in group if r['version']==version]
            summary[version+'_tf']=statistics.mean(r['tf'] for r in version_rows)
            summary[version+'_pe']=statistics.mean(r['pe'] for r in version_rows)
        for component in ['update','agent','judge']:
            for metric in ['tokens','seconds','api_usd']:
                key=component+'_'+metric
                summary[key]=sum(r[key] for r in group)
        for kind,label in [(True,'changed'),(False,'retained')]:
            subset=[r for r in group if r['version']!='original' and r['affected']==kind]
            summary[label+'_episodes']=len(subset)
            summary[label+'_tf']=statistics.mean(r['tf'] for r in subset) if subset else None
        summary['rejected_updates']=sum(r['update_status']=='rejected' for r in group)
        summaries.append(summary)
    save(run_dir/'analysis'/'summary.json',{'status':status,'strategies':summaries,
         'metric_provenance':'Official MCPEvol-Bench rubric, aggregation and population-standard-deviation ECS',
         'limitations':[config['judge_limitation'],'One run per configuration does not estimate stochastic run-to-run variability.']})
    return summaries
