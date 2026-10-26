# codex-riscv

[English](README.md)

OpenAI Codex CLI 的非官方 RISC-V Linux 实验适配，独立于 OpenAI，未获官方背书。

当前实验版为 **`v0.1.0-experimental.2`**，目标系统为 Debian 13 / riscv64。本版加入启用沙箱的 Code Mode host，主 CLI 保持 `.1` 的原始字节。上游开发版本号仍显示 `codex-cli 0.0.0`。

## 安装或原位升级

在开发板上使用普通用户安装，不要以 root 运行安装器或 Codex。系统依赖：

```sh
sudo apt update
sudo apt install ca-certificates curl python3 libc6 libgcc-s1 libssl3t64 bubblewrap
```

要求 Linux riscv64、glibc ≥ 2.39。两个程序合计约 478 MB；下载和暂存建议至少留出约 1.5 GB，另留空间保存旧版本。运行不需要 Rust、Node.js 或编译器。

继续使用原来的 GitHub 安装地址。重新下载并检查脚本后执行：

```sh
curl --fail --location --proto '=https' --proto-redir '=https' --tlsv1.2 \
  https://raw.githubusercontent.com/Elton-Yang/codex-riscv/main/install.sh \
  -o install-codex-riscv.sh
less install-codex-riscv.sh
sh install-codex-riscv.sh upgrade
export PATH="$HOME/.local/bin:$PATH"
sh install-codex-riscv.sh status
codex-riscv --version
```

`upgrade` 也支持首次安装。安装器核对固定 SHA256、两个程序的执行权限与动态库后再切换版本；启动器仍自动加入 `--no-daemon`，沙箱保持启用。保留登录信息、模型设置、`~/.codex`、shell 配置与项目文件。自定义安装目录需继续传入原 `--prefix`。旧脚本不会自动查询 GitHub `latest`，发布新版后需要重新下载。

建议在独立测试项目中首次运行：

```sh
mkdir -p "$HOME/codex-riscv-smoke"
cd "$HOME/codex-riscv-smoke"
codex-riscv -c features.code_mode_only=true
```

让模型创建一个小 Python 文件并执行。该选项只对本次启动启用 Code Mode，不写入配置；沿用现有认证与模型选择。CLI 自动寻找同目录的 host。新版开发板实测仍待确认；出现错误时保留日志，不要关闭沙箱来绕过。

管理命令：

```sh
sh install-codex-riscv.sh rollback
sh install-codex-riscv.sh install --version v0.1.0-experimental.1
sh install-codex-riscv.sh uninstall
```

回滚只切换程序，不撤销 Codex 对文件或配置的修改；卸载保留设置和项目。默认命令为 `codex-riscv`；首次安装可在无冲突时选用 `--command codex`。详见[安装器说明](docs/installer.md)。

## 当前验证

| 检查 | 结果 |
| --- | --- |
| 新 host RISC-V LP64D 源码构建 | 通过 |
| 完整系统 Sv39、受限 rv64gc 指令集、默认 ASLR=2 | 通过 |
| 普通及带分配跟踪的真实 host 协议 | 通过 |
| 三次独立 V8 原生内存与 TurboFan 测试 | 通过；32 GiB cage、160 GiB 完整预留 |
| 低地址冲突、100 GiB 地址空间限制 | 均按预期安全拒绝 |
| 真实 CLI → host → 创建文件与执行 Python | 完整系统模拟通过；仅模型响应为本地模拟 |
| workspace-write 内核检查 | Seccomp=2、NoNewPrivs=1、工作区外写入被拒绝 |
| 新版开发板安装、升级与 Code Mode | **待用户实测** |

历史 `.1` 在 VisionFive 2 / JH7110、Debian 13 上有启动、认证、模型选择、基础对话和只读沙箱拒绝行为的用户记录，不能替代 `.2` 的实机验证。参见[历史验证](docs/validation.md)、[新版发布说明](docs/release-notes-v0.1.0-experimental.2.md)与[新验收证据](docs/code-mode-evidence/)。

以上结果不代表完整安全审计、攻击抵抗认证、长期稳定性或其他板卡/内核兼容。完整 TUI、realtime 外部运行时、npm 更新器及显式 daemon、agents、remote server 仍未验证。

## 源码与许可证

固定上游提交为 [`970111f6cb62cc02fe36a82ea7d71b37a2889c97`](https://github.com/openai/codex/commit/970111f6cb62cc02fe36a82ea7d71b37a2889c97)。Rust 1.99.1、交叉 GCC 14.2、目标 glibc 2.41；使用去除符号、未优化的 `dev-small`。CLI 保留两行 seccomp 架构分派适配；Code Mode 使用 rusty_v8 152.2.0 / V8 15.2.124.1，补丁见 [MODIFICATIONS.md](MODIFICATIONS.md)。

[`.2` Release 页面](https://github.com/Elton-Yang/codex-riscv/releases/tag/v0.1.0-experimental.2)提供程序包、依赖源码包和 `SHA256SUMS`；安装器内也固定程序包摘要。程序依赖系统动态库，不是通用静态二进制。

[Code Mode 构建说明](docs/code-mode.md)记录已准备的源码/工具链布局和补丁；`scripts/build.sh` 仍用于兼容 Debian 13 x86_64 构建主机上的 CLI-only 构建。尚未承诺全新环境 Code Mode 自动搭建或位级一致重建。

再次分发时保留 `LICENSE`、`NOTICE`、完整 `licenses/`、修改记录及相关依赖源码。Code Mode 许可证是对原清单的补充；已知上游归属限制及缺少最终链接映射的边界均有披露。
