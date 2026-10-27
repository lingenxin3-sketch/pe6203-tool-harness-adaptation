"""Read-only byte comparison of extracted official packages against their archives."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def audit(version):
    directory = ROOT / 'runtime' / 'servers' / version
    extraction = json.loads((directory / 'extraction.json').read_text(encoding='utf-8'))
    prefixes = tuple(package + '/' for package in extraction['packages'])
    missing, modified = [], []
    count = 0
    with zipfile.ZipFile(ROOT / 'runtime' / 'downloads' / f'{version}_servers.zip') as archive:
        for entry in archive.infolist():
            if entry.is_dir() or not entry.filename.startswith(prefixes):
                continue
            target = directory / entry.filename
            count += 1
            if not target.is_file():
                missing.append(entry.filename)
            elif hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256(archive.read(entry)).digest():
                modified.append(entry.filename)
    return {'version': version, 'checked_archive_files': count, 'missing': missing,
            'modified': modified, 'passed': not missing and not modified,
            'scope': 'All extracted archive members; extra runtime-generated files are not source changes.'}


if __name__ == '__main__':
    records = [audit(version) for version in ['original', 'iter3', 'iter5']]
    destination = ROOT / 'artifacts' / 'server-source-audit.json'
    destination.write_text(json.dumps(records, indent=2), encoding='utf-8')
    print(json.dumps(records, indent=2))
    raise SystemExit(0 if all(record['passed'] for record in records) else 1)
