# User-operated native validation: v0.1.0-experimental.2

On 2026-10-26, after the `.2` release and installer update, the user reported successful testing on their RISC-V development board. The board was previously identified in this project as VisionFive 2 / JH7110 with Debian 13. Kernel, bubblewrap version and installed artifact hashes were not supplied again for this report; their earlier values are not new measurements.

| User-reported check | Result |
| --- | --- |
| Existing model | Continued using `gpt-5.6-luna` |
| Create a program and run it | Succeeded; user confirmed correct output |
| Exit and resume the session with `/resume` | Succeeded |
| Modify the program after resuming and run it again | Succeeded; user confirmed correct output |

The user's report was: “我已经在开发板上实测通过，现在可以创建程序（仍然使用gpt-5.6-luna模型），并且测试了退出后/resume，然后修改程序，都可以正常进行”.

This is user-operated native functional evidence, separate from the recorded full-system QEMU acceptance. The user subsequently confirmed both executions (initial and after modification) produced correct results. It supports creation, execution, session resumption, modification and re-execution with the existing model on that board. No exit codes, terminal logs, exact launch flags, fresh kernel-policy probes or comprehensive security/stability coverage were supplied. These results do not extend the emulated `Seccomp=2`, `NoNewPrivs=1` and outside-workspace-denial observations to native hardware.

No credentials, private program content or personal paths were collected. The release remains an experimental prerelease. The immutable `.2` release archives, tag, binary hashes and installer checksum are unchanged; this document supplements their original pre-release validation snapshot.

## 用户实机结果

用户于 2026-10-26 在 `.2` 发布后反馈：开发板继续使用 `gpt-5.6-luna`，创建程序成功，退出后使用 `/resume` 恢复会话并继续修改程序成功；随后补充确认初次和修改后两次运行的结果均正确。设备在本项目此前记录为 VisionFive 2 / JH7110、Debian 13；本次未重新提供内核、bubblewrap 或已安装产物摘要。

本次记录覆盖用户报告的创建、执行、恢复编辑和再次执行；新一轮实机内核沙箱检查尚待另行反馈。发布包和安装器摘要保持不变，版本继续标记为实验性 prerelease。

Native sandbox and rollback instructions / 实机沙箱与回滚步骤: [check guide](native-sandbox-check.md).
