# codex-riscv

[简体中文](README.md)

An **unofficial experimental RISC-V Linux build and adaptation of OpenAI Codex CLI**. This project is independent of OpenAI and is not endorsed by OpenAI. It does not indicate official upstream RISC-V support.

The first adaptation release is `v0.1.0-experimental.1`, targeting Debian 13 / riscv64.

## Status

| Check | Result |
| --- | --- |
| Cross-build for `riscv64gc-unknown-linux-gnu` | Passed |
| `codex --version` and `--help` under QEMU | Both exited 0 |
| seccomp policy-selection unit tests under QEMU | 6 passed, 0 failed |
| Native startup on VisionFive 2 / JH7110 | User-operated `--version` / `--help` produced normal output |
| Native read-only sandbox running `/bin/true` | Exit 0 |
| Native read-only sandbox denying file writes / IPv4 socket creation | Read-only filesystem, exit 2 / `EPERM`, exit 1; both outside-sandbox controls succeeded |
| Authentication, model selection and basic interactive conversation | User reported success |
| Tool calls, model-driven file edits, `workspace-write`, full test suite | **Not tested** |

The user ran the native checks on 2026-10-25 on VisionFive 2 / Debian 13 with kernel `6.12.113+deb13-riscv64` and bubblewrap `0.12.0`. These results are separate from the build host's QEMU checks. They cover the listed startup and denial behavior and basic conversation, not a comprehensive sandbox security audit or long-term stability. Do not run Codex as root or disable its sandbox to work around failures. See the [validation record](docs/validation.md).

## Pinned upstream and patch

