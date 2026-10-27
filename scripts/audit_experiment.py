"""Independent read-only checks of recorded protocol and adaptation invariants.

This checks execution evidence, not whether an answer is semantically correct.
Use --allow-incomplete only to inspect an ongoing run; it never labels it complete.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(value):
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


def audit(folder):
    manifest = read(folder/'manifest.json')
    config = manifest['config']
    issues, rows, terminal_failures = [], {}, []
    expected = {(rep, strategy, version, idx) for rep in range(config['repeats'])
                for strategy in config['strategies'] for version in config['versions']
                for idx in manifest['task_ids']}
    original_questions = {r['idx']: r['question'] for r in read(ROOT/'upstream/src/custom/data/test_cases/test_cases.json')}
    for name, expected_hash in manifest['source_hashes'].items():
        if digest((ROOT/name.replace('\\', '/')).read_text(encoding='utf-8')) != expected_hash:
            issues.append({'type': 'source_changed', 'file': name})
    for version, expected_hash in manifest['inventory_hashes'].items():
        if digest(read(ROOT/'artifacts/inventory'/f'{version}.json')) != expected_hash:
            issues.append({'type': 'inventory_changed', 'version': version})
    for path in folder.glob('repeat-*/*/*/*/result.json'):
        record = read(path)
        key = (record['repeat'], record['strategy'], record['version'], record['idx'])
        def fail(kind, **extra):
            issues.append({'key': key, 'type': kind, **extra})
        if key not in expected or key in rows:
            fail('unexpected_or_duplicate_episode')
        rows[key] = record
        if record.get('execution_status') == 'infrastructure_error':
            terminal_failures.append({'key': key, 'error': record.get('terminal_reason')})
            recovery = record.get('failure_evidence_recovery', {})
            failure_receipt = path.with_name('failure-record.json')
            if not failure_receipt.exists() or hashlib.sha256(failure_receipt.read_bytes()).hexdigest() != recovery.get('original_record_sha256'):
                fail('failure_receipt_missing_or_changed')
            events_path = path.with_name('events.jsonl')
            if not events_path.exists() or hashlib.sha256(events_path.read_bytes()).hexdigest() != recovery.get('events_sha256'):
                fail('failure_events_missing_or_changed')
        if record.get('manifest_hash') != digest(manifest):
            fail('wrong_manifest')
        if record.get('question') != original_questions.get(record['idx']):
            fail('question_modified')
        if record.get('status') not in {'awaiting_judge', 'evaluated'}:
            fail('invalid_episode_status', status=record.get('status'), error=record.get('error'))
        if record.get('status') == 'evaluated' and not record.get('eval_result', {}).get('valid'):
            fail('invalid_judgment')
        for component, calls in record.get('model_calls', {}).items():
            expected_model = config['judge_model'] if component == 'judge' else config['model']
            for call_index, call in enumerate(calls):
                request = call['request']
                if request['model'] != expected_model or request['temperature'] != config['temperature']:
                    fail('model_or_decoding_changed', component=component, call=call_index)
                if request['max_tokens'] != config[component+'_max_tokens']:
                    fail('token_limit_changed', component=component, call=call_index)
                if component != 'judge' and request['seed'] != config['seed']:
                    fail('actor_seed_changed', component=component, call=call_index)
                usage = call['usage']
                if usage.get('api_usd') != 0 or usage.get('total_tokens', -1) < 0 or usage.get('wall_seconds', -1) < 0:
                    fail('invalid_cost_record', component=component, call=call_index)
                if component == 'update' and record['question'] in json.dumps(request['messages'], ensure_ascii=False):
                    fail('task_leaked_to_updater')
        receipt = path.with_name('agent-record.json')
        if receipt.exists():
            old = read(receipt)
            for field in ['trajectory_messages', 'knowledge', 'adaptation', 'answer', 'artifact_changes']:
                if old.get(field) != record.get(field):
                    fail('actor_evidence_changed_after_judging', field=field)
        for kind in ['created', 'modified']:
            for name in record.get('artifact_changes', {}).get(kind, []):
                workspace = (path.parent/'workspace').resolve()
                target = (workspace/name).resolve()
                if not target.is_relative_to(workspace) or not target.is_file():
                    fail('recorded_artifact_missing_or_outside_workspace', file=name)
    for key, record in rows.items():
        rep, strategy, version, idx = key
        stage = config['versions'].index(version)
        if stage == 0:
            continue
        previous = rows.get((rep, strategy, config['versions'][stage-1], idx))
        if previous is None:
            issues.append({'key': key, 'type': 'previous_stage_missing'})
            continue
        old, new = previous.get('knowledge', {}), record.get('knowledge', {})
        adaptation = record.get('adaptation', {})
        if strategy == 'no_update' or adaptation.get('status') == 'rejected':
            if old != new:
                issues.append({'key': key, 'type': 'retained_knowledge_changed'})
        elif strategy == 'selective_patch':
            targets = set(adaptation.get('regenerated', []))
            for name in old.get('notes', {}).keys() & new.get('notes', {}).keys() - targets:
                if old['notes'][name] != new['notes'][name]:
                    issues.append({'key': key, 'type': 'unrelated_note_changed', 'tool': name})
        if strategy != 'no_update' and adaptation.get('status') == 'ok':
            expected_tools = {t['name']: {'name': t['name'], 'description': t.get('description') or '',
                                        'inputSchema': t.get('inputSchema', {})}
                              for t in record['evaluation_tools']}
            if new.get('tools') != expected_tools:
                issues.append({'key': key, 'type': 'updated_schema_not_authoritative'})
    missing = sorted(expected-rows.keys())
    unscored = [key for key, row in rows.items() if row.get('status') != 'evaluated']
    return {'expected': len(expected), 'found': len(rows), 'missing': missing,
            'terminal_execution_failures': terminal_failures,
            'status_counts': dict(Counter(row.get('status') for row in rows.values())),
            'issues': issues, 'recorded_invariants_pass': not issues,
            'complete_and_evaluated': not missing and not unscored and not issues,
            'scope': 'Protocol, recorded state, model settings, evidence preservation and artifact presence; not semantic task correctness.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    parser.add_argument('--allow-incomplete', action='store_true')
    args = parser.parse_args()
    folder = args.run_directory.resolve()
    report = audit(folder)
    output = folder/'analysis'/'invariant-audit.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'missing'}, indent=2))
    raise SystemExit(0 if report['recorded_invariants_pass'] and
                     (args.allow_incomplete or report['complete_and_evaluated']) else 1)
