"""Run the frozen main grid and ablation, then score with the larger local judge."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from finalize_failed_episodes import finalize

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'runtime/pipeline-state.json'
MAIN=ROOT/'runs/final-v1'
ABLATION=ROOT/'runs/ablation-v1'
SHELL=shutil.which('pwsh') or shutil.which('powershell')


def state(phase, **extra):
    payload={'pid':os.getpid(),'phase':phase,'updated_epoch':time.time(),**extra}
    STATE.write_text(json.dumps(payload,indent=2),encoding='utf-8')
    print(json.dumps(payload),flush=True)


def shell_script(name,*args):
    subprocess.run([SHELL,'-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'scripts'/name),*args],cwd=ROOT,check=True)


def health(port):
    last=None
    for _ in range(60):
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/health',timeout=3) as response:
                if json.load(response).get('status')=='ok':
                    return
        except Exception as exc:
            last=exc
        time.sleep(1)
    raise RuntimeError(f'Model port {port} unavailable: {last}')


def command(log_name,*args):
    with (ROOT/'runtime'/log_name).open('w',encoding='utf-8') as log:
        invocation = ([sys.executable, str(ROOT/'scripts/judge_with_capacity.py'), *map(str,args[1:])]
                      if args[0] == 'judge' else [sys.executable,'-m','tool_adapt',*map(str,args)])
        subprocess.run(invocation,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)


def check_executed(folder,expected):
    # Score recorded failed trajectories too; keep the original failure receipt.
    # This does not retry, repair, or invent an agent action.
    finalize(folder, apply=True)
    records=[json.loads(p.read_text(encoding='utf-8')) for p in folder.glob('repeat-*/*/*/*/result.json')]
    invalid=[(r['idx'],r['strategy'],r['version'],r.get('status'),r.get('error')) for r in records if r.get('status')!='awaiting_judge']
    if len(records)!=expected or invalid:
        raise RuntimeError(f'{folder.name}: expected {expected}, found {len(records)}, invalid={invalid}')


if __name__=='__main__':
    owns_state = False
    try:
        continuing = '--continue-after-execution' in sys.argv
        if continuing:
            previous = json.loads(STATE.read_text(encoding='utf-8'))
            if previous.get('phase') != 'failed':
                raise RuntimeError('Continuation requires a terminal failed pipeline; never start alongside a live pipeline')
            if len(list(MAIN.glob('repeat-*/*/*/*/result.json'))) != 162:
                raise RuntimeError('Continuation cannot rerun or fill an incomplete actor grid')
        elif MAIN.exists() or ABLATION.exists():
            raise FileExistsError('Formal output already exists; do not silently rerun or overwrite evidence')
        owns_state = True
        state('actor_start')
        shell_script('start-local-model.ps1');health(8081)
        if not continuing:
            state('main_execution',expected=162)
            command('formal-execution.log','run','--split','test','--output',MAIN)
        check_executed(MAIN,162)
        state('ablation_execution',expected=6)
        if not ABLATION.exists():
            command('ablation-execution.log','run','--split','test','--config',ROOT/'configs/ablation-no-dependencies.json','--output',ABLATION)
        check_executed(ABLATION,6)
        state('switch_to_judge')
        shell_script('stop-local-model.ps1','-Role','actor')
        shell_script('start-judge.ps1');health(8082)
        state('main_judging')
        command('formal-judging.log','judge',MAIN)
        state('ablation_judging')
        command('ablation-judging.log','judge',ABLATION)
        state('aggregation')
        command('formal-summary.log','analyze',MAIN)
        command('ablation-summary.log','analyze',ABLATION)
        state('completed')
    except Exception as exc:
        if owns_state:
            state('failed',error=type(exc).__name__+': '+str(exc))
        raise
