#!/usr/bin/env python3
"""Actual CLI -> adjacent host -> real tool handlers, with loopback-only mock SSE.

Run inside the disposable network-disabled Sv39 guest. This does not call a
model or use account credentials. The SSE service supplies predetermined calls;
it does not implement/fake apply_patch, exec_command, or the Code Mode host.
"""
import argparse
import errno
import hashlib
import http.server
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import traceback

MODEL = "gpt-5.6-luna"  # Unmodified metadata bundled in pinned Codex.
MARKER = "CODEX_RISCV_REAL_PYTHON_OK:42"
FINAL = "CLI_CODE_MODE_SMOKE_OK"
MAX_BODY = 4 * 1024 * 1024


def sse(events):
    return "".join("event: " + event["type"] + "\ndata: " + json.dumps(event) + "\n\n"
                   for event in events).encode()


def completed(response_id):
    return {"type": "response.completed", "response": {"id": response_id,
        "usage": {"input_tokens": 0, "input_tokens_details": None,
                  "output_tokens": 0, "output_tokens_details": None, "total_tokens": 0}}}


def tool_response(response_id, call_id, code):
    return sse([{"type": "response.created", "response": {"id": response_id}},
                {"type": "response.output_item.done", "item": {
                    "type": "custom_tool_call", "call_id": call_id,
                    "name": "exec", "input": code}}, completed(response_id)])


def final_response(message):
    return sse([{"type": "response.output_item.done", "item": {
        "type": "message", "role": "assistant", "id": "msg-final",
        "content": [{"type": "output_text", "text": message}]}}, completed("resp-final")])


