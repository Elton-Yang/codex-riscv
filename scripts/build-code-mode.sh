#!/usr/bin/env bash
# Rebuild in a prepared isolated source/toolchain work root, not on the board.
# See docs/code-mode.md; exact dependency sources are included in the source asset.
set -euo pipefail
if [[ $# != 1 ]]; then
  echo "Usage: $0 /absolute/path/to/prepared-code-mode-work-root" >&2
  exit 2
fi
code_mode_root="$(cd -- "$1" && pwd)"
[[ -f "$code_mode_root/env.sh" && -f "$code_mode_root/vendor/v8/Cargo.toml" ]]
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH-}"
source "$code_mode_root/env.sh"
export V8_FROM_SOURCE=1
cd "$code_mode_root/src/codex-rs"
cargo build --locked --offline -p codex-code-mode-host --bin codex-code-mode-host \
  --target riscv64gc-unknown-linux-gnu --profile dev-small
cargo test --locked --offline -p codex-code-mode-runtime --test riscv_sandbox \
  --target riscv64gc-unknown-linux-gnu --profile dev-small --no-run
