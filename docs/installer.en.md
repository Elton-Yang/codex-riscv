# Per-user installer

[简体中文](installer.md) · [README](../README.md)

The existing `install.sh` installs the curated experimental release for Linux riscv64, glibc ≥ 2.39, as an ordinary user. Python 3, curl, CA certificates, `ldd`, `uname`, `getconf`, bubblewrap, libgcc and OpenSSL 3 runtime libraries are required. It does not build Codex or install npm packages.

## Install and upgrade

Re-download the script for newly supported releases; a previously downloaded script does not query GitHub latest.

```sh
curl --fail --location --proto '=https' --proto-redir '=https' --tlsv1.2 \
  https://raw.githubusercontent.com/Elton-Yang/codex-riscv/main/install.sh \
  -o install-codex-riscv.sh
less install-codex-riscv.sh
sh install-codex-riscv.sh upgrade
sh install-codex-riscv.sh status
```

`upgrade` works for first installation too. The default is `.2`; both `v0.1.0-experimental.1` and `v0.1.0-experimental.2` are supported. Exact archive SHA256 values are pinned in `RELEASES` inside the script and published in the release `SHA256SUMS`. Unknown versions, mirrors and checksum bypasses are not supported. HTTPS and the digest protect the selected bytes, not an independent publisher signature.

```sh
sh install-codex-riscv.sh install --version v0.1.0-experimental.2
sh install-codex-riscv.sh upgrade --channel experimental
sh install-codex-riscv.sh rollback
sh install-codex-riscv.sh uninstall
```

Rollback toggles the previous successful version; same-version reinstall does not create history. It switches program versions only and does not undo changes to settings or projects. Uninstall removes verified, unmodified managed files; modified or foreign files are preserved and reported.

## Layout and preservation

```text
~/.local/share/codex-riscv/
├── versions/v0.1.0-experimental.2/
│   ├── bin/codex
│   ├── bin/codex-code-mode-host
│   ├── LICENSE, NOTICE
│   └── licenses/, docs/, manifests/, patches/, scripts/
├── launcher
├── current -> versions/v0.1.0-experimental.2
└── previous -> versions/<previous-successful-tag>
~/.local/bin/codex-riscv -> ~/.local/share/codex-riscv/launcher
```

The launcher adds `--no-daemon` to ordinary calls and preserves internal helper dispatch. CLI discovers the host adjacent to its actual executable. This does not disable sandboxing. Installation does not log in, call a model, modify `~/.codex`, change model settings, alter shell files or touch projects.

`--prefix` and `--bin-dir` must be separate absolute dedicated paths outside Codex configuration; default command is `codex-riscv`. `--command codex` can be chosen for first installation if it does not collide with another command. Existing installations retain their command/bin directory; custom prefixes must be supplied again for later management. The installer never edits PATH; add `~/.local/bin` yourself if needed.

## Activation checks and limits

Before activation, the archive is checked against its exact digest; traversal, links, devices, duplicates and oversized archives are rejected. Regular files are staged in a new directory. Both `.2` binaries must exist, be executable and resolve their dynamic libraries; `.1` requires only the CLI. CLI `--version` runs in a disposable HOME/CODEX_HOME. The installer does not initialize V8 through a model request, so successful installation is not a Code Mode runtime test.

Only after checks pass does the installer atomically replace `current`; it retains the previous version. Download/check failures leave the active version intact. Recoverable activation failures restore history, but the two history links are not a power-loss transaction. A killed install can leave `.stage-*` directories; inspect them before removal. Do not put user files inside managed version directories or delete metadata to override ownership checks.

The fixture suite covers missing host/libraries/permissions, `.1` → `.2` upgrade and rollback, configuration/project preservation and existing installer protections. Local package smoke tests use QEMU and mocked platform gates. Physical `.2` installation and authenticated startup on VisionFive 2 remain pending user confirmation. See [release notes](release-notes-v0.1.0-experimental.2.md).
