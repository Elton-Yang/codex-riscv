#!/usr/bin/env python3
"""Harness-only tests. These do NOT count as a real code-mode-host smoke pass."""

import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest

import stdio_protocol_smoke as smoke


class WireTests(unittest.TestCase):
    def test_length_prefix_is_little_endian_json_byte_length(self):
        message = {"type": "connection/hello", "supportedVersions": [1],
                   "requiredCapabilities": [], "optionalCapabilities": []}
        frame = smoke.encode_frame(message)
        self.assertEqual(struct.unpack("<I", frame[:4])[0], len(frame) - 4)
        self.assertEqual(json.loads(frame[4:]), message)

    def test_tool_definition_matches_v1_snake_case_payload(self):
        self.assertEqual(smoke.tool_definition("apply_patch", "freeform"), {
            "name": "apply_patch",
            "tool_name": {"name": "apply_patch", "namespace": None},
            "description": "Fixed smoke-test callback; not a general-purpose tool.",
            "kind": "freeform", "input_schema": None, "output_schema": None,
        })

    def test_clean_environment_does_not_inherit_api_key(self):
        old = os.environ.get("OPENAI_API_KEY")
        try:
            os.environ["OPENAI_API_KEY"] = "test-value-never-used"
            self.assertNotIn("OPENAI_API_KEY", smoke.isolated_env(Path("/tmp/test-only")))
        finally:
            if old is None:
                os.environ.pop("OPENAI_API_KEY", None)
            else:
                os.environ["OPENAI_API_KEY"] = old


class DelegateTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="host-harness-unit-")
        self.root = Path(self.directory.name)
        self.delegate = smoke.LimitedDelegate(self.root)
        self.delegate.active_tools = {"echo", "apply_patch", "exec_command"}

    def tearDown(self):
        self.directory.cleanup()

    @staticmethod
    def invocation(name, value, kind="function"):
        return {"tool_name": {"name": name, "namespace": None},
                "tool_kind": kind, "input": value}

    def test_exact_fixed_create_and_python_execute(self):
        self.delegate.invoke(self.invocation("echo", {"value": 42}))
        self.delegate.invoke(self.invocation("apply_patch", smoke.PATCH, "freeform"))
        result = self.delegate.invoke(self.invocation("exec_command", {"cmd": "python3 smoke.py"}))
        self.assertEqual(result, {"exit_code": 0, "output": "riscv-code-mode-ok\n"})
        self.assertEqual((self.root / "smoke.py").read_text(), smoke.PYTHON_TEXT)

    def test_rejects_modified_patch_and_never_writes_outside_test_file(self):
        for replacement in ("../escape.py", "/tmp/escape.py", "other.py"):
            with self.assertRaises(smoke.SmokeFailure):
                self.delegate.invoke(self.invocation(
                    "apply_patch", smoke.PATCH.replace("smoke.py", replacement), "freeform"))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_rejects_general_shell_and_extra_arguments(self):
        for value in ({"cmd": "touch unwanted"}, {"cmd": "python3 smoke.py", "tty": True},
                      {"cmd": "python3 smoke.py; echo extra"}):
            with self.assertRaises(smoke.SmokeFailure):
                self.delegate.invoke(self.invocation("exec_command", value))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_rejects_changed_file_before_python_execution(self):
        (self.root / "smoke.py").write_text('raise RuntimeError("not permitted")\n')
        with self.assertRaises(smoke.SmokeFailure):
            self.delegate.invoke(self.invocation("exec_command", {"cmd": "python3 smoke.py"}))

    def test_rejects_unknown_or_inactive_tools(self):
        self.delegate.active_tools = {"echo"}
        for name in ("exec_command", "delete_everything"):
            with self.assertRaises(smoke.SmokeFailure):
                self.delegate.invoke(self.invocation(name, {}))


class TransportFailureTests(unittest.TestCase):
    def run_bad_peer(self, python_source, timeout=3):
        with tempfile.TemporaryDirectory(prefix="host-transport-unit-") as directory:
            client = smoke.ProtocolClient(
                [sys.executable, "-I", "-S", "-c", python_source],
                Path(directory), timeout,
            )
            try:
                with self.assertRaises(smoke.SmokeFailure):
                    client.read_message()
            finally:
                client.cleanup()
            self.assertIsNotNone(client.child.poll())

    def test_peer_timeout_terminates_child(self):
        self.run_bad_peer("import time; time.sleep(30)", timeout=0.2)

    def test_short_frame_is_rejected(self):
        self.run_bad_peer("import os; os.write(1, b'\\x08\\x00\\x00\\x00{}')")

    def test_invalid_json_is_rejected(self):
        self.run_bad_peer("import os; os.write(1, b'\\x01\\x00\\x00\\x00x')")

    def test_oversized_frame_is_rejected_without_allocating_payload(self):
        self.run_bad_peer("import os; os.write(1, b'\\xff\\xff\\xff\\xff')")

    def test_split_valid_frame_is_read(self):
        with tempfile.TemporaryDirectory(prefix="host-transport-unit-") as directory:
            payload = {"type": "connection/ready", "selectedVersion": 1, "capabilities": []}
            frame = smoke.encode_frame(payload)
            source = f"import os,time; os.write(1,{frame[:2]!r}); time.sleep(.02); os.write(1,{frame[2:]!r})"
            client = smoke.ProtocolClient(
                [sys.executable, "-I", "-S", "-c", source], Path(directory), 3
            )
            try:
                self.assertEqual(client.read_message(), payload)
            finally:
                client.cleanup()


if __name__ == "__main__":
    unittest.main()
