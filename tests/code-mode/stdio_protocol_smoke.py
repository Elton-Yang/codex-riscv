#!/usr/bin/env python3
"""Account-free smoke of a real codex-code-mode-host through its stdio protocol.

Usage: python3 stdio_protocol_smoke.py --timeout 180 -- /absolute/host [args...]
The command may instead start with QEMU and its explicit target/sysroot arguments.

Wire format is pinned to Codex 970111f6cb62cc02fe36a82ea7d71b37a2889c97:
  codex-rs/code-mode-protocol/src/host/{codec,message,payload}.rs
  codex-rs/code-mode-host/tests/stdio.rs:
    remote_session_persists_values_forwards_delegates_and_controls_cells

This tests the actual supplied host and JavaScript runtime, but implements a
deliberately tiny TEST delegate, NOT Codex's shell/apply_patch policy handlers.
Only an exact fixed patch and an exact fixed Python command are accepted. The
Python interpreter runs on the test runner's architecture, not necessarily the
host binary's architecture. No account, model API, or user workspace is used.
Passing this does not establish OS sandbox enforcement or full CLI integration.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import selectors
import signal
import struct
import subprocess
import sys
import tempfile
import time

MAX_FRAME_BYTES = 64 * 1024 * 1024
SESSION = "riscv-smoke-session"
PYTHON_TEXT = 'print("riscv-code-mode-ok")\n'
PATCH = (
    "*** Begin Patch\n*** Add File: smoke.py\n"
    '+print("riscv-code-mode-ok")\n*** End Patch\n'
)


class SmokeFailure(RuntimeError):
    """A protocol, runtime, timeout, or expected-output check failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def encode_frame(value: dict) -> bytes:
    payload = json.dumps(value, separators=(",", ":")).encode("utf-8")
    require(len(payload) <= MAX_FRAME_BYTES, "outgoing frame is too large")
    return struct.pack("<I", len(payload)) + payload


def tool_definition(name: str, kind: str = "function") -> dict:
    return {
        "name": name,
        "tool_name": {"name": name, "namespace": None},
        "description": "Fixed smoke-test callback; not a general-purpose tool.",
        "kind": kind,
        "input_schema": None,
        "output_schema": None,
    }


def isolated_env(root: Path) -> dict[str, str]:
    # Intentionally do not inherit credentials, telemetry endpoints, proxies,
    # library preload hooks, or the caller's Codex configuration.
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(root),
        "CODEX_HOME": str(root / ".codex"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TZ": "UTC",
        "TERM": "dumb",
    }


