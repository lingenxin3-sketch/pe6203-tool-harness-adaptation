"""Whitelist-only publication. Refuse other staged work, branch changes or force pushes."""
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.request
import zipfile
from repeat_common import *

REPO='lingenxin3-sketch/pe6203-tool-harness-adaptation'
PUBLIC=ROOT/'docs/追加实验'; RECEIPTS=ROOT/'artifacts'/CAMPAIGN
def cmd(*args):
    p=subprocess.run(list(map(str,args)),cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    if p.returncode:raise RuntimeError('Command failed: '+str(args[:2])+' '+p.stderr[-1200:]+' '+p.stdout[-1200:])
    return p.stdout.strip()
def sensitive(data):
    patterns=[rb'gh[pousr]_[A-Za-z0-9_]{30,}',rb'github_pat_[A-Za-z0-9_]{30,}',rb'sk-[A-Za-z0-9_-]{30,}',rb'hf_[A-Za-z0-9]{30,}',rb'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----']
    return any(re.search(p,data) for p in patterns)
def allowed(name):return name.startswith('docs/追加实验/') or name.startswith('artifacts/'+CAMPAIGN+'/') or name in ['scripts/repeat_common.py','scripts/repeat_preflight.py','scripts/repeat_runner.py','scripts/repeat_publish.py','scripts/repeat_campaign.py','scripts/repeat_supervise_existing.py','tests/test_repeats.py','docs/WORK_STATE_REPEATS.md']
def publish(message):
    if cmd('git','branch','--show-current')!=BRANCH:raise RuntimeError('Branch changed; refusing publication')
    staged=cmd('git','diff','--cached','--name-only','-z').split('\0')
    if any(n and not allowed(n) for n in staged):raise RuntimeError('Other staged work exists; preserve it and stop')
    paths=[p for d in [PUBLIC,RECEIPTS] for p in d.rglob('*') if p.is_file() and p.suffix in ['.md','.json','.csv']]
    paths += [ROOT/p for p in ['scripts/repeat_common.py','scripts/repeat_preflight.py','scripts/repeat_runner.py','scripts/repeat_publish.py','scripts/repeat_campaign.py','scripts/repeat_supervise_existing.py','tests/test_repeats.py','docs/WORK_STATE_REPEATS.md'] if (ROOT/p).is_file()]
    for p in paths:
        if p.stat().st_size>20_000_000 or sensitive(p.read_bytes()):raise RuntimeError('Size/privacy check failed: '+str(p.relative_to(ROOT)))
    cmd('git','add','--',*[p.relative_to(ROOT).as_posix() for p in paths]);cmd('git','diff','--cached','--check')
    # Review the actual staged bytes, including deletions, without printing secrets.
    staged_diff=cmd('git','diff','--cached','--no-ext-diff','--no-color')
    if sensitive(staged_diff.encode()):raise RuntimeError('Staged privacy check failed')
    if staged_diff:cmd('git','commit','-m',message)
    commit=cmd('git','rev-parse','HEAD');cmd('git','push','origin',f'HEAD:refs/heads/{BRANCH}')
    remote=json.loads(cmd('gh','api',f'repos/{REPO}/branches/{BRANCH}'))['commit']['sha']
    if remote!=commit:raise RuntimeError('Remote commit differs after push')
    evidence={}
    for p in paths:
        relative=p.relative_to(ROOT).as_posix()
        raw=cmd('gh','api',f'repos/{REPO}/contents/{relative}?ref={commit}')
        item=json.loads(raw)
        if item.get('encoding')=='base64':data=base64.b64decode(item['content'])
        else:
            with urllib.request.urlopen(item['download_url'],timeout=60) as r:data=r.read()
        # Git uses LF for text. Compare against committed blob, not CRLF worktree.
        expected=subprocess.check_output(['git','show',f'{commit}:{relative}'],cwd=ROOT)
        if data!=expected:raise RuntimeError('Remote content mismatch '+relative)
        evidence[relative]=hashlib.sha256(data).hexdigest()
    receipt={'verified_at':now(),'commit':commit,'branch':BRANCH,'files':evidence}
    save(ROOT/'runtime'/CAMPAIGN/'last-publish.json',receipt)
    return receipt
def status(phase,message,extra=''):
    PUBLIC.mkdir(parents=True,exist_ok=True)
    statuses=[inspect(ROOT/'runs'/n) for n in NAMES]
    lines=['# 追加实验状态','',f'采集时间：{now()}（新加坡时间 UTC+8）。',f'','阶段：'+phase,'',message,'',
        '| 轮次 | 已保存 / 计划 | 有效评分 | 执行异常 | 缺失 |','|---|---:|---:|---:|---:|']
    for s in statuses:lines.append(f"| {s['name']} | {s['found']} / {s['expected']} | {s['scored']} | {s['failures']} | {s['missing']} |")
    pre=RECEIPTS/'preflight.json'; ok=pre.exists() and read(pre).get('compatible_preconditions')
    lines+=['','旧轮兼容前提核验：'+('通过；新增轮完成后还须核对实际 manifest、运行和评分收据。' if ok else '尚未完成。'),'',
        '当前计数来自完整落盘的 result.json；有效评分不等于任务实际成功。尚未完成的轮次不发布最终平均数。',
        '','运行期间进程请求 Windows 保持唤醒，不更改系统电源计划。断电、合盖、重启和网络故障仍可能中断；定时发布不作保证。计划每 15 分钟更新真实快照，并尽力覆盖 08:00 前的状态。',
        '','第一轮新增完成评分、162 条审计、证据发布及远端验证后才启动第二轮。12:00 是争取目标；若届时尚未启动第二轮则不自动启动，等待团队决定。',
        '','固定 seed=6203、temperature=0，重复反映相同设置下的执行稳定性，不等于独立采样或统计显著性。',
        '','旧 PDF、原结果表和六人演讲稿仍是原轮版本。原依赖扩展对照仍为单次辅助实验，不并入主实验重复。',
        '','[冻结与故障协议](冻结与故障协议.md)　[执行指南](执行指南.md)', '',extra]
    for i in [2,3]:
        if (PUBLIC/f'第{i}轮结果.md').exists():lines.append(f'[第{i}轮结果](第{i}轮结果.md)')
    alert=RECEIPTS/'compatibility-alert.json'
    if alert.exists():lines+=['','## 实际输入可比性警示','',read(alert)['message'],'','[详细核查](../../artifacts/'+CAMPAIGN+'/compatibility-alert.json)']
    (PUBLIC/'状态.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8')
    save(RECEIPTS/'latest-status.json',{'collected_at':now(),'phase':phase,'message':message,'rounds':statuses})

def package(folder):
    if not inspect(folder)['complete']:raise ValueError('Unscored/incomplete evidence cannot be packaged as complete')
    files={folder/'manifest.json'}
    files.update(p for p in (folder/'analysis').rglob('*') if p.is_file())
    for rp in folder.glob('repeat-*/*/*/*/result.json'):
        r=read(rp)
        for name in ['result.json','agent-record.json','events.jsonl']:
            p=rp.with_name(name)
            if not p.is_file():raise ValueError('Required evidence missing: '+str(p))
            files.add(p)
        for name in ['failure-record.json']:
            p=rp.with_name(name)
            if p.exists():files.add(p)
        for kind in ['created','modified']:
            for rel in r.get('artifact_changes',{}).get(kind,[]):
                ws=(rp.parent/'workspace').resolve();p=(ws/rel).resolve()
                if not p.is_relative_to(ws) or not p.is_file():raise ValueError('Artifact outside workspace/missing')
                files.add(p)
    files.update(p for p in RECEIPTS.rglob('*.json') if p.is_file())
    target=ROOT/'deliverables'/f'{folder.name}-evidence.zip'
    if target.exists():raise FileExistsError('Evidence archive already exists; inspect instead of overwriting')
    manifest=[];target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(files):
            data=p.read_bytes();name=p.relative_to(ROOT).as_posix()
            if sensitive(data):raise ValueError('Potential credential in '+name)
            z.writestr(name,data);manifest.append({'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
        z.writestr('PACKAGE_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        z.writestr('CONTENTS.txt','Raw saved calls, trajectories, scores and changed artifacts. Original immutable benchmark fixtures and model weights are omitted; restore using frozen hashes. Original absolute workspace paths are retained as provenance. Local judge errors remain uncorrected.\n')
    with zipfile.ZipFile(target) as z:
        if z.testzip():raise ValueError('ZIP CRC error')
        for item in manifest:
            if hashlib.sha256(z.read(item['path'])).hexdigest()!=item['sha256']:raise ValueError('Archive hash mismatch')
    return target
def release(folder,commit):
    target=package(folder);tag=folder.name+'-evidence';checksum=sha(target)
    sums=target.with_suffix('.sha256');sums.write_text(checksum+'  '+target.name+'\n',encoding='ascii')
    notes=ROOT/'runtime'/CAMPAIGN/(tag+'-notes.md');notes.write_text(f'Completed scored round: {folder.name}, 162 records.\n\nSource commit: {commit}\n\nSHA-256: {checksum}\n\nSee branch docs/追加实验 for results, compatibility and limitations. This is experimental evidence, not a course submission.\n',encoding='utf-8')
    cmd('gh','release','create',tag,str(target),str(sums),'--repo',REPO,'--target',commit,'--title',folder.name+' scored evidence','--notes-file',notes,'--latest=false')
    meta=json.loads(cmd('gh','release','view',tag,'--repo',REPO,'--json','url,assets,tagName,targetCommitish'))
    asset=next(a for a in meta['assets'] if a['name']==target.name)
    # Anonymous download verifies actual public access and byte integrity.
    downloaded=target.with_name(target.stem+'-remote-verified.zip')
    req=urllib.request.Request(asset['url'],headers={'User-Agent':'PE6203-evidence-verifier'})
    with urllib.request.urlopen(req,timeout=180) as response,downloaded.open('wb') as out:
        while chunk:=response.read(1024*1024):out.write(chunk)
    if sha(downloaded)!=checksum:raise RuntimeError('Public downloaded asset SHA-256 differs')
    result={'verified_at':now(),'release':meta,'sha256':checksum,'anonymous_download_verified':True,'source_commit':commit}
    save(RECEIPTS/(folder.name+'-release.json'),result);return result
