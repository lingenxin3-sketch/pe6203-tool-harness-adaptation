"""Strict round identity, complete-grid metrics, trace hashes and immutable publication."""
from pathlib import Path
import collections
import hashlib
import json
import math
import statistics
import time
import secrets
from datetime import datetime, timezone, timedelta

ROOT=Path(__file__).resolve().parents[1]
CAMPAIGN='repeats-20261029'
BRANCH='experiments/repeats-20261029'
NAMES=['final-v1','repeat-r2-20261029','final-r3']
POLS=['no_update','full_rewrite','selective_patch']
VERS=['original','iter3','iter5']
def now(): return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True); tmp=p.with_suffix(p.suffix+'.'+secrets.token_hex(4)+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    # Windows scanners/readers can briefly deny rename. This retries only the
    # same local metadata replacement, never an experiment or a model request.
    for attempt in range(20):
        try:tmp.replace(p);return
        except PermissionError:
            if attempt==19:raise
            time.sleep(.1)
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def grid(m):
    c=m['config']; return {(rep,p,v,i) for rep in range(c['repeats']) for p in c['strategies'] for v in c['versions'] for i in m['task_ids']}
def inspect(folder):
    if not (folder/'manifest.json').is_file():
        return {'name':folder.name,'expected':162,'found':0,'scored':0,'failures':0,'missing':162,'complete':False,'issues':[],'status_counts':{}}
    m=read(folder/'manifest.json'); expected=grid(m); seen=set(); issues=[]; rows=[]
    for path in sorted(folder.glob('repeat-*/*/*/*/result.json')):
        try:
            r=read(path); key=(r['repeat'],r['strategy'],r['version'],r['idx'])
            if key in seen or key not in expected:issues.append('duplicate/unexpected '+str(key))
            if tuple(path.relative_to(folder).parts[:4])!=(f'repeat-{key[0]}',key[1],key[2],str(key[3])):issues.append('path/key mismatch '+str(key))
            seen.add(key); rows.append(r)
        except (ValueError,KeyError,OSError) as e:issues.append(str(path.relative_to(folder))+': '+str(e))
    def valid(r):
        a=r.get('eval_result',{}).get('aggregate',{})
        return r.get('status')=='evaluated' and r.get('eval_result',{}).get('valid') and all(type(a.get(k)) in [int,float] and math.isfinite(a[k]) and 1<=a[k]<=10 for k in ['task_fulfillment_mean','planning_and_efficiency_mean'])
    scored=sum(bool(valid(r)) for r in rows)
    return {'name':folder.name,'expected':len(expected),'found':len(rows),'scored':scored,
        'failures':sum(r.get('execution_status')=='infrastructure_error' or r.get('status')=='infrastructure_error' for r in rows),
        'missing':len(expected-seen),'issues':issues,'status_counts':dict(collections.Counter(r.get('status') for r in rows)),
        'complete':seen==expected and len(rows)==len(expected) and scored==len(expected) and not issues}
def compatibility(a,b):
    checks={k:a.get(k)==b.get(k) for k in ['config','task_ids','coverage','inventory_hashes','source_hashes','split']}
    return {'compatible':all(checks.values()),'checks':checks,'meaning':'Output directory and round label differ; all experiment settings and recorded protocol hashes must match exactly.'}
def resource_listing(row):
    calls=row.get('model_calls',{}).get('agent',[])
    if not calls:return None
    content=calls[0]['request']['messages'][0].get('content','')
    prefix='Existing resource files (use these exact paths, never guess filenames):\n'
    if prefix not in content:return None
    return content.split(prefix,1)[1].split('\nUsage notes:',1)[0].splitlines()
def round_compatibility(a,b):
    result=compatibility(read(a/'manifest.json'),read(b/'manifest.json'))
    different=[];unavailable=[];checked=0
    for p in sorted(b.glob('repeat-*/*/*/*/result.json')):
        other=a/p.relative_to(b)
        if not other.exists():unavailable.append(p.relative_to(b).as_posix());continue
        aa=resource_listing(read(other));bb=resource_listing(read(p))
        if aa is None or bb is None:unavailable.append(p.relative_to(b).as_posix());continue
        checked+=1
        if aa!=bb:different.append({'episode':p.relative_to(b).as_posix(),'only_first':sorted(set(aa)-set(bb)),'only_second':sorted(set(bb)-set(aa))})
    result.update(resource_lists_checked=checked,resource_list_differences=different,unavailable_input_checks=unavailable,
        inputs_complete=checked==162 and not unavailable,
        input_limitation='Windows path length can change the resource listing shown to the model even when fixture bytes and manifest hashes match. No claim that these omitted PDFs caused a score change.')
    result['compatible']=result['compatible'] and checked==162 and not different and not unavailable
    return result
def metrics(folder):
    status=inspect(folder)
    if not status['complete']:raise ValueError('Complete scored grid required: '+str(status))
    m=read(folder/'manifest.json'); rows=[read(p) for p in folder.glob('repeat-*/*/*/*/result.json')]; cfg=m['config']
    result=[]; affected={(x['idx'],x['version']):x['affected'] for x in m['coverage']}
    tf=lambda r:r['eval_result']['aggregate']['task_fulfillment_mean']; pe=lambda r:r['eval_result']['aggregate']['planning_and_efficiency_mean']
    by={(r['repeat'],r['strategy'],r['version'],r['idx']):r for r in rows}
    for pol in cfg['strategies']:
        group=[r for r in rows if r['strategy']==pol]; ecs=[]; stages={}; cohorts=[]; costs={}
        for rep in range(cfg['repeats']):
            for idx in m['task_ids']:
                xs=[tf(by[rep,pol,v,idx]) for v in cfg['versions']]; ecs.append(statistics.mean(xs)-statistics.pstdev(xs))
        for v in cfg['versions']:
            sub=[r for r in group if r['version']==v]; stages[v]={'n':len(sub),'tf':statistics.mean(map(tf,sub)),'pe':statistics.mean(map(pe,sub))}
        for v in cfg['versions'][1:]:
            for changed in [True,False]:
                sub=[r for r in group if r['version']==v and affected[r['idx'],v]==changed]
                cohorts.append({'version':v,'cohort':'changed' if changed else 'unaffected','n':len(sub),
                    'tf':statistics.mean(map(tf,sub)) if sub else None,
                    'delta_own_early':statistics.mean(tf(r)-tf(by[r['repeat'],pol,'original',r['idx']]) for r in sub) if sub else None,
                    'delta_same_version_no_update':statistics.mean(tf(r)-tf(by[r['repeat'],'no_update',v,r['idx']]) for r in sub) if sub else None})
        for kind in ['update','agent','judge']:
            calls=[c for r in group for c in r.get('model_calls',{}).get(kind,[])]
            costs[kind]={'calls':len(calls),'tokens':sum(c['usage'].get('total_tokens',0) for c in calls),
                'request_seconds':sum(c['usage'].get('wall_seconds',0) for c in calls),'api_usd':sum(c['usage'].get('api_usd',0) for c in calls)}
        result.append({'strategy':pol,'ecs':statistics.mean(ecs),'stages':stages,'cohorts':cohorts,'costs':costs})
    return {'name':folder.name,'collected_at':now(),'status':status,'strategies':result,'source_manifest_sha256':sha(folder/'manifest.json')}
def merge_views(folders):
    if len(set(p.resolve() for p in folders))!=len(folders):raise ValueError('Duplicate round source')
    ms=[read(p/'manifest.json') for p in folders]
    if any(not compatibility(ms[0],m)['compatible'] for m in ms[1:]):raise ValueError('Incompatible rounds cannot be merged')
    if ms[0].get('split')=='test' and any(not round_compatibility(folders[0],p)['compatible'] for p in folders[1:]):raise ValueError('Actual input resource lists differ or are unverified; cannot merge rounds')
    views=[metrics(p) for p in folders]; combined=[]
    for pol in ms[0]['config']['strategies']:
        parts=[next(s for s in x['strategies'] if s['strategy']==pol) for x in views]
        combined.append({'strategy':pol,'ecs_mean':statistics.mean(p['ecs'] for p in parts),'ecs_sample_sd':statistics.stdev(p['ecs'] for p in parts) if len(parts)>1 else None,
            'stages':{v:{k:statistics.mean(p['stages'][v][k] for p in parts) for k in ['tf','pe']}|{'task_count':len(ms[0]['task_ids']),'observations':sum(p['stages'][v]['n'] for p in parts),
                'tf_round_sample_sd':statistics.stdev(p['stages'][v]['tf'] for p in parts) if len(parts)>1 else None,
                'pe_round_sample_sd':statistics.stdev(p['stages'][v]['pe'] for p in parts) if len(parts)>1 else None} for v in ms[0]['config']['versions']},
            'costs':{kind:{key:sum(p['costs'][kind][key] for p in parts) for key in ['calls','tokens','request_seconds','api_usd']} for kind in ['update','agent','judge']},
            'cohorts':[{**parts[0]['cohorts'][i], 'n':sum(p['cohorts'][i]['n'] for p in parts),
                **{k:statistics.mean(p['cohorts'][i][k] for p in parts) if parts[0]['cohorts'][i][k] is not None else None for k in ['tf','delta_own_early','delta_same_version_no_update']}} for i in range(len(parts[0]['cohorts']))]})
    return {'collected_at':now(),'rounds':views,'total_records':sum(x['status']['found'] for x in views),'strategies':combined,
        'limits':'Same fixed seed/temperature repeats; n=18 distinct tasks, not independent new tasks. SD is across round means. No significance or universal superiority claims. Original one-run ablation is excluded.'}
