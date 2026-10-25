# Validation record / 验证记录

Date: 2026-10-25 UTC. Scope: a preliminary cross-build and emulated startup of the CLI, not a complete platform port.

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

## Commands exercised

From the pinned upstream `codex-rs` workspace, with the recorded cross toolchain and target-specific environment:

```bash
cargo build --locked -p codex-cli --bin codex \
  --target riscv64gc-unknown-linux-gnu --profile dev-small

cargo test --locked -p codex-linux-sandbox --lib \
  --target riscv64gc-unknown-linux-gnu --profile dev-small \
  seccomp::tests -- --test-threads=1
```

The test runner used QEMU with a matching local target sysroot. CLI smoke tests used an empty isolated home/config directory and did not make model API requests.

## Observed results

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

**None of these tests establishes that native RISC-V kernel filtering is enforced.** They test policy-selection logic and do not apply the complete sandbox to real work.

## Binary identity and dynamic dependencies

- Executable size: `314651976` bytes.
- Executable SHA256: `703975ef3ca50630be8349eb30f30e42ef458202bb54339797bae0b4d15e08b7`.
- Direct dynamic dependencies: `libssl.so.3`, `libcrypto.so.3`, `libgcc_s.so.1`, `libm.so.6`, `libc.so.6`, `ld-linux-riscv64-lp64d.so.1`.
- Highest referenced glibc symbol version: `GLIBC_2.39`.
- Referenced OpenSSL symbol version: `OPENSSL_3.0.0`.

The release archive additionally contains notices and documentation, so its checksum differs from the executable and from the earlier bare gzip experiment. Use the release's `SHA256SUMS` for archive verification.

## Not established

- Native VisionFive 2 / JH7110 execution or performance.
- Interactive TUI behavior, login or real model API access.
- Actual seccomp, Landlock, bubblewrap filesystem/network enforcement on a RISC-V kernel.
- Full test-suite success or optimized release-build behavior.
- RISC-V npm launcher, automatic updater or packaged-daemon installation support.
- Optional external code-mode / V8 and realtime runtimes.
- A clean-room end-to-end run of the reorganized public scripts.
- Bit-identical rebuilds across different paths, dates or build hosts.

## Reproduction boundaries

The scripts pin source and dependency inputs and reject checksum/signature mismatches. Debian mirrors can remove old package versions or change distribution indexes. A later reproduction may need matching historical inputs; it must not silently accept different ones. Any extra historical archive route should be verified before being described as supported.

The first native follow-up should use an isolated directory without sensitive files, check `--version` / `--help`, and then verify sandbox restrictions. Installation of bubblewrap does not by itself demonstrate that a board's vendor kernel allows the required namespaces or implements all relevant security mechanisms.

The public Debian-fetch helper was also exercised in verification-only mode: the signed indexes and all 36 package hashes passed. It did not extract packages or rebuild Codex.
