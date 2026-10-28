"""Resume-only boundary adapter for the frozen runner. No model/method code edits.

Completed episodes are read and their knowledge restored; they are never executed
again. An existing workspace without a committed result stops recovery. It cannot
be discarded or retried automatically. The original runner still handles all new
episodes and its normal per-episode exceptions.
"""
import argparse
import ast
import asyncio
from copy import deepcopy
import inspect
from pathlib import Path
import sys
import types

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/'scripts'))
from tool_adapt import experiment as exp
from tool_adapt.knowledge import Knowledge,digest
from repeat_common import read,sha,save,now

def resume_record(output,repeat,strategy,version,case,manifest):
    folder=output/f'repeat-{repeat}'/strategy/version/str(case['idx']); path=folder/'result.json'
    if path.exists():
        r=read(path)
        if (r.get('idx'),r.get('repeat'),r.get('strategy'),r.get('version'))!=(case['idx'],repeat,strategy,version):raise ValueError('Resume identity mismatch')
        if r.get('manifest_hash')!=digest(manifest) or r.get('question')!=case['question']:raise ValueError('Resume source mismatch')
        if r.get('status') not in ['awaiting_judge','evaluated','infrastructure_error','judge_failed']:raise ValueError('Unknown saved state; manual inspection required')
        if not r.get('knowledge'):raise ValueError('No saved tool knowledge; stop without rerunning')
        k=r['knowledge']; return Knowledge(deepcopy(k['tools']),deepcopy(k['notes']),k.get('version','Early'))
    if folder.exists():raise ValueError('Interrupted workspace has no committed result; preserved, no automatic retry: '+str(folder))
    return None

def build_runner():
    tree=ast.parse(inspect.getsource(exp.run_experiment)); fn=tree.body[0]
    # Remove only the directory-exists refusal. validate_manifest below replaces it
    # with an exact-match gate; create-new semantics remain for fresh outputs.
    removed=0
    for node in list(fn.body):
        if isinstance(node,ast.If) and ast.unparse(node.test)=='output.exists()':fn.body.remove(node);removed+=1
    targets=[n for n in ast.walk(fn) if isinstance(n,ast.For) and isinstance(n.target,ast.Name) and n.target.id=='version']
    if removed!=1 or len(targets)!=1:raise RuntimeError('Frozen runner layout changed; adapter refuses')
    targets[0].body[0:0]=ast.parse("saved_knowledge = resume_record(output, repeat, strategy, version, case, manifest)\nif saved_knowledge is not None:\n    knowledge = saved_knowledge\n    continue").body
    ast.fix_missing_locations(tree); namespace=dict(vars(exp)); namespace['resume_record']=resume_record
    namespace['save']=validate_manifest_save
    exec(compile(tree, '<documented-resume-boundary-adapter>', 'exec'),namespace)
    return namespace['run_experiment']

def validate_manifest_save(path,value):
    if path.name=='manifest.json' and path.exists():
        if read(path)!=value:raise ValueError('Existing manifest differs; cannot resume')
        return
    exp.save(path,value)

async def execute(output,config,split='test',task_limit=None,resume=False):
    if output.exists() and not resume:raise FileExistsError('Use explicit --resume; never overwrite an existing run')
    if resume and not (output/'manifest.json').exists():raise ValueError('No manifest to resume')
    baseline=read(ROOT/'runs/final-v1/manifest.json')
    if split=='test' and read(config)!=baseline['config']:raise ValueError('Formal configuration differs from original round')
    for p,h in baseline['source_hashes'].items():
        if digest((ROOT/p).read_text(encoding='utf-8'))!=h:raise ValueError('Frozen core changed: '+p)
    runner=build_runner() if resume else exp.run_experiment
    return await runner(ROOT,config,output,split=split,task_limit=task_limit)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('output',type=Path);p.add_argument('--config',type=Path,default=ROOT/'configs/experiment.json'); p.add_argument('--resume',action='store_true')
    a=p.parse_args();asyncio.run(execute(a.output.resolve(),a.config.resolve(),resume=a.resume))
