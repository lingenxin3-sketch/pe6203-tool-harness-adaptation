"""Read-only original judge context audit against its public evidence archive."""
import hashlib
import json
import zipfile

from repeat_common import CAMPAIGN, ROOT, now, read, save, sha


def verify():
    base = ROOT / 'artifacts' / CAMPAIGN
    public = read(base / 'original-public-evidence-verification.json')
    archive = ROOT / 'deliverables/original-v1-20261029-verified.zip'
    if sha(archive) != public['archive_sha256']:
        raise ValueError('Original public archive hash differs')
    names = [
        'artifacts/judge-runtime.json',
        'artifacts/incidents/judge-oom-after39/judge.stderr.log',
        'artifacts/incidents/judge-oom-after39/incident.json',
        'artifacts/incidents/judge-oom-after39/recovery-verification.json',
        'artifacts/incidents/judge-allocation-after57/recovery-verification.json',
        'tool_adapt/llm.py',
        'scripts/judge_with_capacity.py',
        'configs/judge-capacity.json',
    ]
    evidence = []
    with zipfile.ZipFile(archive) as z:
        contents = {name: z.read(name) for name in names}
    for name, content in contents.items():
        digest = hashlib.sha256(content).hexdigest()
        if sha(ROOT / name) != digest:
            raise ValueError('Archived protocol/runtime evidence differs: ' + name)
        evidence.append({'source': name, 'archive_sha256': digest, 'same_local_bytes': True})
    runtime = json.loads(contents[names[0]])
    recovery39 = json.loads(contents[names[3]])
    recovery57 = json.loads(contents[names[4]])
    incident = json.loads(contents[names[2]])
    startup_lines = [line for line in contents[names[1]].decode('utf-8').splitlines()
                     if 'n_ctx_slot = ' in line]
    server_ok = (runtime['n_ctx'] == 24576 and
                 runtime['model_alias'] == 'qwen2.5-7b-judge' and
                 runtime['build_info'] == 'b11900-74b104c9b' and
                 any('n_ctx_slot = 24576' in line for line in startup_lines) and
                 recovery39['context'] == 24576 and
                 recovery57['server_generation_settings']['n_ctx'] == 24576 and
                 recovery57['generation_settings_equal_previous_server'] is True and
                 recovery39['previous_39_scores_unchanged'] is True and
                 recovery57['previous_57_scores_unchanged'] is True)
    prior_paths = {p['record'].replace('\\', '/'): p['sha256']
                   for p in incident['completed_scores']}
    rows, issues, missing = [], [], []
    for path in sorted((ROOT / 'runs/final-v1').glob('repeat-*/*/*/*/result.json')):
        value = read(path)
        source = path.relative_to(ROOT).as_posix()
        calls = value.get('model_calls', {}).get('judge', [])
        if len(calls) != 1:
            issues.append({'source': source, 'issue': 'Expected one retained judge call'})
        for call in calls:
            context, request = call['context'], call['request']
            is_missing = 'context_limit' not in context
            row = {'source': source, 'sha256': sha(path), 'context': context,
                   'request_message_count': len(request['messages']),
                   'reserved_tokens': context['prompt_tokens_checked'] + request['max_tokens'] + 128,
                   'recorded_context_limit': context.get('context_limit'),
                   'pre_recovery_record': source in prior_paths}
            if context['dropped_messages'] != 0:
                issues.append({'source': source, 'issue': 'Judge input was pruned'})
            if is_missing:
                missing.append(row)
                if source not in prior_paths or sha(path) != prior_paths[source] or row['reserved_tokens'] > 16384:
                    issues.append({'source': source, 'issue': 'Earlier guard/provenance not verified'})
            elif context['context_limit'] != 24576:
                issues.append({'source': source, 'issue': 'Unexpected recorded capacity'})
            rows.append(row)
    if len(rows) != 162 or len(missing) != 39 or len(prior_paths) != 39:
        issues.append({'issue': 'Original 162/39 episode coverage differs'})
    return {
        'checked_at': now(), 'round': 'final-v1', 'original_archive_sha256': public['archive_sha256'],
        'archived_evidence': evidence, 'server_runtime_24576_verified': server_ok,
        'archived_server_startup_lines': startup_lines,
        'retained_judge_calls': len(rows), 'earlier_client_guard_calls': len(missing),
        'earlier_client_guard_capacity': 16384, 'later_client_guard_capacity': 24576,
        'earlier_max_reserved_tokens': max(r['reserved_tokens'] for r in missing),
        'all_saved_judge_inputs_unpruned': all(r['context']['dropped_messages'] == 0 for r in rows),
        'effective_context_check_pass': server_ok and not issues,
        'client_guard_identical_for_every_original_call': False,
        'issues': issues, 'records': rows,
        'interpretation': 'Original server used 24576 throughout. The first 39 retained calls used the earlier 16384 client guard, fit that guard, and dropped zero messages; their hashes match the archived pre-recovery scores. The later 123 used the 24576 adapter. This difference did not alter the retained judge inputs. It must still be disclosed; this is not proof of identical hardware load, cache state, or deterministic outputs. No model requests, rescoring or raw-record changes are performed.'
    }


if __name__ == '__main__':
    result = verify()
    destination = ROOT / 'artifacts' / CAMPAIGN / 'original-effective-context-verification.json'
    if destination.exists():
        raise FileExistsError('Audit already exists; inspect rather than overwrite')
    save(destination, result)
    print(json.dumps({k: v for k, v in result.items() if k not in {'records', 'archived_evidence'}}, ensure_ascii=False))
