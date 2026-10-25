# 用户级安装器

[English](installer.en.md) · [README](../README.zh-CN.md)

`install.sh` 管理已发布的非官方 RISC-V Linux 二进制，不编译 Codex、不安装 npm 包，也不修改上游源码。在 Linux riscv64 上使用普通用户运行 `sh install.sh`。“用户级全局”指把命令目录加入 `PATH` 后，可以从任意目录使用；不是为所有账户安装。

## 依赖与信任范围

- Linux `riscv64`，glibc **2.39 或更新**；目标起点为 Debian 13 riscv64。
- 安装器及安装后的启动器都需要 Python 3（安装后请保留）；下载和平台检查还需要 `curl`、HTTPS CA 证书、`uname`、`getconf`、`ldd` 和系统 `bwrap`。
- 运行库包括 `libgcc-s1`、OpenSSL 3（Debian 13 的 `libssl3t64`）。激活版本前会检查暂存二进制的动态库，并在临时 `HOME` / `CODEX_HOME` 中执行 `--version`。
- 预留压缩包、完整解压目录和保留旧版本的空间。当前可执行文件本身约 315 MB。

Debian 依赖安装命令：

```bash
sudo apt update
sudo apt install ca-certificates curl python3 libc6 libgcc-s1 libssl3t64 bubblewrap
```

