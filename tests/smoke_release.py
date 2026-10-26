#!/usr/bin/env python3
"""Opt-in public-asset smoke test on an x86_64 QEMU host, NOT a native install.

Usage (Debian cross-toolchain layout produced by this repository):
  python3 tests/smoke_release.py --sysroot /absolute/path/to/toolchains/debian/root

Requires the sysroot's usr/bin/qemu-riscv64, target loader/libraries, and curl.
Downloads the unchanged public asset using the real installer download path.
A temporary installer copy's native startup invocation is routed via QEMU;
the unchanged installed launcher's execv transport is also redirected to QEMU.
uname/getconf/bwrap are mocked. ldd uses the real target loader under QEMU.
No credentials, model calls, package installs, root, or user configuration.
"""
import argparse
import hashlib
import fcntl
import os
import pty
import re
import select
import signal
import struct
from pathlib import Path
import shlex
import subprocess
import tempfile
import termios
import time


ROOT = Path(__file__).resolve().parents[1]
TAG = "v0.1.0-experimental.3"


def run(args, env):
    print("+ " + " ".join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), env=env, check=True)


def pty_until(args, env, expected, label):
    """Exercise a real controlling terminal; stop before selecting any login."""
    pid, fd = pty.fork()
    if pid == 0:
        os.chdir(env["HOME"])
        os.execvpe(str(args[0]), list(map(str, args)), env)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 35, 100, 0, 0))
    captured = bytearray()
    status = None
    try:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if select.select([fd], [], [], 0.2)[0]:
                try:
                    block = os.read(fd, 65536)
                except OSError:
                    break
                if not block:
                    break
                captured.extend(block)
                # Answer only terminal capability queries, never login/UI choices.
                if b"\x1b[6n" in block:
                    os.write(fd, b"\x1b[1;1R")
                if b"\x1b]11;?" in block:
                    os.write(fd, b"\x1b]11;rgb:0000/0000/0000\x1b\\")
                if b"\x1b[c" in block:
                    os.write(fd, b"\x1b[?1;2c")
                if expected.lower() in bytes(captured).lower():
                    break
            done, result = os.waitpid(pid, os.WNOHANG)
            if done:
                status = result
                break
        text = captured.decode("utf-8", errors="replace")
        plain = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
        plain = re.sub(r"\x1b\][^\x1b]*(?:\x1b\\|\x07)", "", plain)
        print(label + " PTY output (tail, terminal controls removed): " + repr(plain[-2200:]), flush=True)
        assert expected.lower() in captured.lower(), label + " did not reach expected screen"
        return text
    finally:
        if status is None:
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            os.waitpid(pid, 0)
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sysroot", type=Path, required=True)
    parser.add_argument("--archive", type=Path, help="test a local release archive before publication; checksum checks remain enabled")
    parser.add_argument("--previous-archive", type=Path, help="also exercise actual .1 to .2 upgrade and rollback")
    parser.add_argument("--previous-tag", default="v0.1.0-experimental.2", help="release tag of --previous-archive")
    args = parser.parse_args()
    cross = args.sysroot.resolve()
    qemu = cross / "usr/bin/qemu-riscv64"
    loader = cross / "usr/riscv64-linux-gnu/lib/ld-linux-riscv64-lp64d.so.1"
    for path in (qemu, loader):
        if not path.is_file():
            parser.error("Missing toolchain file: " + str(path))
    with tempfile.TemporaryDirectory(prefix="codex-installer-real-asset-") as tmp:
        work = Path(tmp)
        home, mocks = work / "home", work / "mocks"
        home.mkdir()
        mocks.mkdir()
        env = dict(os.environ, HOME=str(home), CODEX_HOME=str(home / ".codex"),
                   PATH=str(mocks) + ":/usr/bin:/bin", TERM="dumb",
                   LD_LIBRARY_PATH=str(cross / "usr/lib/x86_64-linux-gnu"))
        invocation = [str(qemu), "-L", str(cross / "usr/riscv64-linux-gnu"),
                      "-E", "LD_LIBRARY_PATH=" + str(cross / "usr/lib/riscv64-linux-gnu") + ":" + str(cross / "usr/riscv64-linux-gnu/lib")]
        runner = mocks / "target-runner"
        runner.write_text("#!/bin/sh\nexec " + shlex.join(invocation) + ' "$@"\n')
        runner.chmod(0o755)
        scripts = {
            "uname": "case \"$1\" in -s) echo Linux;; -m) echo riscv64;; *) exit 1;; esac\n",
            "getconf": "echo 'glibc 2.41'\n",
            "bwrap": "echo 'mock presence only: no sandbox validation'; exit 1\n",
            "ldd": "exec " + shlex.join([str(runner), str(loader), "--list"]) + ' "$1"\n',
        }
        if args.archive:
            previous = args.previous_archive.resolve() if args.previous_archive else args.archive.resolve()
            scripts["curl"] = ('out=\nsource=' + shlex.quote(str(args.archive.resolve())) + '\n'
                               'while [ "$#" -gt 0 ]; do\n'
                               '  case "$1" in\n'
                               '    --output) out=$2; shift;;\n'
                               '    */codex-riscv64-linux-gnu-' + args.previous_tag + '.tar.gz) source=' + shlex.quote(str(previous)) + ';;\n'
                               '  esac\n  shift\ndone\ncp -- "$source" "$out"\n')
        for name, body in scripts.items():
            path = mocks / name
            path.write_text("#!/bin/sh\n" + body)
            path.chmod(0o755)
        original = (ROOT / "install.sh").read_text()
        needle = 'subprocess.run([str(binary), "--version"]'
        assert original.count(needle) == 1, "Review smoke harness after changing startup validation"
        modified = original.replace(needle, 'subprocess.run([os.environ["SMOKE_TARGET_RUNNER"], str(binary), "--version"]')
        installer = work / "installer-emulation-harness.sh"
        installer.write_text(modified)
        env["SMOKE_TARGET_RUNNER"] = str(runner)
        prefix = home / ".local/share/codex-riscv"
        command = home / ".local/bin/codex"
        print("EMULATION HARNESS: mocked platform gates; " +
              ("local archive transport" if args.archive else "real HTTPS download") +
              "; real digest, extraction, target libraries and binary.", flush=True)
        if args.previous_archive:
            run(["sh", installer, "install", "--version", args.previous_tag,
                 "--command", "codex-riscv"], env)
            (home / ".codex").mkdir(exist_ok=True)
            (home / ".codex/config.toml").write_text('model = "fixture-preserved-model"\n')
        if args.previous_archive:
            run(["sh", installer, "upgrade", "--command", "codex"], env)
            assert not (home / ".local/bin/codex-riscv").is_symlink()
        else:
            run(["sh", installer], env)
        run(["sh", installer, "status"], env)
        if args.previous_archive:
            run(["sh", installer, "rollback"], env)
            assert (prefix / "current").resolve().name == args.previous_tag
            run(["sh", installer, "upgrade"], env)
            assert (prefix / "current").resolve().name == TAG
            assert (home / ".codex/config.toml").read_text() == 'model = "fixture-preserved-model"\n'
            # Keep the later onboarding check unauthenticated and unconfigured.
            (home / ".codex/config.toml").unlink()
        version = prefix / "versions" / TAG
        assert command.resolve() == prefix / "launcher"
        for relative in ("LICENSE", "NOTICE", "licenses/THIRD-PARTY-NOTICES.html"):
            assert (version / relative).is_file(), relative
        assert os.access(version / "bin/codex-code-mode-host", os.X_OK)
        with (version / "bin/codex").open("rb") as source:
            checksum = hashlib.file_digest(source, "sha256").hexdigest()
        print("Installed binary SHA-256: " + checksum, flush=True)
        # Run the exact installed launcher unchanged. Its execv transport alone
        # is redirected to QEMU, preserving argv0 with QEMU's -0 option.
        launcher_runner = mocks / "emulate-launcher"
        launcher_runner.write_text("#!/usr/bin/env python3\n" +
            "import os, runpy, sys\n" +
            "invocation = " + repr(invocation) + "\n" +
            "native_execv = os.execv\n" +
            "def target_execv(binary, argv):\n" +
            "    native_execv(invocation[0], [*invocation, '-0', argv[0], binary, *argv[1:]])\n" +
            "os.execv = target_execv\n" +
            "sys.argv = sys.argv[1:]\n" +
            "runpy.run_path(sys.argv[0], run_name='__main__')\n")
        launcher_runner.chmod(0o755)
        run([launcher_runner, command, "--version"], env)
        run([launcher_runner, command, "--help"], env)
        run([launcher_runner, command, "resume", "--help"], env)
        run([launcher_runner, command, "fork", "--help"], env)
        run([launcher_runner, command, "exec", "--help"], env)
        # Exercise actual hidden-argument and argv0 dispatch without a model,
        # credentials or sandbox execution, inside this disposable directory.
        for index, alias in enumerate((None, "apply_patch")):
            entry = command
            if alias:
                entry = work / alias
                entry.symlink_to(prefix / "launcher")
            patch = "*** Begin Patch\n*** Add File: helper-smoke-" + str(index) + ".txt\n+ok\n*** End Patch"
            call = [str(launcher_runner), str(entry)]
            if not alias:
                call.append("--codex-run-as-apply-patch")
            subprocess.run([*call, patch], env=env, cwd=work, check=True)
            assert (work / ("helper-smoke-" + str(index) + ".txt")).read_text() == "ok\n"
        sandbox_alias = work / "codex-linux-sandbox"
        sandbox_alias.symlink_to(prefix / "launcher")
        run([launcher_runner, sandbox_alias, "--help"], env)
        print("PASS: actual apply-patch argv1/argv0 dispatch and sandbox-helper help.", flush=True)
        (home / ".codex").mkdir(exist_ok=True)
        # Do not inherit API keys, login/config paths or proxies for startup.
        tui_env = {key: env[key] for key in ("HOME", "CODEX_HOME", "PATH", "LD_LIBRARY_PATH")}
        tui_env.update(TERM="xterm-256color", LANG="C.UTF-8", HTTP_PROXY="http://127.0.0.1:9",
                       HTTPS_PROXY="http://127.0.0.1:9", ALL_PROXY="http://127.0.0.1:9", NO_PROXY="")
        screen = pty_until([launcher_runner, command], tui_env,
                           b"Sign in with ChatGPT", "Managed bare standalone launcher")
        assert "no complete local package" not in screen
        print("PASS: bare managed launcher reaches offline sign-in onboarding, no login selected.", flush=True)
        print("LIMIT: unauthenticated onboarding precedes the daemon decision; this does not reproduce the user's authenticated native startup.", flush=True)
        # Exercise same-release migration from the original installed direct link.
        command.unlink()
        command.symlink_to(str(prefix / "current/bin/codex"))
        (prefix / "launcher").unlink()
        run(["sh", installer, "upgrade"], env)
        assert command.resolve() == prefix / "launcher"
        (home / ".codex").mkdir(exist_ok=True)
        sentinel = home / ".codex" / "DO-NOT-REMOVE.txt"
        sentinel.write_text("isolated smoke fixture, not credentials\n")
        run(["sh", installer, "uninstall"], env)
        assert sentinel.is_file()
        assert not prefix.exists()
        assert not command.is_symlink()
        print("PASS: real-asset install/status/command-name migration and rollback when requested/legacy migration/QEMU bare onboarding/uninstall; preserved isolated .codex sentinel.")
        print("NOT TESTED: native installer/platform detection, native kernel sandbox, authentication, model or tool calls.")


if __name__ == "__main__":
    main()
