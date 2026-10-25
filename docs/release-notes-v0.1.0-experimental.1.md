# v0.1.0-experimental.1

Experimental prerelease of an unofficial RISC-V Linux adaptation of OpenAI Codex CLI. This project is independent of and not endorsed by OpenAI.

## Native validation update / 实机验证补充 — 2026-10-25

The user tested VisionFive 2 / Debian 13 with kernel `6.12.113+deb13-riscv64` and bubblewrap `0.12.0`: native version/help output was normal; read-only sandbox `/bin/true` exited 0; file writes were denied with a read-only filesystem error (exit 2), and IPv4 TCP socket creation with `EPERM` (exit 1). Both outside-sandbox controls succeeded. The user also reported successful authentication, model selection and live conversation.

用户实测上述启动和沙箱检查通过，并报告认证、模型选择与真实对话成功；这些是独立于 QEMU 的用户实机结果。仍为实验版本，工具调用、模型修改文件、`workspace-write`、完整 TUI 行为和长期稳定性尚未验证，也不代表完整沙箱安全审计。

No binary, tag or release asset was changed. The executable still reports `codex-cli 0.0.0`; documentation inside the immutable release archive is the original pre-board-test snapshot. See the [current validation record](https://github.com/Elton-Yang/codex-riscv/blob/main/docs/validation.md) for the updated scope. Tool calls, model-driven edits, `workspace-write`, exhaustive TUI behavior and long-term stability remain untested; this is not a comprehensive sandbox security audit.

二进制、标签和发布附件保持不变；压缩包内的文档保留实机测试之前的原始快照，最新结果以仓库验证记录为准。

## Included

- A stripped, dynamically linked `riscv64gc-unknown-linux-gnu` CLI executable built with the unoptimized `dev-small` profile.
- A two-line functional patch enabling the existing RISC-V seccompiler architecture dispatch, with no sandbox rules removed.
- Pinned cross-build scripts, dependency manifests, validation documentation, upstream attribution and third-party license materials.
- A companion `SHA256SUMS` file for release-asset integrity checks.

Upstream commit: `970111f6cb62cc02fe36a82ea7d71b37a2889c97`.

This adaptation tag is not an upstream Codex version. The pinned development commit declares version `0.0.0`; the executable therefore reports `codex-cli 0.0.0`.

## Initial cross-build and QEMU checks

- Successful CLI cross-build using Rust 1.99.1 and GCC 14.2.
- QEMU `--version` and `--help`, both exit 0.
- Six seccomp policy-selection unit tests under QEMU, all passed; 153 unrelated tests filtered out.

## Important limits

At initial packaging, native hardware, TUI, authentication and model conversation had not yet been tested. The native update above records the subsequent user-operated checks. QEMU tests alone do not establish actual kernel sandbox enforcement. The full test suite and optimized performance remain untested.

The binary requires GNU/Linux runtime libraries including glibc ≥2.39 and OpenSSL 3. Debian 13 riscv64 is the intended starting point. System bubblewrap is required for the normal sandbox path and is not bundled. Kernel namespace/security support must be checked on the board.

npm launcher, automatic updates and packaged-daemon installation are not adapted for this target. Optional external V8/code-mode and realtime runtimes are not included. Do not disable sandboxing to work around platform errors.

## Asset layout

Release asset:

```text
codex-riscv64-linux-gnu-v0.1.0-experimental.1.tar.gz
└── codex-riscv64-linux-gnu-v0.1.0-experimental.1/
    ├── bin/codex
    ├── LICENSE
    ├── NOTICE
    ├── licenses/
    └── documentation
```

Use the repository [English README](../README.md) / [Chinese README](../README.zh-CN.md) for checksum verification, dependencies and non-destructive per-user installation as `codex-riscv`.

完整验证边界见 [validation.md](validation.md)。初始交叉编译和 QEMU 检查之后，已补充上述用户实机结果；仍不代表开发板已获得完整、安全的生产支持。
