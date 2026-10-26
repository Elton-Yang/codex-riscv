#!/bin/sh
# codex-riscv user installer. Python's standard library handles safe tar extraction.
# This installer does not modify shell profiles, ~/.codex, or the upstream binary.
set -eu
command -v python3 >/dev/null 2>&1 || {
    printf '%s\n' 'codex-riscv: python3 is required (Debian: sudo apt install python3).' >&2
    exit 1
}
exec python3 - "$@" <<'PY'
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import uuid

DEFAULT_VERSION = "v0.1.0-experimental.3"
RELEASES = {
    "v0.1.0-experimental.3": "28c6611e150db751b773c818de1b85a29b044a7c0077cc0abcf95f99655026a4",
    "v0.1.0-experimental.2": "409e051bcb98862d615ad468cd4b134456cbf52b6efa4a3c078ed02c219a233c",
    "v0.1.0-experimental.1": "2b70f049652793a2dd6c8035122ce2a6920de680153be1c6f8e2a172dde70120",
}
REPOSITORY = "https://github.com/Elton-Yang/codex-riscv"
ROOT_MARKER = ".codex-riscv-install"
VERSION_MARKER = ".codex-riscv-version"
SCHEMA = 1
LAUNCHER = "launcher"


def fail(message):
    raise RuntimeError(message)


