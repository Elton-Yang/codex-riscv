#!/usr/bin/env bash
# Focused policy-selection logic only; not a native kernel sandbox test.
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
source scripts/env.sh
cd src/codex-rs
cargo test --locked -p codex-linux-sandbox --lib \
  --target riscv64gc-unknown-linux-gnu --profile dev-small \
  seccomp::tests -- --test-threads=1
