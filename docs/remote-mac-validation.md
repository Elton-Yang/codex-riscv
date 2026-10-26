# User-operated Mac Codex App remote validation

On 2026-10-26, after the `.3` update in this project, the user reported connecting from the Codex App on their local Mac to the RISC-V development board over SSH. The board was previously identified as VisionFive 2 / JH7110 running Debian 13. Exact App/macOS versions, remote executable identity and backend launch mechanism were not supplied for this check.

| User-reported step | Result |
| --- | --- |
| Establish SSH connection from Mac Codex App to the board | Succeeded |
| Discover the board's existing saved sessions | User reported all previous sessions appeared automatically |
| Select an existing session | Succeeded |
| Continue remote development in Mac Codex App | User reported normal operation |

The report was: “在本机Mac上连接ssh远程主机到risc-v开发板，可以正常完成ssh连接，并且自动发现开发板上的所有之前session，选中一个后可以正常继续在Mac的Codex App中进行远程开发”.

This supports the tested App/SSH session discovery and continuation workflow on that board. It is distinct from simply using a Mac terminal to run the TUI over SSH. The completeness of session discovery is user-observed, not an independent inventory comparison. No detailed remote edit/execute transcript, fresh remote-process sandbox probes, reconnect/reboot test, concurrent-writer test, App version or server start command was supplied.

In particular, this does not establish that every packaged-daemon, agents, remote-control or remote-server entry point is supported. The mechanism used by the App to start or connect to a backend remains unconfirmed. No SSH configuration, keys, credentials, host addresses, personal paths, session identifiers or conversation content were collected. Binary release assets, tags, installer behavior and checksums remain unchanged.

## 中文

用户已实测：Mac Codex App 能通过 SSH 连接开发板，自动显示此前会话，选中已有会话后可正常继续远程开发。这扩展了此前终端 TUI 的实机结果。

本次尚未提供 App/macOS 版本、远端可执行文件身份及后端启动方式，因此只记录已观察到的连接、会话发现与继续工作流程，不据此认定所有 daemon、agents 或 remote-server 功能都已验证。未收集 SSH 密钥、账号、主机地址或会话原文。
