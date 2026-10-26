#!/usr/bin/env python3
"""Meaningful failure/identity tests for source replay; no network or build."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('upstream', ROOT / 'scripts/upstream.py')
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


class UpstreamTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def archive(self, name, kind=tarfile.REGTYPE):
        p = self.root / 'input.tar.gz'
        with tarfile.open(p, 'w:gz') as t:
            m = tarfile.TarInfo(name)
            m.type = kind
            if kind == tarfile.REGTYPE:
                m.size = 3
                t.addfile(m, io.BytesIO(b'abc'))
            else:
                m.linkname = '/etc/passwd'
                t.addfile(m)
        return p

    def test_extraction_rejects_escape_and_links(self):
        for name, kind in [('../escape', tarfile.REGTYPE), ('/absolute', tarfile.REGTYPE),
                           ('crate/link', tarfile.SYMTYPE), ('crate/.git/config', tarfile.REGTYPE)]:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    u.extract_regular(self.archive(name, kind), self.root / 'dest')
        self.assertFalse((self.root / 'escape').exists())

    def test_exact_crate_prefix_and_no_overwrite(self):
        p = self.archive('crate/src/file')
        with self.assertRaises(ValueError):
            u.extract_regular(p, self.root / 'wrong', 'other')
        dest = self.root / 'dest'
        u.extract_regular(p, dest, 'crate')
        self.assertEqual((dest / 'src/file').read_bytes(), b'abc')
        with self.assertRaises(FileExistsError):
            u.extract_regular(p, dest, 'crate')

    def test_lock_rejects_changed_patch(self):
        lock = json.loads((ROOT / 'manifests/upstream-lock.json').read_text())
        lock['patches'][0]['sha256'] = '0' * 64
        p = self.root / 'lock.json'
        p.write_text(json.dumps(lock))
        with self.assertRaisesRegex(ValueError, 'Patch hash mismatch'):
            u.load_lock(p)

    def test_prepare_refuses_existing_directory_before_mutation(self):
        dest = self.root / 'existing'
        dest.mkdir()
        (dest / 'keep').write_text('user work')
        args = types.SimpleNamespace(output=dest)
        with self.assertRaisesRegex(ValueError, 'Output must not exist'):
            u.prepare(args, {})
        self.assertEqual((dest / 'keep').read_text(), 'user work')

    def test_verify_rejects_committed_unreviewed_tree_and_dirty_tree(self):
        repo = self.root / 'repo'
        repo.mkdir()
        u.run_git(repo, 'init', '--quiet', '-b', 'main')
        (repo / 'pin').write_text('base')
        base = u.commit(repo, 'base')
        tree = u.git(repo, 'rev-parse', 'HEAD^{tree}')
        args = types.SimpleNamespace(source=repo, component='cli')
        lock = {'codex': {'commit': base}, 'expected_sources': {'cli': {
                'pin': hashlib.sha256(b'base').hexdigest()}}, 'expected_git_trees': {'cli': tree}}
        u.verify(args, lock)
        (repo / 'extra').write_text('unreviewed')
        with self.assertRaisesRegex(ValueError, 'uncommitted'):
            u.verify(args, lock)
        u.commit(repo, 'not in reviewed patch series')
        with self.assertRaisesRegex(ValueError, 'tree differs'):
            u.verify(args, lock)

    def test_cli_build_args_match_reviewed_profile(self):
        result = subprocess.check_output(['python3', str(ROOT / 'scripts/upstream.py'),
                                          'build-args', 'cli'], text=True)
        self.assertIn('profile.perf-cli.opt-level=3', result)
        self.assertIn('profile.perf-cli.debug-assertions=true', result)
        self.assertIn('profile.perf-cli.overflow-checks=true', result)
        self.assertIn('riscv64gc-unknown-linux-gnu', result)

    def test_failed_patch_replay_preserves_labeled_partial_work(self):
        repo = self.root / 'input'
        repo.mkdir()
        u.run_git(repo, 'init', '--quiet', '-b', 'main')
        (repo / 'input').write_text('base')
        base = u.commit(repo, 'base')
        args = types.SimpleNamespace(output=self.root / 'output', candidate_commit=None,
                 component='cli', codex_repo=repo, lock=ROOT / 'manifests/upstream-lock.json')
        lock = {'codex': {'commit': base}, 'patches': []}
        with patch.object(u, 'inspect_versions', return_value={}), \
             patch.object(u, 'apply_series', side_effect=ValueError('patch conflict')):
            with self.assertRaisesRegex(ValueError, 'patch conflict'):
                u.prepare(args, lock)
        state = json.loads((args.output / 'source-state.json').read_text())
        self.assertEqual(state['status'], 'FAILED_SOURCE_PREPARATION')
        self.assertFalse(state['runtime_validated'])
        self.assertEqual((repo / 'input').read_text(), 'base')

    def test_discovery_distinguishes_formal_tag_from_forward_upgrade(self):
        spec = importlib.util.spec_from_file_location('discovery', ROOT / 'scripts/check-upstream.py')
        discovery = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(discovery)
        for status in ['ahead', 'diverged', 'behind', 'identical']:
            with self.subTest(status=status):
                output = self.root / (status + '.json')
                def api(endpoint):
                    if endpoint.endswith('releases/latest'):
                        return {'draft': False, 'prerelease': False, 'tag_name': 'v1',
                                'published_at': '2026-10-26', 'html_url': 'https://example.test/v1'}
                    if '/git/ref/tags/' in endpoint:
                        return {'object': {'type': 'tag', 'sha': 'a' * 40}}
                    if '/git/tags/' in endpoint:
                        return {'object': {'type': 'commit', 'sha': 'b' * 40}}
                    if '/compare/' in endpoint:
                        return {'status': status, 'ahead_by': 1, 'behind_by': 1,
                                'merge_base_commit': {'sha': 'c' * 40}}
                    return {'object': {'sha': 'd' * 40}}
                with patch.object(discovery, 'api', side_effect=api), \
                     patch('sys.argv', ['check-upstream.py', '--output', str(output)]):
                    discovery.main()
                result = json.loads(output.read_text())
                self.assertEqual(result['latest_stable']['commit'], 'b' * 40)
                self.assertEqual(result['forward_candidate_available'], status == 'ahead')


if __name__ == '__main__':
    unittest.main()
