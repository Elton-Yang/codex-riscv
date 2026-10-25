# codex-riscv

[English](README.en.md)

OpenAI Codex CLI 的 **非官方 RISC-V Linux 实验构建与适配**。本项目独立于 OpenAI，未获 OpenAI 背书，也不代表上游已经正式支持 RISC-V。

首个适配版本：`v0.1.0-experimental.1`。目标是让 Debian 13 / riscv64 用户能够检查、复现和继续验证一次小范围移植，而不是宣称完整功能已经可用。

## 当前结果

| 项目 | 结果 |
| --- | --- |
| `riscv64gc-unknown-linux-gnu` 交叉编译 | 通过 |
| QEMU 下 `codex --version` / `--help` | 均退出 0 |
| QEMU 下 seccomp 策略选择单元测试 | 6 通过，0 失败 |
| VisionFive 2 / JH7110 实机启动 | 用户实测 `--version` / `--help` 正常 |
| 实机只读沙箱执行 `/bin/true` | 退出 0 |
| 实机只读沙箱拒绝文件写入 / IPv4 socket 创建 | 分别报只读文件系统（退出 2）/ `EPERM`（退出 1）；沙箱外对照成功 |
| 认证、模型选择、基本交互对话 | 用户报告成功 |
| 工具调用、模型修改文件、`workspace-write`、完整测试套件 | **尚未测试** |

实机结果由用户于 2026-10-25 在 VisionFive 2 / Debian 13 上自行运行并反馈：内核 `6.12.113+deb13-riscv64`，bubblewrap `0.12.0`。这与构建主机上的 QEMU 检查是两组不同的验证；实机检查覆盖上述启动、拒绝行为和基本对话，不是完整沙箱安全审计或长期稳定性验证。不要用关闭沙箱来绕过错误，也不要以 root 运行 Codex。

此前成功的基本交互对话使用了 `--no-daemon`。随后用户在实机完成首版安装器安装，但直接运行 `codex-riscv` 进入了未完成适配的 packaged daemon 路径而失败；新版安装器改用默认 standalone 启动器。此修复尚未获实机启动确认，见 [安装器 v1.1 说明](docs/release-notes-installer-v1.1.md)。

完整检查范围见 [验证记录](docs/validation.md)。

## 固定的上游版本与修改

