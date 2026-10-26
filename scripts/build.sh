#!/usr/bin/env bash
# Preliminary Codex RISC-V cross-build on Debian 13 x86_64 (not on the board).
# Prerequisites: bash, curl, git, python3, gcc/g++, make, perl, pkg-config, dpkg-deb,
# gpgv, debian-archive-keyring, libarchive13t64, libjsoncpp26, libcurl4t64,
# libexpat1, libbz2-1.0 and normal GCC runtime libraries. No system writes occur.
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
project_root="$PWD"
rust_version="$(python3 scripts/upstream.py get toolchain.rust)"
target_triple="$(python3 scripts/upstream.py get toolchain.target)"
source_commit="$(python3 scripts/upstream.py get codex.commit)"
source_repository="$(python3 scripts/upstream.py get codex.repository)"
mkdir -p logs toolchains work
export RUSTUP_HOME="$PWD/toolchains/rustup" CARGO_HOME="$PWD/toolchains/cargo"
if [[ ! -x "$CARGO_HOME/bin/rustup" ]]; then
  curl -fLsS https://sh.rustup.rs -o toolchains/rustup-init.sh
  sh toolchains/rustup-init.sh -y --no-modify-path --profile minimal --default-toolchain "$rust_version"
fi
export PATH="$CARGO_HOME/bin:$PATH"
rustup toolchain install "$rust_version" --profile minimal --component rustfmt --component clippy --component rust-src
rustup target add --toolchain "$rust_version" "$target_triple"
command -v gpgv >/dev/null || { echo "Install trusted gpgv and debian-archive-keyring first." >&2; exit 1; }
python3 scripts/fetch-debian.py
if [[ ! -e work/upstream.git ]]; then
  git init --bare work/upstream.git
  git -C work/upstream.git remote add origin "$source_repository"
fi
if ! git -C work/upstream.git cat-file -e "$source_commit^{commit}" 2>/dev/null; then
  git -C work/upstream.git fetch --depth 1 origin "$source_commit"
fi
git -C work/upstream.git update-ref refs/heads/pinned "$source_commit"
if [[ ! -e src ]]; then
  python3 scripts/upstream.py prepare --component cli --codex-repo work/upstream.git --output work/cli
  ln -s work/cli/src src
fi
python3 scripts/upstream.py verify-source --component cli --source "$(cd src && pwd -P)"
source scripts/env.sh
if ldd "$CROSS_ROOT/usr/bin/cmake" | grep -q "not found"; then
  ldd "$CROSS_ROOT/usr/bin/cmake" >&2; exit 1
fi
gpgv --keyring /usr/share/keyrings/debian-archive-keyring.gpg manifests/debian-trixie-InRelease
cd src/codex-rs
profile_output="$(python3 "$project_root/scripts/upstream.py" build-args cli)"
mapfile -t profile_args <<< "$profile_output"
cargo build --locked -p codex-cli --bin codex "${profile_args[@]}" 2>&1 | tee "$project_root/logs/reproduce-build.log"
cli_profile="$(python3 "$project_root/scripts/upstream.py" get profiles.cli.name)"
"$CARGO_TARGET_RISCV64GC_UNKNOWN_LINUX_GNU_RUNNER" "$CARGO_TARGET_DIR/$target_triple/$cli_profile/codex" --version
"$CARGO_TARGET_RISCV64GC_UNKNOWN_LINUX_GNU_RUNNER" "$CARGO_TARGET_DIR/$target_triple/$cli_profile/codex" --help
