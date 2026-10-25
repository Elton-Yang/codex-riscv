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
| VisionFive 2 / JH7110 hardware | **Not tested** |
| Actual kernel seccomp / Landlock / bubblewrap enforcement | **Not tested** |
| Interactive TUI, login, model API calls, full test suite | **Not tested** |

QEMU startup and policy-selection tests do not establish native sandbox enforcement. Do not run Codex as root or disable its sandbox to work around failures. See the [validation record](docs/validation.md).

## Pinned upstream and patch

- Upstream: [openai/codex](https://github.com/openai/codex)
- Commit: [`970111f6cb62cc02fe36a82ea7d71b37a2889c97`](https://github.com/openai/codex/commit/970111f6cb62cc02fe36a82ea7d71b37a2889c97)
- Target: `riscv64gc-unknown-linux-gnu`, LP64D ABI
- Rust `1.99.1`, cross GCC `14.2`, target glibc `2.41`
- Profile: unoptimized `dev-small`, stripped, for experiments

The functional source patch adds two lines selecting `TargetArch::riscv64` in the Linux seccomp architecture dispatch. `seccompiler 0.5.0` already provides this architecture. No filter rules or security checks were removed.

The pinned upstream development commit declares package version `0.0.0`, so `--version` reports `codex-cli 0.0.0`. This repository's release tag identifies the adaptation, not an upstream Codex release.

## Try it on Debian 13 riscv64

Once the prerelease and its assets have been uploaded, use the [release page](https://github.com/Elton-Yang/codex-riscv/releases/tag/v0.1.0-experimental.1). The commands below require those assets to be available. If a download returns 404, check the release page rather than substituting an unknown binary source.

### 1. Check the system and install runtime dependencies

```bash
uname -m                       # expected: riscv64
dpkg --print-architecture      # expected: riscv64
getconf GNU_LIBC_VERSION       # this binary requires glibc >= 2.39

sudo apt update
sudo apt install ca-certificates curl gzip libc6 libgcc-s1 libssl3t64 bubblewrap
```

`libssl3t64` supplies OpenSSL 3 libraries; apt also installs its zlib/zstd dependencies. `git` and `ripgrep` are useful optional development tools:

```bash
sudo apt install git ripgrep
```

You do not need Rust, Node.js or a cross compiler to run the binary. Allow space for the archive and extraction: the executable alone is `314651976` bytes, excluding accompanying notices and documentation.

### 2. Download, verify, then extract

```bash
TAG=v0.1.0-experimental.1
NAME="codex-riscv64-linux-gnu-${TAG}"
BASE="https://github.com/Elton-Yang/codex-riscv/releases/download/${TAG}"
DOWNLOAD_DIR=$(mktemp -d "${TMPDIR:-/tmp}/codex-riscv.XXXXXX")
cd "$DOWNLOAD_DIR"

curl --fail --location --proto '=https' --tlsv1.2 -O "$BASE/$NAME.tar.gz"
curl --fail --location --proto '=https' --tlsv1.2 -O "$BASE/SHA256SUMS"
sha256sum --check --ignore-missing SHA256SUMS
```

**Continue only after checksum verification succeeds:**

```bash
tar -xzf "$NAME.tar.gz"
"./$NAME/bin/codex" --version
"./$NAME/bin/codex" --help
```

`SHA256SUMS` verifies asset integrity; it is not an independent publisher signature. Obtain both files from this project's HTTPS release page.

### 3. Optional per-user installation

After the startup checks, install under a separate name so an existing npm `codex` is not replaced:

```bash
DEST="$HOME/.local/bin/codex-riscv"
mkdir -p "$HOME/.local/bin"
if [ -e "$DEST" ] || [ -L "$DEST" ]; then
  printf 'Existing file was not overwritten: %s\n' "$DEST"
else
  install -m 0755 "./$NAME/bin/codex" "$DEST"
  "$DEST" --version
fi
export PATH="$HOME/.local/bin:$PATH"
```

Keep the extracted `LICENSE`, `NOTICE` and `licenses/` materials, and include them when redistributing. These commands do not edit shell startup files.

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

- npm launcher, automatic updates and packaged-daemon installation paths are not adapted for RISC-V. Use the direct binary and manual installation.
- Optional external code-mode / V8 and realtime runtimes were not built, included or tested.
- No native VisionFive 2 test, interactive validation, login or model API call was performed.
- This large `dev-small` executable does not represent optimized release performance.
- This is a dynamically linked GNU/Linux binary, not a generic static executable.

## Licensing and provenance

Upstream Codex is Apache-2.0. This repository retains [LICENSE](LICENSE), [NOTICE](NOTICE) and modification records. Third-party components may use other licenses; see `licenses/THIRD-PARTY-NOTICES.html` and the original texts and supplemental notices under `licenses/`.

Retain those materials when redistributing. Automated notice generation assists with dependency information; it is not a legal guarantee for every use case.
