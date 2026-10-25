Supplemental native / embedded-data notices for codex-riscv
Upstream Codex commit: 970111f6cb62cc02fe36a82ea7d71b37a2889c97
Target: riscv64gc-unknown-linux-gnu; existing dev-small CLI binary.

This directory supplements, and does not replace, the Rust package notice
inventory and upstream Codex LICENSE/NOTICE. It preserves actual license text
from the exact cached dependency sources. NATIVE-LICENSE-FILES.json records origins
and SHA-256 hashes; SOURCE-ARCHIVES.json records exact MPL source archives.
The manifests intentionally contain no private machine paths.

Applicable bundled components
- aws-lc-sys 0.45.0: the native AWS-LC license includes the original BoringSSL,
  OpenSSL-derived, mlkem/mldsa, etc. notices; its separate Fiat license is kept.
- ring 0.17.14: root license guidance, BoringSSL Apache license, ISC license,
  Fiat license, and nested once_cell licenses are kept.
- libsqlite3-sys 0.37.0: wrapper MIT license and the actual public-domain notice
  at the start of the SQLite 3.51.3 amalgamation are kept. The native sqlite3
  implementation, not the optional SQLCipher source, is used in this build.
- zstd-sys 2.0.16+zstd.1.5.7: wrapper notices and zstd native BSD license kept.
  Native zstd is used under its BSD option, not its alternative GPL option.
- onig_sys 69.9.1: wrapper and native Oniguruma COPYING kept.
- bzip2-sys 0.1.13+1.0.8: wrapper and native bzip2 1.0.8 license kept.
- libbz2-rs-sys 0.2.5 and zlib-rs 0.5.5/0.6.3: preserved license texts.
- tree-sitter 0.25.10: upstream MIT LICENSE retrieved at the exact crate VCS
  revision da6fe9beb4f7f67beb75914ca8e0d48ae48d6406, because the downloaded
  crate does not contain that root file; nested Unicode/ICU license is kept.
- tree-sitter-bash 0.25.1 and tree-sitter-powershell 0.26.4: grammar licenses kept.
- syntect 5.3.0 and two-face 0.5.1: Rust wrapper licenses kept. Codex TUI uses
  two_face::syntax::extra_newlines() and two_face::theme::extra(), so separate
  syntax/theme licenses apply. The complete 205KB upstream generated asset
  acknowledgements are retained, not just the MIT/Apache wrapper licenses.
  The document is pinned to two-face's .cargo_vcs_info.json revision
  61d1e8d42cfe3c80e5f3d1bc9a71a4a59ee9ebee.

MPL-covered source
The unmodified source for nucleo + nucleo-matcher, option-ext 0.2.0, and the
nine Symphonia 0.6.0 packages is included in licenses/sources/ within the binary release archive. They are not stored in Git; SOURCE-ARCHIVES.json also records exact upstream URLs. Those components remain
under MPL-2.0; the containing repository's Apache license does not relicense
them. The exact crate archives were checked against the upstream Codex
Cargo.lock SHA-256 values. The nucleo archive was generated directly from
commit 4253de9faabb4e5c6d81d946a5e35a90f87347ee using git archive, including all
tracked source and license files but no .git directory or untracked files.
Every archive is a tar.gz-compatible file; .crate is Cargo's usual extension.

Not distributed with this binary
- Debian OpenSSL/libssl, glibc/libgcc_s and other system shared libraries are
  runtime dependencies installed separately by the user, not bundled copies.
- No GStreamer/GLib/Opus voice runtime from upstream third_party/voice is in the
  release. Its LGPL licensing pertains to those separate runtime packages.
- No V8/code-mode runtime package is included in this CLI-only build.
- Upstream third_party/wezterm/LICENSE applies to copied Windows PTY source
  (utils/pty/src/win/*), which is not compiled for riscv64 Linux. The independent
  portable-pty crate remains covered by the main Cargo package notice inventory.
- Rust standard-library notices are included separately in rust-standard-library/
  using the official Rust 1.99.1 COPYRIGHT-library.html and license directory.

Collection scope
These files are a conservative notice supplement for the selected dependency
sources. This is not a claim that every alternate backend in those crates is
linked into the final executable, nor an audit of optional unbuilt runtimes.
