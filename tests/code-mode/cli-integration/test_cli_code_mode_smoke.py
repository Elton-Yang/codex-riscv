"""Harness-only checks: no actual CLI, Code Mode host or sandbox pass is implied."""
import json
from pathlib import Path
import tempfile
import unittest
import cli_code_mode_smoke as smoke


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.scenario = smoke.Scenario(self.workspace, self.root)

    def first(self):
        return {"model": smoke.MODEL, "input": [{"type": "additional_tools", "tools": [
            {"type": "namespace", "name": "functions", "tools": [{"name": "exec", "type": "custom"}]}]}]}

    def output(self, call_id, value):
        return {"model": smoke.MODEL, "input": [{"type": "custom_tool_call_output",
                                                "call_id": call_id, "output": value}]}

    def prime(self):
        self.scenario.response(self.first())
        # Synthetic harness-only fixture; the real harness never writes smoke.py.
        (self.workspace / "smoke.py").write_text(self.scenario.program)
        self.scenario.response(self.output("cli-create", [{"type": "input_text", "text": "{}"}]))

    def final(self, report=None, code=0):
        if report is None:
            report = {"seccomp": 2, "no_new_privs": 1, "outside_write_denied": True}
        result = {"exit_code": code, "output": smoke.MARKER + "\n" + json.dumps(report) + "\n"}
        return self.output("cli-run", "Script completed\n" + json.dumps(result))

    def test_exact_three_stage_synthetic_acceptance(self):
        self.prime()
        self.assertIn(smoke.FINAL.encode(), self.scenario.response(self.final()))
        self.assertTrue(self.scenario.finished)

    def test_wrong_model_rejected(self):
        request = self.first()
        request["model"] = "invented"
        with self.assertRaises(AssertionError):
            self.scenario.response(request)

    def test_no_code_mode_tool_rejected(self):
        with self.assertRaises(AssertionError):
            self.scenario.response({"model": smoke.MODEL, "input": []})

    def test_preexisting_fixture_rejected(self):
        (self.workspace / "smoke.py").write_text("old")
        with self.assertRaises(AssertionError):
            self.scenario.response(self.first())

    def test_wrong_patch_bytes_rejected(self):
        self.scenario.response(self.first())
        (self.workspace / "smoke.py").write_text("wrong")
        with self.assertRaises(AssertionError):
            self.scenario.response(self.output("cli-create", "{}"))

    def test_nonzero_python_exit_rejected(self):
        self.prime()
        with self.assertRaises(AssertionError):
            self.scenario.response(self.final(code=1))

    def test_missing_seccomp_rejected(self):
        self.prime()
        with self.assertRaises(AssertionError):
            self.scenario.response(self.final({"seccomp": 0, "no_new_privs": 1, "outside_write_denied": True}))

    def test_outside_write_rejected(self):
        self.prime()
        self.scenario.canary.write_text("escape")
        with self.assertRaises(AssertionError):
            self.scenario.response(self.final())

    def test_explicit_failed_tool_rejected(self):
        with self.assertRaises(AssertionError):
            smoke.text_of({"success": False, "content": "failed"})

    def test_duplicate_output_rejected(self):
        request = self.output("cli-run", "ok")
        request["input"].append(dict(request["input"][0]))
        with self.assertRaises(AssertionError):
            smoke.call_output(request, "cli-run")

    def test_python_source_compiles_and_patch_roundtrip(self):
        compile(self.scenario.program, "smoke.py", "exec")
        patch = smoke.make_patch(self.scenario.program)
        recovered = "\n".join(line[1:] for line in patch.splitlines()[2:-1]) + "\n"
        self.assertEqual(recovered, self.scenario.program)


if __name__ == "__main__":
    unittest.main()