def text_of(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(text_of(item) for item in value)
    if isinstance(value, dict):
        if value.get("success") is False:
            raise AssertionError("tool explicitly reported failure: " + json.dumps(value))
        for key in ["text", "content", "output"]:
            if key in value:
                return text_of(value[key])
    raise AssertionError("unexpected tool-output wire shape: " + repr(value))


def call_output(request, call_id):
    matches = [item for item in request.get("input", []) if isinstance(item, dict)
               and item.get("type") == "custom_tool_call_output"
               and item.get("call_id") == call_id]
    if len(matches) != 1:
        raise AssertionError("expected exactly one custom output for " + call_id)
    return text_of(matches[0]["output"])


def has_named_tool(value, name):
    if isinstance(value, dict):
        return value.get("name") == name or any(has_named_tool(v, name) for v in value.values())
    if isinstance(value, list):
        return any(has_named_tool(v, name) for v in value)
    return False


def python_program(canary):
    # The only attempted out-of-workspace write is in this harness's disposable
    # guest-owned canary directory. No user/host files or network are probed.
    return ("import errno, json\n"
            "from pathlib import Path\n"
            "status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)\n"
            "seccomp = int(status['Seccomp'].strip())\n"
            "no_new_privs = int(status['NoNewPrivs'].strip())\n"
            "denied = False\n"
            "try:\n"
            f"    Path({str(canary)!r}).write_text('unexpected sandbox escape')\n"
            "except OSError as error:\n"
            "    denied = error.errno in (errno.EPERM, errno.EACCES, errno.EROFS)\n"
            "assert seccomp == 2, ('Seccomp', seccomp)\n"
            "assert no_new_privs == 1, ('NoNewPrivs', no_new_privs)\n"
            "assert denied, 'outside-workspace write was not denied'\n"
            f"print({MARKER!r})\n"
            "print(json.dumps({'seccomp': seccomp, 'no_new_privs': no_new_privs, 'outside_write_denied': denied}, sort_keys=True))\n")


def make_patch(program):
    return "*** Begin Patch\n*** Add File: smoke.py\n" + "".join("+" + line + "\n" for line in program.splitlines()) + "*** End Patch\n"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class Scenario:
    def __init__(self, workspace, output_dir):
        self.workspace = workspace
        self.output_dir = output_dir
        self.canary = output_dir / "outside-workspace-canary" / "denied.txt"
        self.canary.parent.mkdir()
        self.program = python_program(self.canary)
        self.requests = []
        self.errors = []
        self.outputs = {}
        self.lock = threading.Lock()
        self.finished = False

    def response(self, request):
        with self.lock:
            self.requests.append(request)
            index = len(self.requests)
            (self.output_dir / f"request-{index}.json").write_text(json.dumps(request, indent=2) + "\n")
            if request.get("model") != MODEL:
                raise AssertionError("unexpected model identity (no metadata overrides allowed)")
            if index == 1:
                tools = [request.get("tools", [])] + [item.get("tools", []) for item in request.get("input", [])
                                                    if isinstance(item, dict) and item.get("type") == "additional_tools"]
                if not has_named_tool(tools, "exec"):
                    raise AssertionError("actual request did not expose Code Mode exec")
                if (self.workspace / "smoke.py").exists():
                    raise AssertionError("fixture already exists before real apply_patch")
                code = "// @exec: {\"yield_time_ms\": 120000, \"max_output_tokens\": 2000}\ntext(await tools.apply_patch(" + json.dumps(make_patch(self.program)) + "));\n"
                return tool_response("resp-create", "cli-create", code)
            if index == 2:
                self.outputs["create"] = call_output(request, "cli-create")
                if (self.workspace / "smoke.py").read_text() != self.program:
                    raise AssertionError("real apply_patch did not write exact Python source")
                code = r'''// @exec: {"yield_time_ms": 120000, "max_output_tokens": 3000}
let result = await tools.exec_command({cmd: "python3 smoke.py", shell: "/bin/sh", login: false, tty: false, yield_time_ms: 10000, max_output_tokens: 2000});
let output = result.output || "";
for (let i = 0; result.session_id != null && i < 6; i++) {
  result = await tools.write_stdin({session_id: result.session_id, chars: "", yield_time_ms: 1000, max_output_tokens: 2000});
  output += result.output || "";
}
if (result.session_id != null) throw new Error("Python process did not complete within bounded test");
text(JSON.stringify({exit_code: result.exit_code, output}));
'''
                return tool_response("resp-run", "cli-run", code)
            if index == 3:
                self.outputs["run"] = call_output(request, "cli-run")
                lines = self.outputs["run"].splitlines()
                results = []
                for line in lines:
                    try:
                        item = json.loads(line)
                    except (ValueError, TypeError):
                        continue
                    if isinstance(item, dict) and "exit_code" in item and "output" in item:
                        results.append(item)
                if len(results) != 1 or results[0]["exit_code"] != 0:
                    raise AssertionError("Python did not return exactly one successful structured result: " + self.outputs["run"])
                result = results[0]
                if MARKER not in result["output"]:
                    raise AssertionError("missing real Python execution marker")
                expected = {"seccomp": 2, "no_new_privs": 1, "outside_write_denied": True}
                reports = []
                for line in result["output"].splitlines():
                    try:
                        report = json.loads(line)
                    except ValueError:
                        continue
                    if report == expected:
                        reports.append(report)
                if len(reports) != 1:
                    raise AssertionError("missing exact real process sandbox status report")
                if self.canary.exists():
                    raise AssertionError("outside-workspace canary was written")
                self.finished = True
                return final_response(FINAL)
            raise AssertionError("unexpected additional model request")


def make_handler(scenario):
    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_args):
            pass

        def do_GET(self):
            scenario.errors.append("unexpected GET " + self.path)
            self.send_error(404)

        def do_POST(self):
            try:
                if self.path != "/v1/responses":
                    raise AssertionError("unexpected mock endpoint " + self.path)
                if self.headers.get("Authorization"):
                    raise AssertionError("test must not transmit any account credential")
                if self.headers.get("Content-Encoding") not in (None, "identity"):
                    raise AssertionError("unexpected request compression " + self.headers["Content-Encoding"])
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_BODY:
                    raise AssertionError("invalid HTTP body length")
                request = json.loads(self.rfile.read(length))
                body = scenario.response(request)
            except Exception:
                scenario.errors.append(traceback.format_exc())
                body = final_response("CLI_CODE_MODE_SMOKE_FAILED")
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            self.wfile.flush()
            self.close_connection = True
    return Handler


