"""Download public, pinned experiment dependencies; never installs globally."""
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import subprocess
import time
import sys

ROOT = Path(__file__).resolve().parents[1]
DOWNLOADS = ROOT / 'runtime' / 'downloads'
PINNED = {row['file']: row['pinned_source'] for row in
          json.loads((ROOT/'artifacts/dependency-revisions.json').read_text(encoding='utf-8'))}
URLS = {
    'llama.zip': 'https://github.com/ggml-org/llama.cpp/releases/download/b11900/llama-b11900-bin-win-cuda-12.4-x64.zip',
    'cudart.zip': 'https://github.com/ggml-org/llama.cpp/releases/download/b11900/cudart-llama-bin-win-cuda-12.4-x64.zip',
    'qwen3-4b-q4.gguf': 'https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/resolve/main/Qwen3-4B-Instruct-2507-Q4_K_M.gguf?download=true',
    **{f'{v}_servers.zip': f'https://huggingface.co/datasets/anonymous2233/evol-servers/resolve/main/{v}_servers.zip?download=true' for v in ['original', 'iter3', 'iter5']},
}
JUDGE_URLS = {f'qwen2.5-7b-instruct-q4_k_m-0000{i}-of-00002.gguf':
    f'https://huggingface.co/Qwen/Qwen2.5-7B-Instruct-GGUF/resolve/main/qwen2.5-7b-instruct-q4_k_m-0000{i}-of-00002.gguf?download=true'
    for i in [1, 2]}

def download(item):
    name, url = item
    # Preserve the exact bytes used by the experiment even if a repository's
    # main branch later changes. Revision headers were checked against SHA-256.
    url = PINNED.get(name, url)
    dest = DOWNLOADS / name
    partial = dest.with_suffix(dest.suffix + '.part')
    if not dest.exists():
        subprocess.run(['curl.exe', '-fL', '--retry', '4', '--connect-timeout', '30', '-C', '-', '-o', str(partial), url], check=True, stdout=subprocess.DEVNULL, stderr=(DOWNLOADS / (name + '.log')).open('w'))
        partial.replace(dest)
    digest = hashlib.file_digest(dest.open('rb'), 'sha256').hexdigest()
    result = {'file': name, 'source': url, 'bytes': dest.stat().st_size, 'sha256': digest}
    (DOWNLOADS / (name + '.json')).write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)
    return result

if __name__ == '__main__':
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        files = JUDGE_URLS if '--judge-only' in sys.argv else URLS
        futures = [pool.submit(download, item) for item in files.items()]
        for future in as_completed(futures):
            future.result()
