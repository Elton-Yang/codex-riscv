# Default CLI command: codex

The installer now defaults to `~/.local/bin/codex`, matching upstream CLI usage and session-resume suggestions. Binary filenames were already `bin/codex`; this changes the installed command entry, not release archive bytes, version tags or checksums. The data prefix remains `~/.local/share/codex-riscv` so existing installations and rollback history are retained.

Re-download and review the installer from the existing main URL, then migrate an existing managed installation:

```sh
curl --fail --location --proto '=https' --proto-redir '=https' --tlsv1.2 \
  https://raw.githubusercontent.com/Elton-Yang/codex-riscv/main/install.sh \
  -o install-codex-riscv.sh
less install-codex-riscv.sh
sh install-codex-riscv.sh upgrade --command codex
sh install-codex-riscv.sh status
codex --version
codex -c features.code_mode_only=true
```

Existing custom installations must keep their original `--prefix`. Plain `upgrade` retains the saved name; fresh installs use `codex`. Explicit `--command codex-riscv` remains available. Renaming is supported only during `install`/`upgrade`, within the saved bin directory. Afterwards rollback, status and uninstall use the new saved name automatically.

The installer refuses to overwrite a foreign command at the destination or shadow another command found on PATH. It verifies ownership of the old managed entry, creates the new link exclusively, saves the new identity and then removes the old entry. Recoverable rename failures remove the new managed link and restore the old identity. A version upgrade completes before the command rename, so a later rename failure can leave the newly activated version accessible under the old command. Inspect `status` after any error. Sudden process termination or power loss is not a multi-file transaction.

Launcher bytes, `--no-daemon`, helper dispatch, user login/configuration and project files remain unchanged. The installer does not modify shell startup files or remove other Codex installations. If no conflict exists but the shell remembers the old entry, use `hash -r` (bash) or `rehash` (zsh).

## 中文

默认 CLI 命令改为 `codex`。已有安装重新下载脚本后执行 `upgrade --command codex` 即可迁移，无需卸载。保留原安装目录、版本历史、登录信息、模型配置和项目文件；旧命令入口在迁移成功后删除。

若目标位置或 PATH 中存在其他来源的 `codex`，安装器会拒绝覆盖；先核对来源再决定使用哪个安装。普通 `upgrade` 会保留旧命令名；新安装默认 `codex`，仍可显式指定 `--command codex-riscv`。仅更新安装器及说明，不替换 `.2` 发布包。此前以旧命令名记录的实机结果保留为历史证据，新入口的实机迁移待用户确认。

## Validation on 2026-10-26

64 installer fixture tests passed, including fresh default installation, explicit legacy-name retention, in-place rename, target/PATH conflicts, old-entry modification, metadata/unlink failure recovery, concurrent target creation, version history, configuration preservation and uninstall. Actual `.1`/`.2` archives passed two QEMU smoke scenarios: fresh `codex` install, and old-name `.1` install followed by `.2` upgrade with command migration and rollback. Helper dispatch, standalone bare onboarding, isolated configuration preservation and uninstall passed. These are emulated checks; native board command migration remains pending.
