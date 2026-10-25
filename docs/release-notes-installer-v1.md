# Installer v1 / 安装器 v1

This is an installer-only update for the unofficial `codex-riscv` project. It installs the existing `v0.1.0-experimental.1` binary release; it is **not a new Codex binary version**. The binary tag and assets are unchanged, and `codex --version` still reports `codex-cli 0.0.0`.

这是仅涉及安装器的更新，继续使用现有 `v0.1.0-experimental.1` 实验二进制；不是新的 Codex 二进制版本。原有标签与附件保持不变，版本输出仍为 `codex-cli 0.0.0`。

## Included / 新增内容

- A `sh`-runnable installer with Python 3 standard-library implementation, for non-root Linux riscv64 users with glibc ≥ 2.39.
- Default `~/.local/bin/codex-riscv` command and complete versioned releases under `~/.local/share/codex-riscv`; explicit `--command codex` with collision checks.
- Pinned version / experimental-channel selection, repeatable installation, upgrade, previous-version rollback, status and managed-only uninstall.
- Exact embedded SHA-256 verification, archive safety checks, staged dependency/startup checks and atomic active-version switching; full license materials retained.
- No shell configuration edits, no deletion of `~/.codex` or credentials, no source rebuild, npm updater or model request.
- English and Chinese guides, plus offline fixture tests for lifecycle and failure paths.

新增无需 root 的用户级安装、显式版本/实验渠道选择、升级、回滚、状态和托管卸载。默认使用 `codex-riscv`，可明确选择 `codex`，但不会覆盖已有命令。发布包完整校验并暂存检查后才切换版本；保留许可证，不改 shell 配置、不删除 `~/.codex` 或登录信息。

## Use / 使用

See the [Chinese README](../README.md) / [English README](../README.en.md) for the download-and-review instructions, and the [Chinese installer guide](installer.md) / [English installer guide](installer.en.md) for all options.

Only `v0.1.0-experimental.1` is currently supported. `upgrade` uses the catalog in the downloaded installer, never GitHub's generic `latest` endpoint; future binary releases require an updated installer. Rollback requires an actual earlier managed version and is not available after a first or same-version installation. Root / system-wide installation is not included.

当前仅支持一个发布版本；升级不会误选 GitHub `latest`，以后新增二进制版本时需更新安装器。首次或重复安装同一版本后没有可回滚版本。当前不提供 root / 系统级安装。

## Validation scope / 验证范围

The installer test suite uses disposable local prefixes, fixture archives and mocked platform/download commands; it needs no credentials, model access or network. Run it with:

```bash
python3 -m unittest discover -s tests -p 'test_install.py' -v
```

Recorded on 2026-10-25:

- Offline fixture suite: **37 tests passed**, including command parsing/collisions, platform/dependency refusal, bad downloads/checksums, unsafe tar members, upgrade/rollback, recoverable activation failures, lock contention, metadata corruption, user-configuration isolation and conservative uninstall.
- Public-asset smoke: the real HTTPS download passed the embedded archive SHA-256 check; full extraction, notices, target-loader dependency checks, QEMU `--version` / `--help`, status, same-version upgrade and uninstall succeeded in a disposable prefix. The isolated `.codex` sentinel survived uninstall.
- Installed binary SHA-256: `703975ef3ca50630be8349eb30f30e42ef458202bb54339797bae0b4d15e08b7`, unchanged from the published binary.
- Shell/Python syntax and `git diff --check` passed. No new CI workflow or package installation was needed.

The opt-in real-asset smoke harness needs the existing Debian cross-toolchain sysroot and downloads the public archive:

```bash
python3 tests/smoke_release.py --sysroot /absolute/path/to/toolchains/debian/root
```

That harness changes only a disposable installer copy to invoke the target binary through QEMU. It mocks `uname`, `getconf` and `bwrap` presence; `ldd` is implemented with the real target loader under QEMU. It is **not a native run of the unmodified installer**. It makes no authentication or model request and does not validate the kernel sandbox.

Mocked-host lifecycle tests and QEMU smoke checks must be distinguished from native installation. This new installer has not yet been exercised on the user's physical RISC-V board. Existing user-reported VisionFive 2 startup, sandbox-denial and conversation results apply to the unchanged binary, not to this installer. The broader experimental limitations in [validation.md](validation.md) remain in effect.

2026-10-25 的 37 项离线夹具测试通过；公开发布包的真实 HTTPS 下载、固定 SHA 校验、目标动态库/QEMU 启动、重复安装与卸载 smoke 也通过，二进制哈希未变。自动测试中的平台和下载行为经过模拟，不能称为实机安装验证；QEMU 检查也不能代替实机安装或完整沙箱审计。新增安装器尚未在用户的 RISC-V 实机执行。此前的 VisionFive 2 结果只针对未改变的二进制，整体仍为实验版本。
