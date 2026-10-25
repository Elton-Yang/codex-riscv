#!/usr/bin/env python3
"""Opt-in public-asset smoke test on an x86_64 QEMU host, NOT a native install.

Usage (Debian cross-toolchain layout produced by this repository):
  python3 tests/smoke_release.py --sysroot /absolute/path/to/toolchains/debian/root

Requires the sysroot's usr/bin/qemu-riscv64, target loader/libraries, and curl.
Downloads the unchanged public asset using the real installer download path.
Only a temporary installer copy's native binary invocation is routed via QEMU;
uname/getconf/bwrap are mocked. ldd uses the real target loader under QEMU.
No credentials, model calls, package installs, root, or user configuration.
"""
import argparse
import hashlib
import os
from pathlib import Path
import shlex
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
TAG = "v0.1.0-experimental.1"


def run(args, env):
    print("+ " + " ".join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), env=env, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sysroot", type=Path, required=True)
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
        command = home / ".local/bin/codex-riscv"
        print("EMULATION HARNESS: mocked platform gates; real HTTPS download, digest, extraction, target libraries and binary.", flush=True)
        run(["sh", installer], env)
        run(["sh", installer, "status"], env)
        version = prefix / "versions" / TAG
        assert command.resolve() == version / "bin/codex"
        for relative in ("LICENSE", "NOTICE", "licenses/THIRD-PARTY-NOTICES.html"):
            assert (version / relative).is_file(), relative
        with (version / "bin/codex").open("rb") as source:
            checksum = hashlib.file_digest(source, "sha256").hexdigest()
        print("Installed binary SHA-256: " + checksum, flush=True)
        run([runner, command, "--version"], env)
        run([runner, command, "--help"], env)
        run(["sh", installer, "upgrade"], env)
        (home / ".codex").mkdir(exist_ok=True)
        sentinel = home / ".codex" / "DO-NOT-REMOVE.txt"
        sentinel.write_text("isolated smoke fixture, not credentials\n")
        run(["sh", installer, "uninstall"], env)
        assert sentinel.is_file()
        assert not prefix.exists()
        assert not command.is_symlink()
        print("PASS: real-asset install/status/reinstall/QEMU startup/uninstall; preserved isolated .codex sentinel.")
        print("NOT TESTED: native installer/platform detection, native kernel sandbox, authentication, model or tool calls.")


if __name__ == "__main__":
    main()
