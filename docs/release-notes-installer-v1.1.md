# Installer v1.1: standalone startup / 安装器 v1.1：默认独立启动

This installer-only repair addresses the bare-startup failure found after the user successfully installed v1 on a RISC-V board. The old command pointed directly to the binary, whose default TUI path attempted to start an incompletely packaged daemon. The earlier successful interactive conversation had used `--no-daemon`.

用户在 RISC-V 实机完成 v1 安装后，直接运行 `codex-riscv` 时遇到启动失败：原命令直连二进制，默认 TUI 路径尝试启动尚未完整适配的 packaged daemon。此前成功的交互对话使用了 `--no-daemon`。

## Change / 修复内容

- Install a managed Python 3 launcher at `<prefix>/launcher`, with the selected command pointing to it rather than directly to `current/bin/codex`.
- Run ordinary CLI calls with `--no-daemon` automatically, without duplicating an explicitly supplied option. Bare startup, `resume` and `fork` default to standalone mode without a shared background daemon.
- Preserve arguments and `exec` exit/signal behavior. Internal helper entry points retain their dispatch without blanket TUI flags.
- Migrate existing v1 managed command links in place during a same-version `install` or `upgrade`; preserve the saved command name and bin directory.

新增托管 Python 3 启动器，默认补充 `--no-daemon`，保留原参数及内部 helper 分派。旧版托管安装可直接升级，无需先卸载。Python 3 现在也是启动命令的运行依赖，安装后请保留。

The `v0.1.0-experimental.1` binary, binary tag, release assets and licenses are unchanged. The binary still reports `codex-cli 0.0.0`. This does not disable sandboxing or enable explicit daemon/agents/remote-server features. The installer update does not change credentials or `~/.codex`.

二进制、原标签、发布附件和许可证保持不变；不是新的 Codex 二进制版本。此修复不关闭沙箱，不扩展 daemon、agents、remote server 功能；安装器更新本身不修改登录信息或 `~/.codex`。

## Update / 更新

Download and review the current installer again using the [README instructions](../README.md); a previously downloaded v1 script will not contain this fix. Then run as your ordinary user, without `sudo`:

请按 [README](../README.zh-CN.md) 重新下载并检查新版安装器；缓存的 v1 脚本不包含此修复。随后以普通用户执行，不要用 `sudo`：

```bash
sh install-codex-riscv.sh upgrade
codex-riscv
```

Optional one-line upgrade for existing users / 已有用户可选的一行升级：

```bash
curl --fail --location --proto '=https' --proto-redir '=https' --tlsv1.2 https://raw.githubusercontent.com/Elton-Yang/codex-riscv/main/install.sh | sh -s -- upgrade
```

This executes downloaded code directly; the download-and-review method above is safer. 此命令直接执行下载的代码；先下载并检查再运行更稳妥。

For a custom installation, pass the original `--prefix`; the saved command name and bin directory are inferred. Until updated, use `codex-riscv --no-daemon`, `codex-riscv --no-daemon resume` or `codex-riscv --no-daemon fork`.

自定义安装目录需沿用原 `--prefix`；原命令名和命令目录会从托管记录读取。更新前可在旧命令中显式添加 `--no-daemon` 临时使用。

## Checks performed / 已完成的检查

On 2026-10-25:

- **53 offline fixture tests passed**, including exact argument/empty-string forwarding, explicit-flag deduplication, internal helper argument/alias dispatch, exit status, same-PID execution and SIGTERM, old-link migration, same-version reinstall, upgrade/rollback/uninstall, foreign/edited launcher preservation, and command-creation races.
- An independent review reran all 53 tests and checked shell/Python syntax and whitespace.
- The real public archive passed the unchanged embedded SHA-256 check. Under QEMU, the installed launcher passed `--version`, `--help`, `resume --help`, `fork --help` and `exec --help`. Actual apply-patch dispatch worked via both the hidden first argument and the `apply_patch` alias in a disposable directory; the `codex-linux-sandbox` alias reached its help parser without added TUI flags.
- **Bare managed-command startup reached the sign-in welcome screen in a real PTY under QEMU**, without selecting login or submitting a prompt. The installed launcher was unchanged; the harness redirected only its `execv` transport to QEMU and preserved `argv0`. A same-release legacy-link migration and managed uninstall then passed, preserving an isolated `.codex` sentinel.

2026-10-25：53 项离线回归通过并经独立复核；真实发布包校验、QEMU 下各 CLI 帮助、apply-patch/helper 分派、PTY 裸启动欢迎页，以及旧链接原位升级和卸载均通过。没有登录或发送模型请求。

Run the offline suite or the opt-in public-asset/QEMU test:

```bash
python3 -m unittest discover -s tests -p 'test_install.py' -v
python3 tests/smoke_release.py --sysroot /absolute/path/to/toolchains/debian/root
```

The smoke harness mocks platform checks and uses target libraries under QEMU, not a physical board. **Unauthenticated onboarding occurs before the daemon decision**: reaching that screen is real bare-launch coverage, but does not reproduce or prove the user's authenticated native path. The standalone flag's forwarding is checked separately in the fixture tests and pinned-source review. These limitations are why native confirmation is still needed.

QEMU 欢迎页位于未登录状态下、daemon 决策之前，不能当作用户已登录实机路径通过。`--no-daemon` 的参数传递另由回归测试和固定源码检查覆盖，仍需实机确认。

## Validation boundary / 验证边界

Native v1 installation succeeded, but bare startup failed before this repair. Native startup of the repaired launcher has **not yet been confirmed**. Mocked-platform tests and QEMU/PTY checks must be reported separately; they do not establish native board behavior, model functionality or kernel sandbox enforcement. Historical v1 test results are retained in the [v1 notes](release-notes-installer-v1.md), not retroactively treated as coverage of this fix.

实机已完成的是 v1 安装，之后裸命令启动失败；新版启动器尚未获得实机启动确认。模拟平台测试或 QEMU/PTY 检查不能替代实机、模型交互或内核沙箱验证；旧版测试记录不自动覆盖本次修复。