def run(args):
    codex = args.codex.resolve(strict=True)
    host = codex.with_name("codex-code-mode-host")
    if not host.is_file() or not os.access(host, os.X_OK):
        raise AssertionError("real adjacent executable host is required")
    if args.output_dir.exists():
        raise AssertionError("output directory must be new; preserve prior run evidence")
    args.output_dir.mkdir(parents=True)
    output_dir = args.output_dir.resolve()
    cpuinfo = Path("/proc/cpuinfo").read_text()
    mmus = [line.split(":", 1)[1].strip() for line in cpuinfo.splitlines()
            if ":" in line and line.split(":", 1)[0].strip() == "mmu"]
    identity = {"uname": list(os.uname()), "mmu_modes": mmus,
                "randomize_va_space": int(Path("/proc/sys/kernel/randomize_va_space").read_text()),
                "cpuinfo": cpuinfo}
    (output_dir / "guest.json").write_text(json.dumps(identity, indent=2) + "\n")
    if os.uname().machine != "riscv64" or not mmus or set(mmus) != {"sv39"}:
        raise AssertionError("this acceptance harness requires actual full-system RISC-V Sv39")
    if identity["randomize_va_space"] != 2:
        raise AssertionError("acceptance requires unchanged default ASLR=2")
    workspace = output_dir / "workspace"
    workspace.mkdir()
    home = output_dir / "home"
    home.mkdir()
    codex_home = home / ".codex"
    codex_home.mkdir()
    scenario = Scenario(workspace, output_dir)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), make_handler(scenario))
    server.daemon_threads = True
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    provider = {"name": "guest-loopback-test", "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                "wire_api": "responses", "requires_openai_auth": False,
                "supports_websockets": False, "request_max_retries": 0, "stream_max_retries": 0}
    provider_toml = "{" + ",".join(k + "=" + json.dumps(v) for k, v in provider.items()) + "}"
    command = [str(codex), "--no-daemon", "exec", "--ignore-user-config", "--ignore-rules", "--ephemeral",
               "--skip-git-repo-check", "--json", "--color", "never", "--sandbox", "workspace-write",
               "--model", MODEL, "--cd", str(workspace), "-c", 'model_provider="guest_mock"',
               "-c", "model_providers.guest_mock=" + provider_toml,
               "-c", "features.code_mode_only=true", "-c", "features.unified_exec=true",
               "-c", 'approval_policy="never"', "-c", "analytics.enabled=false",
               "-c", "feedback.enabled=false",
               "Create smoke.py and run it through the Code Mode tools. This is a local integration test."]
    environment = {"PATH": "/usr/bin:/bin", "HOME": str(home), "CODEX_HOME": str(codex_home),
                   "SHELL": "/bin/sh", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "TERM": "dumb",
                   "TMPDIR": "/tmp", "NO_PROXY": "127.0.0.1,localhost"}
    (output_dir / "invocation.json").write_text(json.dumps({"argv": command, "environment": environment,
        "codex_sha256": sha256(codex), "host_sha256": sha256(host)}, indent=2) + "\n")
    process = subprocess.Popen(command, cwd=workspace, env=environment,
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, start_new_session=True)
    timeout = False
    try:
        stdout, stderr = process.communicate(timeout=args.timeout)
    except subprocess.TimeoutExpired:
        timeout = True
        os.killpg(process.pid, signal.SIGKILL)
        stdout, stderr = process.communicate()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
    (output_dir / "cli.stdout.jsonl").write_bytes(stdout)
    (output_dir / "cli.stderr.txt").write_bytes(stderr)
    ok = (not timeout and process.returncode == 0 and scenario.finished and not scenario.errors
          and len(scenario.requests) == 3 and not scenario.canary.exists()
          and (workspace / "smoke.py").read_text() == scenario.program)
    result = {"pass": ok, "timeout": timeout, "cli_exit_code": process.returncode,
              "model_requests": len(scenario.requests), "scenario_finished": scenario.finished,
              "errors": scenario.errors, "tool_outputs": scenario.outputs,
              "scope": "Actual CLI and adjacent host, real apply_patch and exec_command handlers, genuine guest Python, workspace-write sandbox checks; only model SSE is mocked. No account or model API call.",
              "limits": "Full-system emulation is not physical hardware or comprehensive sandbox/exploit-resistance certification."}
    (output_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    if args.timeout < 1 or args.timeout > 1800:
        parser.error("timeout must be between1 and1800 seconds")
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