class LimitedDelegate:
    def __init__(self, root: Path):
        self.root = root
        self.calls: list[str] = []
        self.notifications: list[str] = []
        self.active_tools: set[str] = set()

    def invoke(self, invocation: dict) -> dict:
        name = invocation.get("tool_name", {})
        require(name.get("namespace") is None, "unexpected tool namespace")
        tool = name.get("name")
        require(tool in self.active_tools, f"unexpected callback tool: {tool!r}")
        expected_kind = "freeform" if tool == "apply_patch" else "function"
        require(invocation.get("tool_kind") == expected_kind, "wrong tool kind")
        value = invocation.get("input")
        path = self.root / "smoke.py"
        if tool == "echo":
            require(value == {"value": 42}, "echo input did not preserve stored JS value")
            result = {"value": 42}
        elif tool == "apply_patch":
            require(value == PATCH, "rejected anything other than the exact fixed patch")
            require(not path.exists(), "smoke.py unexpectedly already exists")
            # Exclusive create prevents following/overwriting an existing path.
            with path.open("x", encoding="utf-8") as output:
                output.write(PYTHON_TEXT)
            result = {"created": "smoke.py"}
        elif tool == "exec_command":
            require(value == {"cmd": "python3 smoke.py"}, "rejected non-fixed command")
            require(path.is_file() and not path.is_symlink(), "missing regular test file")
            require(path.read_text(encoding="utf-8") == PYTHON_TEXT, "test file content changed")
            # Never execute a model-supplied shell string or arbitrary Python.
            completed = subprocess.run(
                [sys.executable, "-I", "-S", str(path)],
                cwd=self.root,
                env=isolated_env(self.root),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            require(completed.returncode == 0, f"fixed Python failed: {completed.stderr}")
            require(completed.stdout == "riscv-code-mode-ok\n", "fixed Python output mismatch")
            require(completed.stderr == "", "fixed Python unexpectedly wrote stderr")
            result = {"exit_code": completed.returncode, "output": completed.stdout}
        else:
            raise SmokeFailure(f"unknown delegate tool: {tool!r}")
        self.calls.append(tool)
        return result


class ProtocolClient:
    def __init__(self, command: list[str], root: Path, timeout: float):
        self.deadline = time.monotonic() + timeout
        self.delegate = LimitedDelegate(root)
        self.child = subprocess.Popen(
            command,
            cwd=root,
            env=isolated_env(root),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            bufsize=0,
        )
        self.selector = selectors.DefaultSelector()
        for label, stream in (("stdout", self.child.stdout), ("stderr", self.child.stderr)):
            os.set_blocking(stream.fileno(), False)
            self.selector.register(stream, selectors.EVENT_READ, label)
        self.buffer = bytearray()
        self.stderr = bytearray()
        self.pending: dict[tuple[str, int | None], dict] = {}
        self.closed_cells: set[str] = set()
        self.delegate_ids: set[int] = set()
        self.next_id = 1
        self.active_call_id: str | None = None
        self.stdout_eof = False

    def remaining(self) -> float:
        remaining = self.deadline - time.monotonic()
        require(remaining > 0, "host protocol smoke exceeded overall timeout")
        return remaining

    def send(self, value: dict) -> None:
        self.remaining()
        frame = encode_frame(value)
        # Smoke frames are small. Host stdin is never used for arbitrary input.
        try:
            self.child.stdin.write(frame)
            self.child.stdin.flush()
        except (BrokenPipeError, OSError) as error:
            raise SmokeFailure(f"host stdin closed: {error}") from error

    def read_message(self) -> dict:
        while True:
            if len(self.buffer) >= 4:
                size = struct.unpack("<I", self.buffer[:4])[0]
                require(size <= MAX_FRAME_BYTES, "host frame exceeds upstream maximum")
                if len(self.buffer) >= size + 4:
                    payload = bytes(self.buffer[4 : size + 4])
                    del self.buffer[: size + 4]
                    try:
                        message = json.loads(payload)
                    except (UnicodeDecodeError, json.JSONDecodeError) as error:
                        raise SmokeFailure(f"invalid host JSON: {error}") from error
                    require(isinstance(message, dict), "host message is not an object")
                    return message
            require(not self.stdout_eof, f"host stdout closed mid-protocol; exit={self.child.poll()}")
            ready = self.selector.select(self.remaining())
            require(bool(ready), "timed out waiting for host output")
            for key, _ in ready:
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    self.selector.unregister(key.fileobj)
                    if key.data == "stdout":
                        self.stdout_eof = True
                elif key.data == "stdout":
                    self.buffer.extend(chunk)
                elif len(self.stderr) < 65536:
                    self.stderr.extend(chunk[: 65536 - len(self.stderr)])

    def pump(self) -> None:
        message = self.read_message()
        kind = message.get("type")
        if kind == "delegate/request":
            require(message.get("sessionId") == SESSION, "wrong callback session")
            callback_id = message["id"]
            require(callback_id not in self.delegate_ids, "duplicate delegate request ID")
            self.delegate_ids.add(callback_id)
            request = message["request"]
            if request.get("type") == "tool/invoke":
                result = self.delegate.invoke(request["invocation"])
                value = {"type": "tool/result", "result": result}
            elif request.get("type") == "notification/send":
                require(request.get("callId") == self.active_call_id, "wrong notification call ID")
                require(request.get("text") == "smoke-notice", "unexpected notification text")
                self.delegate.notifications.append(request["text"])
                value = {"type": "notification/delivered"}
            else:
                raise SmokeFailure(f"unexpected callback: {request!r}")
            self.send({"type": "delegate/response", "id": callback_id,
                       "result": {"status": "ok", "value": value}})
        elif kind == "cell/closed":
            require(message.get("sessionId") == SESSION, "wrong closed-cell session")
            self.closed_cells.add(message["cellId"])
        elif kind in ("operation/response", "execute/initialResponse", "connection/ready"):
            key = (kind, message.get("id"))
            require(key not in self.pending, f"duplicate response: {key}")
            self.pending[key] = message
        else:
            raise SmokeFailure(f"unexpected host message: {message!r}")

    def receive(self, kind: str, request_id: int | None = None) -> dict:
        key = (kind, request_id)
        while key not in self.pending:
            self.pump()
        message = self.pending.pop(key)
        if kind == "connection/ready":
            return message
        result = message["result"]
        require(result.get("status") == "ok", f"host returned error: {result!r}")
        return result["value"]

    def request(self, request: dict) -> tuple[int, dict]:
        request_id = self.next_id
        self.next_id += 1
        self.send({"type": "operation/request", "id": request_id, "request": request})
        return request_id, self.receive("operation/response", request_id)

    def execute(self, source: str, tools: list[dict] | None = None,
                yield_ms: int = 1000, terminal: bool = True) -> tuple[str, dict]:
        tools = tools or []
        self.delegate.active_tools = {tool["name"] for tool in tools}
        self.active_call_id = f"call-{self.next_id}"
        request_id, started = self.request({
            "method": "session/execute", "sessionId": SESSION,
            "request": {
                "tool_call_id": self.active_call_id,
                "enabled_tools": tools,
                "source": source,
                "yield_time_ms": yield_ms,
                "max_output_tokens": 4096,
            },
        })
        require(started.get("type") == "execution/started", "execution was not admitted")
        cell_id = started["cellId"]
        response = self.receive("execute/initialResponse", request_id)
        while terminal and "Yielded" in response:
            response = self.wait_or_terminate("session/wait", cell_id)
        require(len(response) == 1, "malformed runtime response")
        value = next(iter(response.values()))
        require(value.get("cell_id") == cell_id, "runtime returned wrong cell ID")
        require(isinstance(value.get("code_mode_host_duration_ns"), int), "missing host duration")
        if terminal:
            require("Result" in response, f"execution did not complete: {response!r}")
            require(value.get("error_text") is None, f"JavaScript failed: {value.get('error_text')}")
        return cell_id, response

    def wait_or_terminate(self, method: str, cell_id: str) -> dict:
        operation = {"method": method, "sessionId": SESSION}
        if method == "session/wait":
            operation["request"] = {"cell_id": cell_id, "yield_time_ms": 1000}
        else:
            operation["cellId"] = cell_id
        _, response = self.request(operation)
        require(response.get("type") == "wait/completed", "unexpected wait/terminate reply")
        outcome = response["outcome"]
        require(len(outcome) == 1 and "LiveCell" in outcome, f"expected live cell: {outcome!r}")
        return outcome["LiveCell"]

    def cleanup(self) -> None:
        if self.child.stdin and not self.child.stdin.closed:
            self.child.stdin.close()
        if self.child.poll() is None:
            try:
                os.killpg(self.child.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                self.child.wait(timeout=2)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(self.child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                self.child.wait(timeout=5)
        self.selector.close()
        for stream in (self.child.stdout, self.child.stderr):
            stream.close()


def output_text(response: dict) -> list[str]:
    return [item["text"] for item in response["Result"]["content_items"]
            if item.get("type") == "input_text"]


def run_smoke(client: ProtocolClient) -> dict:
    client.send({"type": "connection/hello", "supportedVersions": [1],
                 "requiredCapabilities": [], "optionalCapabilities": []})
    hello = client.receive("connection/ready")
    require(hello.get("selectedVersion") == 1, "wrong protocol version")
    _, opened = client.request({"method": "session/open", "sessionId": SESSION})
    require(opened == {"type": "session/ready", "sessionId": SESSION}, "session did not open")

    _, arithmetic = client.execute('store("answer", 6 * 7); text(load("answer"));')
    require(output_text(arithmetic) == ["42"], f"arithmetic output mismatch: {arithmetic!r}")
    _, echo = client.execute(
        'const r = await tools.echo({value: load("answer")}); '
        'notify("smoke-notice"); text(r.value);',
        [tool_definition("echo")],
    )
    require(output_text(echo) == ["42"], "nested callback output mismatch")

    source = (
        f"await tools.apply_patch({json.dumps(PATCH)});\n"
        'const result = await tools.exec_command({cmd: "python3 smoke.py"});\n'
        'if (result.exit_code !== 0 || result.output !== "riscv-code-mode-ok\\n") '
        'throw Error("Python callback result mismatch");\n'
        'text(result.output.trim());'
    )
    _, python_result = client.execute(
        source, [tool_definition("apply_patch", "freeform"), tool_definition("exec_command")]
    )
    require(output_text(python_result) == ["riscv-code-mode-ok"], "Python callback roundtrip failed")
    require((client.delegate.root / "smoke.py").read_text(encoding="utf-8") == PYTHON_TEXT,
            "final Python file contents differ")
    require(client.delegate.calls == ["echo", "apply_patch", "exec_command"],
            f"unexpected tool call sequence: {client.delegate.calls!r}")
    require(client.delegate.notifications == ["smoke-notice"], "notification was not delivered")

    cell_id, pending = client.execute("await new Promise(() => {});", yield_ms=1, terminal=False)
    require("Yielded" in pending, "pending execution did not yield")
    require("Yielded" in client.wait_or_terminate("session/wait", cell_id), "wait did not yield")
    require("Terminated" in client.wait_or_terminate("session/terminate", cell_id),
            "pending execution did not terminate")
    _, closed = client.request({"method": "session/shutdown", "sessionId": SESSION})
    require(closed == {"type": "session/closed", "sessionId": SESSION}, "session did not close")
    client.child.stdin.close()
    try:
        exit_code = client.child.wait(timeout=min(10, client.remaining()))
    except subprocess.TimeoutExpired as error:
        raise SmokeFailure("host did not exit after clean EOF") from error
    require(exit_code == 0, f"host exit code was {exit_code}")
    return {
        "status": "PASS",
        "protocol": 1,
        "checks": ["real host handshake", "JavaScript arithmetic", "store/load across cells",
                   "mock nested tool roundtrip", "notify callback", "fixed Python file creation",
                   "fixed host-native Python execution", "yield/wait/terminate", "clean shutdown"],
        "limits": ["test delegate, not Codex tool-policy handlers",
                   "not OS sandbox enforcement or full CLI integration",
                   "no account, model API, or user device used"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=180.0,
                        help="overall protocol deadline in seconds (default: 180)")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or args.timeout <= 0:
        parser.error("supply a positive timeout and a host command after --")
    with tempfile.TemporaryDirectory(prefix="codex-host-protocol-smoke-") as directory:
        client = None
        try:
            client = ProtocolClient(command, Path(directory), args.timeout)
            result = run_smoke(client)
            print(json.dumps(result, indent=2))
            return 0
        except (SmokeFailure, OSError, subprocess.SubprocessError, KeyError, TypeError) as error:
            print(json.dumps({"status": "FAIL", "error": str(error)}), file=sys.stderr)
            if client and client.stderr:
                print("Host stderr (at most 64 KiB):", file=sys.stderr)
                print(client.stderr.decode("utf-8", errors="replace"), file=sys.stderr)
            return 1
        finally:
            if client:
                client.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
