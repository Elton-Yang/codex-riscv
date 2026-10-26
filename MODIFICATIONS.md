# Changes from upstream

Current development pins and the canonical split patch series are recorded in
`manifests/upstream-lock.json` and `patches/upstream/`. The sections below describe
published historical artifacts; source-preparation tools do not modify them.
See `docs/upstream-maintenance.md` for upgrade and state-compatibility policy.

This is an unofficial adaptation/build project, not an OpenAI release.

- Upstream: https://github.com/openai/codex
- Exact upstream commit: `970111f6cb62cc02fe36a82ea7d71b37a2889c97`
- Change date: 2026-10-25 UTC.
- Modified file: `codex-rs/linux-sandbox/src/seccomp.rs`.
- Patch: `patches/0001-linux-seccomp-riscv64.patch` (two added lines).
- Change: select the existing `seccompiler::TargetArch::riscv64` variant for a
  RISC-V build. No syscall rules, filesystem rules, approval rules or sandbox
  enforcement paths were removed or disabled.
- No Cargo dependency or lockfile changes were made for the released binary.
- The build uses the upstream `dev-small` profile. It is not optimized for
  production and reports upstream's development version `codex-cli 0.0.0`.

The scripts, packaging, documentation and generated notice collections in this
repository were prepared with an AI assistant for this community experiment.
Their authorship is separate from the upstream OpenAI project. Existing
copyright and attribution notices are preserved; no endorsement is implied.

## Code Mode in v0.1.0-experimental.2 (2026-10-26)

The released CLI is byte-identical to `.1`. A separate host builds rusty_v8
152.2.0 / V8 15.2.124.1 from the pinned published crate and native source inputs.
The Codex runtime requires secure V8 initialization on RISC-V. V8 snapshot and
native constants agree on a 32 GiB cage, two unchanged 64 GiB guards and existing
typed-array masks. PartitionAlloc advisory placement is adapted for Sv39;
Oilpan gains a non-fixed exact-size aligned-reservation fallback without
changing its cage size, compression or red zone. These are experimental
placement adaptations, not an ASLR improvement or security certification.

Replay patches are under patches/code-mode/. Test-only low-Smi preinit and V8
intrinsics remain in a separate regression executable, never in the host.
The installer now checks both binaries before activating `.2`, preserving the
standalone launcher and existing user configuration. See the `.2` release notes
for actual emulated tests and pending physical-board confirmation.

## CLI compiler optimization in v0.1.0-experimental.3

No functional CLI source or dependency changes from the original CLI adaptation.
A new perf-cli profile inherits dev-small, sets opt-level=3, codegen-units=16,
LTO=false and retains debug-assertions=true, overflow-checks=true. The CLI is
stripped; the .2 sandbox-enabled Code Mode host is byte-identical. This is an
experiment for native A/B comparison, not a measured performance claim.
