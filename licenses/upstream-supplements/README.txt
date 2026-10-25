Supplementary original upstream license texts for crates whose package archives
were initially reported as lacking separate license files.

FILES.json maps each preserved file to package names, its origin URL, revision,
SHA256, and exact provenance. 27 files were retrieved from recorded crate VCS
commits; 8 published source copyright/license headers were preserved verbatim;
7 additional official current-revision license/notice files are clearly labeled
as NOT proven to match the exact published crate revision. The latter are only
supplementary and must not be presented as exact-version evidence.

The 42 files include original texts for Rama, age, Starlark/pagable,
OpenTelemetry, ts-rs, tonic, schemafy, Inflector, flatbuffers, include_dir,
fluent-langneg, asn1-rs-impl, SIMD crates, and the Meta crate family.

crc-catalog stores license texts in LICENSES/Apache-2.0.txt and LICENSES/MIT.txt,
which were missed by a filename-only scan; those exact files are preserved.
cookie-factory similarly uses LICENSES/MIT.txt in its pinned source repository.

PUBLISHED-LICENSE-DECLARATIONS.json retains exact crate metadata (including
license identifiers and authors) for all 69 initially missing-file packages.
COVERAGE.json records remaining scope limitations. Generated standard license
texts from cargo-about and the original-license aggregate remain necessary.
Do not infer a new copyright holder/year or imply a complete legal audit.

Only copy files/, FILES.json, PUBLISHED-LICENSE-DECLARATIONS.json, COVERAGE.json
and this README into public artifacts. Collection scripts/logs are internal and
may contain local execution paths; they are not public deliverables.
