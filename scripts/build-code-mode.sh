#!/usr/bin/env bash
# Build reviewed sources in a prepared cross-toolchain environment.
set -euo pipefail
scripts_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# != 1 ]]; then
  echo "Usage: $0 /absolute/path/to/prepared-code-mode-work-root" >&2
  exit 2
fi
code_mode_root="$(cd -- "$1" && pwd)"
[[ -f "$code_mode_root/env.sh" && -f "$code_mode_root/vendor/v8/Cargo.toml" ]]
python3 "$scripts_dir/upstream.py" verify-source --source "$code_mode_root/src" --component code-mode
host_output="$(python3 "$scripts_dir/upstream.py" build-args host)"
test_output="$(python3 "$scripts_dir/upstream.py" build-args sandbox_tests)"
mapfile -t host_args <<< "$host_output"
mapfile -t test_args <<< "$test_output"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH-}"
source "$code_mode_root/env.sh"
export V8_FROM_SOURCE=1
cd "$code_mode_root/src/codex-rs"
cargo build --locked --offline -p codex-code-mode-host --bin codex-code-mode-host "${host_args[@]}"
cargo test --locked --offline -p codex-code-mode-runtime --test riscv_sandbox "${test_args[@]}" --no-run