- 上游：[openai/codex](https://github.com/openai/codex)
- 提交：[`970111f6cb62cc02fe36a82ea7d71b37a2889c97`](https://github.com/openai/codex/commit/970111f6cb62cc02fe36a82ea7d71b37a2889c97)
- 目标：`riscv64gc-unknown-linux-gnu`，LP64D ABI
- Rust：`1.99.1`；交叉 GCC：`14.2`；目标 glibc：`2.41`
- 构建配置：`dev-small`，未优化、已去除符号，仅供实验

功能性源码补丁只有两行：在 Linux seccomp 的架构分派中增加 `TargetArch::riscv64`。所用 `seccompiler 0.5.0` 已提供该架构；没有删除过滤规则或禁用安全检查。补丁和修改说明随本仓库提供。

上游该提交的包版本是 `0.0.0`，所以 `--version` 输出 `codex-cli 0.0.0`。本仓库的 `v0.1.0-experimental.1` 是**适配发布版本**，不是 OpenAI Codex 的上游版本。

## 在 Debian 13 RISC-V 板子上试运行

推荐使用下面的用户级安装器；也可从 [首个预发布版本页面](https://github.com/Elton-Yang/codex-riscv/releases/tag/v0.1.0-experimental.1) 手动下载。安装器只安装这个已发布的实验二进制，不重新构建，也不改变它的版本。

### 1. 确认系统和依赖

```bash
uname -m                       # 应为 riscv64
dpkg --print-architecture      # 应为 riscv64
getconf GNU_LIBC_VERSION       # 本二进制需要 glibc >= 2.39

sudo apt update
sudo apt install ca-certificates curl python3 gzip libc6 libgcc-s1 libssl3t64 bubblewrap
```

`libssl3t64` 提供 OpenSSL 3 动态库，并由 apt 安装所需的 zlib、zstd 等依赖。`git`、`ripgrep` 是常用开发工具，可按需要安装：

```bash
sudo apt install git ripgrep
```

运行发布二进制不需要安装 Rust、Node.js 或交叉编译器。下载和解压需要预留空间：本次二进制本身为 `314651976` 字节，发布包还包含许可证与说明。

### 2. 安装为用户级全局命令（推荐）

下载并检查脚本后，以普通用户执行，**不要使用 `sudo`**：

```bash
curl --fail --location --proto '=https' --proto-redir '=https' --tlsv1.2 \
  https://raw.githubusercontent.com/Elton-Yang/codex-riscv/main/install.sh \
  -o install-codex-riscv.sh
less install-codex-riscv.sh
sh install-codex-riscv.sh
export PATH="$HOME/.local/bin:$PATH"
codex-riscv --version
```

默认将完整发布包安装到 `~/.local/share/codex-riscv/versions/v0.1.0-experimental.1`，并创建 `~/.local/bin/codex-riscv`。该命令经托管的 Python 3 启动器运行原二进制，自动加上 `--no-daemon`；直接启动、`resume` 和 `fork` 默认使用 standalone 模式，不依赖共享后台 daemon。这不会关闭沙箱。安装器核对固定 SHA-256、检查平台与动态库后切换版本，保留许可证，不修改 shell 配置。

以下管理命令按需选择，不必依次执行：

```bash
sh install-codex-riscv.sh status
sh install-codex-riscv.sh install --version v0.1.0-experimental.1
sh install-codex-riscv.sh upgrade --channel experimental
sh install-codex-riscv.sh rollback
sh install-codex-riscv.sh uninstall
```

`upgrade` 使用这份安装器中列出的实验版，不查询 GitHub 的 `latest`。目前仅支持一个版本，重复安装不会制造可回滚的新版本；有过成功的不同版本切换后才能 `rollback`。以后升级前先下载并检查新版安装器。卸载只处理安装器托管且未被修改的文件，不删除 `~/.codex`、登录信息或项目文件。

若已经用首版安装器安装，请**重新下载并检查上面的脚本**，然后执行 `sh install-codex-riscv.sh upgrade`，即可原位更新托管启动器，二进制版本不变，无需先卸载。原有命令名与命令目录会沿用。更新前的临时办法是 `codex-riscv --no-daemon`；恢复或分叉会话可用 `codex-riscv --no-daemon resume` / `codex-riscv --no-daemon fork`。

如确实需要命令名 `codex`，首次安装时显式使用 `--command codex`；目标位置或 `PATH` 中已有其他同名命令时会拒绝安装。旧文档手工复制的 `codex-riscv` 也不会被自动覆盖，请先确认来源，再自行改名或移走。完整选项、目录布局与故障处理见 [安装器说明](docs/installer.md)。

### 3. 手动下载、校验和试运行（不使用安装器）

```bash
TAG=v0.1.0-experimental.1
NAME="codex-riscv64-linux-gnu-${TAG}"
BASE="https://github.com/Elton-Yang/codex-riscv/releases/download/${TAG}"
DOWNLOAD_DIR=$(mktemp -d "${TMPDIR:-/tmp}/codex-riscv.XXXXXX")
cd "$DOWNLOAD_DIR"

curl --fail --location --proto '=https' --proto-redir '=https' --tlsv1.2 \
  -O "$BASE/$NAME.tar.gz"
printf '%s  %s\n' \
  2b70f049652793a2dd6c8035122ce2a6920de680153be1c6f8e2a172dde70120 \
  "$NAME.tar.gz" | sha256sum --check --strict
```

**只在校验成功后继续：**

```bash
tar -xzf "$NAME.tar.gz"
"./$NAME/bin/codex" --version
"./$NAME/bin/codex" --help
```

这个固定校验值仅适用于上述版本，核验完整性但不是独立的发布者签名。若下载返回 404，请检查本项目的 Release 页面，不要改用来源不明的二进制。保留完整解压目录中的 `LICENSE`、`NOTICE` 和 `licenses/`；再次分发时一并提供。

### 4. 先验证沙箱，再用于实际工作

本构建不附带 `bubblewrap`，使用系统的 `bwrap`。除了 apt 软件包，开发板内核和系统策略还需允许相应的用户命名空间与沙箱机制。Debian 用户空间版本并不能证明厂商内核配置满足要求。

建议先在没有敏感文件的独立测试目录检查只读、文件写入和网络拒绝行为。遇到 `bwrap`、命名空间、seccomp 或 Landlock 错误，应记录内核版本与完整错误，再排查支持情况。**不要加关闭沙箱的选项来把失败变成“通过”。**

## 从源码复现

构建脚本面向 **Debian 13 x86_64 构建主机**，不是直接在 RISC-V 板子上运行的安装脚本。先阅读脚本顶部的主机依赖和配置，再运行：

```bash
./scripts/build.sh
./scripts/check.sh
```

脚本固定上游提交、Rust 版本、Debian 包清单，并使用 Cargo `--locked`。构建所用的 Debian 包通过签名与哈希链校验后解包到本地目录。主机依赖仍需预先满足。

本次实际构建和测试命令已经执行；整理后的公共脚本尚未在全新环境完整重跑，也不承诺不同路径、日期或主机上的位级一致性。镜像中的固定版本或索引若不可用，验证应报错，不应静默升级依赖。详见 [验证记录](docs/validation.md)。

许可证清单与文本生成入口：

```bash
./scripts/generate-notices.py
```

## 已知边界

- npm 启动器、上游自动更新和 packaged daemon 安装路径没有完成 RISC-V 适配；托管启动器默认使用 standalone 模式，由本仓库安装器管理升级。显式 daemon、agents 和 remote server 功能不会因此获得支持。安装器不提供 root / 系统级安装。
- 可选 code-mode / V8 和实时功能的外部运行时未构建、未打包、未验证。
- 实机验证仅覆盖上述单台设备上的检查和用户报告的基本对话；工具调用、模型修改文件、`workspace-write`、完整 TUI 交互、其他内核和长期稳定性仍未验证。
- 文件写入与 IPv4 socket 创建被拒绝不等于完整沙箱安全审计；未单独验证 legacy Landlock 后端或全部过滤规则。
- `dev-small` 产物体积较大，性能不代表优化后的 release 构建。
- 这不是通用静态二进制；它依赖 Debian 13 级别的 GNU/Linux 运行库。

## 许可证与来源

上游 Codex 采用 Apache-2.0；本仓库保留 [LICENSE](LICENSE)、[NOTICE](NOTICE) 和修改记录。第三方组件可能使用其他许可证，见 `licenses/THIRD-PARTY-NOTICES.html` 及 `licenses/` 中的原始文本与补充说明。

发布时应保留这些材料。许可证生成工具辅助整理依赖信息，不等同于对所有使用情形的法律保证。
