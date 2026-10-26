#!/usr/bin/env bash
# Build the reviewed CLI source using the centralized upstream/profile lock.
set -euo pipefail
scripts_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ $# != 2 ]]; then
  echo "Usage: $0 /absolute/path/to/prepared/src/codex-rs /absolute/path/to/new-output-directory" >&2
  exit 2
fi
cli_source="$(cd -- "$1" && pwd)"
cli_output="$2"
[[ "$cli_output" = /* && ! -e "$cli_output" ]]
python3 "$scripts_dir/upstream.py" verify-source --source "$cli_source/.." --component cli
profile_output="$(python3 "$scripts_dir/upstream.py" build-args cli)"
mapfile -t profile_args <<< "$profile_output"
mkdir -p -- "$cli_output"
export CARGO_TARGET_DIR="$cli_output/target"
export CARGO_BUILD_JOBS="${CARGO_BUILD_JOBS:-6}"
cd "$cli_source"
set +e
cargo build --locked --offline -p codex-cli --bin codex "${profile_args[@]}" 2>&1 | tee "$cli_output/build.log"
result=${PIPESTATUS[0]}
printf '%s\n' "$result" > "$cli_output/exit-code.txt"
exit "$result"
