# Windows release evaluation — 10 October 2026

**Status: local engineering validation; public release pending.** MIT licensing applies to Aster's own code. The captured medical/model/runtime assets have separate rights decisions and must not be uploaded as a public package while those decisions remain unresolved.

Repository target: [AyushM1701/ASTER-AI](https://github.com/AyushM1701/ASTER-AI). No commit, source push, tag or GitHub Release has been created by this implementation.

## Implemented

- Separate frozen Windows controller, API and web bridge; bundled standalone Ollama, English Tesseract, pinned Qwen weights and offline MiniLM.
- Full-file checksums, index/source/teaching/layout compatibility, explicit packaged settings and environment isolation.
- Owned Windows Job Object services, readiness states, loopback binding, occupied-port refusal and bounded cleanup.
- Writable model metadata/cache isolated from immutable installation files; verified original model blobs are reused through hardlinks when supported.
- Authenticated distribution manifest, resumable bounded HTTPS downloads, verified archive parts, safe extraction, atomic version installation and rollback.
- Fail-closed public/private redistribution checks; pinned CI actions and protected-environment draft-release workflow.
- Edition/model/data visibility in the workspace; handwritten OCR and specialist X-ray scoring disabled in this release profile.

## Local verification

The full source suite passed **535 tests** with one existing Starlette/httpx deprecation warning (53.47 seconds). This is engineering regression evidence, not medical-faculty review or a clean-machine acceptance result. Release-tool linting, frontend JavaScript syntax, PowerShell build-script parsing, workflow YAML parsing and release-document links also passed. Focused independent code reviews found no remaining Important defect after the fixes, including correction of a temporary-file cleanup issue introduced by short-path aliases; they did not perform frozen, clean-VM, permission or medical review.

A fresh build environment installed the exact runtime/build locks and passed `pip check`. The offline MiniLM check in that environment returned a `(1, 384)` vector. Separate PyInstaller onedir components were built; a source-environment encoder check alone did not prove that all dynamic imports were present in the frozen API. The build now includes an actual frozen encoder gate.

The verified local portable directory is `artifacts/release/Aster β's portable`. It contains **7,300 files** totalling **5,886,738,081 bytes**. Its manifest SHA-256 is `fe7b47719cf6ba49868ecc9f5426819b09d4bfeabc2efcc2cfe5842f5d1ea092`. The edition is `ValidationOnly`; it is not approved for redistribution.

**The actual frozen smoke run passed all 11 check groups** for this exact manifest. The frozen encoder independently returned 384 dimensions. Raw evidence: `artifacts/release/frozen-smoke.json`, `frozen-smoke-final.log`, `frozen-encoder-final.log` and `package-verification-final.json`.

Post-run verification also passed with the same manifest, file count and byte count (`artifacts/release/package-verification-post-runtime.json`): the frozen workflow did not modify the immutable installation.

The development app was restored at `http://127.0.0.1:8501/`; both UI and API readiness passed with 266,870 primary sections, 2,916 teaching sections and printed OCR available. The pre-existing developer Ollama process on port 11434 was preserved. Restoration evidence: `artifacts/release/restored-source-ready.json` and `restored-source-processes.json`.

| Frozen check | Observed result |
|---|---|
| Launcher/API/bridge readiness | Passed; actual inference completed before Ready |
| Hostile inherited environment | Passed; packaged handwriting/X-ray flags stayed off |
| Effective edition/data metadata | Passed; matched the manifest |
| General epithelium question | HTTP 200; 3 citations; Simple/Deeper layers |
| Sulcular epithelium question | HTTP 200; 2 citations; Simple/Deeper layers |
| Personal amoxicillin dosing request | `unsupported_input` |
| Current urgent-language request | `urgent_guidance` |
| Ordinary greeting | HTTP 200; local model answer; no fabricated citations or unnecessary layers |
| Synthetic printed prescription | Real vision classification; real bundled Tesseract; nonempty text and 7 editable fields |
| Explain before confirmation | HTTP 409; `needs_confirmation` |
| Controller termination | All three owned service ports freed |

Launch-to-ready measured **166.49 seconds** from controller start on this development workstation, with an existing verified model cache. This is not first-install timing or a hardware minimum. The harness's preliminary package verification runs before that timer. The encoder was checked in a separate run before timing the launcher.

This is one synthetic printed prescription, not a handwritten-prescription accuracy score. Citation counts and format checks do not establish medical correctness. No clean VM, packet-captured air-gap run, native controller visual acceptance, faculty scoring or production deployment is implied. The earlier settings dialog layout check covered desktop and 390×844 phone viewports with no horizontal overflow; the frontend/data profile is unchanged by the final greeting/path fixes.

## Problems found during frozen validation

1. Ollama generated model metadata inside the immutable installation. Aster's unlisted-file verification correctly rejected it. The serving store now lives in writable cache and verifies its model manifest/blobs against the included assets.
2. The frozen retrieval stack failed to import Transformers' `PreTrainedModel`, leaving the primary/teaching libraries unavailable. The controller kept the workspace closed. The offline frozen encoder check exposed missing Torchvision `_C_stable`/`image_stable` native files: the pinned PyInstaller hook searched older filenames. The spec now explicitly includes the native files from the pinned dependency.
3. CI provisioning copied data/configuration but omitted native runtimes. It now provisions Ollama/Tesseract from the verified asset installation. Public/private builds reject missing provisioned Tesseract rather than borrowing the runner's installation. Two staging regression tests cover these paths. Existing large assets are compared using streaming hashes.
4. Independent code review identified five further gaps. Setup now checks its own runtime rights; startup requires actual inference and actual loaded library counts/versions; reduced lexical/hybrid profiles include only needed encoder assets; secondary records retain their nested checksum/count binding; resumed setup accounts for already allocated download/archive space. Regression tests cover these fixes separately from live frozen acceptance.
5. The packaged primary index used `medical_reference_v2`, but the release profile selected `medical_reference_v1`. The strict loaded-library gate caught this mismatch. The profile now uses the included collection, and compatibility verification rejects mismatched primary/teaching collection identifiers before launch. A regression test reproduced the missing preflight check before the fix.

6. A full 1400×1050 prescription was unnecessarily used for startup warmup. In the actual CPU run it took over five minutes; the test controller was manually stopped, and its Job Object cleanup passed. Startup now sends a constant 64×64 synthetic RGB image and still requires a real completed vision inference. The full prescription remains in the separate OCR acceptance test. The abandoned run is retained as `artifacts/release/frozen-smoke-full-image-probe-aborted.json`; it is not a passed acceptance result.

7. The controller's web-bridge health request lacked `X-Aster-Client: 1`, so the actual bridge returned HTTP 403 while the workspace itself served correctly. The controller now supplies the required header; host, Origin and route protections are unchanged. A regression test uses the actual web bridge and verifies both rejected headerless requests and accepted controller readiness. The fix also returned Ready against the running frozen bridge. The earlier run was manually ended and retained as `artifacts/release/frozen-smoke-bridge-probe-aborted.json`.

8. Actual frozen general chat returned HTTP 502 for a greeting. A controlled reproduction showed that “If you have a question” matched the broad `you have` diagnosis guard. Conversation validation now allows only the narrow question-invitation phrase while retaining diagnosis, treatment and input-policy checks. Greeting responses discard model-added deeper commentary. Regression cases include the captured harmless wording and diagnosis/dosing statements, including an unsafe sentence following a harmless invitation.

9. The bundled Tesseract process failed with `filesystem error: Cannot convert character sequence: Illegal byte sequence` when its data directory contained `β`. The same included executable and data succeeded using their Windows short path. Packaged data/temp paths now use ASCII aliases verified to resolve to the original locations; unavailable aliases fail with repair guidance. The controller canonicalizes scratch paths before deletion, and tests cover Unicode cache cleanup and alias failure. `--writable` permits a user-selected ASCII cache outside the immutable installation. This is a documented compatibility limitation, not proof that every Windows filesystem/profile works.

## Required before public publication

| Gate | Current evidence/status |
|---|---|
| Code ownership/license | Owner confirmed permission; MIT `LICENSE` created |
| Third-party distribution rights | Pending; public preflight refuses unresolved components |
| Source regression | 535 tests passed |
| Actual frozen runtime | All 11 local smoke groups passed; frozen encoder passed; 166.49-second launch-to-ready |
| Clean Windows 10/11, no global runtimes | Not performed |
| Network disabled and packet capture | Not performed; local/offline flags are not air-gap evidence |
| CPU/RAM/disk/GPU support matrix | Not established; no hardware minimum guarantee |
| Trusted setup executable and real install/download tests | Sources implemented; final rights-cleared distribution/setup not built or published |
| Authenticode/SmartScreen testing | No signing certificate configured; untested |
| Protected GitHub branch/tags/environments/asset runner | Workflow supplied; repository settings not configured |
| Clinical/faculty review | Pending; no reviewer scores claimed |

The 23-case `packaging/acceptance-template.json` intentionally remains incomplete. Release acceptance requires explicit reviewer/date, measurements, evidence and the exact final manifest hash. Source-test results cannot fill clean-machine cases.

Build and operational instructions are in [Windows release guide](WINDOWS_RELEASE.md). Local build logs, inventories and validation packages are under `artifacts/release`, excluded from Git source control. The `ValidationOnly` package is for local testing and is not approved for redistribution.