def exists(path):
    return os.path.lexists(path)


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    if path.is_symlink() or not path.is_file():
        fail("Missing or unsafe managed metadata: " + str(path))
    with path.open(encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        fail("Invalid managed metadata object: " + str(path))
    return value


def write_json(path, value):
    with path.open("x", encoding="utf-8") as dest:
        json.dump(value, dest, indent=2, sort_keys=True)
        dest.write("\n")
    path.chmod(0o600)


def tag_ok(tag):
    return isinstance(tag, str) and re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?", tag)


def absolute_path(value, label):
    path = Path(value).expanduser()
    if not path.is_absolute():
        fail(label + " must be an absolute path")
    if path.is_symlink():
        fail(label + " must not be a symlink")
    return path.resolve()


def within(path, parent):
    return path == parent or parent in path.parents


def managed_state(prefix):
    state = read_json(prefix / ROOT_MARKER)
    if (state.get("schema") != SCHEMA or state.get("prefix") != str(prefix)
            or state.get("command") not in ("codex-riscv", "codex")
            or not isinstance(state.get("bin_dir"), str)
            or not Path(state["bin_dir"]).is_absolute()):
        fail("Invalid installation metadata; refusing to modify " + str(prefix))
    return state


def managed_version(prefix, tag, verify=False):
    if not tag_ok(tag):
        fail("Invalid managed version name")
    directory = prefix / "versions" / tag
    if directory.is_symlink() or not directory.is_dir():
        fail("Missing or unsafe managed version: " + tag)
    data = read_json(directory / VERSION_MARKER)
    if (data.get("schema") != SCHEMA or data.get("tag") != tag
            or not re.fullmatch(r"[0-9a-f]{64}", str(data.get("sha256", "")))
            or not isinstance(data.get("files"), dict)
            or not isinstance(data.get("dirs"), list)):
        fail("Invalid version metadata: " + tag)
    if verify:
        files, dirs = inventory(directory)
        if files != data["files"] or dirs != data["dirs"]:
            fail("Modified or untracked files in " + str(directory) + "; preserved. Move your files out or restore the managed files before retrying.")
    return data


def pointer(prefix, name):
    path = prefix / name
    if not exists(path):
        return None
    if not path.is_symlink():
        fail("Refusing to replace unmanaged path: " + str(path))
    target = os.readlink(path)
    if not target.startswith("versions/") or not tag_ok(target[len("versions/"):]):
        fail("Invalid managed " + name + " link")
    tag = target[len("versions/"):]
    managed_version(prefix, tag)
    return tag


def inventory(directory):
    files, dirs = {}, []
    for base, dirnames, filenames in os.walk(directory, followlinks=False):
        for name in dirnames + filenames:
            path = Path(base) / name
            relative = path.relative_to(directory).as_posix()
            if relative == VERSION_MARKER:
                continue
            mode = path.lstat().st_mode
            if stat.S_ISDIR(mode):
                dirs.append(relative)
            elif stat.S_ISREG(mode):
                files[relative] = {"sha256": digest(path), "mode": stat.S_IMODE(mode)}
            else:
                fail("Unexpected symlink or special file; preserved: " + str(path))
    return files, sorted(dirs)


def atomic_link(prefix, name, tag):
    temporary = prefix / ("." + name + "." + uuid.uuid4().hex)
    try:
        temporary.symlink_to("versions/" + tag)
        os.replace(temporary, prefix / name)
    finally:
        if exists(temporary):
            temporary.unlink()



def activate(prefix, current, previous):
    # Each symlink replacement is atomic. Restore history on a recoverable
    # current-link failure, so a failed upgrade does not discard rollback.
    old_previous = pointer(prefix, "previous")
    if previous:
        atomic_link(prefix, "previous", previous)
    try:
        atomic_link(prefix, "current", current)
    except BaseException:
        if previous:
            if old_previous:
                atomic_link(prefix, "previous", old_previous)
            else:
                (prefix / "previous").unlink()
        raise


def launcher_bytes(prefix):
    # Keep argv0 for the upstream multicall aliases. Internal helpers inspect
    # argv1 before clap, so never put a user-facing flag ahead of their sentinel.
    # os.execv replaces the launcher: arguments, exit status and process signals
    # belong to the binary, with no waiting wrapper process.
    program = """#!/usr/bin/env python3
# Managed by codex-riscv install.sh. Reinstall rather than editing this file.
import os
import sys

binary = {binary!r}
args = sys.argv[1:]
internal = (os.path.basename(sys.argv[0]) in
            ("codex-linux-sandbox", "apply_patch", "applypatch") or
            (args and args[0].startswith("--codex-run-as-")))
options = args[:args.index("--")] if "--" in args else args
if not internal and "--no-daemon" not in options:
    args = ["--no-daemon", *args]
os.execv(binary, [sys.argv[0], *args])
"""
    return program.format(binary=str(prefix / "current/bin/codex")).encode("utf-8")


def launcher_owned(prefix):
    path = prefix / LAUNCHER
    return (not path.is_symlink() and path.is_file()
            and stat.S_IMODE(path.stat().st_mode) == 0o755
            and path.read_bytes() == launcher_bytes(prefix))


def check_launcher(prefix):
    if exists(prefix / LAUNCHER) and not launcher_owned(prefix):
        fail("Unmanaged or modified launcher; preserved: " + str(prefix / LAUNCHER))


def ensure_launcher(prefix):
    check_launcher(prefix)
    if launcher_owned(prefix):
        return
    temporary = prefix / (".launcher." + uuid.uuid4().hex)
    try:
        with temporary.open("xb") as dest:
            dest.write(launcher_bytes(prefix))
        temporary.chmod(0o755)
        os.replace(temporary, prefix / LAUNCHER)
    finally:
        if exists(temporary):
            temporary.unlink()


def command_owned(command_path, prefix):
    if not command_path.is_symlink() or not exists(prefix / ROOT_MARKER):
        return False
    state = managed_state(prefix)
    if str(command_path) != str(Path(state["bin_dir"]) / state["command"]):
        return False
    target = os.readlink(command_path)
    # The original installer installed this exact direct link. Only adopt it
    # when its saved installation identity matches, never a merely similar link.
    if target == str(prefix / "current/bin/codex"):
        return True
    return target == str(prefix / LAUNCHER) and launcher_owned(prefix)


def replace_command_link(command_path, target):
    temporary = command_path.parent / ("." + command_path.name + "." + uuid.uuid4().hex)
    try:
        temporary.symlink_to(target)
        os.replace(temporary, command_path)
    finally:
        if exists(temporary):
            temporary.unlink()


def check_command(command_path, prefix):
    if exists(command_path) and not command_owned(command_path, prefix):
        fail("Command already exists; not overwritten: " + str(command_path))
    found = shutil.which(command_path.name)
    if found and Path(os.path.abspath(found)) != command_path:
        fail("Command already exists on PATH; not shadowed: " + found)


def migrate_command(prefix, old_path, new_path):
    """Rename only a verified managed entry; preserve the old entry on failure."""
    check_launcher(prefix)
    if not command_owned(old_path, prefix):
        fail("Old command is missing or modified; preserved: " + str(old_path))
    check_command(new_path, prefix)
    original = managed_state(prefix)
    old_identity = old_path.lstat()
    updated = dict(original, command=new_path.name)
    temporary = prefix / (".install-state." + uuid.uuid4().hex)
    created = False
    state_changed = False
    try:
        write_json(temporary, updated)
        # Exclusive creation prevents overwriting a concurrent foreign command.
        new_path.symlink_to(str(prefix / LAUNCHER))
        created = True
        current_identity = old_path.lstat()
        if ((current_identity.st_dev, current_identity.st_ino, current_identity.st_mtime_ns,
             current_identity.st_ctime_ns) !=
                (old_identity.st_dev, old_identity.st_ino, old_identity.st_mtime_ns,
                 old_identity.st_ctime_ns) or not command_owned(old_path, prefix)):
            fail("Old command changed during migration; preserved: " + str(old_path))
        os.replace(temporary, prefix / ROOT_MARKER)
        state_changed = True
        old_path.unlink()
    except BaseException:
        if state_changed:
            write_json(temporary, original)
            os.replace(temporary, prefix / ROOT_MARKER)
        if created and new_path.is_symlink() and os.readlink(new_path) == str(prefix / LAUNCHER):
            new_path.unlink()
        raise
    finally:
        if exists(temporary):
            temporary.unlink()
    print("Command migrated: " + str(old_path) + " -> " + str(new_path))


def output(argv):
    return subprocess.check_output(argv, text=True, stderr=subprocess.STDOUT).strip()


def check_platform():
    if os.geteuid() == 0:
        fail("Run as your normal user, not root. System-wide installation is not supported.")
    for name in ("uname", "getconf", "curl", "ldd", "bwrap"):
        if not shutil.which(name):
            fail("Missing dependency: " + name + ". On Debian 13 install python3 ca-certificates curl libc-bin libc6 libgcc-s1 libssl3t64 bubblewrap.")
    if output(["uname", "-s"]) != "Linux" or output(["uname", "-m"]) != "riscv64":
        fail("This release requires Linux riscv64; no files were activated.")
    libc = output(["getconf", "GNU_LIBC_VERSION"])
    match = re.fullmatch(r"glibc (\d+)\.(\d+)", libc)
    if not match or tuple(map(int, match.groups())) < (2, 39):
        fail("glibc >= 2.39 is required; found " + libc)


def check_binary(directory, tag):
    binary = directory / "bin/codex"
    binaries = [binary]
    if tag != "v0.1.0-experimental.1":
        binaries.append(directory / "bin/codex-code-mode-host")
    for executable in binaries:
        if not executable.is_file() or not os.access(executable, os.X_OK):
            fail("Missing executable: " + executable.name + "; no version was activated")
        result = subprocess.run(["ldd", str(executable)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if result.returncode or "not found" in result.stdout:
            fail("Runtime library check failed for " + executable.name + "; no version was activated:\n" + result.stdout)
    # Even --version may initialize upstream PATH aliases. Keep that side effect
    # in a disposable home, never the user's Codex settings/credentials.
    with tempfile.TemporaryDirectory(prefix="codex-riscv-check-") as temporary:
        check_env = dict(os.environ, HOME=temporary, CODEX_HOME=temporary)
        result = subprocess.run([str(binary), "--version"], env=check_env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if result.returncode:
            fail("Binary startup check failed; no version was activated:\n" + result.stdout)
        print(result.stdout.strip())


def extract_archive(archive, destination, tag):
    root = "codex-riscv64-linux-gnu-" + tag
    with tarfile.open(archive, "r:gz") as package:
        members = package.getmembers()
        if len(members) > 10000 or sum(m.size for m in members) > 1024 * 1024 * 1024:
            fail("Archive exceeds extraction limits")
        seen = set()
        for member in members:
            name = member.name.rstrip("/")
            parts = name.split("/")
            if (not name or name.startswith("/") or "\\" in name
                    or any(ord(c) < 32 or ord(c) == 127 for c in name)
                    or any(p in ("", ".", "..") for p in parts)
                    or parts[0] != root or name in seen
                    or not (member.isdir() or member.isfile())
                    or (len(parts) > 1 and parts[1] == VERSION_MARKER)):
                fail("Unsafe or unexpected archive member: " + repr(member.name))
            seen.add(name)
        # Never use extractall: copy only prevalidated regular files/directories,
        # ignoring archive ownership, setuid bits, timestamps, and extended metadata.
        for member in members:
            parts = member.name.rstrip("/").split("/")[1:]
            path = destination.joinpath(*parts)
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            else:
                if not parts:
                    fail("Archive root must be a directory")
                path.parent.mkdir(parents=True, exist_ok=True)
                with package.extractfile(member) as source, path.open("xb") as dest:
                    shutil.copyfileobj(source, dest)
                path.chmod(0o755 if member.mode & 0o111 else 0o644)
    if (not (destination / "bin/codex").is_file()
            or not os.access(destination / "bin/codex", os.X_OK)
            or not (destination / "LICENSE").is_file()
            or not (destination / "NOTICE").is_file()
            or not (destination / "licenses").is_dir()):
        fail("Archive is missing the executable or required license notices")


def install(prefix, command_path, tag):
    check_launcher(prefix)
    check_command(command_path, prefix)
    previous_current = pointer(prefix, "current")
    pointer(prefix, "previous")
    directory = prefix / "versions" / tag
    if exists(directory):
        data = managed_version(prefix, tag, verify=True)
        if data["sha256"] != RELEASES[tag]:
            fail("Installed version does not match the pinned archive checksum")
        check_binary(directory, tag)
    else:
        with tempfile.TemporaryDirectory(prefix=".stage-", dir=prefix) as temporary:
            temporary = Path(temporary)
            archive = temporary / "release.tar.gz"
            url = REPOSITORY + "/releases/download/" + tag + "/codex-riscv64-linux-gnu-" + tag + ".tar.gz"
            print("Downloading " + url, flush=True)
            subprocess.run(["curl", "--fail", "--location", "--proto", "=https", "--proto-redir", "=https", "--tlsv1.2", "--retry", "2", "--connect-timeout", "30", "--output", str(archive), url], check=True)
            if digest(archive) != RELEASES[tag]:
                fail("SHA-256 checksum mismatch; nothing was activated")
            staged = temporary / "unpacked"
            staged.mkdir()
            extract_archive(archive, staged, tag)
            check_binary(staged, tag)
            files, dirs = inventory(staged)
            write_json(staged / VERSION_MARKER, {"schema": SCHEMA, "tag": tag, "sha256": RELEASES[tag], "files": files, "dirs": dirs})
            staged.rename(directory)
    check_command(command_path, prefix)
    command_path.parent.mkdir(parents=True, exist_ok=True)
    old_command_target = os.readlink(command_path) if exists(command_path) else None
    ensure_launcher(prefix)
    desired_target = str(prefix / LAUNCHER)
    command_changed = old_command_target != desired_target
    if command_changed:
        if old_command_target is None:
            # Different prefixes have different locks: never replace a command
            # another installation created after our last collision check.
            command_path.symlink_to(desired_target)
        else:
            replace_command_link(command_path, desired_target)
    try:
        if previous_current != tag:
            activate(prefix, tag, previous_current)
    except BaseException:
        if command_changed and command_owned(command_path, prefix):
            if old_command_target is None:
                command_path.unlink()
            else:
                replace_command_link(command_path, old_command_target)
        raise
    print("Installed " + tag + " -> " + str(command_path) + " (standalone --no-daemon launcher)")
    if str(command_path.parent) not in os.environ.get("PATH", "").split(os.pathsep):
        import shlex
        print("Add this directory to PATH yourself (no shell files were changed):\n  export PATH=" + shlex.quote(str(command_path.parent)) + ':"$PATH"')
    print("Use this installer for upgrades. Validate the native sandbox before real work.")


def uninstall(prefix, command_path):
    # Preflight everything before deletion; never recursively delete the prefix.
    allowed = {ROOT_MARKER, ".lock", "versions", "current", "previous", LAUNCHER}
    check_launcher(prefix)
    extras = {p.name for p in prefix.iterdir()} - allowed
    if extras:
        fail("Untracked files in installation prefix; preserved: " + ", ".join(sorted(extras)))
    pointer(prefix, "current")
    pointer(prefix, "previous")
    versions = list((prefix / "versions").iterdir())
    for version in versions:
        managed_version(prefix, version.name, verify=True)
    if exists(command_path):
        if command_owned(command_path, prefix):
            command_path.unlink()
        else:
            print("Preserving unrelated command: " + str(command_path))
    for name in ("current", "previous"):
        if exists(prefix / name):
            (prefix / name).unlink()
    for version in versions:
        # A validated tree contains only manifest-listed regular files/directories.
        shutil.rmtree(version)
    (prefix / "versions").rmdir()
    if exists(prefix / LAUNCHER):
        (prefix / LAUNCHER).unlink()
    (prefix / ROOT_MARKER).unlink()
    print("Uninstalled managed versions. ~/.codex, credentials and shell profiles were not touched.")


def main():
    parser = argparse.ArgumentParser(prog="install.sh", description="Unofficial codex-riscv per-user installer (Linux riscv64, glibc >= 2.39). No root/system-wide installation.")
    parser.add_argument("action", nargs="?", default="install", choices=("install", "upgrade", "rollback", "uninstall", "status"))
    parser.add_argument("--version", help="exact supported adaptation tag (not the upstream CLI version)")
    parser.add_argument("--channel", choices=("experimental",), help="curated experimental channel; never GitHub latest")
    parser.add_argument("--prefix", default=str(Path.home() / ".local/share/codex-riscv"), help="absolute managed data directory")
    parser.add_argument("--bin-dir", help="absolute command directory (default: ~/.local/bin)")
    parser.add_argument("--command", choices=("codex", "codex-riscv"), help="command name; default codex for new installs, existing name retained unless explicitly changed during install/upgrade")
    args = parser.parse_args()
    if args.action not in ("install", "upgrade") and (args.version or args.channel):
        parser.error("--version/--channel apply only to install or upgrade")
    if args.version and args.channel:
        parser.error("choose --version or --channel, not both")
    tag = args.version or DEFAULT_VERSION
    if args.action in ("install", "upgrade") and tag not in RELEASES:
        fail("Unsupported version: " + tag + ". Download a newer installer for newly supported releases.")
    prefix = absolute_path(args.prefix, "--prefix")
    home = Path.home().resolve()
    default_codex_home = (home / ".codex").resolve()
    codex_home = Path(os.environ.get("CODEX_HOME", str(default_codex_home))).expanduser().resolve()
    if prefix in (Path("/"), home) or within(prefix, default_codex_home) or within(prefix, codex_home):
        fail("Refusing unsafe install prefix or Codex configuration directory")
    state = None
    if exists(prefix):
        if not prefix.is_dir():
            fail("Installation prefix is not a directory")
        if exists(prefix / ROOT_MARKER):
            state = managed_state(prefix)
        elif any(prefix.iterdir()):
            fail("Refusing unmanaged nonempty installation prefix: " + str(prefix))
    if args.action not in ("install", "upgrade") and not state:
        fail("No managed installation at " + str(prefix))
    bin_dir = absolute_path(args.bin_dir or (state["bin_dir"] if state else str(home / ".local/bin")), "--bin-dir")
    command = args.command or (state["command"] if state else "codex")
    if (within(bin_dir, prefix) or within(prefix, bin_dir) or within(bin_dir, default_codex_home) or within(bin_dir, codex_home)):
        fail("Install and command directories must be separate, outside Codex configuration")
    if state and state["bin_dir"] != str(bin_dir):
        fail("This installation has a different bin directory. Uninstall it before changing that option.")
    rename_command = bool(state and state["command"] != command)
    if rename_command and args.action not in ("install", "upgrade"):
        fail("Command renaming applies only to install or upgrade")
    command_path = bin_dir / command
    old_command_path = bin_dir / state["command"] if rename_command else command_path
    if args.action == "status":
        print("Current: " + str(pointer(prefix, "current") or "none"))
        print("Previous: " + str(pointer(prefix, "previous") or "none"))
        print("Command: " + str(command_path) + (" (managed)" if command_owned(command_path, prefix) else " (missing or changed)"))
        return
    if os.geteuid() == 0:
        fail("Run as your normal user, not root. System-wide installation is not supported.")
    if args.action in ("install", "upgrade", "rollback"):
        check_platform()
        check_command(command_path, prefix)
        if rename_command and not command_owned(old_command_path, prefix):
            fail("Old command is missing or modified; preserved: " + str(old_command_path))
    prefix.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = prefix / ".lock"
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            fail("Another installer is using this prefix; retry when it finishes")
        # Recheck after acquiring the lock, including first-install races.
        if exists(prefix / ROOT_MARKER):
            state = managed_state(prefix)
            if state["bin_dir"] != str(bin_dir) or state["command"] != old_command_path.name:
                fail("Installation configuration changed; retry")
        elif set(p.name for p in prefix.iterdir()) - {".lock"}:
            fail("Refusing unmanaged installation prefix")
        else:
            write_json(prefix / ROOT_MARKER, {"schema": SCHEMA, "prefix": str(prefix), "bin_dir": str(bin_dir), "command": command})
        versions = prefix / "versions"
        if versions.is_symlink():
            fail("Unsafe versions directory")
        versions.mkdir(exist_ok=True)
        if args.action in ("install", "upgrade"):
            install(prefix, old_command_path, tag)
            if rename_command:
                migrate_command(prefix, old_command_path, command_path)
        elif args.action == "rollback":
            current, previous = pointer(prefix, "current"), pointer(prefix, "previous")
            if not current or not previous or current == previous:
                fail("No previous managed version to roll back to")
            managed_version(prefix, previous, verify=True)
            check_binary(prefix / "versions" / previous, previous)
            if not command_owned(command_path, prefix):
                fail("Managed command link is missing; rerun install first")
            activate(prefix, previous, current)
            print("Rolled back to " + previous)
        elif args.action == "uninstall":
            uninstall(prefix, command_path)
            # Keep the lock held until its directory is removed.
            lock_path.unlink()
            prefix.rmdir()
    finally:
        os.close(lock_fd)


try:
    main()
except (RuntimeError, OSError, ValueError, tarfile.TarError, subprocess.SubprocessError) as error:
    print("codex-riscv: " + str(error), file=sys.stderr)
    sys.exit(1)
except KeyboardInterrupt:
    print("codex-riscv: interrupted; rerun the installer to retry", file=sys.stderr)
    sys.exit(130)
PY
