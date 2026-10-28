"""Read-only compatibility audit; receipts are written only under the new campaign."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'scripts'))
from audit_experiment import audit
from audit_server_sources import audit as audit_servers
from tool_adapt.knowledge import digest

DEST=ROOT/'artifacts/repeats-20261029'
def sha(path):
    with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def stamp(): return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
def main():
    DEST.mkdir(parents=True,exist_ok=True)
    baseline=ROOT/'runs/final-v1'; m=json.loads((baseline/'manifest.json').read_text(encoding='utf-8'))
    result={'collected_at':stamp(),'baseline':'runs/final-v1','guide_sha256':sha(ROOT/'docs/追加实验/执行指南.md'),
            'config_matches_original':json.loads((ROOT/'configs/experiment.json').read_text())==m['config'],
            'baseline_audit':audit(baseline),'baseline_manifest_sha256':sha(baseline/'manifest.json'),
            'dependencies':[], 'servers':[],
            'source_hashes_match':all(digest((ROOT/p).read_text(encoding='utf-8'))==v for p,v in m['source_hashes'].items()),
            'upstream_commit':subprocess.check_output(['git','-C',str(ROOT/'upstream'),'rev-parse','HEAD'],text=True).strip(),
            'raw_evidence_hashes':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in baseline.rglob('*')
                                   if p.is_file() and 'workspace' not in p.parts and 'analysis' not in p.parts}}
    for e in json.loads((ROOT/'artifacts/dependency-lock.json').read_text()):
        p=ROOT/'runtime/downloads'/e['file']; ok=p.is_file() and p.stat().st_size==e['bytes'] and sha(p)==e['sha256']
        result['dependencies'].append({'file':e['file'],'passed':ok}); print('dependency',e['file'],ok,flush=True)
    for v in m['config']['versions']:
        r=audit_servers(v); result['servers'].append(r); print('servers',v,r['passed'],flush=True)
    result['compatible_preconditions']=all([result['baseline_audit']['complete_and_evaluated'],result['config_matches_original'],
        result['source_hashes_match'],result['upstream_commit']==m['config']['upstream_commit'],
        all(e['passed'] for e in result['dependencies']),all(e['passed'] for e in result['servers'])])
    result['interpretation']='Same fixed seed and temperature repeats measure execution stability, not independent sampling uncertainty. New manifest, runtime and scorer receipts must still be checked per round.'
    (DEST/'preflight.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['raw_evidence_hashes','baseline_audit','servers','dependencies']},ensure_ascii=False,indent=2))
    return 0 if result['compatible_preconditions'] else 1
if __name__=='__main__': raise SystemExit(main())
