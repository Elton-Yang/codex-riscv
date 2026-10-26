# v0.1.0-experimental.2: RISC-V Code Mode

This experimental prerelease adds a sandbox-enabled `codex-code-mode-host` next to the existing CLI. The CLI bytes and pinned upstream commit (`970111f6cb62cc02fe36a82ea7d71b37a2889c97`) are unchanged from `.1`; both still use the upstream development version `0.0.0`. Physical VisionFive 2 validation of this new package is pending.

本版增加与 CLI 同目录的 Code Mode host；主 CLI 保持 `.1` 的原始字节。已完成下述完整系统模拟验证，真实开发板升级及 Code Mode 运行仍待用户确认。

## Changes

- Build rusty_v8 152.2.0 / V8 15.2.124.1 from pinned source with sandbox, pointer compression and external code space enabled.
- Make snapshot/native RISC-V sandbox constants agree. Use a 32 GiB cage with both 64 GiB guards, existing typed-array masks and mandatory `--sandbox-prohibit-insecure-mode`.
- Adjust PartitionAlloc advisory placement for Sv39 without changing pool sizes, metadata, BRP or zero guard.
- Handle Oilpan's aligned reservation on Sv39 without the transient 32/48 GiB alignment overhead: try exact-size, non-fixed mappings at compression-compatible slots; verify actual alignment and compression bit, free only mappings owned by the attempt. Cage size, compression, red zone, guards and failure behavior remain intact. This placement fallback is not an ASLR improvement or exploit-resistance claim.
- Install both executable files; check the host's executable permission and dynamic dependencies before activating a new version. Keep the standalone launcher and original upgrade/rollback layout.
- Preserve original license materials, dependency sources, source patches and bounded validation evidence.

## Validation on 2026-10-26

All runtime tests below used local full-system QEMU 10.0.13, Linux 6.12.107, Sv39, two restricted rv64gc-oriented harts, default ASLR=2 and 2 GiB RAM. There was no external network interface, login, account or real model API call.

- Actual host stdio protocol passed with and without allocation tracing: handshake, JS, persistent cells, mock delegated tools, notification, yield/wait/terminate and clean shutdown.
- Three fresh guests passed the separate native-buffer and optimized-array test: secure mode 0, 32 GiB cage, 160 GiB full reservation, process maps, native↔JS bytes, DataView, typed arrays, BigInt, atomics, RAB/GSAB and explicit TurboFan checks.
- Low-Smi preinitialization collision and 100 GiB VA limit both produced the expected fail-closed V8 refusal. Generic crashes were not accepted as passes.
- Actual CLI discovered its adjacent host; real `apply_patch` created Python source and real `exec_command` ran it under `workspace-write`. Python reported `Seccomp=2`, `NoNewPrivs=1`, exit 0, and denied a write to a disposable canary outside the workspace. Only model HTTP/SSE responses were simulated on guest loopback; CLI, host, handlers, Python and bubblewrap were real.
- The installer passed 57 offline regression tests. The actual `.1` and `.2` archives passed an emulated install, upgrade, rollback, configuration-sentinel preservation, helper dispatch, bare onboarding and uninstall smoke test. Platform gates and execution transport were emulated; this is not native installation confirmation.
- All 1,960 V8 archive members matched the generated objects. All 188 preserved attribution files matched their inventories; the selected 561 Cargo package identities matched prior license coverage. Full final linker map and known upstream attribution limits remain disclosed under `licenses/code-mode/`.

See [validation evidence](code-mode-evidence/) and [Code Mode notes](code-mode.md). Simulation is not physical-board certification, a full security audit, performance/stability coverage or validation of every optional runtime.

## Upgrade and test on your board

Re-download `install.sh` from the existing GitHub main URL, review it, then:

```sh
sh install-codex-riscv.sh upgrade
sh install-codex-riscv.sh status
codex-riscv --version
codex-riscv -c features.code_mode_only=true
```

The installer preserves `~/.codex`, login information, model settings, shell files and projects. No persistent feature/config changes are made. Use a disposable project for the first Code Mode task. `sh install-codex-riscv.sh rollback` switches back to the previous managed program version; it does not undo changes made by Codex to configuration or project files.

新版仍由原安装地址升级，无需卸载；默认 standalone 启动。首次验证建议使用空测试项目，通过 `-c features.code_mode_only=true` 临时启用 Code Mode。若异常请保留终端错误，再使用安装器回滚；不要关闭沙箱来绕过失败。
