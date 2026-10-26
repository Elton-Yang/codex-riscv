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
sh install-codex-riscv.sh upgrade --command codex
sh install-codex-riscv.sh status
```

`upgrade` works for first installation too. The default is `.3`; `.1`, `.2` and `.3` are supported. Exact archive SHA256 values are pinned in `RELEASES` inside the script and published in the release `SHA256SUMS`. Unknown versions, mirrors and checksum bypasses are not supported. HTTPS and the digest protect the selected bytes, not an independent publisher signature.

```sh
sh install-codex-riscv.sh install --version v0.1.0-experimental.3
sh install-codex-riscv.sh upgrade --channel experimental
sh install-codex-riscv.sh rollback
sh install-codex-riscv.sh uninstall
```

Rollback toggles the previous successful version; same-version reinstall does not create history. It switches program versions only and does not undo changes to settings or projects. Uninstall removes verified, unmodified managed files; modified or foreign files are preserved and reported.

## Layout and preservation

```text
~/.local/share/codex-riscv/
├── versions/v0.1.0-experimental.3/
│   ├── bin/codex
│   ├── bin/codex-code-mode-host
│   ├── LICENSE, NOTICE
│   └── licenses/, docs/, manifests/, patches/, scripts/
├── launcher
├── current -> versions/v0.1.0-experimental.3
└── previous -> versions/<previous-successful-tag>
~/.local/bin/codex -> ~/.local/share/codex-riscv/launcher
```

The launcher adds `--no-daemon` to ordinary calls and preserves internal helper dispatch. CLI discovers the host adjacent to its actual executable. This does not disable sandboxing. Installation does not log in, call a model, modify `~/.codex`, change model settings, alter shell files or touch projects.

`--prefix` and `--bin-dir` must be separate absolute dedicated paths outside Codex configuration; the default command is `codex`. Existing installations retain their saved command on plain `upgrade`; `upgrade --command codex` migrates a managed `codex-riscv` entry in place. A foreign target or another `codex` on PATH prevents migration. The old managed entry is removed only after the new entry and metadata are ready, and recoverable rename failures restore the old command metadata. Existing version history, launcher and user settings are retained. An explicit `--command codex-riscv` is still supported. The bin directory cannot be changed in place; custom prefixes must be supplied again for later management. The installer never edits PATH; add `~/.local/bin` yourself if needed.

## Activation checks and limits

Before activation, the archive is checked against its exact digest; traversal, links, devices, duplicates and oversized archives are rejected. Regular files are staged in a new directory. Both `.2`/`.3` binaries must exist, be executable and resolve their dynamic libraries; `.1` requires only the CLI. CLI `--version` runs in a disposable HOME/CODEX_HOME. The installer does not initialize V8 through a model request, so successful installation is not a Code Mode runtime test.

Only after checks pass does the installer atomically replace `current`; it retains the previous version. Download/check failures leave the active version intact. Recoverable activation failures restore history, but the two history links are not a power-loss transaction. A killed install can leave `.stage-*` directories; inspect them before removal. Do not put user files inside managed version directories or delete metadata to override ownership checks.

The fixture suite covers missing host/libraries/permissions, `.1` → `.2` upgrade and rollback, configuration/project preservation and existing installer protections. Local package smoke tests use QEMU and mocked platform gates. The user has since reported native program creation and exit → `/resume` → editing with `gpt-5.6-luna`; the subsequent terminal transcript also confirms native `.2` → `.1` → `.2` rollback/upgrade, retained model/program, correct editing/execution and the measured sandbox probes (kernel `6.12.113+deb13-riscv64`, bubblewrap `0.12.0`). See [native functional results](native-validation-v0.1.0-experimental.2.md). See [release notes](release-notes-v0.1.0-experimental.2.md).

`.3` optimizes the CLI and retains the `.2` host. Native post-selection resume loading is user-reported improved; quantitative timings and startup behavior remain unmeasured; see [new notes](release-notes-v0.1.0-experimental.3.md).
