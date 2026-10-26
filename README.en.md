# codex-riscv

[简体中文](README.zh-CN.md)

Unofficial experimental RISC-V Linux adaptation of OpenAI Codex CLI. Independent of OpenAI; no endorsement or official upstream RISC-V support is implied.

The current experimental release is **`v0.1.0-experimental.3`**, for Debian 13 / riscv64. It enables `opt-level=3` for the CLI and reuses the `.2` Code Mode host. The user reports noticeably faster native `/resume` post-selection loading with perceived pauses essentially eliminated; numerical timings and startup speed remain unmeasured. The upstream development version still prints `codex-cli 0.0.0`.

## One-minute demo

Starting Codex on a VisionFive 2 / JH7110 running Debian 13 and creating a simple Python program.

https://github.com/user-attachments/assets/adcac9ee-0b42-407c-8a33-9d6d42cf6928

[Open or download the MP4 video](https://github.com/user-attachments/assets/adcac9ee-0b42-407c-8a33-9d6d42cf6928)

## Install or upgrade

Use an ordinary user, without `sudo`, on the board. Runtime dependencies:

```sh
sudo apt update
sudo apt install ca-certificates curl python3 libc6 libgcc-s1 libssl3t64 bubblewrap
```

Requires Linux riscv64 and glibc ≥ 2.39. The two executables together occupy about 509 MB; allow roughly 1.5 GB free for download/staging and keep space for the previous installed version. No Rust, Node.js or compiler is needed to run the package.

Download and inspect the existing installer URL, then upgrade in place:

```sh
curl --fail --location --proto '=https' --proto-redir '=https' --tlsv1.2 \
  https://raw.githubusercontent.com/Elton-Yang/codex-riscv/main/install.sh \
  -o install-codex-riscv.sh
less install-codex-riscv.sh
sh install-codex-riscv.sh upgrade --command codex
export PATH="$HOME/.local/bin:$PATH"
sh install-codex-riscv.sh status
codex --version
```

`upgrade` also installs on a fresh system. It checks a pinned archive SHA256, executable permissions and both binaries' dynamic dependencies before switching `current`. The launcher keeps `--no-daemon`; no sandbox is disabled. Existing login information, model settings, `~/.codex`, shell files and projects are preserved. Existing custom prefixes require the original `--prefix` option. Re-download the script for a new release: old scripts do not query GitHub `latest`.

Start Code Mode in a disposable project:

```sh
mkdir -p "$HOME/codex-riscv-smoke"
cd "$HOME/codex-riscv-smoke"
codex -c features.code_mode_only=true
```

Ask it to create a small Python file and execute it. This enables Code Mode for this invocation only; existing authentication and model selection apply. The CLI finds `bin/codex-code-mode-host` beside its actual executable automatically. The user has reported native program creation and `/resume` followed by editing with `gpt-5.6-luna`; see [native validation](docs/native-validation-v0.1.0-experimental.2.md). Retain errors rather than disable sandboxing.

Management commands:

```sh
sh install-codex-riscv.sh rollback
sh install-codex-riscv.sh install --version v0.1.0-experimental.1
sh install-codex-riscv.sh uninstall
```

Rollback switches program versions and does not undo edits made by Codex. Uninstall preserves settings and projects. The default command is `codex`. Existing `codex-riscv` installations migrate in place with `upgrade --command codex`; plain `upgrade` retains their saved command. Foreign `codex` commands are never overwritten or shadowed. `--command codex-riscv` remains available explicitly. See [installer details](docs/installer.en.md).

## `.3` optimized candidate

Same CLI source/dependencies, retained debug assertions, overflow checks and security mechanisms. CLI size increases from about 315 MB to 345 MB. Full-system Sv39 tool integration, persistent resume and kernel-policy probes passed; simulation is not native performance evidence. Subsequent user feedback confirms qualitatively improved resume responsiveness on VisionFive 2 with SD storage over SSH; no speedup ratio is claimed. See [`.3` release notes](docs/release-notes-v0.1.0-experimental.3.md) and [comparison steps](docs/performance.md).

The user also reports successful Mac Codex App SSH connection to the board, automatic discovery of existing sessions and continuation of a selected session. See [remote validation and scope](docs/remote-mac-validation.md).

## Historical `.2` validation

| Scope | Result |
| --- | --- |
| `.2` host source build, RISC-V LP64D | Passed |
| Full-system Sv39, restricted rv64gc-oriented ISA, ASLR=2 | Passed |
| Actual host stdio protocol, ordinary and traced runs | Passed |
| Three fresh secure V8/native-buffer/TurboFan runs | Passed: 32 GiB cage, 160 GiB full reservation |
| Low-Smi collision and 100 GiB VA limit | Expected fail-closed refusals passed |
| Actual CLI → host → real patch/Python tools | Passed in full-system simulation; only model responses mocked |
| Native workspace-write / read-only checks | Passed: policy-specific writes, outside-write/socket denials, Seccomp=2, NoNewPrivs=1 |
| Native `.2` → `.1` → `.2` rollback/upgrade | Passed; model/program retained and subsequent edit/run correct |
| User-operated native program creation on the development board | Reported success with `gpt-5.6-luna` |
| Native exit → `/resume` → program editing | User reported success |
| Native program runs before and after modification | User confirmed both results correct |

The historical `.1` user tests covered VisionFive 2 / JH7110, Debian 13, startup, authentication/model choice/basic conversation and two read-only sandbox denial probes. Native `.2` creation and resumed editing are recorded separately in the [user report](docs/native-validation-v0.1.0-experimental.2.md). See [`.1` validation](docs/validation.md), [`.2` release notes](docs/release-notes-v0.1.0-experimental.2.md) and [new evidence](docs/code-mode-evidence/).

These checks are not an exploit-resistance certification, full sandbox audit, long-term stability result or validation of other boards/kernels. Full TUI coverage, realtime runtime, npm updater and full packaged daemon/agents/remote-server coverage remains unvalidated beyond the reported App/SSH workflow.

## Sources, changes and licenses

Pinned CLI upstream: [`970111f6cb62cc02fe36a82ea7d71b37a2889c97`](https://github.com/openai/codex/commit/970111f6cb62cc02fe36a82ea7d71b37a2889c97). Rust 1.99.1, cross GCC 14.2, target glibc 2.41; `.3` CLI uses stripped `perf-cli` (opt-level=3, no LTO, debug assertions and overflow checks retained); host remains the `.2` `dev-small` build. CLI changes retain the two-line RISC-V seccomp architecture selection. Code Mode uses rusty_v8 152.2.0 / V8 15.2.124.1 with the source adaptations recorded in [MODIFICATIONS.md](MODIFICATIONS.md).

Download binary and dependency-source archives plus `SHA256SUMS` from the [`.3` prerelease](https://github.com/Elton-Yang/codex-riscv/releases/tag/v0.1.0-experimental.3). The fixed binary archive digest is also embedded in `install.sh`. The package is dynamically linked, not a universal static Linux executable.

The [Code Mode build notes](docs/code-mode.md) describe the prepared source/toolchain layout and replay patches. `scripts/build.sh` reproduces the CLI-only build on a compatible Debian 13 x86_64 build host. No clean-room Code Mode setup or bit-identical rebuild is claimed.

Keep `LICENSE`, `NOTICE`, `licenses/`, modification records and the relevant dependency-source materials when redistributing. The Code Mode notice supplement supplements the baseline; known upstream attribution gaps and absent final linker map are explicitly disclosed. Inventory coverage is not legal clearance.

## Upstream alignment / 上游对齐

Current source, toolchain, profiles and patch identities are pinned in [upstream-lock.json](manifests/upstream-lock.json). See [source preparation and upgrade policy](docs/upstream-maintenance.md) for clean patch commits, repeatable replay, release discovery, state-compatibility tests and the first formal-release rehearsal. The validated `.3` baseline remains unchanged.
