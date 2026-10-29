"""Verify disjoint work allocation and package provenance on a synthetic Git repository."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import build_member_packages as packages


class MemberPackageTests(unittest.TestCase):
    def test_partition_rejects_duplicate_unsafe_and_unknown_paths(self):
        self.assertEqual(packages.owner('contributions/members/E_LIN_GENXIN/README.md'),'e')
        with self.assertRaisesRegex(ValueError,'Unknown member'):
            packages.owner('contributions/members/Z_UNKNOWN/README.md')
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            packages.partition(['README.md','README.md'])
        with self.assertRaisesRegex(ValueError,'Unsafe'):
            packages.owner('../secret.txt')
        with self.assertRaisesRegex(ValueError,'No reviewed'):
            packages.owner('scripts/unreviewed-local-file.py')

    def test_six_packages_cover_commit_once_and_ignore_dirty_or_untracked_files(self):
        parent=Path(__file__).resolve().parents[1]/'runtime/test-fixtures'
        parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temp:
            root=Path(temp).resolve()
            def write(name,content):
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(content,encoding='utf-8')
            def git(*args):
                return subprocess.check_output(['git',*args],cwd=root,stderr=subprocess.PIPE)
            git('init','-q')
            seed=['README.md','tool_adapt/agent.py','tool_adapt/knowledge.py',
                  'configs/experiment.json','tool_adapt/results.py','docs/CASE_28_REVIEW.md']
            for name in seed:write(name,'synthetic committed baseline')
            roles={'members':{m:{'title':'Synthetic role '+m,'slug':'role'+m} for m in packages.MEMBERS}}
            write('contributions/roles.json',json.dumps(roles))
            write('contributions/ownership.json','{}')
            for m in packages.MEMBERS:write(f'contributions/roles/{m}.md','Synthetic planned work; no student completion claim.')
            git('add','--',*seed,'contributions')
            with patch.object(packages,'ROOT',root):
                packages.write_ownership()
                git('add','--','contributions/ownership.json')
                git('-c','user.name=Synthetic packaging fixture','-c','user.email=fixture@example.invalid',
                    'commit','-qm','Synthetic test baseline')
                commit=git('rev-parse','HEAD').decode().strip()
                write('tool_adapt/agent.py','dirty working copy must not enter frozen package')
                write('scripts/private-note.py','untracked draft must not enter package')
                result=packages.build(commit,root/'packages')
                with self.assertRaises(FileExistsError):packages.build(commit,root/'packages')
            owned=[]
            for p in result['packages']:
                with zipfile.ZipFile(root/'packages'/p['file']) as z:
                    manifest=json.loads(z.read('PACKAGE_MANIFEST.json'))
                    self.assertEqual(manifest['source_commit'],commit)
                    self.assertEqual(manifest['status'],'planned_responsibility')
                    owned.extend(f['path'] for f in manifest['files'])
                    if 'source/tool_adapt/agent.py' in z.namelist():
                        self.assertEqual(z.read('source/tool_adapt/agent.py'),b'synthetic committed baseline')
            expected=git('ls-tree','-r','--name-only','HEAD').decode().splitlines()
            self.assertEqual(set(owned),set(expected))
            self.assertEqual(len(owned),len(set(owned)))
            self.assertNotIn('scripts/private-note.py',owned)
            self.assertEqual(len(result['packages']),6)


if __name__=='__main__':unittest.main()
