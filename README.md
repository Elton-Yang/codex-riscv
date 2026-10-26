# codex-riscv

[简体中文](README.zh-CN.md)

Unofficial experimental RISC-V Linux adaptation of OpenAI Codex CLI. Independent of OpenAI; no endorsement or official upstream RISC-V support is implied.

The current experimental release is **`v0.1.0-experimental.2`**, for Debian 13 / riscv64. It adds a sandbox-enabled Code Mode host alongside the unchanged `.1` CLI. The upstream development version still prints `codex-cli 0.0.0`.

## Install or upgrade

Use an ordinary user, without `sudo`, on the board. Runtime dependencies:

```sh
sudo apt update
sudo apt install ca-certificates curl python3 libc6 libgcc-s1 libssl3t64 bubblewrap
```

Requires Linux riscv64 and glibc ≥ 2.39. The two executables together occupy about 478 MB; allow roughly 1.5 GB free for download/staging and keep space for the previous installed version. No Rust, Node.js or compiler is needed to run the package.

Download and inspect the existing installer URL, then upgrade in place:

```sh
curl --fail --location --proto '=https' --proto-redir '=https' --tlsv1.2 \
  https://raw.githubusercontent.com/Elton-Yang/codex-riscv/main/install.sh \
  -o install-codex-riscv.sh
less install-codex-riscv.sh
sh install-codex-riscv.sh upgrade
export PATH="$HOME/.local/bin:$PATH"
sh install-codex-riscv.sh status
codex-riscv --version
```

`upgrade` also installs on a fresh system. It checks a pinned archive SHA256, executable permissions and both binaries' dynamic dependencies before switching `current`. The launcher keeps `--no-daemon`; no sandbox is disabled. Existing login information, model settings, `~/.codex`, shell files and projects are preserved. Existing custom prefixes require the original `--prefix` option. Re-download the script for a new release: old scripts do not query GitHub `latest`.

Start Code Mode in a disposable project:

```sh
mkdir -p "$HOME/codex-riscv-smoke"
cd "$HOME/codex-riscv-smoke"
codex-riscv -c features.code_mode_only=true
```

Ask it to create a small Python file and execute it. This enables Code Mode for this invocation only; existing authentication and model selection apply. The CLI finds `bin/codex-code-mode-host` beside its actual executable automatically. The user has reported native program creation and `/resume` followed by editing with `gpt-5.6-luna`; see [native validation](docs/native-validation-v0.1.0-experimental.2.md). Retain errors rather than disable sandboxing.

Management commands:

```sh
sh install-codex-riscv.sh rollback
sh install-codex-riscv.sh install --version v0.1.0-experimental.1
sh install-codex-riscv.sh uninstall
```

Rollback switches program versions and does not undo edits made by Codex. Uninstall preserves settings and projects. The default command is `codex-riscv`; `--command codex` is available for a new install if it does not collide with another installation. See [installer details](docs/installer.en.md).

## Validation

| Scope | Result |
| --- | --- |
| `.2` host source build, RISC-V LP64D | Passed |
| Full-system Sv39, restricted rv64gc-oriented ISA, ASLR=2 | Passed |
| Actual host stdio protocol, ordinary and traced runs | Passed |
| Three fresh secure V8/native-buffer/TurboFan runs | Passed: 32 GiB cage, 160 GiB full reservation |
| Low-Smi collision and 100 GiB VA limit | Expected fail-closed refusals passed |
| Actual CLI → host → real patch/Python tools | Passed in full-system simulation; only model responses mocked |
| Workspace-write kernel checks | Seccomp=2, NoNewPrivs=1, outside-workspace write denied |
| User-operated native program creation on the development board | Reported success with `gpt-5.6-luna` |
| Native exit → `/resume` → program editing | User reported success |
| Native program runs before and after modification | User confirmed both results correct |

The historical `.1` user tests covered VisionFive 2 / JH7110, Debian 13, startup, authentication/model choice/basic conversation and two read-only sandbox denial probes. Native `.2` creation and resumed editing are recorded separately in the [user report](docs/native-validation-v0.1.0-experimental.2.md). See [`.1` validation](docs/validation.md), [`.2` release notes](docs/release-notes-v0.1.0-experimental.2.md) and [new evidence](docs/code-mode-evidence/).

These checks are not an exploit-resistance certification, full sandbox audit, long-term stability result or validation of other boards/kernels. Full TUI coverage, realtime runtime, npm updater and explicit packaged daemon/agents/remote-server workflows remain unvalidated.

## Sources, changes and licenses

Pinned CLI upstream: [`970111f6cb62cc02fe36a82ea7d71b37a2889c97`](https://github.com/openai/codex/commit/970111f6cb62cc02fe36a82ea7d71b37a2889c97). Rust 1.99.1, cross GCC 14.2, target glibc 2.41; stripped, unoptimized `dev-small`. CLI changes retain the two-line RISC-V seccomp architecture selection. Code Mode uses rusty_v8 152.2.0 / V8 15.2.124.1 with the source adaptations recorded in [MODIFICATIONS.md](MODIFICATIONS.md).

Download binary and dependency-source archives plus `SHA256SUMS` from the [`.2` prerelease](https://github.com/Elton-Yang/codex-riscv/releases/tag/v0.1.0-experimental.2). The fixed binary archive digest is also embedded in `install.sh`. The package is dynamically linked, not a universal static Linux executable.

The [Code Mode build notes](docs/code-mode.md) describe the prepared source/toolchain layout and replay patches. `scripts/build.sh` reproduces the CLI-only build on a compatible Debian 13 x86_64 build host. No clean-room Code Mode setup or bit-identical rebuild is claimed.

Keep `LICENSE`, `NOTICE`, `licenses/`, modification records and the relevant dependency-source materials when redistributing. The Code Mode notice supplement supplements the baseline; known upstream attribution gaps and absent final linker map are explicitly disclosed. Inventory coverage is not legal clearance.
