"""Predeclared original/R3 comparison; no inference, rescoring, or raw-data writes."""
import argparse
import hashlib
import json
import subprocess

from repeat_common import BRANCH, CAMPAIGN, NAMES, POLS, VERS, ROOT
from repeat_common import inspect, merge_views, metrics, now, read, resource_listing, round_compatibility, save, sha
from audit_experiment import audit
from repeat_original_context_audit import verify as verify_original_context

ARTIFACTS = ROOT / 'artifacts' / CAMPAIGN
RUNTIME = ROOT / 'runtime' / CAMPAIGN
SELECTED = [ROOT / 'runs' / NAMES[0], ROOT / 'runs' / NAMES[2]]


def gate_path(name):
    local = RUNTIME / (name + '-gate.json')
    public = ARTIFACTS / 'publication-gates' / (name + '-gate.json')
    if local.exists() and public.exists() and read(local) != read(public):
        raise ValueError('Local and exported publication gate contents differ')
    return local if local.exists() else public


def readiness():
    statuses = [inspect(folder) for folder in SELECTED]
    gates = [gate_path(name) for name in NAMES[1:]]
    gate_ok = all(p.is_file() and read(p).get('scored') == 162 and
                  read(p).get('release_verified', {}).get('anonymous_download_verified') and
                  read(p).get('publish_verified', {}).get('commit') for p in gates)
    receipts = all((ARTIFACTS / ('r3-' + role + '-start-runtime.json')).is_file()
                   for role in ['actor', 'judge'])
    return {'collected_at': now(), 'selected_rounds': [p.name for p in SELECTED],
            'statuses': statuses, 'both_new_round_publication_gates_verified': bool(gate_ok),
            'r3_runtime_receipts_present': receipts,
            'ready_for_full_validation': all(s['complete'] for s in statuses) and gate_ok and receipts,
            'scope': 'Readiness only; full protocol, input and source checks precede any comparison.'}


def input_fairness():
    rounds = []
    for name in NAMES:
        folder = ROOT / 'runs' / name
        manifest = read(folder / 'manifest.json')
        groups, pending = [], []
        for task in manifest['task_ids']:
            for version in VERS:
                paths = {p: folder / f'repeat-0/{p}/{version}/{task}/result.json' for p in POLS}
                if not all(p.is_file() for p in paths.values()):
                    pending.append({'task': task, 'version': version})
                    continue
                listings = {p: resource_listing(read(path)) for p, path in paths.items()}
                if any(value is None for value in listings.values()):
                    pending.append({'task': task, 'version': version})
                    continue
                digests = {p: hashlib.sha256(json.dumps(value, ensure_ascii=False,
                           separators=(',', ':')).encode('utf-8')).hexdigest() for p, value in listings.items()}
                groups.append({'task': task, 'version': version,
                               'sources': {p: path.relative_to(ROOT).as_posix() for p, path in paths.items()},
                               'resource_counts': {p: len(value) for p, value in listings.items()},
                               'listing_sha256': digests, 'same_across_strategies': len(set(digests.values())) == 1})
        rounds.append({'round': name, 'expected_groups': 54, 'checked_groups': len(groups),
                       'pending_groups': pending,
                       'differing_groups': sum(not g['same_across_strategies'] for g in groups), 'groups': groups})
    return {'checked_at': now(), 'scope': 'Actual initial resource lists across strategies, same task/version.',
            'listing_hash_encoding': 'Compact JSON list, ensure_ascii=False, UTF-8, SHA-256', 'rounds': rounds}


def actor_field_differences(actor, scored):
    canonical = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    changed = [key for key, value in actor.items()
               if key not in {'status', 'eval_result', 'model_calls'} and
               (key not in scored or canonical(scored[key]) != canonical(value))]
    old_calls, new_calls = actor.get('model_calls', {}), scored.get('model_calls', {})
    for role in ['agent', 'update']:
        if (role in old_calls) != (role in new_calls) or canonical(old_calls.get(role)) != canonical(new_calls.get(role)):
            changed.append('model_calls.' + role)
    return changed


