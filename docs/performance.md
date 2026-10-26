# Startup and resume comparison

`.3` is a compiler-optimized CLI candidate, not a measured performance fix. The reported `.2` board behavior was: SD-card storage, ordinary SSH terminal input responsive, `/resume` list fast, several seconds of pause after selecting a short conversation. This points to post-selection recovery/display work; CPU, IO and UI event waiting have not yet been separated by native profiling.

## What changed

Only the CLI compiler profile changed from unoptimized `dev-small` to `perf-cli` with `opt-level=3`, 16 codegen units, no LTO, retained debug assertions/overflow checks and stripped symbols. Fixed source and dependencies remain unchanged. The `.2` host is reused without rebuilding. The CLI grows from 314,651,976 to 345,346,040 bytes; faster CPU execution and larger cold IO can compete on an SD card.

## Compare on VisionFive 2

Use the same SSH terminal, terminal dimensions, working directory, model and dedicated saved test conversation. Exit all Codex processes before switching versions. Do not clear the kernel cache or change sandbox permissions.

```sh
sh install-codex-riscv.sh status
codex -c features.code_mode_only=true
```

For each version, record 5 trials:

1. Start command to first editable input echo.
2. `/resume` selection + Enter to history displayed and input responsive.
3. Resume, edit and run a small existing test program to confirm correctness.

List time separately from conversation-load time. Keep the first launch separate from later warm-cache runs. Approximate timings are useful; do not report simulation timings as native results.

After upgrading `.2` to `.3`, the installer normally retains `.2` as previous. Check `status` before rollback:

```sh
sh install-codex-riscv.sh rollback
sh install-codex-riscv.sh status
codex -c features.code_mode_only=true
# Exit Codex before upgrading again.
sh install-codex-riscv.sh upgrade
sh install-codex-riscv.sh status
```

Expected versions: `.3 → .2 → .3`. Rollback switches programs, not project/configuration/session contents. Use a disposable test conversation, preserve existing data and report any differences. If rollback history differs, use `install --version v0.1.0-experimental.2` explicitly. Installer authentication/model configuration is preserved; do not share login files, tokens or conversation contents.

## Correctness evidence

The `.3` release manifest records artifact hashes and bounded emulated checks. Existing `.2` native validation is historical; `.3` native TUI responsiveness, session-list selection, kernel-policy tests and performance remain pending user confirmation.

If compiler optimization is insufficient, the next step is stage timing for configuration restoration, thread resume, history hydration/layout and UI attachment. History may include tool output and metadata beyond visible chat text. The current source awaits multiple stages during session switching; responsiveness needs measurement, not assumptions about 4 cores/8GB or SD-card fault alone.

For `.3`, the actual optimized CLI passed full-system Sv39 real patch/Python tool integration with the unchanged `.2` host. A second guest run passed workspace-write/read-only probes, outside writes/socket denials, `Seccomp=2`, `NoNewPrivs=1`, and two actual CLI processes that saved and resumed a synthetic conversation. Only loopback model responses were mocked. The native-check script's root refusal alone was replaced in the disposable root guest fixture; real CLI/kernel enforcement was unchanged. This CLI `exec resume` test is correctness coverage, not measurement of TUI `/resume` latency.

The installer also passed 64 offline regressions and an actual-archive QEMU smoke covering `.2` → `.3`, old-name → `codex` migration, rollback, settings sentinel preservation, helper dispatch, bare onboarding and uninstall. This validates the packaged path with emulated platform checks; native `.3` installation and performance remain pending. `performance-evidence/artifact.json` is the initial post-build snapshot; the release manifest and subsequent test records describe completed pre-publication correctness checks.

The `.3` dependency-source asset includes `optimized-cli-source/codex-rs` with the original CLI lockfile, alongside the adapted `.2` host sources. `build-cli-performance.sh` in that source asset records the optimization profile.
