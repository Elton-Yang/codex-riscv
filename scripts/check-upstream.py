#!/usr/bin/env python3
"""Read GitHub release/commit metadata; never changes pins, source or releases."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]


def api(endpoint):
    return json.loads(subprocess.check_output(['gh', 'api', endpoint], text=True))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, help='write a new audit file; refuses overwrite')
    args = p.parse_args()
    pin = json.loads((ROOT / 'manifests/upstream-lock.json').read_text())['codex']['commit']
    latest = api('repos/openai/codex/releases/latest')
    if latest['draft'] or latest['prerelease']:
        raise ValueError('Latest response is not a formal public release')
    ref = api('repos/openai/codex/git/ref/tags/' + quote(latest['tag_name'], safe=''))['object']
    for _ in range(8):
        if ref['type'] == 'commit':
            break
        if ref['type'] != 'tag':
            raise ValueError('Unexpected release tag object')
        ref = api('repos/openai/codex/git/tags/' + ref['sha'])['object']
    else:
        raise ValueError('Too many annotated tag levels')
    compare = api('repos/openai/codex/compare/' + pin + '...' + ref['sha'])
    main_sha = api('repos/openai/codex/git/ref/heads/main')['object']['sha']
    forward = compare['status'] == 'ahead'
    record = {'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'repository': 'openai/codex', 'current_pin': pin,
              'current_main_at_check': main_sha,
              'latest_stable': {'tag': latest['tag_name'], 'commit': ref['sha'],
                                'published_at': latest['published_at'],
                                'release_url': latest['html_url']},
              'compare_current_to_stable': {'status': compare['status'],
                       'stable_only_commits': compare['ahead_by'],
                       'current_only_commits': compare['behind_by'],
                       'merge_base': compare['merge_base_commit']['sha']},
              'forward_candidate_available': forward,
              'decision': 'REVIEW_FORWARD_CANDIDATE' if forward else 'KEEP_CURRENT_PIN',
              'note': 'Read-only discovery. A forward candidate still requires source, dependency, state-schema, security, functional and native review; no automatic upgrade.'}
    if args.output:
        with args.output.open('x', encoding='utf-8') as target:
            json.dump(record, target, indent=2)
            target.write('\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
