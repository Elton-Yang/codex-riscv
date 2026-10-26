# v0.1.0-experimental.3: optimized CLI candidate

This prerelease enables Rust compiler optimization for the main CLI while reusing the byte-identical, sandbox-enabled Code Mode host from `.2`. It is intended for board-side comparison of startup and session-resume responsiveness. **Native speedup has not been measured; no specific performance improvement is claimed.**

本实验版优化主 CLI，沿用 `.2` 的原始 Code Mode host。目标是比较启动与 `/resume` 选中会话后的响应。真实开发板性能、交互恢复行为仍需用户验证，不承诺加速幅度。

## Build changes

- Same upstream commit `970111f6cb62cc02fe36a82ea7d71b37a2889c97`, original CLI Cargo.lock, dependency versions and two-line RISC-V seccomp adaptation.
- New `perf-cli` profile inherits `dev-small`: `opt-level=3`, 16 codegen units, LTO off, debug assertions and overflow checks retained. This isolates compiler optimization without enabling release-only updater/startup branches.
- CLI remains stripped RISC-V RVC / LP64D PIE, glibc ≥ 2.39, with the same expected dynamic library names. Its upstream version still reports `codex-cli 0.0.0`; use installer `status` to identify `.3`.
- CLI size is 345,346,040 bytes, about 9.8% larger than `.2`; optimization/inlining can increase code size, so SD-card cold-start performance may not improve. No size reduction is claimed.
- Code Mode host SHA256 is unchanged: `833501f801ae9b640ec9aa725fd0c62f03062e4faf729397a82136a8841f3f88`. V8 remains the previously validated debug build. Cage, guards, pointer compression, seccomp, fail-closed behavior and standalone launcher are retained.

The exact build profile, source hashes, artifact identity and validation evidence are under `docs/performance-evidence/` and `manifests/release-v0.1.0-experimental.3.json`. `scripts/build-cli-performance.sh` rebuilds from prepared source/toolchain inputs; no clean-room setup or bit-identical reproduction is claimed.

## Validation

The actual optimized CLI and unchanged adjacent host passed a full-system restricted-ISA Sv39 test: real apply_patch created a Python file and real exec_command ran it successfully; `Seccomp=2`, `NoNewPrivs=1` and denial of an outside-workspace canary were observed. Only model HTTP/SSE responses were simulated on guest loopback; there was no external NIC, real account or model API call.

Additional correctness checks and installer smoke results are recorded in [validation details](performance.md). These emulated results are not native performance measurements. Historical `.2` native creation/run/resume/edit, sandbox and rollback results remain documented separately; they are not automatically `.3` native passes.

## Update and compare on your board

Re-download and inspect the existing installer, then:

```sh
sh install-codex-riscv.sh upgrade --command codex
sh install-codex-riscv.sh status
codex -c features.code_mode_only=true
```

Use the same terminal, SD card and saved conversation to compare `.2` with `.3`, especially the delay between selecting a session and the conversation becoming editable. Record several trials separately from the first cold launch. Keep security settings unchanged. See [comparison instructions](performance.md).

登录信息、模型设置和程序继续沿用。先退出所有 Codex 会话，再升级；需要对比旧版时用安装器回滚，比较完成后再次升级。程序版本回滚不撤销会话或项目修改，建议使用独立测试会话。

Pre-publication installer checks: 64 regressions passed; actual `.2`/`.3` archives passed QEMU upgrade, rollback, configuration preservation, command migration, helper dispatch, bare onboarding and uninstall smoke. Both binaries and exact source inputs were hash-verified before upload.
