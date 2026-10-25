# Validation record / 验证记录

Date: 2026-10-25 UTC. Scope: a preliminary cross-build, emulated checks, and subsequent user-operated native checks on one VisionFive 2 board. This remains an experimental adaptation, not a complete platform port.

## Inputs

| Item | Value |
| --- | --- |
| Upstream repository | <https://github.com/openai/codex> |
| Upstream commit | `970111f6cb62cc02fe36a82ea7d71b37a2889c97` |
| Upstream package version | `0.0.0` |
| Build host | Debian 13, x86_64 GNU/Linux |
| Target | `riscv64gc-unknown-linux-gnu` |
| ABI | LP64D |
| Rust | `1.99.1 (58cf8f9c3 2026-10-13)` |
| LLVM | `23.1.1` |
| Cross GCC | `14.2.0`, Debian package `14.2.0-19cross1` |
| Target glibc | `2.41-11cross1` |
| Target OpenSSL | `3.5.7-1~deb13u2` |
| QEMU user-mode | `10.0.13`, Debian `1:10.0.13+ds-0+deb13u1` |
| Profile | `dev-small`: unoptimized, stripped |

## Scope of the change

The functional patch adds `TargetArch::riscv64` to the Linux seccomp architecture selection. Existing syscall policy and deny rules remain unchanged. The linked `seccompiler 0.5.0` has RISC-V support.

The initial unmodified build stopped because the cross-compilation environment lacked target OpenSSL libraries and headers. Target Debian packages and target-specific include/library configuration resolved that environment issue. The dependency setup also includes OpenSSL's target zlib/zstd runtime dependencies.

Building only `codex-cli` / `codex` avoids the optional V8 runtime package. This does not validate external runtime features.

## Cross-build and QEMU commands exercised

From the pinned upstream `codex-rs` workspace, with the recorded cross toolchain and target-specific environment:

```bash
cargo build --locked -p codex-cli --bin codex \
  --target riscv64gc-unknown-linux-gnu --profile dev-small

cargo test --locked -p codex-linux-sandbox --lib \
  --target riscv64gc-unknown-linux-gnu --profile dev-small \
  seccomp::tests -- --test-threads=1
```

The test runner used QEMU with a matching local target sysroot. CLI smoke tests used an empty isolated home/config directory and did not make model API requests.

## Cross-build and QEMU results

| Check | Observed result |
| --- | --- |
| Debian archive signature, both package indexes and 36 package hashes | Verified |
| Cross-compiled C hello-world under QEMU | Passed |
| Target OpenSSL link and execution under QEMU | Passed |
| CLI cross-build | Exit 0; successful build reported 10m 21s after dependency setup |
| ELF inspection | RISC-V, RVC, LP64D, dynamically linked, stripped |
| `codex --version` under QEMU | `codex-cli 0.0.0`, exit 0 |
| `codex --help` under QEMU | Help output, exit 0 |
| Focused policy-selection tests under QEMU | 6 passed, 0 failed, 153 filtered out |
| Focused test-harness build | 6m 52s; test execution 0.02s |
| `git diff --check` | Passed |
| Focused `rustfmt --check` | Passed; stable rustfmt warned about an upstream nightly-only formatting option |
| Upstream `Cargo.lock` | Unchanged |

The six policy-selection tests cover:

- full network policy without managed networking skips network seccomp;
- full network mode without a managed proxy selects no network seccomp mode;
- managed networking still requires seccomp with a full network policy;
- managed proxy routes select proxy-routed mode;
- restricted networking always requires seccomp;
- restricted networking without proxy routing selects restricted mode.

**The QEMU policy-selection tests alone do not establish native RISC-V kernel filtering.** They test policy-selection logic and do not apply the complete sandbox to real work. Separate native checks are recorded below.

## User-operated native validation / 用户实机验证

On 2026-10-25, the user ran the released executable on their board and supplied terminal results. They separately reported successful authentication, model selection and live conversation. These are user-operated native results, not tests performed through remote access by the build environment. No account details, model name, conversation content or private paths are recorded here.

