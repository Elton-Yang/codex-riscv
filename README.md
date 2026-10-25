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
| VisionFive 2 / JH7110 实机 | **尚未测试** |
| 实际 seccomp / Landlock / bubblewrap 沙箱执行 | **尚未测试** |
| 交互 TUI、登录、真实模型请求、完整测试套件 | **尚未测试** |

QEMU 启动和策略选择测试不能证明开发板上的内核沙箱有效。不要用关闭沙箱来绕过错误，也不要以 root 运行 Codex。

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

发布文件上传完成后，可从 [首个预发布版本页面](https://github.com/Elton-Yang/codex-riscv/releases/tag/v0.1.0-experimental.1) 下载。以下命令以该 Release 及其附件可用为前提；若返回 404，请先检查 Release 页面，不要改用来源不明的二进制。

### 1. 确认系统和依赖

```bash
uname -m                       # 应为 riscv64
dpkg --print-architecture      # 应为 riscv64
getconf GNU_LIBC_VERSION       # 本二进制需要 glibc >= 2.39

sudo apt update
sudo apt install ca-certificates curl gzip libc6 libgcc-s1 libssl3t64 bubblewrap
```

`libssl3t64` 提供 OpenSSL 3 动态库，并由 apt 安装所需的 zlib、zstd 等依赖。`git`、`ripgrep` 是常用开发工具，可按需要安装：

```bash
sudo apt install git ripgrep
```

运行发布二进制不需要安装 Rust、Node.js 或交叉编译器。下载和解压需要预留空间：本次二进制本身为 `314651976` 字节，发布包还包含许可证与说明。

### 2. 下载、校验，再解压

```bash
TAG=v0.1.0-experimental.1
NAME="codex-riscv64-linux-gnu-${TAG}"
BASE="https://github.com/Elton-Yang/codex-riscv/releases/download/${TAG}"
DOWNLOAD_DIR=$(mktemp -d "${TMPDIR:-/tmp}/codex-riscv.XXXXXX")
cd "$DOWNLOAD_DIR"

curl --fail --location --proto '=https' --tlsv1.2 -O "$BASE/$NAME.tar.gz"
curl --fail --location --proto '=https' --tlsv1.2 -O "$BASE/SHA256SUMS"
sha256sum --check --ignore-missing SHA256SUMS
```

**只在校验成功后继续：**

```bash
tar -xzf "$NAME.tar.gz"
"./$NAME/bin/codex" --version
"./$NAME/bin/codex" --help
```

`SHA256SUMS` 用于核验附件完整性，不是独立的发布者签名。应从本项目的 HTTPS Release 页面获取文件和校验和。

### 3. 可选：安装为单独的命令

先完成上面的启动检查，再执行。使用 `codex-riscv` 名称，避免覆盖已有 npm 安装的 `codex`：

```bash
DEST="$HOME/.local/bin/codex-riscv"
mkdir -p "$HOME/.local/bin"
if [ -e "$DEST" ] || [ -L "$DEST" ]; then
  printf '已有文件，未覆盖：%s\n' "$DEST"
else
  install -m 0755 "./$NAME/bin/codex" "$DEST"
  "$DEST" --version
fi
export PATH="$HOME/.local/bin:$PATH"
```

保留解压包中的 `LICENSE`、`NOTICE` 和 `licenses/` 目录；再次分发时一并提供。上述命令不会改写 shell 配置文件。

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

- npm 启动器、自动更新和 packaged daemon 安装路径没有完成 RISC-V 适配；本项目采用直接二进制、手动安装方式。
- 可选 code-mode / V8 和实时功能的外部运行时未构建、未打包、未验证。
- 本次没有进行 VisionFive 2 实机验证、交互体验验证、登录或真实 API 请求。
- `dev-small` 产物体积较大，性能不代表优化后的 release 构建。
- 这不是通用静态二进制；它依赖 Debian 13 级别的 GNU/Linux 运行库。

## 许可证与来源

上游 Codex 采用 Apache-2.0；本仓库保留 [LICENSE](LICENSE)、[NOTICE](NOTICE) 和修改记录。第三方组件可能使用其他许可证，见 `licenses/THIRD-PARTY-NOTICES.html` 及 `licenses/` 中的原始文本与补充说明。

发布时应保留这些材料。许可证生成工具辅助整理依赖信息，不等同于对所有使用情形的法律保证。
