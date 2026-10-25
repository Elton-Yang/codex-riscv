# Per-user installer

[简体中文](installer.md) · [README](../README.en.md)

`install.sh` manages the existing unofficial RISC-V Linux release. It does not build Codex, install an npm package or change upstream source. Run it with `sh` as an ordinary user on Linux riscv64. “User-global” means the command can be used from any directory after its bin directory is on your `PATH`; it does not install for every account.

## Requirements and trust

- Linux `riscv64`, glibc **2.39 or newer**; Debian 13 riscv64 is the intended starting point.
- Python 3 for the installer, `curl` and CA certificates for HTTPS downloads, `uname`, `getconf`, `ldd`, and system `bwrap`.
- Runtime libraries including `libgcc-s1` and OpenSSL 3 (`libssl3t64` on Debian 13). The installer checks the staged binary's dynamic dependencies and runs `--version` with a disposable `HOME` / `CODEX_HOME` before activation.
- Enough free disk space for the compressed archive, the full extracted release and retained previous versions. The current executable alone is about 315 MB.

Debian dependencies:

```bash
sudo apt update
sudo apt install ca-certificates curl python3 libc6 libgcc-s1 libssl3t64 bubblewrap
```

The package installation uses `sudo`; the Codex installer and Codex itself must not. Presence of `bwrap` is not proof that the board's kernel and policy support its sandbox. Follow the separate [native sandbox validation guidance](../README.en.md#4-validate-the-native-sandbox-before-real-work).

Download the script from this repository and review it before running. The `main` URL in the README can change. For repeatable installation, use an inspected repository commit in place of `main` and retain that script. The embedded archive SHA-256 pins the expected release bytes, but is not a publisher signature or an independent way to authenticate the installer itself.

The current catalog contains exactly:

| Adaptation release | SHA-256 of the `.tar.gz` archive |
| --- | --- |
| `v0.1.0-experimental.1` | `2b70f049652793a2dd6c8035122ce2a6920de680153be1c6f8e2a172dde70120` |

The archive is `codex-riscv64-linux-gnu-v0.1.0-experimental.1.tar.gz` from this project's GitHub Release. No mirror, unknown version, checksum bypass or alternative source is accepted by the production installer. The default `experimental` channel is an explicit opt-in to this repository's experimental build by running its installer; it is not an upstream stable channel. There is no `stable` or `latest` fallback.

## Commands

```text
sh install.sh [install|upgrade|rollback|uninstall|status]
              [--version TAG] [--channel experimental]
              [--prefix ABSOLUTE_PATH] [--bin-dir ABSOLUTE_PATH]
              [--command codex-riscv|codex]
```

Use `sh install.sh --help` for the authoritative option list. With no action, the installer performs `install`.

```bash
# Default: supported experimental release, separate command name.
sh install.sh

# Explicit adaptation version; binary --version still says 0.0.0.
sh install.sh install --version v0.1.0-experimental.1
sh install.sh status

# Same installation path; selects the release pinned in this script.
sh install.sh upgrade --channel experimental

# Only after a different managed version has been activated.
sh install.sh rollback

# Removes the managed installation, not user data or credentials.
sh install.sh uninstall
```

There is currently only one published binary release. Installing or upgrading to it again does not manufacture a previous version. Future upgrade support requires an updated installer catalog; download and review that installer first. Rollback switches to the previously active managed version, not an arbitrary upstream release. Keep the same custom `--prefix` when managing a non-default installation.

## Paths and command names

Defaults:

```text
~/.local/share/codex-riscv/
├── versions/
│   └── v0.1.0-experimental.1/
│       ├── bin/codex
│       ├── LICENSE
│       ├── NOTICE
│       ├── licenses/
│       └── ...release documentation and installer metadata
├── current -> versions/v0.1.0-experimental.1
└── previous -> versions/<previous-tag>  # only after a version switch

~/.local/bin/codex-riscv -> ~/.local/share/codex-riscv/current/bin/codex
```

Use `--prefix` for the managed installation directory and `--bin-dir` for its command directory, both absolute paths. Choose a dedicated, empty prefix, not a project directory or your home directory. Root / system-wide installation is deliberately not implemented.

The installer prints a `PATH` hint if needed. For the defaults, this command affects only the current shell:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

It does not modify `.profile`, `.bashrc`, `.zshrc` or other startup files. Add a line yourself only if you want persistence and after checking your existing `PATH` configuration.

The safe default is `codex-riscv`. To choose `codex`, pass `--command codex` at first installation. The installer refuses an unrelated file or link at the command destination, and an unrelated same-name executable found on `PATH`. It does not remove or overwrite an npm, package-manager or manually installed Codex. Inspect a collision and decide yourself whether to rename or move it. Changing the command name of an existing managed installation requires uninstalling and reinstalling it.

## Safety and failure behavior

- Download over HTTPS and require the exact archive digest from the installer catalog before inspecting or executing its contents.
- Preflight the archive; reject absolute paths, traversal, links, special files and duplicate paths. Extract only ordinary directories and files into a fresh staging directory, not over a live installation.
- Preserve the complete release, including notices. Check dynamic libraries and startup before replacing the `current` symlink atomically. A download, checksum or startup failure does not switch the active version.
- Keep the previously active managed version for rollback. This does not undo changes Codex or you made to a project or to `~/.codex`.
- Before uninstalling, check ownership metadata and recorded file contents. Refuse modified or untracked installation files rather than deleting them. Do not put personal files under the managed prefix.
- Never delete `~/.codex`, authentication, shell settings or project files. No model request or login is performed during installation.

If uninstall reports altered or untracked files, inspect and back them up or move them out yourself, then retry. Do not remove the ownership metadata to force the installer to accept the directory. An unrelated file replacing the command symlink is not removed. A forced termination can leave a `.stage-*` directory; inspect and remove only that abandoned staging directory yourself before retrying uninstall. Active-link replacements are atomic, but current/previous history is not a power-loss-safe two-link transaction.

## Updates and validation limits

The existing binary was built from a development commit whose package version is `0.0.0`, and upstream update checks are disabled for that development version. The installer introduces no wrapper and makes no source or binary change. Use this installer for upgrades; do not use an upstream/npm update path to replace the RISC-V binary.

Installer fixture tests use isolated directories and mocked platform/download commands; they are not native board tests. Likewise, QEMU startup of the published binary does not prove that the installer or sandbox works on a physical board. The repository's earlier user-reported VisionFive 2 tests apply to the binary, not automatically to this new installer. See [validation records](validation.md) and the [installer release notes](release-notes-installer-v1.md) for the recorded scope.
