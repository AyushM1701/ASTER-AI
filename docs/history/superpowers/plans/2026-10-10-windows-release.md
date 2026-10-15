# Aster Windows release implementation

Goal: deliver a relocatable Windows launcher, frozen API/web services, authenticated bootstrapper, immutable asset staging and release gates from the supplied blueprint.

Architecture: preserve the existing single-worker API and same-origin frontend. A standard-library controller verifies the entire installation before launching owned loopback services in a Windows Job Object. A bootstrapper embeds a distribution manifest hash and installs verified archive parts into versioned directories. Public builds require affirmative, documented rights for every component.

Stack: Python 3.13, PyInstaller onedir, FastAPI/uvicorn, standalone Ollama, English Tesseract; existing CPU retrieval stack. Spec: [supplied release blueprint](2026-10-10-release-spec.md).

Constraints: no clinical behavior rewrite, no end-user package/model downloads, no root admin or unrelated-process termination, no clinical validation claims, no private development snapshots shipped. Public distribution is blocked while data permissions remain unreviewed. Local validation builds are explicitly non-distributable.

Review focus: inherited environment isolation, archive traversal and authenticated downloads, hash compatibility, actual frozen execution, child cleanup and truthful readiness.

- [x] Capture baseline and asset inventory; add owner-authorized MIT license and record unresolved third-party rights.
- [x] Implement immutable manifests, rights-filtered staging, offline compatibility checks and explicit frozen settings.
- [x] Implement owned-process launcher, responsive status/diagnostics and API/web entrypoints.
- [x] Implement pinned bootstrapper, archive splitting, resume, atomic installation and rollback.
- [x] Implement pinned Windows build and fail-closed publication workflow.
- [x] Run regression/security/packaging tests, freeze and smoke-test actual binaries; document measured results and untested VM matrix. 535 source tests and all 11 local frozen smoke groups passed; see [evaluation](../../WINDOWS_RELEASE_EVALUATION.md).
- [ ] Resolve third-party redistribution permissions and complete notices for the selected public edition.
- [ ] Build and validate the final bootstrapper/distribution on clean Windows machines and from downloaded release assets.
- [ ] Import source into GitHub, configure protected branch/tags/environments/runner, and publish an accepted beta.

Acceptance: no network acquisition after install; exact model/store/index/layout hashes; handwritten OCR and X-ray off by default; public release cannot bypass rights gate. Source tests are separate from frozen acceptance and clean-VM validation.
