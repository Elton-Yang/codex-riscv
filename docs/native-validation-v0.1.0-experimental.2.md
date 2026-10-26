# User-operated native validation: v0.1.0-experimental.2

On 2026-10-26, the user supplied terminal results and functional feedback from their VisionFive 2 / JH7110 development board, previously identified as Debian 13. These are user-operated native results, separate from the recorded full-system QEMU acceptance.

| Environment | User-supplied value |
| --- | --- |
| Architecture | `riscv64` |
| Kernel | `6.12.113+deb13-riscv64` |
| bubblewrap | `0.12.0` |
| Current managed version | `v0.1.0-experimental.2` |
| Previous managed version | `v0.1.0-experimental.1` |
| Existing model | `gpt-5.6-luna` |

## Native functional results

The user reported successful program creation, correct initial execution, exit followed by `/resume`, modification after resumption, and correct execution of the modified program. After rollback and re-upgrade, the user confirmed the program and model remained available and modification/execution still produced correct results.

The supplied post-upgrade invocation was `codex-riscv -c features.code_mode_only=true`. Program contents, model conversation, token usage, personal paths and session identifiers are omitted.

## Native sandbox checks

The user ran [tests/native_sandbox.py](../tests/native_sandbox.py) as their ordinary user. The script uses a fresh HOME/CODEX_HOME, a dedicated workspace and an outside sibling directory. Before launching the sandbox it checks that ordinary filesystem permissions allow the outside write and that IPv4 socket creation works. The socket probe neither resolves a hostname nor connects to an address.

Both emitted JSON records had `pass: true`; the final output was `PASS: workspace write, read-only denial, outside denial, socket denial, seccomp and no_new_privs`.

| Native check | `workspace-write` | `read-only` |
| --- | --- | --- |
| Workspace file write | Allowed | Denied |
| Outside-workspace sibling write | Denied | Denied |
| IPv4 TCP socket creation | Denied | Denied |
| `/proc/self/status` Seccomp | 2 | 2 |
| `/proc/self/status` NoNewPrivs | 1 | 1 |

The script accepts filesystem denial only for EPERM/EACCES/EROFS and socket denial only for EPERM/EACCES. Its assertions and terminal output support these measured native behaviors. These direct CLI sandbox probes are separate from the user's Code Mode tasks; no kernel-status measurement inside the model-driven task was supplied.

## Native rollback and re-upgrade

The user supplied the following state transitions using the managed installer:

| Step | Current | Previous | Result |
| --- | --- | --- | --- |
| Before rollback | `.2` | `.1` | Managed command present |
| `rollback` | `.1` | `.2` | Installer reported successful rollback; CLI version output normal |
| `upgrade` | `.2` | `.1` | Installer reported successful activation with standalone launcher |
| Start Code Mode again | `.2` | `.1` | Model and program retained; modification and execution correct |

CLI `--version` remains `codex-cli 0.0.0` in both releases; the installer `status` identifies the adaptation version. This supports the tested upgrade/rollback path and preservation of the program/model workflow. It is not a byte-for-byte audit of all user settings or project files, nor a destructive rollback of edits.

## Native command-name migration

The user then ran `sh install-codex-riscv.sh upgrade --command codex` on the same `riscv64` development board. The installer reported `Command migrated` from the old managed entry to `codex`. Final status showed current `.2`, previous `.1`, and the managed command basename `codex`; `codex --version` returned `codex-cli 0.0.0`. The intermediate install-stage message used the old entry before renaming, as expected. This confirms native command migration and version startup; a new interactive task after renaming was not reported.

## Evidence and limits

A [sanitized structured transcript](code-mode-evidence/native-board-20261026.json) records the supplied checks and state transitions. No installed binary digest or separate shell exit-code transcript was supplied. This single-board result does not establish all filter rules, every TUI flow, other boards/kernels, long-term stability, performance or exploit resistance.

The release remains an experimental prerelease. The immutable `.2` release archives, tag, binary hashes and installer checksum are unchanged; this document supplements their original pre-release validation snapshot.

## 用户实机结果

用户提供了 VisionFive 2 上的终端结果：`riscv64`、内核 `6.12.113+deb13-riscv64`、bubblewrap `0.12.0`。`workspace-write` 与 `read-only` 两组脚本均通过：工作区写入按策略允许或拒绝，工作区外写入和 IPv4 socket 创建均被拒绝，`Seccomp=2`、`NoNewPrivs=1`。

托管版本按 `.2 → .1 → .2` 完成回滚与升级。升级后继续启用 Code Mode，原模型 `gpt-5.6-luna` 和程序仍在，修改与运行结果正确；此前的创建、初次运行、退出后 `/resume`、修改及再次运行也已确认成功。

用户随后确认 `upgrade --command codex` 实机迁移成功，托管入口为 `codex`，当前 `.2` / 上一 `.1` 保持不变，版本输出正常。

该记录覆盖所测单板配置、拒绝行为和实际工作流，不能替代完整安全审计。复测步骤见[沙箱与回滚检查](native-sandbox-check.md)。
