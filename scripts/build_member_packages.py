"""Partition a committed project into six planned work packages, without authorship claims."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPO = 'https://github.com/lingenxin3-sketch/pe6203-tool-harness-adaptation'
MEMBERS = tuple('abcdef')
A_SCRIPTS = {'windows_loader.mjs'}
B_SCRIPTS = {'probe_servers.py'}
C_SCRIPTS = {'audit_experiment.py', 'audit_server_sources.py', 'download_runtime.py',
             'prepare_servers.py', 'repeat_campaign.py', 'repeat_preflight.py',
             'repeat_runner.py', 'repeat_supervise_existing.py', 'repeat_validate_path.py',
             'resume_scoring.py', 'run_full_pipeline.py', 'start-judge.ps1',
             'start-local-model.ps1', 'stop-local-model.ps1', 'verify_downloads.py',
             'verify_final_workflow.py'}
D_SCRIPTS = {'analyze_comparisons.py', 'calibrate_judge.py', 'check_judge_context.py',
             'judge_with_capacity.py', 'plot_results.py', 'repeat_common.py',
             'repeat_original_context_audit.py', 'repeat_pair_comparison.py',
             'repeat_verify_archive.py', 'write_result_tables.py'}
E_SCRIPTS = {'check_saved_artifacts.py', 'demo_evidence.py', 'finalize_failed_episodes.py',
             'inspect_tool_errors.py'}
F_SCRIPTS = {'build_submission.py', 'render_report.py', 'repeat_publish.py',
             'write_final_report.py', 'build_member_packages.py'}


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def owner(name):
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name:
        raise ValueError('Unsafe source path: '+name)
    if name.startswith('contributions/members/'):
        member = p.parts[2].split('_',1)[0].lower()
        if member not in MEMBERS: raise ValueError('Unknown member directory: '+name)
        return member
    if name == 'README.md' or name.startswith(('contributions/', 'output/pdf/')):
        return 'f'
    if name in {'.gitattributes', '.gitignore', 'pyproject.toml', 'requirements-lock.txt', 'requirements-report.txt'}:
        return 'c'
    if name.startswith('tool_adapt/'):
        if p.name == 'knowledge.py': return 'b'
        if p.name == 'experiment.py': return 'c'
        if p.name in {'official.py', 'results.py'}: return 'd'
        if p.name in {'__init__.py', '__main__.py', 'agent.py', 'cli.py', 'llm.py', 'mcp_runtime.py'}: return 'a'
    if name.startswith('scripts/'):
        for member, names in zip(MEMBERS, [A_SCRIPTS, B_SCRIPTS, C_SCRIPTS, D_SCRIPTS, E_SCRIPTS, F_SCRIPTS]):
            if p.name in names: return member
    if name.startswith('tests/'):
        test_owners = {'test_context.py':'a', 'test_knowledge.py':'b',
                       'test_protocol.py':'c', 'test_repeats.py':'c',
                       'test_judge_capacity.py':'d', 'test_failure_accounting.py':'e',
                       'test_packaging.py':'f', 'test_member_packages.py':'f'}
        if p.name in test_owners: return test_owners[p.name]
    if name.startswith('configs/'):
        return 'b' if p.name == 'ablation-no-dependencies.json' else 'c'
    if name.startswith(('archive/development/', 'archive/progress/')): return 'c'
    if name.startswith('docs/'):
        if p.name.startswith('CASE_') or p.name in {'TASK_REVIEW_GUIDE_ZH.md', '第一新增轮案例核查.md', '第二新增轮案例核查.md'}: return 'e'
        if p.name in {'EXPERIMENT_PROTOCOL.md', '冻结与故障协议.md'}: return 'c'
        if p.name in {'第2轮结果.md', '第3轮结果.md', '原轮与第二新增轮对照.md'}: return 'd'
        if p.name in {'REPORT.md', 'REPRODUCTION.md', 'REQUIREMENTS_EVIDENCE_ZH.md',
                       'ACCEPTANCE_CHECKLIST.md', 'ACCEPTANCE_CHECKLIST_ORIGINAL.md',
                       '交付与核验.md', '状态.md'}: return 'f'
    if name.startswith('artifacts/inventory/'): return 'b'
    if name.startswith('artifacts/incidents/'): return 'e'
    if name.startswith(('artifacts/figures/', 'artifacts/judge-calibration/')): return 'd'
    if name.startswith('artifacts/repeats-20261029/'):
        if any(k in p.name for k in ['case-', 'failure', 'failures', 'scoring-discrepancy', 'score-evidence']): return 'e'
        if any(k in p.name for k in ['metrics', 'comparison', 'paired-evidence', 'fairness',
                                     'context', 'original-public', 'original-local-serialization',
                                     'no_update-iter5-113', 'independent-statistics']): return 'd'
        if any(k in p.name for k in ['publication', 'release', 'remote-verification', 'requirements-audit']): return 'f'
        return 'c'
    if name.startswith('artifacts/'):
        if p.name in {'final-result-tables.md', 'final-report-data.json', 'judge-capacity-amendment.json', 'judge-runtime.json'}: return 'd'
        if p.name == 'final-delivery-checks.json': return 'f'
        if p.name in {'coverage.json', 'dependency-lock.json', 'dependency-revisions.json', 'reproduction-checks.json', 'server-source-audit.json'}: return 'c'
    raise ValueError('No reviewed responsibility rule for: '+name)


def partition(paths):
    paths = list(paths)
    if len(paths) != len(set(paths)): raise ValueError('Duplicate source paths')
    groups = {m: [] for m in MEMBERS}
    for path in sorted(paths): groups[owner(path)].append(path)
    assert sum(map(len, groups.values())) == len(paths)
    return groups


def write_ownership():
    names = [n for n in git('ls-files', '-z').decode('utf-8').split('\0') if n]
    groups = partition(names)
    data = {'status':'planned_responsibilities_not_completed_contributions',
            'scope':'Complete experiments/repeats-20261029 snapshot; main is a subset. ZIP manifests pin the exact source commit.',
            'total_files':len(names), 'overlap':0, 'members':{m:{'count':len(v),'files':v} for m,v in groups.items()}}
    (ROOT/'contributions/ownership.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return data


def sensitive(data):
    return bool(re.search(rb'(?:gh[pousr]_|github_pat_|sk-|hf_)[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----', data))


def build(ref, output):
    commit = git('rev-parse', ref+'^{commit}').decode().strip()
    paths = [n for n in git('ls-tree', '-r', '--name-only', '-z', commit).decode('utf-8').split('\0') if n]
    groups = partition(paths)
    if any(not v for v in groups.values()): raise ValueError('Every member needs a substantive file set')
    plan = json.loads(git('show', commit+':contributions/roles.json'))
    ownership = json.loads(git('show', commit+':contributions/ownership.json'))
    if {m:ownership['members'][m]['files'] for m in MEMBERS} != groups:
        raise ValueError('Committed responsibility map is stale; review and regenerate it')
    output = output.resolve()
    if output.exists(): raise FileExistsError('Preserve existing package directory: '+str(output))
    output.mkdir(parents=True)
    index = {'source_commit':commit,'status':'planned_work_packages_not_evidence_of_personal_authorship',
             'scope':'All tracked files of the committed project; model weights and full runs are in the shared evidence Releases.',
             'total_owned_files':len(paths),'overlap':0,'packages':[]}
    for member in MEMBERS:
        role = plan['members'][member]
        name = f'PE6203_member_{member}_{role["slug"]}.zip'
        target = output/name
        items = []
        guide = f'''# 成员{member}集合包：{role['title']}

本包用于组织实际工作，不证明成员已经完成开发或核查。现有代码和文档是共同AI协助基线；已登记的负责人见任务卡，实际完成情况由本人记录。

源代码快照：{commit}
完整共同项目：{REPO}/tree/{commit}
个人任务说明：见ROLE_TASKS_ZH.md。

source/内只放本成员负责的文件，每份项目源文件只归一个成员。它是完整系统的一个板块，不能当作独立项目直接运行。执行测试/回放时请使用完整共同仓库和复现环境；本包不含模型权重或完整runs目录，原始证据仍在三轮Release中。

成员应亲自完成任务卡要求的检查、分析或修改，保留命令输出、案例路径和结论，再填写实际贡献记录。若修改冻结核心代码，新增实验必须另存目录并标明新版本，不能把旧分数归给新代码。请勿覆盖原始结果、旧ZIP或同学负责的文件。

提交建议：保留完整共同仓库链接、个人集合包与本人填写的实际贡献记录；如有修改，附本人的真实提交/差异。六个包共同组成一个项目，不应冒充六套独立原创系统。
'''
        with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            z.writestr('PACKAGE_GUIDE_ZH.md',guide)
            z.writestr('ROLE_TASKS_ZH.md',git('show',commit+f':contributions/roles/{member}.md'))
            for path in groups[member]:
                data=git('show',commit+':'+path)
                if sensitive(data): raise ValueError('Credential check failed: '+path)
                blob=git('rev-parse',commit+':'+path).decode().strip()
                z.writestr('source/'+path,data)
                items.append({'path':path,'archive_path':'source/'+path,'bytes':len(data),
                              'sha256':hashlib.sha256(data).hexdigest(),'git_blob_sha':blob})
            manifest={'member':member,'role':role['title'],'source_commit':commit,
                      'status':'planned_responsibility','owned_file_count':len(items),'files':items}
            z.writestr('PACKAGE_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
        with zipfile.ZipFile(target) as z:
            if z.testzip(): raise ValueError('ZIP CRC failed')
            for item in items:
                if hashlib.sha256(z.read(item['archive_path'])).hexdigest()!=item['sha256']:
                    raise ValueError('Packaged source mismatch: '+item['path'])
        index['packages'].append({'member':member,'role':role['title'],'file':name,
                                  'owned_file_count':len(items),'bytes':target.stat().st_size,
                                  'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
    (output/'work-packages-index.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output/'SHA256SUMS.txt').write_text(''.join(p['sha256']+'  '+p['file']+'\n' for p in index['packages']),encoding='ascii')
    return index


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--write-ownership',action='store_true')
    p.add_argument('--ref',default='HEAD')
    p.add_argument('--output',type=Path,default=ROOT/'deliverables/member-work-20261029')
    args=p.parse_args()
    result=write_ownership() if args.write_ownership else build(args.ref,args.output)
    print(json.dumps({k:v for k,v in result.items() if k!='members'},ensure_ascii=False,indent=2))