| Environment | Reported value |
| --- | --- |
| Board | VisionFive 2 / JH7110 |
| Operating system / architecture | Debian 13 / riscv64 |
| Kernel | `6.12.113+deb13-riscv64` |
| bubblewrap | `0.12.0` |
| Executable version | `codex-cli 0.0.0` (unchanged release binary) |

The sandbox checks used isolated temporary working and home/config directories with `env -i`, without authentication or model requests. The policy was explicitly selected with `sandbox -c 'sandbox_mode="read-only"'`. The socket probe created an `AF_INET` / `SOCK_STREAM` socket only: it did not perform DNS resolution or connect to any address.

| Native check | Observed or reported result |
| --- | --- |
| `--version` / `--help` | Normal version/help output; separate exit codes were not supplied |
| Read-only sandbox running `/bin/true` | Exit 0 |
| File-write control outside the sandbox | Succeeded in the temporary test directory |
| File-write attempt inside the read-only sandbox | `Read-only file system`, exit 2 |
| IPv4 TCP socket-creation control outside the sandbox | Succeeded |
| IPv4 TCP socket creation inside the read-only sandbox | `PermissionError: [Errno 1] Operation not permitted` (`EPERM`), exit 1 |
| Authentication, model selection and live conversation | User reported success; this supports basic TUI/conversation usability, not exhaustive UI or authentication-flow coverage |

The successful controls help distinguish the two sandbox denials from ordinary host filesystem permissions or lack of host socket support. These observations establish the tested native denial behaviors on this configuration. They do not audit every sandbox rule, establish a separate legacy Landlock result, or validate other boards/kernels. The authentication method was not established and no particular login route is claimed.

用户实机检查确认了启动、只读沙箱执行、文件写入拒绝和 IPv4 socket 创建拒绝；用户另行报告认证、模型选择与真实对话成功。这些结果独立于 QEMU 检查，不代表工具调用、模型修改文件、`workspace-write`、全部 TUI 操作或长期稳定性已经验证。

## Binary identity and dynamic dependencies

- Executable size: `314651976` bytes.
- Executable SHA256: `703975ef3ca50630be8349eb30f30e42ef458202bb54339797bae0b4d15e08b7`.
- Direct dynamic dependencies: `libssl.so.3`, `libcrypto.so.3`, `libgcc_s.so.1`, `libm.so.6`, `libc.so.6`, `ld-linux-riscv64-lp64d.so.1`.
- Highest referenced glibc symbol version: `GLIBC_2.39`.
- Referenced OpenSSL symbol version: `OPENSSL_3.0.0`.

The release archive additionally contains notices and documentation, so its checksum differs from the executable and from the earlier bare gzip experiment. Use the release's `SHA256SUMS` for archive verification.

## Not established

- Tool calls, model-driven file edits, or `workspace-write` behavior.
- Exhaustive TUI and authentication-flow coverage, native performance or long-term stability.
- Comprehensive sandbox/security validation beyond the two native denial probes, including the legacy Landlock backend, other filter rules, and other boards/kernels.
- Full test-suite success or optimized release-build behavior.
- RISC-V npm launcher, automatic updater or packaged-daemon installation support.
- Optional external code-mode / V8 and realtime runtimes.
- A clean-room end-to-end run of the reorganized public scripts.
- Bit-identical rebuilds across different paths, dates or build hosts.

## Reproduction boundaries

The scripts pin source and dependency inputs and reject checksum/signature mismatches. Debian mirrors can remove old package versions or change distribution indexes. A later reproduction may need matching historical inputs; it must not silently accept different ones. Any extra historical archive route should be verified before being described as supported.

For another board or kernel, repeat startup and sandbox checks in an isolated directory without sensitive files. The recorded success on this board is not a substitute for those checks. Installation of bubblewrap alone does not demonstrate that a different kernel allows the required namespaces or implements all relevant security mechanisms.

The public Debian-fetch helper was also exercised in verification-only mode: the signed indexes and all 36 package hashes passed. It did not extract packages or rebuild Codex.
