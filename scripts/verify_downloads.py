"""Verify downloaded bytes against the hashes used by the frozen experiment."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if __name__ == '__main__':
    entries = json.loads((ROOT/'artifacts/dependency-lock.json').read_text(encoding='utf-8'))
    failed = []
    for entry in entries:
        path = ROOT/'runtime/downloads'/entry['file']
        valid = path.is_file() and path.stat().st_size == entry['bytes']
        if valid:
            with path.open('rb') as handle:
                valid = hashlib.file_digest(handle, 'sha256').hexdigest() == entry['sha256']
        print(('OK ' if valid else 'FAIL ') + entry['file'], flush=True)
        if not valid:
            failed.append(entry['file'])
    raise SystemExit(1 if failed else 0)
