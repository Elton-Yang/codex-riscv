#!/usr/bin/env python3
"""Persist and resume a synthetic conversation against guest-loopback SSE only."""
import http.server
import json
import os
from pathlib import Path
import subprocess
import threading
from cli_code_mode_smoke import MODEL, final_response


def run(codex, output):
    output.mkdir()
    workspace = output / 'workspace'
    workspace.mkdir()
    home = output / 'home'
    (home / '.codex').mkdir(parents=True)
    requests = []
    errors = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            try:
                assert not self.headers.get('Authorization')
                length = int(self.headers['Content-Length'])
                assert 0 < length <= 4 * 1024 * 1024
                data = json.loads(self.rfile.read(length))
                assert data['model'] == MODEL
                requests.append(data)
                assert len(requests) <= 2
                if len(requests) == 2:
                    assert 'PERSISTED_FIRST_REPLY_42' in json.dumps(data['input'])
                body = final_response('PERSISTED_FIRST_REPLY_42' if len(requests) == 1 else 'RESUMED_REPLY_43')
            except Exception as error:
                errors.append(str(error))
                body = final_response('FAILED')
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    provider = '{name="guest-resume",base_url="http://127.0.0.1:' + str(server.server_port) + '/v1",wire_api="responses",requires_openai_auth=false,supports_websockets=false,request_max_retries=0,stream_max_retries=0}'
    common = [str(codex), '--no-daemon', 'exec', '--ignore-user-config', '--ignore-rules',
              '--skip-git-repo-check', '--json', '--color', 'never', '--model', MODEL,
              '-c', 'model_provider="guest_mock"', '-c', 'model_providers.guest_mock=' + provider,
              '-c', 'features.code_mode_only=true', '-c', 'analytics.enabled=false',
              '-c', 'feedback.enabled=false', '-c', 'approval_policy="never"']
    env = {'HOME': str(home), 'CODEX_HOME': str(home / '.codex'), 'PATH': '/usr/bin:/bin',
           'SHELL': '/bin/sh', 'TERM': 'dumb', 'LANG': 'C.UTF-8', 'NO_PROXY': '127.0.0.1,localhost'}
    results = []
    try:
        for index, extra in enumerate([['--sandbox', 'workspace-write', 'Remember the synthetic number 42.'],
                                       ['resume', '--last', 'Continue the saved conversation with 43.']]):
            result = subprocess.run(common + extra, cwd=workspace, env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
            (output / f'run-{index}.stdout.jsonl').write_bytes(result.stdout)
            (output / f'run-{index}.stderr.txt').write_bytes(result.stderr)
            expected = b'PERSISTED_FIRST_REPLY_42' if index == 0 else b'RESUMED_REPLY_43'
            results.append(result.returncode == 0 and expected in result.stdout)
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
    record = {'pass': all(results) and len(requests) == 2 and not errors,
              'runs_pass': results, 'model_requests': len(requests), 'errors': errors,
              'scope': 'Actual CLI persists and resumes synthetic history; loopback SSE only, no real account/model; not TUI performance measurement'}
    (output / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    return record