只有安装系统软件包这一步使用 `sudo`，不要用它运行 Codex 安装器或 Codex。检测到 `bwrap` 不代表开发板内核和策略已经支持沙箱；仍须按照 [实机沙箱验证说明](../README.zh-CN.md#4-先验证沙箱再用于实际工作) 单独检查。

从本仓库下载脚本，阅读后再执行。README 中的 `main` 地址会随仓库更新；若需要可重复安装，可以将 URL 中的 `main` 换成已检查的仓库提交，并保留那份脚本。内置 SHA-256 固定发布包字节，但不是发布者签名，也不能独立证明安装器本身可信。

安装器当前只支持一个适配版本：

| 适配发布版本 | `.tar.gz` 发布包的 SHA-256 |
| --- | --- |
| `v0.1.0-experimental.1` | `2b70f049652793a2dd6c8035122ce2a6920de680153be1c6f8e2a172dde70120` |

发布包为本项目 GitHub Release 的 `codex-riscv64-linux-gnu-v0.1.0-experimental.1.tar.gz`。正式安装器不接受镜像、未知版本、跳过校验或替代下载源。默认 `experimental` 渠道就是本仓库的实验构建，运行该安装器即选择它，不代表上游稳定版；没有 `stable` 或 `latest` 回退逻辑。

## 命令

```text
sh install.sh [install|upgrade|rollback|uninstall|status]
              [--version TAG] [--channel experimental]
              [--prefix ABSOLUTE_PATH] [--bin-dir ABSOLUTE_PATH]
              [--command codex-riscv|codex]
```

以 `sh install.sh --help` 输出的选项为准。省略操作名时执行 `install`。

```bash
# 默认：受支持的实验版，使用独立命令名。
sh install.sh

# 显式指定适配版本；二进制 --version 仍显示 0.0.0。
sh install.sh install --version v0.1.0-experimental.1
sh install.sh status

# 管理同一安装目录，选择本脚本固定的版本。
sh install.sh upgrade --channel experimental

# 只有成功切换过不同的托管版本后才能回滚。
sh install.sh rollback

# 移除托管安装，不删除用户数据或登录信息。
sh install.sh uninstall
```

目前只发布了一个二进制版本，重复安装或升级到同一版本不会制造“上一版本”。未来版本需要更新安装器中的目录，因此升级前先下载并检查新版安装器。回滚切换到此前激活过的托管版本，不会下载任意上游版本。使用自定义目录时，后续管理操作也要传入相同的 `--prefix`。

## 从首版安装器升级

首版安装器在用户的 RISC-V 实机上完成了安装，但其直连二进制的命令在不带参数时进入 packaged daemon 路径并启动失败。此前成功的 TUI 对话使用了 `--no-daemon`。

按照 README **重新下载并检查新版 `install.sh`**，不要继续使用缓存的 v1 脚本，然后运行：

```bash
sh install-codex-riscv.sh upgrade
```

已有用户也可选择下面的一行升级命令。它会**直接执行下载的代码**；上面先下载、检查再执行的方式更稳妥。

```bash
curl --fail --location --proto '=https' --proto-redir '=https' --tlsv1.2 https://raw.githubusercontent.com/Elton-Yang/codex-riscv/main/install.sh | sh -s -- upgrade
```

这会将旧的托管命令链接原位迁移到 standalone 启动器，仍使用同一个二进制发布版本，不需要先卸载。已有 `--command` 和 `--bin-dir` 会从托管记录读取；自定义安装目录仍须传入原来的 `--prefix`。新建命令仍执行冲突保护。

更新前的临时用法：

```bash
codex-riscv --no-daemon
codex-riscv --no-daemon resume
codex-riscv --no-daemon fork
```

## 路径与命令名

默认布局：

```text
~/.local/share/codex-riscv/
├── versions/
│   └── v0.1.0-experimental.1/
│       ├── bin/codex
│       ├── LICENSE
│       ├── NOTICE
│       ├── licenses/
│       └── ...发布包文档与安装器元数据
├── launcher                            # 托管的 Python 3 启动器
├── current -> versions/v0.1.0-experimental.1
└── previous -> versions/<previous-tag>  # 切换不同版本后才存在

~/.local/bin/codex-riscv -> ~/.local/share/codex-riscv/launcher
```

`--prefix` 指定托管安装目录，`--bin-dir` 指定命令目录，均须使用绝对路径。请选择专用的空目录，不要使用项目目录或整个 home 目录。当前明确不支持 root / 系统级安装。

如果命令目录不在 `PATH` 中，安装器会打印提示。默认路径可在当前 shell 中临时加入：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

安装器不修改 `.profile`、`.bashrc`、`.zshrc` 等配置。需要永久生效时，在检查现有配置后自行添加。

推荐保留默认命令名 `codex-riscv`。如需 `codex`，在首次安装时传入 `--command codex`。目标位置已有其他文件或链接，或者 `PATH` 中存在其他同名可执行程序时，安装器会拒绝覆盖，不会移除 npm、软件包管理器或手工安装的 Codex。请检查冲突文件后自行决定是否改名或移走。已托管安装如需更换命令名，先卸载再重新安装。

## 安全与失败处理

- 通过 HTTPS 下载；必须与安装器目录中的精确 SHA-256 一致，才检查或执行压缩包内容。
- 解压前检查全部归档项，拒绝绝对路径、目录穿越、链接、特殊文件和重复路径。只把普通目录和文件写入新建的暂存目录，不覆盖当前版本。
- 保留完整发布包及许可证，先检查动态库与启动，再原子替换 `current` 符号链接。下载、校验或启动失败不会切换当前版本。
- 保留此前激活的托管版本以供回滚；回滚不撤销你或 Codex 对项目、`~/.codex` 所作的修改。
- 卸载前检查托管标记和文件记录。遇到已修改或未记录的文件时拒绝删除，不要把个人文件放进托管目录。
- 不删除 `~/.codex`、登录信息、shell 配置或项目文件。安装期间不登录、不调用模型。

卸载如提示内容被修改或存在额外文件，请先检查、备份或自行移出，再重试。不要删除托管标记来强行让安装器接受目录。如果命令链接被换成其他文件，该文件也不会被删除。强制终止可能留下 `.stage-*` 目录，请先检查并自行移除确认已废弃的暂存目录，再重试卸载。当前版本链接的替换是原子的，但 current/previous 两个链接的历史更新不保证断电一致性。

## 升级与验证边界

当前二进制来自包版本为 `0.0.0` 的开发提交，上游更新检查对这个开发版本关闭。托管启动器通过 `exec` 调用未修改的 `current/bin/codex`，为普通 CLI 调用自动补充 `--no-daemon`，已有该选项时不重复添加；保留用户参数、进程退出状态和信号行为。内部 helper 入口保留原有分派，不强加 TUI 参数。默认直接启动、`resume` 和 `fork` 不依赖共享后台 daemon；此选项不关闭沙箱，也不让显式 daemon、agents 或 remote server 功能自动可用。请通过本安装器升级，不要用上游/npm 更新路径替换 RISC-V 二进制。

安装器的夹具测试使用独立临时目录和模拟的平台、下载命令，不是实机测试。即使发布二进制在 QEMU 下启动成功，也不能证明本安装器或沙箱在开发板上通过。用户已在实机完成首版安装，但随后裸命令启动失败；standalone 修复尚未获得实机启动确认。之前的 VisionFive 2 二进制检查不能代替这次修复的验证。实际记录范围见 [验证记录](validation.md)、[v1 历史说明](release-notes-installer-v1.md) 和 [v1.1 修复说明](release-notes-installer-v1.1.md)。
