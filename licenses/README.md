# License and source notice collection

The adaptation/build scripts and documentation are provided under the repository
Apache-2.0 license. This does **not** relicense upstream or third-party code.
Keep the top-level `LICENSE` and `NOTICE` when redistributing this build.

The released executable is based on upstream Codex commit
`970111f6cb62cc02fe36a82ea7d71b37a2889c97`, with the change described in
[`MODIFICATIONS.md`](../MODIFICATIONS.md).

## Included material

- `THIRD-PARTY-NOTICES.html`: generated using **cargo-about 0.9.2**, with
  `--locked --fail`, the CLI manifest, and the target-specific `about.toml`.
- `ORIGINAL-LICENSE-TEXTS.txt`: full original license/notice file contents from
  the exact downloaded Cargo packages and Git dependencies, deduplicated only
  when their SHA256 hashes match. Copyright statements are preserved.
- `cargo-license-inventory.json`: normal and build dependency inventory. It
  conservatively includes build-time tools that may not be linked into the
  executable. Host-only cpufeatures and libbz2-rs-sys are covered by their
  original license texts and native supplements even when cargo-about omits
  them from its target graph.
- `native/` and `NATIVE-LICENSE-FILES.json`: reviewed native/embedded-data
  supplements, including complete two-face syntax/theme acknowledgements.
- `rust-standard-library/`: the official Rust **1.99.1** library copyright
  document and referenced license texts; Cargo metadata does not include std.
- `SOURCE-ARCHIVES.json`: origin and SHA256 of the unchanged MPL-covered
  sources. Those archives are supplied in `licenses/sources/` in the binary
  release archive and in the separate MPL-source release asset; they are not
  checked into Git. A Cargo `.crate` file is a gzip-compressed source tar archive.

The MPL-covered components (nucleo, nucleo-matcher, option-ext and Symphonia)
remain under MPL-2.0. Their exact source is provided so recipients can exercise
those rights. Permissive alternatives were selected where applicable, e.g.
Apache-2.0 rather than GPL for self_cell, and BSD for zstd.

System OpenSSL, glibc and other shared libraries are **not bundled**. Debian
installs those dependencies separately. Optional V8/code-mode, voice runtime,
and Windows-only components are outside this Linux CLI artifact.

This collection documents the selected experimental build. It is not a claim
that every optional backend or feature in upstream Codex has been audited or
redistributed. See the per-file provenance manifests and native supplement for
scope and source details.

## Upstream archives without standalone license files

`upstream-supplements/` preserves additional exact upstream license/NOTICE
texts and published source headers, with origin/commit/hash records. A few
supplementary current-revision files are explicitly labeled as not proven to
match the crate revision; they are not used to invent licensing terms.

Five packages (`debugserver-types`, `eventsource-stream`, `intl_pluralrules`,
`io_tee`, `linux-keyutils`) supply declared license metadata but no standalone
license file in their published archives or inspected pinned repository roots.
Their declared authors/license metadata, the generated license terms, and the
complete exact published source archives are retained. No copyright holder or
date has been inferred. The separate dependency-source asset includes these
five archives as well as the MPL-covered archives.
