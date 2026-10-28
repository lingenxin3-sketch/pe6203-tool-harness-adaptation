"""No-inference filesystem test for the not-yet-started second added round."""
import sys,os,tempfile,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from repeat_common import *
def native(p):return Path('\\\\?\\'+str(p.resolve())) if os.name=='nt' else p
source=ROOT/'upstream/anotation_path'
resources=[p for p in source.rglob('*') if p.is_file()]
fixture_names={((prefix/p.relative_to(source)).as_posix()) for p in resources for prefix in [Path('.'),Path('anotation_path')]}
temporary=tempfile.TemporaryDirectory(dir=ROOT/'runs',prefix='')
folder=Path(temporary.name).resolve();parent=(ROOT/'runs').resolve()
if folder.parent!=parent or len(folder.name)!=len('final-v1'):raise ValueError('Test root must have the same path length as original output')
checks=[]
try:
    for idx in [9,28,103]:
        for strategy in POLS:
            for version in VERS:
                ws=folder/f'repeat-0/{strategy}/{version}/{idx}/workspace'
                for p in resources:
                    for prefix in [Path('.'),Path('anotation_path')]:
                        target=ws/prefix/p.relative_to(source);native(target.parent).mkdir(parents=True,exist_ok=True)
                        os.link(native(p),native(target))
                # Match the frozen agent's non-extended visibility behavior.
                seen=sorted(p.relative_to(ws).as_posix() for p in ws.rglob('*') if p.is_file())
                old=read(ROOT/f'runs/final-v1/repeat-0/{strategy}/{version}/{idx}/result.json')
                expected=sorted(set(resource_listing(old))&fixture_names)
                checks.append({'idx':idx,'strategy':strategy,'version':version,'expected_visible_fixture_names':len(expected),'actual_visible_fixture_names':len(seen),'passed':seen==expected,'only_old':sorted(set(expected)-set(seen)),'only_test':sorted(set(seen)-set(expected))})
    result={'verified_at':now(),'purpose':'No-model test before second new round; current first new round unchanged','planned_second_new_round':'final-r3','same_basename_length':len('final-r3')==len('final-v1'),
        'representative_task_id_lengths':[1,2,3],'fixture_files':len(resources),'workspace_layout_checks':len(checks),'passed':all(c['passed'] for c in checks),'checks':checks,
        'limits':'Confirms fixture-name visibility for existing Windows runtime at the same path length. Actual new actor prompts must still be checked. Model, decoding, tasks and method unchanged.'}
    save(ROOT/'artifacts'/CAMPAIGN/'second-new-round-path-validation.json',result)
    print('same-length layout checks',len(checks),'passed',result['passed'])
    if not result['passed']:raise ValueError('Do not start second new round under unverified layout')
finally:
    # Only this newly created, owned 8-character temporary root may be removed.
    resolved=Path(temporary.name).resolve()
    if resolved!=folder or resolved.parent!=parent:raise ValueError('Refusing cleanup outside the exact owned test directory')
    temporary._finalizer.detach()
    shutil.rmtree(native(folder))
