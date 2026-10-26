# Upstream alignment and upgrade policy

## Current pin

The authoritative current development input is [upstream-lock.json](../manifests/upstream-lock.json). It pins Codex `970111f6cb62cc02fe36a82ea7d71b37a2889c97` (development package version `0.0.0`), Rust 1.99.1, rusty_v8 152.2.0 / V8 15.2.124.1, target ABI, separate CLI/host build profiles, source-input checksums, patch order and expected prepared source trees.

Published `.1`, `.2` and `.3` manifests, archives, tags and checksums are historical immutable identities. Updating the development lock does not rewrite those records. The checked-in `manifests/rust-toolchain.toml` and `cargo-lock.sha256` are retained historical baseline artifacts; build scripts read the new lock. `install.sh` has a separate catalog of tested released archives, not a floating upstream source pin.

## Patch ownership

The canonical series is now [patches/upstream/](../patches/upstream/), whose exact hashes/order are in the lock:

| Layer | Commits |
| --- | --- |
| Codex CLI | RISC-V seccomp architecture selection |
| Codex Code Mode | Local exact V8 source/lock adjustment; mandatory secure initialization; separate test-only probes |
| V8 source build | Standard proxy-aware tool downloader |
| V8 runtime | Target/snapshot sandbox layout; PartitionAlloc advisory placement; Oilpan aligned reservation |

Historical `patches/code-mode/` files remain as published evidence, not a second editable active series. Do not disable sandboxing, reduce guards or accept insecure initialization to resolve an upgrade conflict. When upstream solves an issue, review the behavior and remove the obsolete patch together with its old expectation; do not automatically skip patch failures.

## Reproduce committed source trees

Use Python 3.11+ and Git. Source preparation never compiles, runs the candidate, installs packages, overwrites a destination or changes the active pin. Inputs must already be downloaded and authenticated. Existing local Codex repositories are used only as clone sources, preserving their dirty work. Every applied patch becomes an independent commit in a fresh repository.

```sh
python3 scripts/upstream.py check-lock
python3 scripts/upstream.py prepare --component cli \
  --codex-repo /absolute/path/to/local-codex-repository \
  --output /absolute/path/to/new-cli-work
```

The result is `<work>/src/codex-rs` with a clean adaptation commit on `riscv/current` above the pinned upstream commit. For the host:

```sh
python3 scripts/upstream.py prepare --component code-mode \
  --codex-repo /absolute/path/to/local-codex-repository \
  --v8-crate /absolute/path/to/v8-152.2.0.crate \
  --chromium-archives /absolute/path/to/chromium-rust-source-archives \
  --icu-data /absolute/path/to/icudtl.dat \
  --output /absolute/path/to/new-host-work
```

This creates independent Codex and V8 repositories. The V8 base is a synthetic import of the exact published crate, not the native V8 Git revision. It then commits the 51 authenticated Chromium Rust source archives and exact ICU data, followed by the V8 patches. Native upstream component identities remain in the provenance manifests. Binary toolchains, sysroots and environment scripts are not supplied or executed by source preparation; a full offline build environment still needs separate setup.

`source-state.json` records base, commit/tree identities, inputs and status. Repeating into a new directory must produce the same Git **trees**; synthetic commit timestamps may differ. Existing destinations are rejected rather than silently patched twice. A failure leaves a labeled report and the partial directory for review.

Before building:

```sh
python3 scripts/upstream.py verify-source --component cli --source /path/to/new-cli-work/src
python3 scripts/upstream.py verify-source --component code-mode --source /path/to/new-host-work/src
```

Verification requires dedicated clean repositories, the pinned upstream ancestor, exact expected files and full reviewed tree identities. Any committed extra changes or dirty source are rejected. Build-generated V8 files/toolchain directories can make a prepared repository dirty; isolate outputs and review generated inputs rather than bypassing verification. Source preparation has been tested locally; clean-room host/toolchain setup is not claimed.

Build scripts read target/profile/toolchain values from the lock. `build-cli-performance.sh` requires prepared committed CLI source and an unused output directory; `build-code-mode.sh` additionally needs an explicitly prepared `env.sh`. The old mutable recovery work copies remain preserved and are no longer the recommended verified build inputs.

