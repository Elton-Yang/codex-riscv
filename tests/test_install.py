#!/usr/bin/env python3
"""Installer black-box tests, with local archives and a mocked target platform.

Run: python3 -m unittest discover -s tests -v

The host is NOT a native RISC-V device. These tests replace only the version/digest
catalog in disposable installer copies (plus simulated-root/activation-fault cases),
mock
platform/download commands through PATH, and run the real sh/Python launcher,
archive validation and filesystem operations. Production code contains no test-only platform, URL, or checksum bypass. No network, credentials,
models, package installation or root access are used by this suite.
"""
import fcntl
import hashlib
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest


REPOSITORY = Path(__file__).resolve().parents[1]
TAG = "v0.1.0-experimental.1"
NEXT_TAG = "v0.1.0-experimental.2"
PUBLISHED_SHA = "2b70f049652793a2dd6c8035122ce2a6920de680153be1c6f8e2a172dde70120"

MOCK_PROGRAM = r'''#!/usr/bin/env python3
import os
from pathlib import Path
import shutil
import sys
name = Path(sys.argv[0]).name
args = sys.argv[1:]
if name == "uname":
    print(os.environ.get("TEST_SYSTEM", "Linux") if "-s" in args else os.environ.get("TEST_MACHINE", "riscv64"))
elif name == "getconf":
    print(os.environ.get("TEST_GLIBC", "glibc 2.41"))
elif name == "ldd":
    if os.environ.get("TEST_MISSING_LIBRARY"):
        print("libssl.so.3 => not found")
        sys.exit(0)
    print("libssl.so.3 => /lib/libssl.so.3 (0x1234)")
    print("libcrypto.so.3 => /lib/libcrypto.so.3 (0x1234)")
    print("libgcc_s.so.1 => /lib/libgcc_s.so.1 (0x1234)")
    print("libc.so.6 => /lib/libc.so.6 (0x1234)")
elif name == "bwrap":
    print("bubblewrap 0.12.0")
elif name == "curl":
    if os.environ.get("TEST_DOWNLOAD_FAIL"):
        print("curl: simulated download failure", file=sys.stderr)
        sys.exit(22)
    url = next((x for x in args if x.startswith("https://")), "")
    filename = url.rsplit("/", 1)[-1]
    archive = Path(os.environ["TEST_ARCHIVES"]) / filename
    if not archive.is_file():
        print("mock curl: unexpected URL " + url, file=sys.stderr)
        sys.exit(22)
    output = None
    for option in ("-o", "--output"):
        if option in args:
            output = args[args.index(option) + 1]
    if "-O" in args or "--remote-name" in args:
        output = filename
    if output:
        shutil.copyfile(archive, output)
    else:
        sys.stdout.buffer.write(archive.read_bytes())
else:
    raise SystemExit("unexpected mock command " + name)
'''


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="codex-installer-test-")
        self.addCleanup(self.temporary.cleanup)
        self.work = Path(self.temporary.name)
        self.home = self.work / "home"
        self.home.mkdir()
        self.prefix = self.home / ".local/share/codex-riscv"
        self.bin = self.home / ".local/bin"
        self.command = self.bin / "codex-riscv"
        self.archives = self.work / "archives"
        self.archives.mkdir()
        self.mocks = self.work / "mock-bin"
        self.mocks.mkdir()
        for name in ("uname", "getconf", "ldd", "bwrap", "curl"):
            executable = self.mocks / name
            executable.write_text(MOCK_PROGRAM)
            executable.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home),
                        PATH=str(self.mocks) + ":/usr/bin:/bin",
                        TEST_ARCHIVES=str(self.archives))
        # Prevent invocation environment from contaminating isolated cases.
        for variable in list(self.env):
            if variable.startswith("TEST_") and variable != "TEST_ARCHIVES":
                del self.env[variable]
        self.installer = self.make_installer(TAG)

    def make_archive(self, tag, extra=(), omit=(), binary_script=None):
        root = "codex-riscv64-linux-gnu-" + tag
        target = self.archives / (root + ".tar.gz")
        entries = {
            root + "/bin/codex": (binary_script or "#!/bin/sh\nprintf 'codex-cli 0.0.0\\n'\n".encode(), 0o755),
            root + "/LICENSE": (b"Test license\n", 0o644),
            root + "/NOTICE": (b"Test notice\n", 0o644),
            root + "/licenses/test.txt": (b"Third-party test license\n", 0o644),
        }
        with tarfile.open(target, "w:gz", format=tarfile.USTAR_FORMAT) as archive:
            for name, (data, mode) in entries.items():
                if name.split(root + "/", 1)[-1] in omit:
                    continue
                info = tarfile.TarInfo(name)
                info.mode = mode
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
            for info, data in extra:
                archive.addfile(info, io.BytesIO(data) if data is not None else None)
        return target

    def make_installer(self, tag, archive=None, checksum=None):
        archive = archive or self.make_archive(tag)
        digest = checksum or hashlib.sha256(archive.read_bytes()).hexdigest()
        source = (REPOSITORY / "install.sh").read_text()
        self.assertIn(PUBLISHED_SHA, source, "Test fixture must replace the real pinned digest")
        source = source.replace(PUBLISHED_SHA, digest).replace(TAG, tag)
        installer = self.work / ("installer-" + tag + ".sh")
        installer.write_text(source)
        return installer

    def run_installer(self, *args, success=True, installer=None, **environment):
        env = dict(self.env, **environment)
        result = subprocess.run(["sh", str(installer or self.installer), *args],
                                env=env, cwd=self.work, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                timeout=30)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def assert_current(self, tag):
        self.assertTrue((self.prefix / "current").is_symlink())
        self.assertEqual((self.prefix / "current").resolve(), self.prefix / "versions" / tag)
        self.assertTrue(self.command.is_symlink())
        self.assertEqual(self.command.resolve(), self.prefix / "versions" / tag / "bin/codex")

    def test_help_without_platform_check_or_mutation(self):
        output = self.run_installer("--help", TEST_MACHINE="x86_64").stdout
        self.assertIn("--version", output)
        self.assertFalse(self.prefix.exists())

    def test_reject_invalid_arguments_before_mutation(self):
        cases = [("--wat",), ("--version",), ("--prefix",), ("--bin-dir",),
                 ("--command",), ("--channel",), ("--command", "../codex"),
                 ("--version", "latest"), ("--channel", "stable"),
                 ("--version", "../../outside"), ("--prefix", "relative"),
                 ("--bin-dir", "relative"),
                 ("--version", TAG, "--channel", "experimental")]
        for arguments in cases:
            with self.subTest(arguments=arguments):
                self.run_installer(*arguments, success=False)
                self.assertFalse(self.prefix.exists())

    def test_platform_guards(self):
        for environment in ({"TEST_SYSTEM": "Darwin"}, {"TEST_MACHINE": "x86_64"},
                            {"TEST_GLIBC": "glibc 2.38"}, {"TEST_GLIBC": "musl"}):
            with self.subTest(environment=environment):
                self.run_installer(success=False, **environment)
                self.assertFalse(self.command.exists())

    def test_root_guard(self):
        source = self.installer.read_text()
        self.assertIn("os.geteuid()", source)
        source = source.replace("os.geteuid()", "0")
        root_installer = self.work / "simulated-root.sh"
        root_installer.write_text(source)
        self.run_installer(installer=root_installer, success=False)
        self.assertFalse(self.command.exists())

    def test_startup_check_does_not_touch_user_home_or_codex_home(self):
        default_config = self.home / ".codex"
        default_config.mkdir()
        (default_config / "keep.toml").write_text("default configuration\n")
        custom_config = self.work / "custom-codex-home"
        custom_config.mkdir()
        (custom_config / "keep.toml").write_text("custom configuration\n")
        program = (b"#!/bin/sh\nset -eu\n"
                   b'mkdir -p "$HOME/.codex" "$CODEX_HOME"\n'
                   b'printf "startup write\\n" > "$HOME/startup-home-marker"\n'
                   b'printf "startup write\\n" > "$HOME/.codex/startup-default-marker"\n'
                   b'printf "startup write\\n" > "$CODEX_HOME/startup-codex-marker"\n'
                   b"printf 'codex-cli isolated-fixture\\n'\n")
        archive = self.make_archive(TAG, binary_script=program)
        installer = self.make_installer(TAG, archive=archive)
        for action in ("install", "upgrade"):
            output = self.run_installer(action, installer=installer,
                                        CODEX_HOME=str(custom_config)).stdout
            self.assertIn("codex-cli isolated-fixture", output)
            self.assertFalse((self.home / "startup-home-marker").exists())
            self.assertEqual(sorted(p.name for p in default_config.iterdir()), ["keep.toml"])
            self.assertEqual(sorted(p.name for p in custom_config.iterdir()), ["keep.toml"])
            self.assertEqual((default_config / "keep.toml").read_text(), "default configuration\n")
            self.assertEqual((custom_config / "keep.toml").read_text(), "custom configuration\n")
        self.assert_current(TAG)

    def test_install_default_and_status(self):
        self.run_installer()
        self.assert_current(TAG)
        self.assertTrue((self.prefix / ".codex-riscv-install").is_file())
        version = self.prefix / "versions" / TAG
        self.assertTrue((version / ".codex-riscv-version").is_file())
        self.assertEqual((version / "NOTICE").read_text(), "Test notice\n")
        self.assertTrue((version / "licenses/test.txt").is_file())
        self.assertIn(TAG, self.run_installer("status").stdout)
        self.assertFalse((self.home / ".profile").exists())
        self.assertFalse((self.home / ".bashrc").exists())

    def test_install_explicit_version_and_channel(self):
        self.run_installer("install", "--version", TAG)
        self.assert_current(TAG)
        self.run_installer("upgrade", "--channel", "experimental")
        self.assert_current(TAG)

    def test_custom_paths_with_spaces(self):
        prefix = self.work / "custom location" / "codex-riscv"
        bin_dir = self.work / "custom commands"
        self.run_installer("--prefix", str(prefix), "--bin-dir", str(bin_dir))
        self.assertEqual((bin_dir / "codex-riscv").resolve(), prefix / "versions" / TAG / "bin/codex")
        self.run_installer("uninstall", "--prefix", str(prefix))
        self.assertFalse((bin_dir / "codex-riscv").is_symlink())

    def test_regular_command_collision(self):
        self.bin.mkdir(parents=True)
        self.command.write_text("do not overwrite\n")
        self.run_installer(success=False)
        self.assertEqual(self.command.read_text(), "do not overwrite\n")

    def test_dangling_command_collision(self):
        self.bin.mkdir(parents=True)
        self.command.symlink_to(self.work / "missing")
        self.run_installer(success=False)
        self.assertEqual(os.readlink(self.command), str(self.work / "missing"))

    def test_explicit_codex_command(self):
        self.run_installer("--command", "codex")
        self.assertTrue((self.bin / "codex").is_symlink())
        self.assertFalse(self.command.exists())
        self.run_installer("uninstall")
        self.assertFalse((self.bin / "codex").is_symlink())

    def test_explicit_codex_collision(self):
        self.bin.mkdir(parents=True)
        codex = self.bin / "codex"
        codex.write_text("existing npm codex\n")
        self.run_installer("--command", "codex", success=False)
        self.assertEqual(codex.read_text(), "existing npm codex\n")

    def test_explicit_codex_path_collision(self):
        codex = self.mocks / "codex"
        codex.write_text("#!/bin/sh\nprintf 'existing codex\\n'\n")
        codex.chmod(0o755)
        self.run_installer("--command", "codex", success=False)
        self.assertFalse((self.bin / "codex").exists())
        self.assertTrue(codex.is_file())

    def test_checksum_failure_has_no_active_install(self):
        wrong = self.make_installer(TAG, checksum="0" * 64)
        result = self.run_installer(installer=wrong, success=False)
        self.assertIn("checksum", result.stdout.lower())
        self.assertFalse(self.command.exists())
        self.assertFalse((self.prefix / "current").exists())

    def test_download_failure_has_no_active_install(self):
        self.run_installer(success=False, TEST_DOWNLOAD_FAIL="1")
        self.assertFalse(self.command.exists())
        self.assertFalse((self.prefix / "current").exists())

    def test_missing_runtime_library_has_no_active_install(self):
        self.run_installer(success=False, TEST_MISSING_LIBRARY="1")
        self.assertFalse(self.command.exists())
        self.assertFalse((self.prefix / "current").exists())

    def test_repeat_install_is_safe(self):
        self.run_installer()
        self.run_installer()
        self.assert_current(TAG)
        self.assertFalse((self.prefix / "previous").is_symlink())

    def test_upgrade_and_rollback(self):
        self.run_installer()
        newer = self.make_installer(NEXT_TAG)
        self.run_installer("upgrade", installer=newer)
        self.assert_current(NEXT_TAG)
        self.assertEqual((self.prefix / "previous").resolve(), self.prefix / "versions" / TAG)
        self.run_installer("rollback", installer=newer)
        self.assert_current(TAG)
        self.run_installer("rollback", installer=newer)
        self.assert_current(NEXT_TAG)

    def test_failed_upgrade_keeps_working_version(self):
        self.run_installer()
        newer = self.make_installer(NEXT_TAG, checksum="0" * 64)
        self.run_installer("upgrade", installer=newer, success=False)
        self.assert_current(TAG)
        self.run_installer("upgrade", installer=newer, success=False, TEST_DOWNLOAD_FAIL="1")
        self.assert_current(TAG)

    def test_failed_activation_preserves_current_and_previous(self):
        self.run_installer()
        second = self.make_installer(NEXT_TAG)
        self.run_installer("upgrade", installer=second)
        third = self.make_installer("v0.1.0-experimental.3")
        source = third.read_text()
        replacement = "        os.replace(temporary, prefix / name)"
        self.assertIn(replacement, source)
        source = source.replace(replacement,
            '        if name == "current":\n'
            '            raise OSError("simulated activation failure")\n' + replacement)
        third.write_text(source)
        self.run_installer("upgrade", installer=third, success=False)
        self.assert_current(NEXT_TAG)
        self.assertEqual((self.prefix / "previous").resolve(), self.prefix / "versions" / TAG)
        self.run_installer("rollback", installer=third, success=False)
        self.assert_current(NEXT_TAG)
        self.assertEqual((self.prefix / "previous").resolve(), self.prefix / "versions" / TAG)
        self.run_installer("rollback", installer=second)
        self.assert_current(TAG)

    def test_codex_config_symlink_remains_protected_with_home_override(self):
        config = self.work / "real-codex-config"
        config.mkdir()
        (config / "keep.toml").write_text("configuration\n")
        (self.home / ".codex").symlink_to(config, target_is_directory=True)
        override = str(self.home / "other-codex-home")
        self.run_installer("--prefix", str(config / "installation"),
                           success=False, CODEX_HOME=override)
        self.run_installer("--bin-dir", str(config / "bin"),
                           success=False, CODEX_HOME=override)
        self.assertEqual(sorted(p.name for p in config.iterdir()), ["keep.toml"])

    def test_malformed_metadata_fails_without_traceback(self):
        self.run_installer()
        for path in (self.prefix / ".codex-riscv-install",
                     self.prefix / "versions" / TAG / ".codex-riscv-version"):
            original = path.read_text()
            for malformed in ("null", "[]", "{invalid json"):
                with self.subTest(path=path.name, value=malformed):
                    path.write_text(malformed)
                    result = self.run_installer("status", success=False)
                    self.assertNotIn("Traceback", result.stdout)
                    path.write_text(original)
        self.assert_current(TAG)

    def test_failed_first_install_can_be_retried(self):
        self.run_installer(success=False, TEST_DOWNLOAD_FAIL="1")
        self.run_installer()
        self.assert_current(TAG)

    def test_lock_prevents_concurrent_mutation(self):
        self.run_installer()
        with (self.prefix / ".lock").open("r+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.run_installer("upgrade", success=False)
            self.run_installer("uninstall", success=False)
            self.assert_current(TAG)
        self.run_installer("upgrade")
        self.assert_current(TAG)

    def test_uninstall_invalid_current_pointer_preserves_foreign_files(self):
        self.run_installer()
        foreign = self.work / "foreign-data"
        foreign.mkdir()
        (foreign / "keep.txt").write_text("unrelated\n")
        (self.prefix / "current").unlink()
        (self.prefix / "current").symlink_to(foreign)
        self.run_installer("uninstall", success=False)
        self.assertEqual((foreign / "keep.txt").read_text(), "unrelated\n")
        self.assertTrue((self.prefix / "versions" / TAG).is_dir())

    def test_rollback_without_previous_fails_safely(self):
        self.run_installer()
        self.run_installer("rollback", success=False)
        self.assert_current(TAG)

    def test_uninstall_preserves_user_configuration(self):
        config = self.home / ".codex"
        config.mkdir()
        (config / "config.toml").write_text("user configuration\n")
        self.bin.mkdir(parents=True)
        other = self.bin / "other-tool"
        other.write_text("unrelated\n")
        self.run_installer()
        self.run_installer("uninstall")
        self.assertFalse(self.command.is_symlink())
        self.assertFalse((self.prefix / "versions" / TAG).exists())
        self.assertEqual((config / "config.toml").read_text(), "user configuration\n")
        self.assertEqual(other.read_text(), "unrelated\n")

    def test_unmanaged_prefix_is_not_adopted_or_deleted(self):
        self.prefix.mkdir(parents=True)
        sentinel = self.prefix / "unrelated.txt"
        sentinel.write_text("keep me\n")
        self.run_installer(success=False)
        self.run_installer("uninstall", success=False)
        self.assertEqual(sentinel.read_text(), "keep me\n")

    def test_uninstall_preserves_modified_managed_version(self):
        self.run_installer()
        notice = self.prefix / "versions" / TAG / "NOTICE"
        notice.write_text("user modification\n")
        self.run_installer("uninstall", success=False)
        self.assertEqual(notice.read_text(), "user modification\n")
        self.assert_current(TAG)

    def test_uninstall_preserves_foreign_prefix_contents(self):
        self.run_installer()
        sentinel = self.prefix / "unrelated-user-file"
        sentinel.write_text("keep me\n")
        self.run_installer("uninstall", success=False)
        self.assertEqual(sentinel.read_text(), "keep me\n")
        self.assert_current(TAG)

    def test_uninstall_replaced_command_is_not_deleted(self):
        self.run_installer()
        self.command.unlink()
        self.command.write_text("replacement owned by user\n")
        # Refusing uninstall or preserving the foreign command are both safe.
        result = subprocess.run(["sh", str(self.installer), "uninstall"], env=self.env,
                                cwd=self.work, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=30)
        self.assertEqual(self.command.read_text(), "replacement owned by user\n", result.stdout)

    def test_tar_parent_traversal_rejected(self):
        info = tarfile.TarInfo("../../escaped-by-tar")
        info.size = 8
        archive = self.make_archive(TAG, extra=[(info, b"unsafe!\n")])
        installer = self.make_installer(TAG, archive=archive)
        self.run_installer(installer=installer, success=False)
        self.assertFalse(self.command.exists())
        self.assertFalse((self.work / "escaped-by-tar").exists())

    def test_tar_absolute_path_rejected(self):
        escape = self.work / "escaped-absolute"
        info = tarfile.TarInfo(str(escape))
        info.size = 8
        archive = self.make_archive(TAG, extra=[(info, b"unsafe!\n")])
        installer = self.make_installer(TAG, archive=archive)
        self.run_installer(installer=installer, success=False)
        self.assertFalse(escape.exists())
        self.assertFalse(self.command.exists())

    def test_tar_symlink_and_hardlink_rejected(self):
        for link_type in (tarfile.SYMTYPE, tarfile.LNKTYPE):
            with self.subTest(link_type=link_type):
                info = tarfile.TarInfo("codex-riscv64-linux-gnu-" + TAG + "/unsafe-link")
                info.type = link_type
                info.linkname = "../../outside"
                archive = self.make_archive(TAG, extra=[(info, None)])
                installer = self.make_installer(TAG, archive=archive)
                self.run_installer(installer=installer, success=False)
                self.assertFalse(self.command.exists())

    def test_symlink_prefix_is_not_followed(self):
        foreign = self.work / "foreign-installation"
        foreign.mkdir()
        sentinel = foreign / "keep.txt"
        sentinel.write_text("foreign data\n")
        self.prefix.parent.mkdir(parents=True)
        self.prefix.symlink_to(foreign, target_is_directory=True)
        self.run_installer(success=False)
        self.run_installer("uninstall", success=False)
        self.assertEqual(sentinel.read_text(), "foreign data\n")
        self.assertEqual(sorted(p.name for p in foreign.iterdir()), ["keep.txt"])

    def test_tar_duplicate_and_special_members_rejected(self):
        root = "codex-riscv64-linux-gnu-" + TAG
        duplicate = tarfile.TarInfo(root + "/NOTICE")
        duplicate.size = 9
        special = tarfile.TarInfo(root + "/unsafe-fifo")
        special.type = tarfile.FIFOTYPE
        for entry in ((duplicate, b"duplicate"), (special, None)):
            with self.subTest(member=entry[0].name):
                archive = self.make_archive(TAG, extra=[entry])
                installer = self.make_installer(TAG, archive=archive)
                self.run_installer(installer=installer, success=False)
                self.assertFalse(self.command.exists())

    def test_missing_binary_or_notices_rejected(self):
        for missing in ("bin/codex", "LICENSE", "NOTICE", "licenses/test.txt"):
            with self.subTest(missing=missing):
                archive = self.make_archive(TAG, omit=[missing])
                installer = self.make_installer(TAG, archive=archive)
                self.run_installer(installer=installer, success=False)
                self.assertFalse(self.command.exists())


if __name__ == "__main__":
    unittest.main()
