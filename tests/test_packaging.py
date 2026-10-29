"""Package boundaries using a temporary Git index, without model calls or real audits."""
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import build_submission as packaging


class PackagingTests(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).resolve().parents[1]/'runtime/test-fixtures'
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.git('init', '-q')
        self.patch = patch.object(packaging, 'ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, stderr=subprocess.PIPE)

    def write(self, name, content='synthetic evidence'):
        path = self.root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path

    def test_ignored_and_untracked_drafts_stay_out_archived_evidence_stays_in(self):
        self.write('.gitignore', 'docs/追加实验/执行指南.md\n')
        tracked = ['README.md', 'tool_adapt/agent.py', 'docs/REPORT.md',
                   'archive/progress/repeats-20261029/snapshot.json']
        for name in tracked:
            self.write(name)
        self.git('add', '--', '.gitignore', *tracked)
        for name in ['docs/追加实验/执行指南.md', 'scripts/private-note.ps1',
                     'tests/test_dashboard.py', 'docs/local-plan.md']:
            self.write(name)
        included = {p.relative_to(self.root).as_posix() for p in packaging.source_files()}
        self.assertEqual(included, set(tracked)|{'.gitignore'})
        # Explicit exclusions still apply if an internal document is force-added.
        self.git('add', '-f', '--', 'docs/追加实验/执行指南.md')
        self.assertNotIn(self.root/'docs/追加实验/执行指南.md', packaging.source_files())

    def test_missing_tracked_source_stops_packaging(self):
        path = self.write('docs/REPORT.md')
        self.git('add', '--', 'docs/REPORT.md')
        path.unlink()
        with self.assertRaisesRegex(ValueError, 'missing or outside'):
            packaging.source_files()

    def test_existing_package_stops_before_audits_or_writes(self):
        original_exists = Path.exists
        def exists(path):
            return path.name == 'PE6203_Project4_Submission.zip' or original_exists(path)
        with patch.object(Path, 'exists', exists), \
             patch('audit_experiment.audit') as audit, \
             patch('analyze_comparisons.compare') as compare:
            with self.assertRaisesRegex(FileExistsError, 'must be preserved'):
                runpy.run_path(packaging.__file__, run_name='__main__')
        audit.assert_not_called()
        compare.assert_not_called()

    def test_collect_keeps_ignored_raw_failures_events_and_created_artifacts(self):
        self.write('.gitignore', 'runs/\ndocs/追加实验/执行指南.md\n')
        for name in ['docs/REPORT.md', 'output/pdf/PE6203_Project4_Report.pdf']:
            self.write(name)
        self.git('add', '--', '.gitignore', 'docs', 'output')
        self.write('docs/追加实验/执行指南.md')
        expected = set()
        for run in ['final-v1', 'ablation-v1', 'final-workflow-verification']:
            prefix = f'runs/{run}'
            expected.add(self.write(prefix+'/manifest.json', '{}'))
            expected.add(self.write(prefix+'/analysis/summary.json', '{}'))
            episode = prefix+'/repeat-0/no_update/original/3/'
            record = {'artifact_changes': {'created': ['tasks.md'], 'modified': []}}
            expected.add(self.write(episode+'result.json', json.dumps(record)))
            for name in ['agent-record.json', 'events.jsonl', 'failure-record.json',
                         'workspace/server.stderr.log', 'workspace/tasks.md']:
                expected.add(self.write(episode+name))
        for run in ['dev-v2', 'dev-v3']:
            expected.add(self.write(f'runs/{run}/manifest.json', '{}'))
            expected.add(self.write(f'runs/{run}/repeat-0/no_update/original/3/result.json', '{}'))
        with patch.object(packaging, 'audit', return_value={'complete_and_evaluated': True}), \
             patch.object(packaging, 'compare'):
            included = set(packaging.collect())
        self.assertTrue(expected <= included)
        self.assertNotIn(self.root/'docs/追加实验/执行指南.md', included)


if __name__ == '__main__':
    unittest.main()
