# User-operated native validation: v0.1.0-experimental.2

On 2026-10-26, after the `.2` release and installer update, the user reported successful testing on their RISC-V development board. The board was previously identified in this project as VisionFive 2 / JH7110 with Debian 13. Kernel, bubblewrap version and installed artifact hashes were not supplied again for this report; their earlier values are not new measurements.

| User-reported check | Result |
| --- | --- |
| Existing model | Continued using `gpt-5.6-luna` |
| Create a program | Succeeded |
| Exit and resume the session with `/resume` | Succeeded |
| Modify the program after resuming | Succeeded |

The user's report was: “我已经在开发板上实测通过，现在可以创建程序（仍然使用gpt-5.6-luna模型），并且测试了退出后/resume，然后修改程序，都可以正常进行”.

This is user-operated native functional evidence, separate from the recorded full-system QEMU acceptance. It supports program creation and resumed editing with the existing model on that board. No native program-execution result, exit codes, terminal logs, exact launch flags, fresh kernel-policy probes or comprehensive security/stability coverage were supplied. These results do not extend the emulated `Seccomp=2`, `NoNewPrivs=1` and outside-workspace-denial observations to native hardware.

No credentials, private program content or personal paths were collected. The release remains an experimental prerelease. The immutable `.2` release archives, tag, binary hashes and installer checksum are unchanged; this document supplements their original pre-release validation snapshot.

## 用户实机结果

用户于 2026-10-26 在 `.2` 发布后反馈：开发板继续使用 `gpt-5.6-luna`，创建程序成功，退出后使用 `/resume` 恢复会话并继续修改程序成功。设备在本项目此前记录为 VisionFive 2 / JH7110、Debian 13；本次未重新提供内核、bubblewrap 或已安装产物摘要。

本次记录覆盖用户报告的创建与恢复编辑流程，不能据此补记“程序执行成功”或新一轮实机内核沙箱检查通过。发布包和安装器摘要保持不变，版本继续标记为实验性 prerelease。
