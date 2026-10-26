#!/usr/bin/env bash
# Rebuild optimized CLI only in a prepared Codex/cross-toolchain environment.
# First source the recorded cross-toolchain environment. Existing .2 host is reused.
set -euo pipefail
if [[ $# != 2 ]]; then
  echo "Usage: $0 /absolute/path/to/codex-rs /absolute/path/to/new-output-directory" >&2
  exit 2
fi
cli_source="$(cd -- "$1" && pwd)"
cli_output="$2"
[[ "$cli_output" = /* && ! -e "$cli_output" ]]
mkdir -p -- "$cli_output"
export CARGO_TARGET_DIR="$cli_output/target"
export CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-6}"
cd "$cli_source"
set +e
cargo build --locked --offline -p codex-cli --bin codex \
  --target riscv64gc-unknown-linux-gnu --profile perf-cli \
  --config 'profile.perf-cli.inherits="dev-small"' \
  --config 'profile.perf-cli.opt-level=3' \
  --config 'profile.perf-cli.codegen-units=16' \
  --config 'profile.perf-cli.lto=false' \
  --config 'profile.perf-cli.debug-assertions=true' \
  --config 'profile.perf-cli.overflow-checks=true' \
  --config 'profile.perf-cli.incremental=false' 2>&1 | tee "$cli_output/build.log"
result=${PIPESTATUS[0]}
printf '%s\n' "$result" > "$cli_output/exit-code.txt"
exit "$result"
