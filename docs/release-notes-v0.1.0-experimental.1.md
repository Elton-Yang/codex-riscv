# v0.1.0-experimental.1

Experimental prerelease of an unofficial RISC-V Linux adaptation of OpenAI Codex CLI. This project is independent of and not endorsed by OpenAI.

## Included

- A stripped, dynamically linked `riscv64gc-unknown-linux-gnu` CLI executable built with the unoptimized `dev-small` profile.
- A two-line functional patch enabling the existing RISC-V seccompiler architecture dispatch, with no sandbox rules removed.
- Pinned cross-build scripts, dependency manifests, validation documentation, upstream attribution and third-party license materials.
- A companion `SHA256SUMS` file for release-asset integrity checks.

Upstream commit: `970111f6cb62cc02fe36a82ea7d71b37a2889c97`.

This adaptation tag is not an upstream Codex version. The pinned development commit declares version `0.0.0`; the executable therefore reports `codex-cli 0.0.0`.

## Verified

- Successful CLI cross-build using Rust 1.99.1 and GCC 14.2.
- QEMU `--version` and `--help`, both exit 0.
- Six seccomp policy-selection unit tests under QEMU, all passed; 153 unrelated tests filtered out.

## Important limits

**Not yet tested on VisionFive 2 / JH7110 hardware.** QEMU tests do not establish actual kernel sandbox enforcement. Interactive TUI, authentication, model API requests, the full test suite and optimized performance were not tested.

The binary requires GNU/Linux runtime libraries including glibc ≥2.39 and OpenSSL 3. Debian 13 riscv64 is the intended starting point. System bubblewrap is required for the normal sandbox path and is not bundled. Kernel namespace/security support must be checked on the board.

npm launcher, automatic updates and packaged-daemon installation are not adapted for this target. Optional external V8/code-mode and realtime runtimes are not included. Do not disable sandboxing to work around platform errors.

## Asset layout

Intended release asset:

```text
codex-riscv64-linux-gnu-v0.1.0-experimental.1.tar.gz
└── codex-riscv64-linux-gnu-v0.1.0-experimental.1/
    ├── bin/codex
    ├── LICENSE
    ├── NOTICE
    ├── licenses/
    └── documentation
```

Use the repository [README](../README.md) / [English README](../README.en.md) for checksum verification, dependencies and non-destructive per-user installation as `codex-riscv`. Release links and downloads become usable after publication of the assets.

完整验证边界见 [validation.md](validation.md)。本版本仅证明交叉编译和有限的 QEMU 检查通过，不代表开发板已获得完整、安全的生产支持。