def verify_execution_freeze():
    snapshot = ARTIFACTS / 'r3-execution-freeze.json'
    frozen = read(snapshot)
    rows = frozen['records']
    if len(rows) != 162 or len({r['episode'] for r in rows}) != 162:
        raise ValueError('Incomplete or duplicate actor snapshot')
    failures = 0
    for row in rows:
        episode = SELECTED[1] / row['episode']
        actor = episode.with_name('agent-record.json')
        if sha(actor) != row['pre_scoring_sha256']:
            raise ValueError('Pre-scoring actor bytes changed: ' + row['episode'])
        if actor_field_differences(read(actor), read(episode)):
            raise ValueError('Scored result changed execution fields: ' + row['episode'])
        if sha(ROOT / row['events_source']) != row['events_sha256']:
            raise ValueError('Closed event bytes changed: ' + row['episode'])
        failure = episode.with_name('failure-record.json')
        if row['raw_failure_source']:
            failures += 1
            if sha(failure) != row['raw_failure_sha256']:
                raise ValueError('Raw failure bytes changed: ' + row['episode'])
        elif failure.exists():
            raise ValueError('Unexpected later failure record')
    return {'verified_at': now(), 'snapshot_source': snapshot.relative_to(ROOT).as_posix(),
            'snapshot_sha256': sha(snapshot), 'records_checked': 162,
            'all_actor_bytes_preserved': True, 'all_event_bytes_preserved': True,
            'all_scored_results_preserve_actor_fields': True,
            'raw_failure_records_checked': failures, 'all_frozen_failure_bytes_preserved': True,
            'successful_scores_at_snapshot': frozen['status_at_snapshot']['scored']}


