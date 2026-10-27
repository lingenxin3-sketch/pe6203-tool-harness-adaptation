from __future__ import annotations
import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from .agent import run_agent
from .knowledge import Knowledge, adapt, canonical, digest, normalize_tools
from .llm import LocalModel
from .mcp_runtime import MCPRuntime, public_name
from .official import OfficialEvaluator


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def save(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def copy_resources(source: Path, destination: Path):
    # Windows legacy path limits affect the benchmark's long PDF filenames.
    # Extended paths preserve every original fixture without renaming it.
    def native(path):
        value = str(path.resolve())
        return '\\\\?\\' + value if os.name == 'nt' and not value.startswith('\\\\?\\') else value
    shutil.copytree(native(source), native(destination))


def scoped_tools(case, inventory, early_inventory):
    tools = []
    for server, original_names in case['servers'].items():
        current = inventory[server]
        if current['status'] != 'ok':
            raise ValueError(f'Server unavailable: {server}')
        original_all = {t['name'] for t in early_inventory[server]['tools']}
        wanted = {public_name(server, name) for name in original_names}
        tools.extend(t for t in current['tools'] if t['name'] in wanted or t['name'] not in original_all)
    return sorted(tools, key=lambda t: t['name'])


def model_from(config, kind):
    base_url = config.get('judge_base_url', config['base_url']) if kind == 'judge' else config['base_url']
    model = config.get('judge_model', config['model']) if kind == 'judge' else config['model']
    return LocalModel(base_url, model, temperature=config['temperature'],
                      seed=config['seed'], max_tokens=config[kind + '_max_tokens'])


async def run_experiment(root: Path, config_path: Path, output: Path, *, split='test', task_limit=None):
    config = read(config_path)
    commit = subprocess.check_output(['git', '-C', str(root/'upstream'), 'rev-parse', 'HEAD'], text=True).strip()
    if commit != config['upstream_commit']:
        raise ValueError('Upstream commit differs from protocol')
    if set(config['development_ids']) & set(config['test_ids']):
        raise ValueError('Development/test overlap')
    if output.exists():
        raise FileExistsError('Output exists; use a new directory to preserve raw evidence')
    inventories = {v: read(root/'artifacts/inventory'/f'{v}.json') for v in config['versions']}
    all_cases = read(root/'upstream/src/custom/data/test_cases/test_cases.json')
    chosen = {item['idx'] for item in read(root/'upstream/src/custom/data/test_cases/chosen_idx.json')['samples']}
    ids = config[split + '_ids']
    if task_limit is not None:
        if split != 'development':
            raise ValueError('Cannot truncate the frozen test subset')
        ids = ids[:task_limit]
    if not set(ids) <= chosen:
        raise ValueError('Task outside official 201-task chosen set')
    cases = [next(case for case in all_cases if case['idx'] == idx) for idx in ids]
    coverage = []
    for case in cases:
        early = normalize_tools(scoped_tools(case, inventories['original'], inventories['original']))
        for v in config['versions']:
            now = normalize_tools(scoped_tools(case, inventories[v], inventories['original']))
            coverage.append({'idx': case['idx'], 'version': v, 'affected': now != early,
                             'tool_count': len(now), 'contract_hash': digest(now)})
    manifest = {'config': config, 'split': split, 'task_ids': ids, 'coverage': coverage,
                'inventory_hashes': {v: digest(x) for v, x in inventories.items()},
                'source_hashes': {str(p.relative_to(root)): digest(p.read_text(encoding='utf-8')) for p in sorted((root/'tool_adapt').glob('*.py'))}}
    save(output/'manifest.json', manifest)
    evaluator = OfficialEvaluator(root/'upstream')
    for repeat in range(config['repeats']):
        for case in cases:
            for strategy in config['strategies']:
                knowledge = Knowledge.initial(scoped_tools(case, inventories['original'], inventories['original']))
                for version in config['versions']:
                    run = output/f'repeat-{repeat}'/strategy/version/str(case['idx'])
                    workspace = run/'workspace'
                    copy_resources(root/'upstream/anotation_path', workspace)
                    # Original questions sometimes name this prefix explicitly.
                    copy_resources(root/'upstream/anotation_path', workspace/'anotation_path')
                    current = scoped_tools(case, inventories[version], inventories['original'])
                    update_model = model_from(config, 'update')
                    agent_model = model_from(config, 'agent')
                    judge_model = model_from(config, 'judge')
                    result = {'idx': case['idx'], 'question': case['question'], 'servers': case['servers'],
                              'strategy': strategy, 'version': version, 'repeat': repeat,
                              'split': split, 'manifest_hash': digest(manifest)}
                    try:
                        if version != 'original':
                            try:
                                knowledge, audit = await asyncio.to_thread(adapt, knowledge, current, strategy,
                                    update_model.generate_notes, version=version,
                                    dependency_closure=config.get('dependency_closure', True))
                            except (ValueError, TypeError) as exc:
                                audit = {'status': 'rejected', 'error': str(exc), 'strategy': strategy,
                                         'retained_knowledge_hash': digest(knowledge.to_dict())}
                        else:
                            audit = {'status': 'initial', 'strategy': strategy}
                        result['adaptation'] = audit
                        result['knowledge'] = knowledge.to_dict()
                        async with MCPRuntime(root, version, list(case['servers']), workspace) as runtime:
                            live = {t['name']: t for t in runtime.tools}
                            if any(live.get(t['name']) != t for t in current):
                                raise ValueError('Live server contracts differ from captured inventory')
                            result.update(await run_agent(agent_model, runtime, knowledge, case['question'],
                                max_steps=config['max_steps'], event_path=run/'events.jsonl'))
                        # Save the complete agent trace BEFORE invoking the judge.
                        save(run/'result.json', result)
                        result['evaluation_tools'] = current
                        if config.get('defer_judging', False):
                            result['status'] = 'awaiting_judge'
                        else:
                            result['eval_result'] = await asyncio.to_thread(evaluator.judge, result, current, judge_model,
                                repeats=config['judge_repeats'], seed=config['seed'] + case['idx'])
                            result['status'] = 'evaluated' if result['eval_result']['valid'] else 'judge_failed'
                    except Exception as exc:
                        result['status'] = 'infrastructure_error'
                        result['error'] = type(exc).__name__ + ': ' + str(exc)
                    finally:
                        result['model_calls'] = {'update': update_model.calls, 'agent': agent_model.calls, 'judge': judge_model.calls}
                        save(run/'result.json', result)
                    scores = result.get('eval_result', {}).get('aggregate', {})
                    print(canonical({'idx': case['idx'], 'strategy': strategy, 'version': version,
                        'status': result['status'], 'scores': {k: scores.get(k) for k in ['task_fulfillment_mean','planning_and_efficiency_mean']},
                        'error': result.get('error')}), flush=True)
    return manifest


def judge_experiment(root: Path, run_dir: Path):
    """Deferred scoring allows actor and larger judge to share one small GPU."""
    config = read(run_dir/'manifest.json')['config']
    evaluator = OfficialEvaluator(root/'upstream')
    for path in sorted(run_dir.glob('repeat-*/*/*/*/result.json')):
        record = read(path)
        if record.get('status') != 'awaiting_judge':
            continue
        model = model_from(config, 'judge')
        # Preserve the agent-only record as an immutable pre-judge receipt.
        receipt = path.with_name('agent-record.json')
        if not receipt.exists():
            save(receipt, record)
        record['eval_result'] = evaluator.judge(record, record['evaluation_tools'], model,
            repeats=config['judge_repeats'], seed=config['seed'] + record['idx'])
        record['model_calls']['judge'] = model.calls
        record['status'] = 'evaluated' if record['eval_result']['valid'] else 'judge_failed'
        save(path, record)
        scores=record['eval_result']['aggregate']
        print(canonical({'idx':record['idx'],'strategy':record['strategy'],'version':record['version'],
                         'status':record['status'],'tf':scores.get('task_fulfillment_mean'),
                         'pe':scores.get('planning_and_efficiency_mean')}),flush=True)