- Upstream: [openai/codex](https://github.com/openai/codex)
- Commit: [`970111f6cb62cc02fe36a82ea7d71b37a2889c97`](https://github.com/openai/codex/commit/970111f6cb62cc02fe36a82ea7d71b37a2889c97)
- Target: `riscv64gc-unknown-linux-gnu`, LP64D ABI
- Rust `1.99.1`, cross GCC `14.2`, target glibc `2.41`
- Profile: unoptimized `dev-small`, stripped, for experiments

The functional source patch adds two lines selecting `TargetArch::riscv64` in the Linux seccomp architecture dispatch. `seccompiler 0.5.0` already provides this architecture. No filter rules or security checks were removed.

The pinned upstream development commit declares package version `0.0.0`, so `--version` reports `codex-cli 0.0.0`. This repository's release tag identifies the adaptation, not an upstream Codex release.

## Try it on Debian 13 riscv64

Use the per-user installer below, or download manually from the [release page](https://github.com/Elton-Yang/codex-riscv/releases/tag/v0.1.0-experimental.1). The installer uses the existing experimental binary without rebuilding or changing its version.

### 1. Check the system and install runtime dependencies

```bash
uname -m                       # expected: riscv64
dpkg --print-architecture      # expected: riscv64
getconf GNU_LIBC_VERSION       # this binary requires glibc >= 2.39

sudo apt update
sudo apt install ca-certificates curl python3 gzip libc6 libgcc-s1 libssl3t64 bubblewrap
```

`libssl3t64` supplies OpenSSL 3 libraries; apt also installs its zlib/zstd dependencies. `git` and `ripgrep` are useful optional development tools:

```bash
sudo apt install git ripgrep
```

You do not need Rust, Node.js or a cross compiler to run the binary. Allow space for the archive and extraction: the executable alone is `314651976` bytes, excluding accompanying notices and documentation.

### 2. Install a user-global command (recommended)

Download and review the script, then run it as your ordinary user, **without `sudo`**:

```bash
curl --fail --location --proto '=https' --proto-redir '=https' --tlsv1.2 \
  https://raw.githubusercontent.com/Elton-Yang/codex-riscv/main/install.sh \
  -o install-codex-riscv.sh
less install-codex-riscv.sh
sh install-codex-riscv.sh
export PATH="$HOME/.local/bin:$PATH"
codex-riscv --version
```

The default installation retains the full release under `~/.local/share/codex-riscv/versions/v0.1.0-experimental.1` and creates `~/.local/bin/codex-riscv`. The installer checks a pinned SHA-256, platform and dynamic libraries, then runs `--version` before switching the active version. It preserves license materials and does not edit shell startup files.

Choose the management action you need; do not run all of these in sequence:

```bash
sh install-codex-riscv.sh status
sh install-codex-riscv.sh install --version v0.1.0-experimental.1
sh install-codex-riscv.sh upgrade --channel experimental
sh install-codex-riscv.sh rollback
sh install-codex-riscv.sh uninstall
```

`upgrade` selects the experimental release listed in this installer, not GitHub's `latest`. Only one release is currently supported; reinstalling it does not create a rollback version. Rollback requires an earlier successful switch between different installed versions. Download and review an updated installer before upgrading to future releases. Uninstall removes only managed, unmodified installation files, never `~/.codex`, credentials or project files.

To use the name `codex`, explicitly pass `--command codex` on the first installation. An unrelated command at the destination or on `PATH` blocks installation. A `codex-riscv` binary copied using the old instructions is not overwritten either: inspect it before manually moving or renaming it. See the [installer guide](docs/installer.en.md) for options, layout and troubleshooting.

### 3. Manual download and startup check (without the installer)

```bash
TAG=v0.1.0-experimental.1
NAME="codex-riscv64-linux-gnu-${TAG}"
BASE="https://github.com/Elton-Yang/codex-riscv/releases/download/${TAG}"
DOWNLOAD_DIR=$(mktemp -d "${TMPDIR:-/tmp}/codex-riscv.XXXXXX")
cd "$DOWNLOAD_DIR"

curl --fail --location --proto '=https' --proto-redir '=https' --tlsv1.2 \
  -O "$BASE/$NAME.tar.gz"
printf '%s  %s\n' \
  2b70f049652793a2dd6c8035122ce2a6920de680153be1c6f8e2a172dde70120 \
  "$NAME.tar.gz" | sha256sum --check --strict
```

**Continue only after checksum verification succeeds:**

```bash
tar -xzf "$NAME.tar.gz"
"./$NAME/bin/codex" --version
"./$NAME/bin/codex" --help
```

This fixed checksum applies only to the named release. It verifies integrity, not an independent publisher signature. If a download returns 404, check this project's release page rather than substituting an unknown binary source. Keep the full extracted `LICENSE`, `NOTICE` and `licenses/` materials, including when redistributing.

### 4. Validate the native sandbox before real work

This build does not bundle bubblewrap. It uses the system `bwrap`, and the board's kernel and system policy must permit the relevant user namespaces and sandbox mechanisms. A Debian userland version alone does not establish that a vendor kernel is suitable.

Start in an isolated test directory without sensitive files. Validate read-only, write-restriction and network-denial behavior. Record the kernel version and full errors if bubblewrap, namespace, seccomp or Landlock operations fail. Do not turn off sandboxing to claim compatibility.

## Reproduce the cross-build

The build scripts target a **Debian 13 x86_64 build host**, not native installation on the board. Read the host prerequisites in the scripts first:

```bash
./scripts/build.sh
./scripts/check.sh
```

The upstream commit, Rust version and Debian package manifests are pinned; Cargo uses `--locked`. Debian packages are checked against a signature/hash chain and extracted locally. Host prerequisites must already be present.

The underlying build and test commands were executed successfully. The reorganized public scripts have not been run end-to-end in a fresh environment. Bit-for-bit reproducibility across paths, dates and hosts is not claimed. Missing or changed pinned mirror content must fail verification rather than silently upgrade dependencies. See [validation details](docs/validation.md).

To regenerate license notices:

```bash
./scripts/generate-notices.py
```

## Limitations

- npm launcher, upstream automatic updates and packaged-daemon installation paths are not adapted for RISC-V. This repository’s installer manages direct-binary upgrades. Root / system-wide installation is not supported.
- Optional external code-mode / V8 and realtime runtimes were not built, included or tested.
- Native validation covers only the listed checks on one board and user-reported basic conversation. Tool calls, model-driven file edits, `workspace-write`, exhaustive TUI behavior, other kernels and long-term stability remain untested.
- The file-write and IPv4-socket denials are not a comprehensive sandbox security audit. The legacy Landlock backend and the full set of filter rules were not separately validated.
- This large `dev-small` executable does not represent optimized release performance.
- This is a dynamically linked GNU/Linux binary, not a generic static executable.

## Licensing and provenance

Upstream Codex is Apache-2.0. This repository retains [LICENSE](LICENSE), [NOTICE](NOTICE) and modification records. Third-party components may use other licenses; see `licenses/THIRD-PARTY-NOTICES.html` and the original texts and supplemental notices under `licenses/`.

Retain those materials when redistributing. Automated notice generation assists with dependency information; it is not a legal guarantee for every use case.