def generate():
    ready = readiness()
    if not ready['ready_for_full_validation']:
        raise RuntimeError('Complete scoring and verified publication are required; no outputs written')
    branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT,
                                     text=True, encoding='utf-8').strip()
    if branch != BRANCH:
        raise RuntimeError('Expected the dedicated experiment branch')
    targets = [ARTIFACTS / 'original-r3-comparison.json',
               ARTIFACTS / 'original-r3-paired-evidence.json',
               ROOT / 'docs/追加实验/原轮与第二新增轮对照.md']
    if any(p.exists() for p in targets):
        raise FileExistsError('Comparison already exists; inspect instead of overwriting')
    compatibility = round_compatibility(*SELECTED)
    if not compatibility['compatible']:
        raise ValueError('Actual inputs or frozen protocol differ; comparison refused')
    fairness = input_fairness()
    if any(r['checked_groups'] != 54 or r['pending_groups'] or r['differing_groups']
           for r in fairness['rounds'] if r['round'] in [NAMES[0], NAMES[2]]):
        raise ValueError('Comparable rounds do not have complete equal inputs across strategies')
    execution_preservation = verify_execution_freeze()
    audits = [audit(folder) for folder in SELECTED]
    if any(not a['complete_and_evaluated'] or not a['recorded_invariants_pass'] or a['issues'] for a in audits):
        raise ValueError('Full scored-grid audit did not pass')
    if read(SELECTED[0] / 'analysis/judge-capacity.json') != read(SELECTED[1] / 'analysis/judge-capacity.json'):
        raise ValueError('Judge policy/capacity differs')
    original_context = verify_original_context()
    if not original_context['effective_context_check_pass']:
        raise ValueError('Original effective judge input/server conditions not verified')
    request_checks = []
    for folder in SELECTED:
        counts = {'agent': 0, 'update': 0, 'judge': 0}
        for path in folder.glob('repeat-*/*/*/*/result.json'):
            record = read(path)
            for role, calls in record.get('model_calls', {}).items():
                if role not in counts:
                    raise ValueError('Unexpected inference role')
                for call in calls:
                    req = call['request']
                    expected_model = 'qwen2.5-7b-judge' if role == 'judge' else 'qwen3-4b'
                    if (req.get('model') != expected_model or req.get('temperature') != 0 or
                            req.get('seed') != 6203 or req.get('max_tokens') != 2048 or
                            call['response'].get('system_fingerprint') != 'b11900-74b104c9b'):
                        raise ValueError('Saved model decoding/backend conditions differ')
                    if role == 'judge' and (call['context']['dropped_messages'] != 0 or
                            (folder.name == NAMES[2] and call['context'].get('context_limit') != 24576)):
                        raise ValueError('Judge input was pruned or new judge capacity differs')
                    counts[role] += 1
        if counts['judge'] != 162:
            raise ValueError('Expected exactly 162 saved judge calls')
        request_checks.append({'round': folder.name, 'checked_calls': counts, 'all_pass': True})
    actual_runtimes = {}
    for role, capacity in [('actor', 16384), ('judge', 24576)]:
        runtime = read(ARTIFACTS / ('r3-' + role + '-start-runtime.json'))
        actual_runtimes[role] = runtime
        props = runtime['properties']
        if props['default_generation_settings']['n_ctx'] != capacity or props['build_info'] != 'b11900-74b104c9b':
            raise ValueError('Actual R3 model runtime differs from frozen conditions')
    prior_gate, new_gate = [read(gate_path(name)) for name in NAMES[1:]]
    if not (prior_gate['completed_at'] <= actual_runtimes['actor']['recorded_at'] <=
            actual_runtimes['judge']['recorded_at'] <= new_gate['completed_at']):
        raise ValueError('Runtime/publication chronology differs from the staged protocol')
    preflight = read(ARTIFACTS / 'preflight.json')
    if any(sha(ROOT / name) != expected for name, expected in preflight['raw_evidence_hashes'].items()):
        raise ValueError('Original frozen evidence changed')
    public_old = read(ARTIFACTS / 'original-public-evidence-verification.json')
    if not public_old['all_public_evidence_content_matches_frozen_baseline']:
        raise ValueError('Original public evidence content is not verified')
    if sha(ROOT / 'deliverables/original-v1-20261029-verified.zip') != public_old['archive_sha256']:
        raise ValueError('Verified original public archive changed')

    combined = merge_views(SELECTED)
    first = metrics(SELECTED[0])
    for strategy in combined['strategies']:
        original_strategy = next(s for s in first['strategies'] if s['strategy'] == strategy['strategy'])
        for index, cohort in enumerate(strategy['cohorts']):
            cohort.update(n_observations=cohort['n'],
                          distinct_tasks=original_strategy['cohorts'][index]['n'],
                          n_unit='Repeated task observations; not independent new tasks')
    serialization = {x['source']: x for x in public_old['serialization_differences']}
    pairs = []
    for new_path in sorted(SELECTED[1].glob('repeat-*/*/*/*/result.json')):
        old_path = SELECTED[0] / new_path.relative_to(SELECTED[1])
        old, new = read(old_path), read(new_path)
        if old['question'] != new['question']:
            raise ValueError('Question mismatch')
        a, b = old['eval_result']['aggregate'], new['eval_result']['aggregate']
        controls = []
        for folder in SELECTED:
            control_path = folder / f"repeat-0/no_update/{new['version']}/{new['idx']}/result.json"
            control = read(control_path)['eval_result']['aggregate']
            controls.append({'source': control_path.relative_to(ROOT).as_posix(),
                             'sha256': sha(control_path),
                             'tf': control['task_fulfillment_mean'],
                             'pe': control['planning_and_efficiency_mean']})
        original_name = old_path.relative_to(ROOT).as_posix()
        pairs.append({'strategy': new['strategy'], 'version': new['version'], 'idx': new['idx'],
                      'old_source': original_name, 'old_local_sha256': sha(old_path),
                      'old_public_sha256': serialization.get(original_name, {}).get('public_archive_sha256', sha(old_path)),
                      'new_source': new_path.relative_to(ROOT).as_posix(), 'new_sha256': sha(new_path),
                      'old_tf': a['task_fulfillment_mean'], 'new_tf': b['task_fulfillment_mean'],
                      'tf_difference_new_minus_old': b['task_fulfillment_mean'] - a['task_fulfillment_mean'],
                      'old_pe': a['planning_and_efficiency_mean'], 'new_pe': b['planning_and_efficiency_mean'],
                      'pe_difference_new_minus_old': b['planning_and_efficiency_mean'] - a['planning_and_efficiency_mean'],
                      'same_task_version_no_update_controls': controls,
                      'old_tf_delta_same_version_no_update': a['task_fulfillment_mean'] - controls[0]['tf'],
                      'new_tf_delta_same_version_no_update': b['task_fulfillment_mean'] - controls[1]['tf'],
                      'old_pe_delta_same_version_no_update': a['planning_and_efficiency_mean'] - controls[0]['pe'],
                      'new_pe_delta_same_version_no_update': b['planning_and_efficiency_mean'] - controls[1]['pe'],
                      'old_execution_status': old.get('execution_status'),
                      'new_execution_status': new.get('execution_status')})
    if len(pairs) != 162 or len({(r['strategy'], r['version'], r['idx']) for r in pairs}) != 162:
        raise ValueError('Expected 162 unique matched pairs')
    combined.update(selected_rounds=[p.name for p in SELECTED], excluded_round=NAMES[1],
                    compatibility=compatibility, original_public_evidence=public_old,
                    within_round_input_fairness=fairness,
                    r3_execution_preservation=execution_preservation,
                    original_effective_context_check=original_context,
                    saved_request_protocol_checks=request_checks,
                    source_manifests=[{'path': (p / 'manifest.json').relative_to(ROOT).as_posix(),
                                       'sha256': sha(p / 'manifest.json')} for p in SELECTED],
                    selection_rule='Predeclared before R3 scores; exclude R2 for actual input differences, never by score')
    save(targets[0], combined)
    save(targets[1], {'collected_at': now(), 'matched_pairs': 162, 'observations': 324,
                      'distinct_tasks': 18, 'source_rounds': [p.name for p in SELECTED], 'records': pairs})

    labels = {'no_update': '不更新', 'full_rewrite': '全部重写', 'selective_patch': '选择性更新'}
    lines = ['# 原轮与第二新增轮的可比对照', '', '采集时间：' + now(), '',
             '仅包含final-v1和final-r3：324条观测、18个不同任务、每个任务/策略/版本组合2次。',
             '第一新增轮repeat-r2-20261029因评分前已发现的资源清单差异始终独立报告；本页不是三轮或486条可比汇总。', '',
             '| 策略 | Early TF / PE | Middle TF / PE | Late TF / PE | ECS |',
             '|---|---:|---:|---:|---:|']
    for s in combined['strategies']:
        cells = [f"{s['stages'][v]['tf']:.2f}±{s['stages'][v]['tf_round_sample_sd']:.2f} / {s['stages'][v]['pe']:.2f}±{s['stages'][v]['pe_round_sample_sd']:.2f}" for v in VERS]
        lines.append('| ' + labels[s['strategy']] + ' | ' + ' | '.join(cells) + f" | {s['ecs_mean']:.3f}±{s['ecs_sample_sd']:.3f} |")
    lines += ['', '±表示两次轮均值之间的样本标准差，n=2；不是跨18题的标准差，不是置信区间或显著性检验。ECS内部跨版本的总体标准差按原定义计算。', '',
              '## 两轮合计成本', '', '| 策略 | 阶段 | 调用次数 | Token | 请求秒数 | 本地API美元 |',
              '|---|---|---:|---:|---:|---:|']
    for s in combined['strategies']:
        for phase, c in s['costs'].items():
            lines.append(f"| {labels[s['strategy']]} | {phase} | {c['calls']} | {c['tokens']} | {c['request_seconds']:.2f} | {c['api_usd']:.2f} |")
    full = next(s for s in combined['strategies'] if s['strategy'] == 'full_rewrite')
    selective = next(s for s in combined['strategies'] if s['strategy'] == 'selective_patch')
    full_update, selective_update = full['costs']['update']['tokens'], selective['costs']['update']['tokens']
    full_total = sum(c['tokens'] for c in full['costs'].values())
    selective_total = sum(c['tokens'] for c in selective['costs'].values())
    if full_update:
        lines += ['', f'两轮合计更新token节省率：{100*(1-selective_update/full_update):.1f}%。仅指更新阶段。']
    if full_total:
        lines += [f'三阶段合计token：全部重写{full_total:,}，选择性更新{selective_total:,}，后者相对变化{100*(selective_total/full_total-1):+.1f}%（正值表示更多）。']
    lines += ['', '请求秒数是模型请求累计耗时，不是完整运行墙钟。本地API零计费不含电费、硬件和开发成本。以上成本来自已保存并返回用量的调用；旧轮评分服务中断等未返回调用的成本未知，不能把缺失成本解释为真实零消耗。', '',
              '## 来源、分母与局限', '',
              '完整指标、各轮独立值、恢复/保持分组见[比较JSON](../../artifacts/' + CAMPAIGN + '/original-r3-comparison.json)。cohorts.n及n_observations表示重复观测，distinct_tasks表示不同任务数；各版本每策略18个任务、36条观测。', '',
              '162组同任务/同版本/同策略的原轮与新轮配对差及每条来源SHA见[配对索引](../../artifacts/' + CAMPAIGN + '/original-r3-paired-evidence.json)。旧公开ZIP有一条JSON序列化格式差异、内容相同；索引同时列旧本机SHA与旧公开SHA，详情见[来源核验](../../artifacts/' + CAMPAIGN + '/original-public-evidence-verification.json)。不改写旧记录。', '',
              '选择口径在R3评分前已声明，见[冻结协议](冻结与故障协议.md)。固定seed、temperature=0的重复只描述相同条件下的执行稳定性，不把重复当成新增独立任务，也不作普遍优越或单句改写因果结论。Early尚未更新，其差异不能算更新效果。', '',
              '原轮前39条评分的客户端上限检查仍为16384，后123条及新轮为24576；这不是所有客户端代码完全相同。旧公开日志证明服务器一直为24576，前39条最长预留15505、全部零消息删减，且39条原件SHA与当时异常归档一致。因此保留评分输入未受这一检查差异影响；本对照以实际输入和服务器条件为口径，仍披露该实现差异。详见[上下文核验](../../artifacts/' + CAMPAIGN + '/original-effective-context-verification.json)。', '',
              '官方自动分数不等于实际成功率。已知任务113、117评分盲点、漏更新与过度更新案例均保留；参见[第一新增轮](第一新增轮案例核查.md)、[第二新增轮](第二新增轮案例核查.md)。AI辅助核查不冒充成员独立复核。原依赖扩展对照仍为单次辅助实验，旧Word/PDF/演讲材料未同步更新。']
    targets[2].write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(json.dumps({'created_at': now(), 'observations': 324, 'matched_pairs': 162,
                      'distinct_tasks': 18, 'excluded_round': NAMES[1]}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-ready', action='store_true', help='Read-only readiness; no output artifacts')
    args = parser.parse_args()
    if args.check_ready:
        print(json.dumps(readiness(), ensure_ascii=False))
    else:
        generate()
