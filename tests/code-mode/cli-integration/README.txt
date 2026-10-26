Account-free actual CLI / Code Mode integration test

The Python harness replaces ONLY the model's HTTP/SSE responses. It does not
replace the Codex CLI, Code Mode host, apply_patch handler, exec_command handler,
Python interpreter, or Linux sandbox. It must run inside the disposable guest
with no external NIC. The HTTP server binds127.0.0.1 only; the child receives a
fresh HOME/CODEX_HOME and no credential variables. Any Authorization header is
rejected. Bundled gpt-5.6-luna metadata is used unchanged; no model catalog or
metadata override is supplied.

Required guest inputs
- Actual pinned Codex ELF at /codex.
- Actual validated RISC-V codex-code-mode-host ELF adjacent at
  /codex-code-mode-host. Automatic adjacent discovery is exercised.
- Official Debian Python3.13 interpreter and standard library, bubblewrap,
  and their authenticated runtime dependency closure.
- BusyBox /bin/sh, proc/sys/dev/tmp support, and only guest loopback enabled.
  No Bash, pip, account, model service, public network, or security bypass.

Run in a fresh guest/output directory
  python3 /cli-integration/cli_code_mode_smoke.py \
    --codex /codex --output-dir /cli-smoke-results --timeout 600

The raw CLI is invoked with --no-daemon, matching the existing installer
wrapper's standalone behavior; sandboxed internal dispatch is left unchanged.
The harness asks for workspace-write and approval_policy=never. It does not
silently retry with unrestricted access or disable sandbox mechanisms.

Acceptance requirements
1. First real request exposes Code Mode exec using the expected bundled model.
2. Real tools.apply_patch creates exact smoke.py bytes in a new workspace.
3. Real tools.exec_command runs genuine `python3 smoke.py` with BusyBox sh,
   login=false and tty=false. The program prints a42 marker only after checking
   /proc/self/status Seccomp=2, NoNewPrivs=1, and refusal to write the dedicated
   guest-owned canary outside the workspace. No host/user file is probed.
4. The next actual CLI request includes tool exit0, exact marker and sandbox
   status report; no canary file exists. Exactly3 model requests occur.
5. CLI exits0, no timeout/handler error, and exact created file remains.

Evidence
All invocation arguments/clean environment/hashes, request JSON, CLI stdout and
stderr, final result.json, and smoke.py are saved below /cli-smoke-results.
The guest runner exports this bounded directory after completion. Credentials
and personal workspace files are never included.

Limits
- This is emulated Sv39 Linux, not physical RISC-V hardware certification.
- Functional checks and these kernel status/access probes are not a complete
  sandbox audit or exploit-resistance certification.
- The11 harness-only unit tests and raw CLI --help parser check are preparation
  checks, not a claim that the actual integration has run or passed.
- Upstream source patterns: core/tests/suite/code_mode.rs
  code_mode_only_can_call_nested_tools and
  code_mode_can_apply_patch_via_nested_tool; exec/tests/suite/apply_patch.rs
  uses a custom loopback Responses provider without OpenAI auth.
