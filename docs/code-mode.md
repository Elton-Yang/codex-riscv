# Code Mode on RISC-V

The `.2` package includes `bin/codex` and `bin/codex-code-mode-host`. The CLI resolves the host beside its actual executable; no separate host command in PATH or runtime download is needed. The user launcher continues to supply `--no-daemon`.

Code Mode host support is enabled by default in this pinned CLI, while the Code Mode-only workflow is opt-in:

```sh
codex-riscv -c features.code_mode_only=true
```

This invocation does not rewrite existing settings. In a new disposable directory, ask Codex to create a small Python file and execute it. Authentication and model choice remain your existing configuration. Report installation status, kernel/bubblewrap versions and errors if a failure occurs; do not include login files or tokens.

## Source and build

The dependency-source release asset contains the exact adapted Codex and V8 sources, original source inputs for baseline dependencies, preserved notices, Chromium Rust source archives and replay patches. Build-only binary toolchains, sysroots and caches are excluded; this is source delivery, not a complete offline build environment.

The original CLI-only `scripts/build.sh` remains available. For the Code Mode host, read `scripts/build-code-mode.sh`: it uses a separately prepared work root with `src/codex-rs`, `vendor/v8` and the recorded cross-toolchain environment. The exact V8/Chromium source pins are in `licenses/code-mode/SOURCE-PROVENANCE.json`. Patches 0001 and 0004 apply at the Codex source root; 0002, 0003, 0005 and 0006 apply at the V8 crate root. The source asset already has those changes applied. The two-line baseline seccomp patch also remains applied.

No clean-room run of toolchain/source setup or bit-identical rebuild is claimed. Public mirror availability, Python/Clang compatibility, downloaded toolchain provenance and host dependencies must be checked for a new build environment. Do not substitute a no-sandbox V8 archive.

## Validation limits

Full-system Sv39 simulation passed with default ASLR and restricted rv64gc-oriented CPU settings. The user subsequently reported native program creation and exit → `/resume` → editing with `gpt-5.6-luna`; the later terminal transcript confirms native sandbox probes and rollback/re-upgrade with preserved model/program and correct subsequent execution. See [native validation](native-validation-v0.1.0-experimental.2.md) for the measured scope. The first unmodified candidate failed Oilpan reservation and is excluded from the release; the final artifact identity is recorded in `manifests/release-v0.1.0-experimental.2.json`.

V8 cage 32 GiB, full reservation 160 GiB, front/back guards 64 GiB each; low-Smi protection and mandatory refusal remain. Oilpan and PartitionAlloc placement adaptations preserve their sizes and checks, but their entropy and exploit resistance have not been certified. Complete TUI coverage, long-term stability, other boards/kernels, realtime runtime and explicit daemon/agents/remote-server support remain unvalidated.