## Discover and rehearse a candidate

```sh
python3 scripts/check-upstream.py --output /path/to/new-audit.json
```

This read-only command resolves the latest formal release tag to a full commit and compares its ancestry with the current pin. It never changes manifests, source, installer defaults or releases. Use immutable SHA values for all trials; review security fixes promptly, otherwise prefer formal releases over alpha/main snapshots. A formal tag is not automatically newer than our current development commit.

Fetch a selected SHA/tag into a separate local upstream cache, then rehearse CLI patch replay:

```sh
python3 scripts/upstream.py prepare --component cli \
  --codex-repo /path/to/upstream-cache.git \
  --candidate-commit FULL_40_CHARACTER_SHA \
  --output /path/to/new-candidate-work
```

The explicit candidate mode uses `riscv/rehearsal`, records `CANDIDATE_PATCH_REPLAY_ONLY`, inspects the candidate Rust/package/V8 versions and does **not** accept the current lock's source identity as candidate validation. Host candidate preparation is deliberately rejected: a changed V8/toolchain/lock needs a separately reviewed candidate lock, patch port and source provenance. CLI/host protocol compatibility must not be assumed across upstream commits. Build wrappers reject candidate source until it has been reviewed into a new lock.

### First rehearsal: 2026-10-26

The latest formal release observed was `rust-v0.164.0`, resolved to `6aaac694803004a63c6f393d153c96d22521a6b9`; the current main was still our pinned `970111f6…`. Their merge base was `342ed69a…`; current pin has 91 unique commits and stable has 1. Thus this is a branch alignment exercise, **not a forward upgrade**. CLI patch replay on stable passed, but no build/runtime/native upgrade was attempted. Current pin remains unchanged. See [audit](../manifests/upstream-audit-2026-10-26.json).

## Promote a new upstream baseline

1. Preserve the current release, dedicated source commits and backup inputs; use an `upgrade/<upstream-tag>-riscv` branch and fresh target/output directories.
2. Review upstream changes since the real merge base, Rust/lock/V8/native inputs, helper/CLI-host protocols and session database/rollout migrations. Keep candidate and installed user state separate.
3. Port patches as individual commits. Update the candidate lock's source checksums and expected trees only after reviewing all changes, not by copying observed hashes to silence a failure. Reconcile all selected dependencies, notices and source delivery.
4. Build both CLI and host against the same selected upstream version unless an explicit protocol check proves reuse safe. Run tool/helper/protocol tests; applicable V8/Sv39 positives, fail-closed negatives and native kernel probes; startup/resume regression and performance checks.
5. Test upgrade on synthetic **copies** of old configuration/session data. Confirm actual TUI resume, original model/settings and program edit/run. Rollback of binaries does not undo schema migrations; old binaries may not read new data. Document a restored-state rollback procedure or mark rollback unsupported until established. Never inspect real login secrets.
6. Package immutable artifacts and source/notice evidence, retain old downloads, update only the curated installer catalog after all required checks. Native user testing remains explicitly distinguished from emulation. An ancestry change alone is not release authorization.

Future naming can use `<upstream-version>-riscv.<revision>` once we choose a formal release baseline. Do not rename existing experimental tags or claim the current development commit is exactly 0.164.0.

## 中文摘要

统一清单固定当前输入，补丁逐项成为独立提交，准备脚本在新目录重放并校验完整源码树。每次上游升级使用独立分支、完整 SHA 和候选清单；先审查依赖、host 协议与会话数据库，再构建/验收，不能因补丁能应用就直接发布。当前最新正式版 0.164.0 与现有锚点分叉，本次只做了源码重放演练，继续保留已验证 `.3` 基线。

Local repeatability and rejection checks are summarized in [source replay validation](upstream-evidence/source-replay-validation.json). Eight tooling tests cover identity, safe extraction, failure recording and ancestry classification. Source/Cargo metadata replay passed; no new full cross-build or runtime validation was performed for this orchestration refactor.

The source-maintenance GitHub workflow checks lock/patch digests, tooling failure cases and shell syntax on changes to these files. It does not automatically update dependencies, run model requests, build releases or publish. Full source replay uses the separately authenticated inputs described above.
