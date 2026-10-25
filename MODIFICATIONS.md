# Changes from upstream

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
