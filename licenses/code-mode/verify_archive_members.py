#!/usr/bin/env python3
"""Stream-verify archive members against recorded Ninja object inputs.

Reads only source artifacts; never extracts an archive or invokes a build.
"""
from collections import defaultdict
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORK = ROOT.parent
OUT = WORK / "target/riscv64gc-unknown-linux-gnu/dev-small/gn_out"
ARCHIVE = OUT / "obj/librusty_v8.a"


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def stat_identity(path):
    st = path.stat()
    return dict(size=st.st_size, mtime_ns=st.st_mtime_ns, inode=st.st_ino)


def main():
    graph_path = ROOT / "manifests/v8-archive-link-input-closure.json"
    graph = json.loads(graph_path.read_text())
    expected = defaultdict(list)
    input_objects = []
    for row in graph["objects"]:
        path = OUT / row["object"]
        identity = stat_identity(path)
        sha = digest(path)
        assert identity == stat_identity(path), f"object changed while reading: {path}"
        record = dict(row, bytes=identity["size"], sha256=sha)
        input_objects.append(record)
        expected[(path.name, sha)].append(row["object"])

    before = stat_identity(ARCHIVE)
    whole = hashlib.sha256()
    members = []
    special = []
    name_table = b""
    with ARCHIVE.open("rb") as stream:
        magic = stream.read(8)
        assert magic == b"!<arch>\n", "expected ordinary ar archive, not thin archive"
        whole.update(magic)
        while True:
            header_offset = stream.tell()
            header = stream.read(60)
            if not header:
                break
            assert len(header) == 60 and header[-2:] == b"`\n", "malformed ar header"
            whole.update(header)
            raw_name = header[:16].decode("ascii").strip()
            size = int(header[48:58])
            member_hash = hashlib.sha256()
            data_offset = stream.tell()
            remaining = size
            if raw_name == "//":
                assert size < 16 * 1024 * 1024, "unexpectedly large GNU filename table"
                name_table = stream.read(size)
                assert len(name_table) == size
                whole.update(name_table)
                member_hash.update(name_table)
                remaining = 0
            if raw_name.startswith("#1/"):
                name_size = int(raw_name[3:])
                name_bytes = stream.read(name_size)
                assert len(name_bytes) == name_size
                whole.update(name_bytes)
                remaining -= name_size
                name = name_bytes.rstrip(b"\0").decode()
                data_offset += name_size
                object_size = remaining
            elif raw_name.startswith("/") and raw_name[1:].isdigit():
                name_offset = int(raw_name[1:])
                name_end = name_table.index(b"/\n", name_offset)
                name = name_table[name_offset:name_end].decode()
                object_size = size
            else:
                name = raw_name.removesuffix("/")
                object_size = size
            while remaining:
                block = stream.read(min(1024 * 1024, remaining))
                assert block, "truncated archive member"
                whole.update(block)
                member_hash.update(block)
                remaining -= len(block)
            if size % 2:
                padding = stream.read(1)
                assert len(padding) == 1
                whole.update(padding)
            record = dict(name=name, raw_name=raw_name, header_offset=header_offset,
                          data_offset=data_offset, bytes=object_size,
                          sha256=member_hash.hexdigest())
            if raw_name in ("/", "//", "/SYM64/") or name.startswith("__.SYMDEF"):
                special.append(record)
            else:
                candidates = expected.get((name, record["sha256"]), [])
                record["matches_expected_object"] = candidates.pop() if candidates else None
                members.append(record)
    after = stat_identity(ARCHIVE)
    assert before == after, "archive changed during verification"
    unexpected = [m for m in members if m["matches_expected_object"] is None]
    missing = [obj for values in expected.values() for obj in values]
    report = dict(
        status="PASS" if not unexpected and not missing else "FAIL",
        method="Streaming ar parse and SHA-256 of every member; compare multiset of member basenames and content hashes against actual Ninja object files. No extraction or duplicate archive copy.",
        archive=str(ARCHIVE.relative_to(WORK)), archive_bytes=before["size"],
        archive_sha256=whole.hexdigest(), archive_stable_during_read=True,
        expected_object_count=len(input_objects), actual_object_member_count=len(members),
        special_metadata_members=special, unexpected_members=unexpected,
        missing_expected_objects=missing, object_members=members,
        expected_objects=input_objects,
        graph_manifest_sha256=digest(graph_path),
        scope="Confirms exact archive object content against generated graph. Does not prove all archived objects survive final linker garbage collection or resolve upstream copied-from revision caveats.",
    )
    (ROOT / "manifests/actual-v8-archive-members.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "archive_bytes", "archive_sha256", "expected_object_count", "actual_object_member_count", "unexpected_members", "missing_expected_objects")}, indent=2))
    assert not unexpected and not missing, "archive does not exactly match expected object multiset"


if __name__ == "__main__":
    main()
