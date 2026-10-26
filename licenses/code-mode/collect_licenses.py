#!/usr/bin/env python3
"""Conservative exact-revision notice harvest; does not infer linked closure."""
import base64
import concurrent.futures
import configparser
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORK = ROOT.parent
BASE = WORK.parent / "codex-riscv-probe"
REV = "2768994f664e8a6e3aba27503606c58339136e2a"
V8REV = "c4ca1eccb90c5464d826b7713dc27178a53b0cfe"
records = []
errors = []
notice = re.compile(r"^(license|copying|copyright|notice)(?:$|[._-])", re.I)


def request(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Codex-RISCV-License-Audit"}), timeout=60) as r:
                return r.read()
        except (OSError, urllib.error.URLError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def write(data, relative, **metadata):
    p = ROOT / "files" / relative
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    records.append(dict(file=str(p.relative_to(ROOT)), sha256=hashlib.sha256(data).hexdigest(), bytes=len(data), **metadata))


def fetch_one(task):
    url, relative, fmt, metadata = task
    try:
        data = request(url)
        if fmt == "gitiles":
            data = base64.b64decode(data)
        write(data, relative, source_url=url, **metadata)
    except Exception as exc:
        errors.append(dict(source_url=url, file=relative, error=str(exc)))


def pool(tasks):
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(fetch_one, tasks))


def gitiles_directory(repo, rev, path=""):
    repo = repo.removesuffix(".git")
    url = f"{repo}/+/{rev}/{path}?format=JSON"
    data = request(url).decode()
    return json.loads(data[data.index("\n") + 1:])["entries"]


def main():
    # Original notices from cached crates, including build-only additions.
    md = json.loads((BASE / "cargo-metadata-riscv64.json").read_text())
    new = json.loads((ROOT / "manifests/cargo-additional-package-declarations.json").read_text())
    added = {(p["name"], p["version"]) for p in new}
    for p in md["packages"]:
        if (p["name"], p["version"]) not in added or not p["source"]:
            continue
        source = Path(p["manifest_path"]).parent
        for f in source.rglob("*"):
            if f.is_file() and notice.match(f.name):
                relative = str(f.relative_to(source))
                write(f.read_bytes(), f"cargo/{p['name']}-{p['version']}/{relative}", component=p["name"], version=p["version"], declared_license=p["license"], provenance="exact cached published crate", source_path=relative, package_source=p["source"])

    tasks = []
    tree = json.loads((ROOT / "manifests/v8-recursive-tree.json").read_text())
    for entry in tree["tree"]:
        path = entry["path"]
        if entry["type"] == "blob" and not path.startswith("test/") and (notice.match(Path(path).name) or path == "AUTHORS"):
            tasks.append((f"https://raw.githubusercontent.com/denoland/v8/{V8REV}/{path}", f"native/v8/{path}", "raw", dict(component="v8", revision=V8REV, source_path=path, source_blob_sha1=entry["sha"])))
    tasks.append((f"https://raw.githubusercontent.com/denoland/rusty_v8/{REV}/LICENSE", "native/rusty-v8/LICENSE", "raw", dict(component="rusty-v8", version="152.2.0", revision=REV, source_path="LICENSE")))
    pool(tasks)

    tree = json.loads((ROOT / "manifests/rusty-v8-recursive-tree.json").read_text())
    pins = {e["path"]: e["sha"] for e in tree["tree"] if e["type"] == "commit"}
    config = configparser.ConfigParser()
    config.read(ROOT / "manifests/rusty-v8.gitmodules")
    roots = []
    for section in config.sections():
        path, repo = config[section]["path"], config[section]["url"]
        if path in ("v8", "tools/win", "tools/clang", "third_party/rust"):
            continue
        roots.append(dict(path=path, repository=repo, revision=pins[path]))
    (ROOT / "manifests/native-component-pins.json").write_text(json.dumps(roots, indent=2) + "\n")

    def native(root):
        path, repo, rev = root["path"], root["repository"], root["revision"]
        try:
            if "github.com" in repo:
                slug = repo.split("github.com/", 1)[1].removesuffix(".git")
                entries = json.loads(request(f"https://api.github.com/repos/{slug}/git/trees/{rev}"))["tree"]
                files = [e["path"] for e in entries if e["type"] == "blob" and (notice.match(e["path"]) or e["path"] == "README.chromium")]
                return [(f"https://raw.githubusercontent.com/{slug}/{rev}/{f}", f"native/{path}/{f}", "raw", dict(component=path, revision=rev, source_path=f)) for f in files]
            entries = gitiles_directory(repo, rev)
            files = [e["name"] for e in entries if e["type"] == "blob" and (notice.match(e["name"]) or e["name"] == "README.chromium")]
            return [(f"{repo}/+/{rev}/{f}?format=TEXT", f"native/{path}/{f}", "gitiles", dict(component=path, revision=rev, source_path=f)) for f in files]
        except Exception as exc:
            errors.append(dict(component=path, revision=rev, error=str(exc)))
            return []

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        groups = list(ex.map(native, roots))
    pool([task for group in groups for task in group])
    (ROOT / "LICENSE-FILES.json").write_text(json.dumps(sorted(records, key=lambda r: r["file"]), indent=2) + "\n")
    (ROOT / "manifests/retrieval-errors.json").write_text(json.dumps(errors, indent=2) + "\n")
    print(f"Collected {len(records)} exact-source notice files; retrieval errors: {len(errors)}")


if __name__ == "__main__":
    main()
