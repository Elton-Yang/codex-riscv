#!/usr/bin/env bash
# Preliminary Codex RISC-V cross-build on Debian 13 x86_64 (not on the board).
# Prerequisites: bash, curl, git, python3, gcc/g++, make, perl, pkg-config, dpkg-deb,
# gpgv, debian-archive-keyring, libarchive13t64, libjsoncpp26, libcurl4t64,
# libexpat1, libbz2-1.0 and normal GCC runtime libraries. No system writes occur.
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
mkdir -p logs toolchains
export RUSTUP_HOME="$PWD/toolchains/rustup" CARGO_HOME="$PWD/toolchains/cargo"
if [[ ! -x "$CARGO_HOME/bin/rustup" ]]; then
  curl -fLsS https://sh.rustup.rs -o toolchains/rustup-init.sh
  sh toolchains/rustup-init.sh -y --no-modify-path --profile minimal --default-toolchain 1.99.1
fi
export PATH="$CARGO_HOME/bin:$PATH"
rustup toolchain install 1.99.1 --profile minimal --component rustfmt --component clippy --component rust-src
rustup target add --toolchain 1.99.1 riscv64gc-unknown-linux-gnu
command -v gpgv >/dev/null || { echo "Install trusted gpgv and debian-archive-keyring first." >&2; exit 1; }
python3 scripts/fetch-debian.py
if [[ ! -e src/.git ]]; then
  git init src
  git -C src remote add origin https://github.com/openai/codex.git
  git -C src fetch --depth 1 origin 970111f6cb62cc02fe36a82ea7d71b37a2889c97
  git -C src checkout --detach FETCH_HEAD
fi
[[ "$(git -C src rev-parse HEAD)" == 970111f6cb62cc02fe36a82ea7d71b37a2889c97 ]]
if git -C src apply --check ../patches/0001-linux-seccomp-riscv64.patch; then
  git -C src apply ../patches/0001-linux-seccomp-riscv64.patch
else
  git -C src apply --reverse --check ../patches/0001-linux-seccomp-riscv64.patch
fi
source scripts/env.sh
if ldd "$CROSS_ROOT/usr/bin/cmake" | grep -q "not found"; then
  ldd "$CROSS_ROOT/usr/bin/cmake" >&2; exit 1
fi
gpgv --keyring /usr/share/keyrings/debian-archive-keyring.gpg manifests/debian-trixie-InRelease
cd src/codex-rs
cargo build --locked -p codex-cli --bin codex --target riscv64gc-unknown-linux-gnu --profile dev-small 2>&1 | tee ../../logs/reproduce-build.log
cd ../..
"$CARGO_TARGET_RISCV64GC_UNKNOWN_LINUX_GNU_RUNNER" target/riscv64gc-unknown-linux-gnu/dev-small/codex --version
"$CARGO_TARGET_RISCV64GC_UNKNOWN_LINUX_GNU_RUNNER" target/riscv64gc-unknown-linux-gnu/dev-small/codex --help
