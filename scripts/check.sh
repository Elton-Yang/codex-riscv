#!/usr/bin/env bash
# Focused policy-selection logic only; not a native kernel sandbox test.
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
source scripts/env.sh
target_triple="$(python3 scripts/upstream.py get toolchain.target)"
python3 scripts/upstream.py verify-source --component cli --source "$(cd src && pwd -P)"
cd src/codex-rs
cargo test --locked -p codex-linux-sandbox --lib \
  --target "$target_triple" --profile dev-small \
  seccomp::tests -- --test-threads=1
