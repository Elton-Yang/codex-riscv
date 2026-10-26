# 用户级安装器

[English](installer.en.md) · [README](../README.zh-CN.md)

继续使用原 `install.sh` 安装入口。目标系统为 Linux riscv64、glibc ≥ 2.39；用普通用户执行，不要给安装器加 sudo。需要 Python 3、curl、CA 证书、ldd、uname、getconf、bubblewrap、libgcc 和 OpenSSL 3 运行库。安装器不编译 Codex，不安装 npm 包。

## 安装、升级与回滚

发布新版本后重新下载并检查脚本，旧脚本不会查询 GitHub latest：

```sh
curl --fail --location --proto '=https' --proto-redir '=https' --tlsv1.2 \
  https://raw.githubusercontent.com/Elton-Yang/codex-riscv/main/install.sh \
  -o install-codex-riscv.sh
less install-codex-riscv.sh
sh install-codex-riscv.sh upgrade
sh install-codex-riscv.sh status
```

`upgrade` 也支持首次安装。默认版本为 `.2`，保留 `.1` 安装支持。两个版本的精确 SHA256 固定在脚本 `RELEASES` 中，并随 Release 的 `SHA256SUMS` 发布。不接受未知版本、镜像或跳过校验；摘要不等于独立发布者签名。

```sh
sh install-codex-riscv.sh install --version v0.1.0-experimental.2
sh install-codex-riscv.sh install --version v0.1.0-experimental.1
sh install-codex-riscv.sh rollback
sh install-codex-riscv.sh uninstall
```

回滚切换到上次成功版本；同版本重装不会制造历史。回滚只切换程序，不撤销模型对文件或配置的修改。卸载只删除已验证、未修改的托管文件，遇到修改或外来文件时保留并报错。

## 布局与配置保护

默认程序位于 `~/.local/share/codex-riscv/versions/<tag>/`；`.2` 内含 `bin/codex`、相邻 `bin/codex-code-mode-host`、许可证、文档及来源材料。`current` 和 `previous` 指向当前及上一成功版本。`~/.local/bin/codex-riscv` 指向托管 Python 启动器。

启动器对普通调用自动加 `--no-daemon`，内部 helper 保留原分派；CLI 自动发现相邻 host。沙箱保持启用。安装过程不登录、不调用模型，不修改 `~/.codex`、登录信息、模型设置、shell 配置或项目。

`--prefix`、`--bin-dir` 必须是分离的绝对专用目录，不能放入 Codex 配置目录。默认命令为 `codex-riscv`；首次安装可选 `--command codex`，但不能覆盖其他命令。旧安装沿用原命令名和命令目录，自定义 prefix 在后续管理时仍需传入。安装器不编辑 PATH，必要时自行加入 `~/.local/bin`。

## 激活前检查

固定摘要通过后才解包；拒绝路径穿越、链接、特殊文件、重复条目和超限包。仅将普通文件暂存到新目录。`.2` 的两个程序均须存在、有执行权限且动态库完整；`.1` 只要求主 CLI。CLI `--version` 在临时 HOME/CODEX_HOME 中检查。安装成功不等于 V8 或 Code Mode 运行成功，运行验证需另行完成。

检查全部通过后才原子替换 `current`，保留旧版本；下载、校验、依赖或启动失败不会切换当前程序。可恢复的激活错误会恢复历史，但两个链接的更新不保证断电事务一致性。强制终止可能留下 `.stage-*`，应检查后再清理。不要将个人文件放入托管版本目录，也不要删除标记来绕过保护。

57 项夹具回归覆盖 host 缺失、依赖缺失、执行权限、`.1` → `.2` 升级回滚和配置/项目保留。实际发布包安装烟测使用 QEMU 和模拟平台门槛；开发板 `.2` 安装、已登录启动和 Code Mode 仍待用户确认。详见[发布说明](release-notes-v0.1.0-experimental.2.md)。
