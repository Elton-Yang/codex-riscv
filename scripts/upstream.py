#!/usr/bin/env python3
"""Pinned source preparation, patch commits and upgrade rehearsal; no build/publish."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = ROOT / 'manifests/upstream-lock.json'


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


def run_git(path, *args):
    subprocess.run(['git', '-C', str(path), *args], check=True, stdout=subprocess.DEVNULL)


def load_lock(path):
    lock = json.loads(path.read_text())
    if lock['schema'] != 1 or not re.fullmatch(r'[0-9a-f]{40}', lock['codex']['commit']):
        raise ValueError('Unsupported lock or invalid Codex commit')
    for row in lock['patches']:
        p = ROOT / row['file']
        if digest(p) != row['sha256']:
            raise ValueError('Patch hash mismatch: ' + row['file'])
    row = lock['additional_sources']['chromium_rust']
    if digest(ROOT / row['manifest']) != row['sha256']:
        raise ValueError('Chromium input manifest hash mismatch')
    return lock


def commit(path, subject):
    run_git(path, 'add', '--all')
    run_git(path, '-c', 'user.name=codex-riscv source preparation',
            '-c', 'user.email=source-preparation@codex-riscv.invalid',
            '-c', 'core.hooksPath=/dev/null', 'commit', '--quiet', '--no-gpg-sign', '-m', subject)
    return git(path, 'rev-parse', 'HEAD')


def apply_series(path, lock, repository, component):
    rows = []
    for row in lock['patches']:
        if row['repository'] != repository or component not in row['components']:
            continue
        patch = str((ROOT / row['file']).resolve())
        run_git(path, 'apply', '--check', patch)
        run_git(path, 'apply', patch)
        rows.append({'id': row['id'], 'commit': commit(path, row['subject']),
                     'patch_sha256': row['sha256']})
    return rows


def extract_regular(archive, destination, prefix=None):
    """Extract authenticated source only; reject links, traversal and collisions."""
    total = 0
    seen = set()
    with tarfile.open(archive, 'r|*') as source:
        for member in source:
            name = member.name.removeprefix('./')
            p = PurePosixPath(name)
            if p.is_absolute() or '..' in p.parts or '\\' in name or not p.parts:
                raise ValueError('Unsafe archive path: ' + name)
            if prefix:
                if p.parts[0] != prefix:
                    raise ValueError('Unexpected crate prefix: ' + name)
                p = PurePosixPath(*p.parts[1:])
            if str(p) == '.':
                if not member.isdir():
                    raise ValueError('Invalid archive root')
                continue
            if '.git' in p.parts or not (member.isfile() or member.isdir()):
                raise ValueError('Unexpected source member: ' + name)
            if str(p) in seen:
                raise ValueError('Duplicate source member: ' + name)
            seen.add(str(p))
            total += member.size
            if total > 512 * 1024 * 1024 or len(seen) > 100000:
                raise ValueError('Source archive exceeds limits')
            target = destination.joinpath(*p.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as dest, source.extractfile(member) as data:
                    while block := data.read(1024 * 1024):
                        dest.write(block)
                target.chmod(0o755 if member.mode & 0o111 else 0o644)


def expected_sources(path, expected):
    for name, sha in expected.items():
        if digest(path / name) != sha:
            raise ValueError('Source identity mismatch: ' + name)


def inspect_versions(source):
    base = source / 'codex-rs'
    cargo = tomllib.loads((base / 'Cargo.toml').read_text())
    lock = tomllib.loads((base / 'Cargo.lock').read_text())
    return {'package_version': cargo.get('workspace', {}).get('package', {}).get('version'),
            'rust': tomllib.loads((base / 'rust-toolchain.toml').read_text())['toolchain']['channel'],
            'v8': [dict(name=p['name'], version=p['version'], checksum=p.get('checksum'))
                   for p in lock['package'] if p['name'] == 'v8']}


def prepare(args, lock):
    output = args.output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('Output must not exist; existing work is never overwritten')
    candidate = args.candidate_commit
    if candidate and not re.fullmatch(r'[0-9a-f]{40}', candidate):
        raise ValueError('Candidate must be a full immutable commit SHA')
    if candidate and args.component != 'cli':
        raise ValueError('Upgrade rehearsal first replays CLI only; host requires a new reviewed lock')
    # Validate all inputs before creating a destination.
    supplemental = []
    if args.component == 'code-mode':
        if not args.v8_crate or digest(args.v8_crate) != lock['v8']['crate_sha256']:
            raise ValueError('Exact V8 crate is required; checksum mismatch or missing input')
        if not args.icu_data or digest(args.icu_data) != lock['additional_sources']['icu_data']['sha256']:
            raise ValueError('Exact ICU input is required')
        if not args.chromium_archives:
            raise ValueError('Pinned Chromium Rust source archives are required')
        supplemental = json.loads((ROOT / lock['additional_sources']['chromium_rust']['manifest']).read_text())
        for row in supplemental:
            if digest(args.chromium_archives / row['file']) != row['sha256']:
                raise ValueError('Chromium archive mismatch: ' + row['file'])
    output.mkdir(parents=True)
    record = {'schema': 1, 'status': 'PREPARING', 'component': args.component,
              'lock_sha256': digest(args.lock), 'base_commit': candidate or lock['codex']['commit'],
              'candidate': bool(candidate), 'build_validated': False,
              'runtime_validated': False, 'source_only': True, 'repositories': {}}
    report = output / 'source-state.json'
    try:
        src = output / 'src'
        subprocess.run(['git', 'clone', '--quiet', '--no-hardlinks', '--no-checkout',
                        str(args.codex_repo.resolve()), str(src)], check=True)
        run_git(src, 'checkout', '--quiet', '--detach', record['base_commit'])
        run_git(src, 'switch', '--quiet', '-c', 'riscv/rehearsal' if candidate else 'riscv/current')
        record['observed_versions'] = inspect_versions(src)
        commits = apply_series(src, lock, 'codex', args.component)
        if not candidate:
            expected_sources(src, lock['expected_sources'][args.component])
            if git(src, 'rev-parse', 'HEAD^{tree}') != lock['expected_git_trees'][args.component]:
                raise ValueError('Prepared Codex tree does not match reviewed lock')
        record['repositories']['codex'] = {'path': 'src', 'head': git(src, 'rev-parse', 'HEAD'),
                                          'tree': git(src, 'rev-parse', 'HEAD^{tree}'), 'patches': commits}
        if args.component == 'code-mode':
            v8 = output / 'vendor/v8'
            v8.mkdir(parents=True)
            extract_regular(args.v8_crate, v8, lock['v8']['crate_prefix'])
            run_git(v8, 'init', '--quiet', '-b', 'adaptation')
            base = commit(v8, 'Import exact published V8 crate ' + lock['v8']['crate_version'])
            for row in supplemental:
                extract_regular(args.chromium_archives / row['file'], v8 / row['destination'])
            icu = v8 / lock['additional_sources']['icu_data']['destination']
            icu.parent.mkdir(parents=True, exist_ok=True)
            icu.write_bytes(args.icu_data.read_bytes())
            supplemental_commit = commit(v8, 'Restore authenticated Chromium Rust and pinned ICU source inputs')
            commits = apply_series(v8, lock, 'v8', 'code-mode')
            expected_sources(v8, lock['expected_sources']['v8'])
            if git(v8, 'rev-parse', 'HEAD^{tree}') != lock['expected_git_trees']['v8']:
                raise ValueError('Prepared V8 tree does not match reviewed lock')
            record['repositories']['v8'] = {'path': 'vendor/v8', 'base': base,
                 'source_input_commit': supplemental_commit, 'head': git(v8, 'rev-parse', 'HEAD'),
                 'tree': git(v8, 'rev-parse', 'HEAD^{tree}'), 'patches': commits,
                 'base_kind': 'published-crate import, not upstream V8 Git commit'}
        record['status'] = 'CANDIDATE_PATCH_REPLAY_ONLY' if candidate else 'PINNED_SOURCE_REPLAY_PASS'
        report.write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps(record, indent=2))
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        record.update(status='FAILED_SOURCE_PREPARATION', error=str(error))
        report.write_text(json.dumps(record, indent=2) + '\n')
        raise


def verify(args, lock):
    source = args.source.resolve()
    git_root = Path(git(source, 'rev-parse', '--show-toplevel')).resolve()
    if source != git_root:
        raise ValueError('Source must be a dedicated Git repository root')
    actual = git(source, 'status', '--porcelain', '--untracked-files=all')
    if actual:
        raise ValueError('Source has uncommitted changes; commit/review them before building')
    run_git(source, 'merge-base', '--is-ancestor', lock['codex']['commit'], 'HEAD')
    expected_sources(source, lock['expected_sources'][args.component])
    if git(source, 'rev-parse', 'HEAD^{tree}') != lock['expected_git_trees'][args.component]:
        raise ValueError('Committed source tree differs from the reviewed patch result')
    if args.component == 'code-mode':
        v8 = source.parent / 'vendor/v8'
        if Path(git(v8, 'rev-parse', '--show-toplevel')).resolve() != v8.resolve():
            raise ValueError('V8 must be a dedicated source repository')
        if git(v8, 'status', '--porcelain', '--untracked-files=all'):
            raise ValueError('V8 source has uncommitted changes')
        if git(v8, 'rev-parse', 'HEAD^{tree}') != lock['expected_git_trees']['v8']:
            raise ValueError('V8 source tree differs from reviewed crate, inputs and patches')
        expected_sources(v8, lock['expected_sources']['v8'])
    print('Verified committed pinned ' + args.component + ' source')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--lock', type=Path, default=DEFAULT_LOCK)
    sub = p.add_subparsers(dest='action', required=True)
    query = sub.add_parser('get')
    query.add_argument('key', help='dot-separated manifest key')
    sub.add_parser('check-lock')
    profile = sub.add_parser('build-args')
    profile.add_argument('component', choices=['cli', 'host', 'sandbox_tests'])
    prep = sub.add_parser('prepare')
    prep.add_argument('--output', type=Path, required=True)
    prep.add_argument('--codex-repo', type=Path, required=True)
    prep.add_argument('--component', choices=['cli', 'code-mode'], required=True)
    prep.add_argument('--v8-crate', type=Path)
    prep.add_argument('--chromium-archives', type=Path)
    prep.add_argument('--icu-data', type=Path)
    prep.add_argument('--candidate-commit', help='rehearsal only; never changes the current pin')
    v = sub.add_parser('verify-source')
    v.add_argument('--source', type=Path, required=True)
    v.add_argument('--component', choices=['cli', 'code-mode'], required=True)
    args = p.parse_args()
    lock = load_lock(args.lock)
    if args.action == 'get':
        value = lock
        for key in args.key.split('.'):
            value = value[key]
        print(value if isinstance(value, str) else json.dumps(value))
    elif args.action == 'build-args':
        config = lock['profiles'][args.component]
        print('--target\n' + lock['toolchain']['target'] + '\n--profile\n' + config['name'])
        for key, value in config.items():
            if key != 'name':
                print('--config\nprofile.' + config['name'] + '.' + key + '=' + json.dumps(value, separators=(',', ':')))
    elif args.action == 'prepare':
        prepare(args, lock)
    elif args.action == 'verify-source':
        verify(args, lock)
    else:
        print('Lock, patch digests and additional source manifest verified')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        print('upstream: ' + str(error), file=sys.stderr)
        sys.exit(1)
