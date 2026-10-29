"""Independently verify a downloaded repeat evidence ZIP; never modify raw data."""
import argparse
import hashlib
import json
from pathlib import PurePosixPath
import zipfile

from repeat_common import CAMPAIGN, NAMES, ROOT, inspect, now, read, save, sha
from repeat_pair_comparison import actor_field_differences


def verify(name):
    if name not in NAMES[1:]:
        raise ValueError('Expected one of the two authorized new rounds')
    gate = read(ROOT / 'runtime' / CAMPAIGN / (name + '-gate.json'))
    receipt = gate['release_verified']
    path = ROOT / 'deliverables' / (name + '-evidence-remote-verified.zip')
    if not receipt['anonymous_download_verified'] or sha(path) != receipt['sha256']:
        raise ValueError('Downloaded archive digest/access receipt not verified')
    status = inspect(ROOT / 'runs' / name)
    if not status['complete']:
        raise ValueError('Local complete scored dataset required')
    prefix = 'runs/' + name + '/repeat-0/'
    with zipfile.ZipFile(path) as archive:
        entries = archive.namelist()
        if len(entries) != len(set(entries)) or archive.testzip() is not None:
            raise ValueError('ZIP duplicate name or CRC failure')
        if any(PurePosixPath(n).is_absolute() or '..' in PurePosixPath(n).parts or ':' in n for n in entries):
            raise ValueError('Unsafe ZIP entry name')
        manifest = json.loads(archive.read('PACKAGE_MANIFEST.json'))
        if len(manifest) != len({r['path'] for r in manifest}):
            raise ValueError('Duplicate manifest entry')
        if set(entries) != {r['path'] for r in manifest} | {'PACKAGE_MANIFEST.json', 'CONTENTS.txt'}:
            raise ValueError('Manifest does not cover every evidence entry')
        for row in manifest:
            data = archive.read(row['path'])
            if len(data) != row['bytes'] or hashlib.sha256(data).hexdigest() != row['sha256']:
                raise ValueError('Entry size/SHA mismatch: ' + row['path'])
        counts = {suffix: sum(n.startswith(prefix) and n.endswith('/' + suffix) for n in entries)
                  for suffix in ['result.json', 'agent-record.json', 'events.jsonl', 'failure-record.json']}
        if any(counts[s] != 162 for s in ['result.json', 'agent-record.json', 'events.jsonl']):
            raise ValueError('Incomplete 162-episode raw archive')
        if counts['failure-record.json'] != status['failures']:
            raise ValueError('Failure count mismatch')
        raw = [r for r in manifest if r['path'].startswith(prefix) and
               r['path'].rsplit('/', 1)[-1] in counts]
        if any(sha(ROOT / r['path']) != r['sha256'] for r in raw):
            raise ValueError('Sealed raw sources differ from the local analyzed sources')
        keys = set()
        for entry in entries:
            if not entry.startswith(prefix) or not entry.endswith('/result.json'):
                continue
            row = json.loads(archive.read(entry))
            actor = json.loads(archive.read(entry.removesuffix('result.json') + 'agent-record.json'))
            if actor_field_differences(actor, row):
                raise ValueError('Scored fields changed execution evidence: ' + entry)
            aggregate = row['eval_result']['aggregate']
            if row['status'] != 'evaluated' or not row['eval_result']['valid']:
                raise ValueError('Invalid retained score')
            for field in ['task_fulfillment_mean', 'grounding_mean', 'planning_and_efficiency_mean']:
                value = aggregate[field]
                if type(value) not in [int, float] or not 1 <= value <= 10:
                    raise ValueError('Invalid score range/type')
            key = (row['repeat'], row['strategy'], row['version'], row['idx'])
            if key in keys:
                raise ValueError('Duplicate episode identity')
            keys.add(key)
        logs = [f'runtime/{CAMPAIGN}/{name}-{phase}.log' for phase in ['execution', 'scoring', 'summary']]
        if not all(n in entries for n in logs):
            raise ValueError('Closed phase logs missing')
        extra = {}
        if name == NAMES[2]:
            copy = f'artifacts/{CAMPAIGN}/original-local-serialization/no_update-iter5-113.json'
            expected = '7227279529b71bbe8c95cac2d43c7935b20faeca3e56b3d89170e43205cc4335'
            if hashlib.sha256(archive.read(copy)).hexdigest() != expected:
                raise ValueError('Original local serialization bytes missing/changed')
            frozen_name = f'artifacts/{CAMPAIGN}/r3-execution-freeze.json'
            frozen = json.loads(archive.read(frozen_name))
            for row in frozen['records']:
                agent = 'runs/' + name + '/' + row['episode'].removesuffix('result.json') + 'agent-record.json'
                if hashlib.sha256(archive.read(agent)).hexdigest() != row['pre_scoring_sha256']:
                    raise ValueError('Sealed actor differs from execution freeze')
                if hashlib.sha256(archive.read(row['events_source'])).hexdigest() != row['events_sha256']:
                    raise ValueError('Sealed events differ from execution freeze')
                if row['raw_failure_source'] and hashlib.sha256(archive.read(row['raw_failure_source'])).hexdigest() != row['raw_failure_sha256']:
                    raise ValueError('Sealed failure differs from execution freeze')
            extra = {'all_162_execution_snapshots_match_sealed_raw_evidence': True,
                     'original_local_serialization_entry': copy,
                     'original_local_serialization_sha256': expected,
                     'case_postscore_review_in_original_zip': f'artifacts/{CAMPAIGN}/r3-case-postscore-review.json' in entries}
    return {'verified_at': now(), 'round': name, 'archive': path.relative_to(ROOT).as_posix(),
            'archive_sha256': sha(path), 'archive_bytes': path.stat().st_size,
            'manifest_entries': len(manifest), 'all_entry_sizes_hashes_and_crc_pass': True,
            'raw_counts': counts, 'unique_scored_episodes': len(keys),
            'all_raw_sources_match_local_analyzed_dataset': True,
            'all_scored_results_preserve_actor_fields': True,
            'closed_phase_logs': logs, 'archive_access_receipt': receipt['verified_at'],
            'scope': 'Independent examination of the actual cached anonymous remote download. Later analysis/gate/source-code additions are on the branch and are not claimed to be inside this immutable ZIP.', **extra}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('round', choices=NAMES[1:])
    args = parser.parse_args()
    output = ROOT / 'artifacts' / CAMPAIGN / ('r3-independent-archive-verification.json' if args.round == NAMES[2] else 'r2-independent-archive-verification.json')
    if output.exists():
        raise FileExistsError('Verification already recorded; inspect rather than overwrite')
    result = verify(args.round)
    save(output, result)
    print(json.dumps(result, ensure_ascii=False))
