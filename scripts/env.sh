#!/usr/bin/env bash
PROBE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export RUSTUP_HOME="$PROBE_ROOT/toolchains/rustup"
export CARGO_HOME="$PROBE_ROOT/toolchains/cargo"
export CROSS_ROOT="$PROBE_ROOT/toolchains/debian/root"
export PATH="$PROBE_ROOT/scripts/bin:$CARGO_HOME/bin:$CROSS_ROOT/usr/bin:$PATH"
export LD_LIBRARY_PATH="$CROSS_ROOT/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export CARGO_TARGET_RISCV64GC_UNKNOWN_LINUX_GNU_LINKER=riscv64-linux-gnu-gcc
export CC_riscv64gc_unknown_linux_gnu=riscv64-linux-gnu-gcc
export CXX_riscv64gc_unknown_linux_gnu=riscv64-linux-gnu-g++
export AR_riscv64gc_unknown_linux_gnu=riscv64-linux-gnu-ar
export CARGO_TARGET_DIR="$PROBE_ROOT/target"
export CARGO_BUILD_JOBS=2
export CARGO_INCREMENTAL=0
# Target OpenSSL from signed Debian trixie riscv64 packages; never use host libs.
export RISCV64GC_UNKNOWN_LINUX_GNU_OPENSSL_LIB_DIR="$CROSS_ROOT/usr/lib/riscv64-linux-gnu"
export RISCV64GC_UNKNOWN_LINUX_GNU_OPENSSL_INCLUDE_DIR="$CROSS_ROOT/usr/include"
export CFLAGS_riscv64gc_unknown_linux_gnu="-I$CROSS_ROOT/usr/include/riscv64-linux-gnu"
export CXXFLAGS_riscv64gc_unknown_linux_gnu="-I$CROSS_ROOT/usr/include/riscv64-linux-gnu"
export CARGO_TARGET_RISCV64GC_UNKNOWN_LINUX_GNU_RUNNER="$PROBE_ROOT/scripts/bin/qemu-codex-riscv64"
