# 开发板沙箱与升级回滚检查

先退出所有 Codex 会话。以下使用普通用户，不加 sudo。沙箱脚本使用全新的临时 HOME/CODEX_HOME，不登录、不调用模型；只在当前用户主目录下创建独立测试目录，并保留结果。

## 1. 记录环境

```sh
uname -m
uname -r
bwrap --version
sh install-codex-riscv.sh status
```

确认当前托管版本是 `v0.1.0-experimental.2`。CLI 的 `--version` 仍为 `0.0.0`，不能用于区别 `.1` 和 `.2`。

## 2. 检查沙箱

```sh
curl --fail --location --proto '=https' --proto-redir '=https' --tlsv1.2 \
  https://raw.githubusercontent.com/Elton-Yang/codex-riscv/main/tests/native_sandbox.py \
  -o native_sandbox.py
less native_sandbox.py
python3 native_sandbox.py
```

脚本先在沙箱外验证测试目录可写、IPv4 socket 可以创建，然后通过真实 `codex-riscv sandbox` 分别启动 `workspace-write` 和 `read-only`。它检查工作区写入、只读写入拒绝、工作区外兄弟目录写入拒绝、IPv4 socket 创建拒绝，以及子进程的 `Seccomp=2`、`NoNewPrivs=1`。socket 检查不解析域名、不连接任何地址。

两条 JSON 的 `pass` 均应为 `true`，最后显示 `PASS`。工作区外探针只针对脚本自己创建的文件，不接触其他文件。脚本会打印结果目录，其中 `results.json` 保存两次调用的退出码和输出。它不会删除该目录；检查后可自行删除。失败时保留结果，不改用关闭沙箱的参数。

这些是所测内核行为的证据，不能代替完整安全审计；它直接检查 CLI 沙箱入口，Code Mode 的创建/执行/恢复编辑另由实际任务验证。

## 3. 回滚后重新升级

使用刚从原 GitHub 地址下载并检查过的安装器。自定义安装目录须在每条命令中附加原来的 `--prefix`。

```sh
sh install-codex-riscv.sh status
```

仅当 `Current` 为 `.2`、`Previous` 为 `.1` 时，执行：

```sh
sh install-codex-riscv.sh rollback
sh install-codex-riscv.sh status
codex-riscv --version
sh install-codex-riscv.sh upgrade
sh install-codex-riscv.sh status
codex-riscv -c features.code_mode_only=true
```

预期状态依次为 `.2` → `.1` → `.2`。最后在 `.2` 中 `/resume` 恢复此前测试会话，检查所用模型和程序仍在，再执行一次小修改/运行。回滚期间仅检查版本，不需要在 `.1` 中恢复 `.2` 的会话。

若 `Previous: none`，不要为了制造历史而卸载；先跳过回滚检查并反馈状态。回滚只切换程序版本，不撤销项目或配置编辑。

反馈环境四项、沙箱两条 JSON/最终 PASS，以及三次安装状态即可；不要提供认证文件或 token。

脚本的命令与断言已在现有 Sv39 客体中通过检查；客体由 root 启动，测试包装器仅替换了脚本的普通用户门槛，真实 CLI 与内核沙箱未被替换。该准备检查不算开发板测试通过。
