2026-10-26 release revalidation
The current immutable identities are in manifests/release-artifact-identity.json.
The original Oilpan failure was corrected with the recorded non-fixed aligned
reservation fallback; runtime and CLI acceptance now pass in full Sv39 guests.
Physical-board testing remains pending. Historical discussion follows; sizes
and success claims below refer to the previous audit unless updated here.

Code Mode / V8 original notice supplement

This directory supplements the existing Codex CLI license bundle. It does not
replace upstream Codex LICENSE/NOTICE, the baseline Rust dependency inventory,
native notices, or Rust 1.99.1 standard-library notices. It is a conservative
source notice collection, not a legal opinion or a final linked-object audit.

Pinned source provenance
- Rusty V8 crate 152.2.0 records VCS revision
  2768994f664e8a6e3aba27503606c58339136e2a. The published crate deliberately
  excludes LICENSE*, AUTHORS, and many documentation files; those notices were
  recovered from its exact official repository revision and submodule pins.
- Its V8 submodule is denoland/v8
  c4ca1eccb90c5464d826b7713dc27178a53b0cfe (V8 15.2.124.1).
- Rusty V8's actual Git tree pins override some versions in v8/DEPS. For
  example, the Chromium build and Abseil forks have distinct recorded pins.
  The preserved recursive Git tree and .gitmodules document the actual pins.
- All 51 restored GN Rust crate directories come from Chromium third_party/rust
  afbc96607d0e659715d803cc099607dd1737fc41. Their original notices are preserved
  separately from Cargo's dependencies. GN includes Temporal 0.2.4, whereas
  this Codex Cargo.lock also selects Temporal 0.2.3; both are inventoried.
- PartitionAlloc's split commit ff3b8b885b8374cbd3902642d94dc737bda93d5d has
  GitOrigin-RevId e2ee5821963baed92f29e830f05d257fbfdc6bdd. Its inherited
  Chromium BSD license was recovered from that exact Chromium source commit.

ICU data proof
deno_core_icudata 0.78.0's src/icudtl.dat is 10,876,560 bytes, SHA-256
9f48c7f9c7c94d516a14870707e910ab94d75ae640ff6842c4af53276cd26ebe.
Its Git blob SHA-1 9655a2e17f08c56d6dbbc47f6e52e3fd3ef2436e exactly equals
common/icudtl.dat at the actual pinned ICU commit
d578f2e8b7bd5938e21cfb6bf15c079e0aa5b738 (ICU 78.2). The complete ICU LICENSE
therefore has direct byte-level provenance to the embedded data, rather than
relying only on the Rust wrapper's MIT metadata. See icu-data-provenance.json.
The small wrapper repository itself contains no separate MIT license file;
its exact published Cargo declaration is preserved without inventing a
copyright holder/year or relabeling another repository's license.

Coverage and use
- SOURCE-PROVENANCE.json identifies the source inputs; the original v8 crate
  SHA-256 was checked against upstream Codex Cargo.lock.
- LICENSE-FILES.json records each saved file's exact origin, revision or
  published package identity, byte count, and SHA-256. All hashes are verified.
  Its kind field distinguishes notices from component README metadata,
  declarations, and four conservatively collected copying-phase source files
  (which are source provenance, not separate license texts).
- files/cargo contains additional top-level Cargo dependency notices.
- files/gn-cargo contains all notices from the 51 exact GN Rust crate trees.
- files/native includes V8, Rusty V8, ICU, libc++/libc++abi/libunwind,
  llvm-libc, Abseil, simdutf, Highway, fast_float, Dragonbox, FP16,
  PartitionAlloc, plus conservative V8 nested and build-source notices.
- files/toolchain contains the exact Chromium-pinned Rust toolchain's
  COPYRIGHT-library.html and associated license texts for source-built std.
- Optional/build-only source notices are retained conservatively. Their
  presence does not claim that those components are linked on RISC-V Linux.
  In particular, the Apple APSL source notice does not mean Apple-only code
  is compiled for this target.
- COVERAGE.json records remaining limits. The final build/link graph should
  be revalidated if sources or artifacts change before publication. This work
  does not authorize publication.

Generated build-graph reconciliation (2026-10-25)
GRAPH-LICENSE-RECONCILIATION.json now records the selected host's locked Cargo
tree: 561 packages, comprising 538 external packages (511 baseline-covered,
27 supplement-covered) and 23 Codex workspace packages. The supplement now
also preserves the exact selected libm 0.2.16 notice. No selected package is
unmapped to a notice inventory, but inventory coverage is not legal clearance.

The final V8 archive rule has 1,960 explicit object inputs, all mapped to
source families. Its 56 Rust rlibs and compiler-rt archive are implicit build
dependencies, not archived by its ${in}-only response file. The generated
graph includes all 51 GN Rust crate directories already covered here.
The completed 1,369,779,476-byte archive has now been streamed, without
extraction, and all 1,960 member contents exactly match the generated input
objects by basename and SHA-256 multiset. No unexpected or missing member was
found. All 1,960 final objects also have VALID compiler-reported Ninja
dependency records. Those -MMD records exclude system headers; they are not
a full preprocessor trace. The production GoogleTest header encountered in
the completed records is now covered by its verbatim original BSD notice,
verified against the original Cargo.lock-verified v8 crate archive.

The successful host's SHA-256, actual ELF shared-library dependencies,
unchanged Cargo.lock, source/graph hashes, package selection, and native build
link directives have been reconciled. The only external shared libraries are
the expected libssl, libcrypto, libgcc_s, libm, libc, and dynamic loader.
No full final linker map/trace was retained, so this does not claim which
individual archive objects survived final linker garbage collection.
See actual_artifacts in GRAPH-LICENSE-RECONCILIATION.json for immutable hashes
and the detailed archive/member and host-linkage evidence.

Two linked Chromium allocator C++ source files exactly match upstream Git
blobs; their inherited BSD license was recovered using GitOrigin-RevId.
Inspector source also explicitly derives from Node.js and ChromeDevTools.
The upstream Rusty V8 introduction does not pin those copied-from revisions.
Original notices from frozen official pre-introduction candidate revisions
are conservatively retained in files/supplementary-origin-candidates/, with
the origin uncertainty explicitly recorded. Do not present those candidate
revisions as proven copied-from origins. Existing baseline original-text
limitations for debugserver-types and eventsource-stream remain applicable.

Packaging: include README.txt, COVERAGE.json, SOURCE-PROVENANCE.json,
GRAPH-LICENSE-RECONCILIATION.json, LICENSE-FILES.json, and files/. Selected
public provenance manifests may accompany them. Raw cargo-metadata, cargo
tree, Ninja command/input/header dumps, source snapshots, and API-history
responses in manifests/ are internal audit evidence; they can contain local
build paths and need not be shipped. Collection scripts are optional audit
tooling, not runtime dependencies. No account credentials were collected.
