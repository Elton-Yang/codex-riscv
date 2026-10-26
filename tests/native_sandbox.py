#!/usr/bin/env python3
"""Account-free native sandbox probes in a fresh directory under the user's HOME.

Usage: python3 tests/native_sandbox.py --codex /absolute/path/to/codex-riscv
Keeps the test directory and JSON results for inspection. Never reads credentials.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile


PROBE = r'''
import errno, json, socket, sys
from pathlib import Path
mode, outside = sys.argv[1:]
status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
checks = {'seccomp_filter': status['Seccomp'].strip() == '2',
          'no_new_privs': status['NoNewPrivs'].strip() == '1'}
def denied(path):
    try:
        Path(path).write_text('disposable sandbox test\n')
    except OSError as error:
        return error.errno in (errno.EPERM, errno.EACCES, errno.EROFS)
    return False
if mode == 'workspace-write':
    inside = Path('inside.txt')
    inside.write_text('workspace write passed\n')
    checks['workspace_write'] = inside.read_text() == 'workspace write passed\n'
else:
    checks['workspace_write_denied'] = denied('readonly-denied.txt')
checks['outside_write_denied'] = denied(outside)
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM):
        pass
except OSError as error:
    checks['ipv4_socket_denied'] = error.errno in (errno.EPERM, errno.EACCES)
else:
    checks['ipv4_socket_denied'] = False
print(json.dumps({'mode': mode, 'checks': checks, 'pass': all(checks.values())}, sort_keys=True))
raise SystemExit(0 if all(checks.values()) else 1)
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex', default='codex-riscv')
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error('Run as your ordinary user, without sudo')
    if os.uname().machine != 'riscv64':
        parser.error('Run this native acceptance check on the RISC-V board')
    # Keep the launcher path: resolving it would change argv0/entry semantics.
    found = shutil.which(args.codex)
    if not found:
        parser.error('Cannot find ' + args.codex)
    codex = str(Path(found).absolute())
    root = Path(tempfile.mkdtemp(prefix='codex-riscv-sandbox-', dir=Path.home()))
    print('Results directory: ' + str(root), flush=True)
    for name in ('workspace', 'outside', 'home'):
        (root / name).mkdir()
    (root / 'home/.codex').mkdir()
    probe = root / 'probe.py'
    probe.write_text(PROBE)
    canary = root / 'outside/denied.txt'
    # Demonstrate that ordinary filesystem permissions permit the outside write.
    canary.write_text('outside-sandbox control\n')
    assert canary.read_text() == 'outside-sandbox control\n'
    canary.unlink()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM):
        pass
    environment = {'HOME': str(root / 'home'), 'CODEX_HOME': str(root / 'home/.codex'),
                   'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8',
                   'SHELL': '/bin/sh', 'TMPDIR': '/tmp'}
    records = []
    for mode in ('workspace-write', 'read-only'):
        command = [codex, 'sandbox', '-c', 'sandbox_mode=' + json.dumps(mode),
                   '-c', 'sandbox_workspace_write.network_access=false', '--',
                   sys.executable, str(probe), mode, str(canary)]
        try:
            result = subprocess.run(command, cwd=root / 'workspace', env=environment,
                                    text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, timeout=60)
        except subprocess.TimeoutExpired:
            print('FAIL: sandbox command exceeded 60 seconds', file=sys.stderr)
            return 1
        record = {'mode': mode, 'command': command, 'exit_code': result.returncode,
                  'stdout': result.stdout, 'stderr': result.stderr}
        print(result.stdout, end='')
        if result.stderr:
            print(result.stderr, file=sys.stderr, end='')
        records.append(record)
        (root / 'results.json').write_text(json.dumps(records, indent=2) + '\n')
        if result.returncode or canary.exists():
            print('FAIL: inspect results.json; no broader-access retry was made', file=sys.stderr)
            return 1
    print('PASS: workspace write, read-only denial, outside denial, socket denial, seccomp and no_new_privs')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
