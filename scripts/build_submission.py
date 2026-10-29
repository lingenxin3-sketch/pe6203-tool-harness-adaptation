"""Create a portable evidence package only after final results/report are verified."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

from audit_experiment import audit
from analyze_comparisons import compare

ROOT = Path(__file__).resolve().parents[1]

SOURCE_DIRECTORIES = ['tool_adapt', 'scripts', 'tests', 'configs', 'artifacts', 'docs', 'output/pdf', 'archive']
ROOT_FILES = ['README.md', 'pyproject.toml', 'requirements-lock.txt', 'requirements-report.txt', '.gitignore']
INTERNAL_DOCUMENTS = {
    'docs/REPORT_DRAFT.md', 'docs/WORK_STATE.md', 'docs/TEAM_PLAN_ZH.md',
    'docs/DEMO_GUIDE_ZH.md', 'docs/SUBMISSION_GUIDE_ZH.md',
    'docs/WORK_STATE_REPEATS.md', 'docs/追加实验/执行指南.md',
}


def source_files():
    """Package reviewed Git-tracked sources, never ignored or untracked drafts."""
    paths = subprocess.check_output(
        ['git', 'ls-files', '-z', '--', *SOURCE_DIRECTORIES, *ROOT_FILES], cwd=ROOT,
    ).decode('utf-8').split('\0')
    files = set()
    for name in filter(None, paths):
        path = ROOT/name
        if name in INTERNAL_DOCUMENTS or '__pycache__' in path.parts or path.suffix == '.pyc':
            continue
        if not path.resolve().is_relative_to(ROOT.resolve()) or not path.is_file():
            raise ValueError(f'Tracked package source is missing or outside the project: {name}')
        files.add(path)
    return files


def collect():
    for name in ['final-v1', 'ablation-v1', 'final-workflow-verification']:
        result = audit(ROOT/'runs'/name)
        if not result['complete_and_evaluated']:
            raise ValueError(f'{name} is incomplete or failed invariant checks')
    compare(ROOT/'runs/final-v1', ROOT/'runs/ablation-v1')
    for name in ['docs/REPORT.md', 'output/pdf/PE6203_Project4_Report.pdf']:
        if not (ROOT/name).is_file():
            raise FileNotFoundError(f'Final reviewed report missing: {name}')
    files = source_files()
    for name in ['final-v1', 'ablation-v1', 'final-workflow-verification']:
        folder = ROOT/'runs'/name
        files.add(folder/'manifest.json')
        for path in (folder/'analysis').rglob('*'):
            if path.is_file():
                files.add(path)
        for record_path in folder.glob('repeat-*/*/*/*/result.json'):
            record = json.loads(record_path.read_text(encoding='utf-8'))
            for filename in ['result.json', 'agent-record.json', 'events.jsonl']:
                path = record_path.with_name(filename)
                if not path.is_file():
                    raise FileNotFoundError(f'Missing raw evidence: {path}')
                files.add(path)
            failure_receipt = record_path.with_name('failure-record.json')
            if failure_receipt.is_file():
                files.add(failure_receipt)
                files.update(p for p in (record_path.parent/'workspace').glob('*.stderr.log') if p.is_file())
            for kind in ['created', 'modified']:
                for relative in record.get('artifact_changes', {}).get(kind, []):
                    workspace = (record_path.parent/'workspace').resolve()
                    path = (workspace/relative).resolve()
                    if not path.is_relative_to(workspace) or not path.is_file():
                        raise ValueError(f'Invalid artifact path: {path}')
                    files.add(path)
    # The two calibration source cases are cited in the report and retained.
    for run_name in ['dev-v2', 'dev-v3']:
        folder = ROOT/'runs'/run_name
        files.add(folder/'manifest.json')
        record_path = folder/'repeat-0/no_update/original/3/result.json'
        files.add(record_path)
        record = json.loads(record_path.read_text(encoding='utf-8'))
        for kind in ['created', 'modified']:
            for relative in record.get('artifact_changes', {}).get(kind, []):
                path = record_path.parent/'workspace'/relative
                if path.is_file():
                    files.add(path)
    return sorted(files)


if __name__ == '__main__':
    directory = ROOT/'deliverables'
    target = directory/'PE6203_Project4_Submission.zip'
    if target.exists():
        raise FileExistsError(f'Existing evidence package must be preserved: {target}')
    files = collect()
    directory.mkdir(exist_ok=True)
    temporary = target.with_suffix('.zip.tmp')
    manifest = []
    with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            name = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            archive.writestr(name, data)
            manifest.append({'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
        archive.writestr('PACKAGE_MANIFEST.json', json.dumps(manifest, indent=2))
        archive.writestr('PACKAGE_CONTENTS.txt',
            'Code, configuration, report, raw formal evidence and created/modified artifacts.\n'
            'Large model/server binaries and duplicate unchanged benchmark fixtures are omitted.\n'
            'Restore original dependencies and fixtures using docs/REPRODUCTION.md and dependency hashes.\n'
            'Saved trajectories retain original absolute paths for provenance; reruns create new isolated paths.\n'
            'This archive is prepared locally; it has not been uploaded or submitted to an instructor.\n')
    with zipfile.ZipFile(temporary) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP CRC verification failed')
        for entry in manifest:
            if hashlib.sha256(archive.read(entry['path'])).hexdigest() != entry['sha256']:
                raise ValueError('Packaged file hash mismatch: '+entry['path'])
    temporary.replace(target)
    print(json.dumps({'file': str(target), 'files': len(manifest), 'bytes': target.stat().st_size,
                      'verified': True}, indent=2))
