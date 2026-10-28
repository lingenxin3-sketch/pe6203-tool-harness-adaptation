"""Handoff management only; keep the already-running actor process untouched.

Needed after discovering a publication compatibility guard must be strengthened.
Open and retain the existing worker handle, prevent sleep before stopping only
the old management process, wait for the same worker to exit, then resume at
record boundaries with the corrected manager. No actor/model request is retried.
"""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from repeat_common import *
import repeat_campaign as campaign
import repeat_publish as pub

def main():
    p=argparse.ArgumentParser();p.add_argument('--controller',type=int,required=True);p.add_argument('--worker',type=int,required=True);a=p.parse_args()
    kernel=ctypes.windll.kernel32
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
    kernel.TerminateProcess.argtypes=[wintypes.HANDLE,wintypes.UINT]
    kernel.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    command=f"Get-CimInstance Win32_Process -Filter 'ProcessId={a.controller} OR ProcessId={a.worker}' | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    rows=json.loads(subprocess.check_output([campaign.SHELL,'-NoProfile','-Command',command],text=True,encoding='utf-8',creationflags=campaign.NO_WINDOW));rows=[rows] if isinstance(rows,dict) else rows
    by={r['ProcessId']:r['CommandLine'] for r in rows}
    if 'repeat_campaign.py' not in by.get(a.controller,'') or 'repeat_runner.py' not in by.get(a.worker,'') or str(ROOT) not in by[a.worker]:raise RuntimeError('Process identity mismatch; no process stopped')
    worker=kernel.OpenProcess(0x100000|0x1000,False,a.worker);manager=kernel.OpenProcess(0x100000|0x1000|1,False,a.controller)
    if not worker or not manager:raise RuntimeError('Could not retain original process handles')
    guard=None
    if not kernel.SetThreadExecutionState(0x80000001):raise RuntimeError('Sleep prevention handoff failed')
    try:
        if kernel.WaitForSingleObject(worker,0)!=258:raise RuntimeError('Worker is no longer running; inspect before handoff')
        if not kernel.TerminateProcess(manager,90):raise RuntimeError('Could not stop old management process')
        if kernel.WaitForSingleObject(manager,10000)!=0:raise RuntimeError('Old management process not confirmed terminal')
        if kernel.WaitForSingleObject(worker,0)!=258:raise RuntimeError('Worker ended during handoff; inspect saved records')
        import msvcrt
        for _ in range(50):
            try:
                guard=(ROOT/'runtime/dashboard/control.lock').open('a+b');guard.seek(0);msvcrt.locking(guard.fileno(),msvcrt.LK_NBLCK,1);break
            except OSError:
                if guard:guard.close();guard=None
                time.sleep(.1)
        if guard is None:raise RuntimeError('Could not hold model-control lock after handoff')
        def progress():
            campaign.state('executing_existing_worker','原执行进程继续；管理程序已接管，禁止因资源清单差异合并旧轮',child_pid=a.worker,previous_controller=a.controller)
            pub.status('executing_existing_worker','同一执行进程继续运行，未重跑任务。实际输入可比性警示见下方。')
            try:pub.publish('Publish input compatibility warning and existing-worker handoff '+now())
            except Exception as e:save(campaign.RUNTIME/'handoff-publish-error.json',{'at':now(),'error':str(e)})
        save(campaign.RUNTIME/'management-handoff.json',{'at':now(),'old_controller':a.controller,'same_worker':a.worker,'new_supervisor':os.getpid(),'worker_was_live_after_handoff':True,'reason':'Actual resource-list differences require blocking unsupported old/new merge; no actor execution restarted.'})
        progress();last=time.monotonic()
        while kernel.WaitForSingleObject(worker,50000)==258:
            print(now(),'waiting for original worker',a.worker,inspect(ROOT/'runs'/NAMES[1])['found'],flush=True)
            if time.monotonic()-last>=900:progress();last=time.monotonic()
        code=wintypes.DWORD()
        if not kernel.GetExitCodeProcess(worker,ctypes.byref(code)):raise RuntimeError('Could not read original worker exit status')
        if code.value!=0:raise RuntimeError(f'Original actor exited {code.value}; records preserved, no automatic retry')
        guard.close();guard=None
        campaign.state('resuming_management','原执行进程已正常结束；由修正后的管理程序继续评分和发布，已完成记录将全部跳过',child_pid=None)
        with (campaign.RUNTIME/'controller-continuation.stdout.log').open('ab',buffering=0) as out,(campaign.RUNTIME/'controller-continuation.stderr.log').open('ab',buffering=0) as err:
            proc=subprocess.Popen([sys.executable,str(ROOT/'scripts/repeat_campaign.py'),'--resume'],cwd=ROOT,stdout=out,stderr=err,creationflags=campaign.NO_WINDOW)
        save(campaign.RUNTIME/'management-continuation.json',{'at':now(),'launcher_pid':proc.pid,'original_worker_exit':code.value,'mode':'--resume completed-record skip'})
        for _ in range(60):
            time.sleep(1);state=read(campaign.STATE)
            if state.get('pid')!=os.getpid() and state.get('awake_request') and state.get('phase') not in ['blocked','resuming_management']:break
            if proc.poll() is not None:raise RuntimeError('Continuation manager exited; inspect logs')
        else:raise RuntimeError('Continuation manager not confirmed ready')
    except Exception as e:
        campaign.state('handoff_attention',str(e)+'；保留原执行现场，不自动重跑')
        try:pub.status('handoff_attention',str(e));pub.publish('Publish management handoff attention state '+now())
        except Exception:pass
        raise
    finally:
        if guard:guard.close()
        kernel.SetThreadExecutionState(0x80000000);kernel.CloseHandle(worker);kernel.CloseHandle(manager)
if __name__=='__main__':main()
