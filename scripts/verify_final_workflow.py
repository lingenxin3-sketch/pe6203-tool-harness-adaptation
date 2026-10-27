"""Verify the frozen final workflow on held-out development task 3 after formal scoring.

This is reproduction verification, not a method-selection or benchmark run.
It must never compete with the active formal pipeline for the local GPU.
"""
import json
from pathlib import Path
import subprocess
import sys

from run_full_pipeline import ROOT, shell_script, health, check_executed
from audit_experiment import audit


if __name__ == '__main__':
    state = json.loads((ROOT/'runtime/pipeline-state.json').read_text(encoding='utf-8'))
    if state['phase'] != 'completed':
        raise RuntimeError('Formal pipeline must finish before final workflow verification')
    for name in ['final-v1', 'ablation-v1']:
        if not audit(ROOT/'runs'/name)['complete_and_evaluated']:
            raise RuntimeError('Formal evidence must pass its full audit first')
    output = ROOT/'runs/final-workflow-verification'
    if output.exists():
        raise FileExistsError('Verification evidence already exists; inspect it rather than overwrite')
    shell_script('stop-local-model.ps1', '-Role', 'judge')
    shell_script('start-local-model.ps1')
    health(8081)
    with (ROOT/'runtime/final-workflow-verification.log').open('w', encoding='utf-8') as log:
        subprocess.run([sys.executable, '-m', 'tool_adapt', 'run', '--split', 'development',
                        '--task-limit', '1', '--output', str(output)], cwd=ROOT,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
        check_executed(output, 9)
        shell_script('stop-local-model.ps1', '-Role', 'actor')
        shell_script('start-judge.ps1')
        health(8082)
        subprocess.run([sys.executable, str(ROOT/'scripts/judge_with_capacity.py'), str(output)], cwd=ROOT,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run([sys.executable, '-m', 'tool_adapt', 'analyze', str(output)], cwd=ROOT,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    report = audit(output)
    (output/'analysis/invariant-audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    final_manifest = json.loads((ROOT/'runs/final-v1/manifest.json').read_text(encoding='utf-8'))
    verification_manifest = json.loads((output/'manifest.json').read_text(encoding='utf-8'))
    if verification_manifest['task_ids'] != [3] or verification_manifest['source_hashes'] != final_manifest['source_hashes']:
        raise RuntimeError('Verification must use held-out task3 and the unchanged final source')
    if not report['complete_and_evaluated']:
        raise RuntimeError('Final workflow verification failed its audit')
    print(json.dumps({'purpose': 'Post-formal reproduction only; excluded from benchmark results',
                      'output': str(output), 'audit': report}, indent=2))
