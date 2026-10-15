# Aster Windows one-click release

The release tooling implements the [supplied blueprint](superpowers/plans/2026-10-10-release-spec.md). Repository: [AyushM1701/ASTER-AI](https://github.com/AyushM1701/ASTER-AI). A public installer has not been published. The application remains medical education and research software; clinical accuracy and faculty review are not established.

## Editions and current status

| Edition | Intended audience | Build gate |
|---|---|---|
| `ValidationOnly` | This development workstation; local engineering tests | Exact asset integrity; explicitly not distributable |
| `PublicStandard` | Public GitHub Release | Every included file covered by affirmative reviewed redistribution rights, exact manifests, packaged and clean-machine acceptance |
| `PrivateAuthorized` | Recipients with documented distribution permission | Same affirmative redistribution gate; private access is not a license waiver |

The captured development profile contains 266,870 primary sections, 2,916 teaching sections and 6,670 unverified secondary notes. These are **not promised as public coverage**. The public rights register currently blocks the medical datasets, native runtime dependencies and other unreviewed assets. MIT authorization covers Aster's own code. Individual CC, noncommercial, share-alike, publisher and dataset terms still need review. Replace the profile with a permitted reduced library and rebuild its indexes/counts if full redistribution is unavailable; do not silently relabel the development collection public.

Handwriting and specialist X-ray scores are disabled in the packaged profile. Qwen vision still routes images. Printed English OCR uses bundled Tesseract and mandatory confirmation. Unsupported medical/personal dosing requests retain the existing policy. Simple/deeper explanations are shown only where source-bound notes/layouts support them. No model is fine-tuned during installation.

## End-user installation, once a release is published

1. Download the setup executable from the official GitHub Release. Verify the publisher's hash/signature through a trusted channel. No Authenticode signing certificate has been configured here.
2. Run setup without administrator privileges, choose a writable folder and install. Setup authenticates the release metadata against its compiled hash, then downloads and verifies immutable parts. Interrupted parts are resumed when the server supports ranges, otherwise retried cleanly.
3. Select **Launch Aster**. Keep the controller open while using the workspace. The controller verifies installation bytes, checks the exact model digest, checks the actual loaded library versions/counts, and runs local inference using the included synthetic image before opening the browser. Model loading stays in **Loading AI**; no patient image is used for this startup check.
4. For a disconnected machine, copy setup, `distribution.json` and **all** `.partNNN` files into a folder. Choose **Use downloaded parts (offline)** in setup. Alternatively extract the complete externally hosted offline ZIP and run `Aster.exe`.

Runtime does not install packages, pull models, contact model registries or invoke cloud inference. The only network dependencies in setup are authenticated HTTPS release downloads. Full air-gapped runtime and clean-machine support must be verified for each public artifact; local development checks do not prove this.

Windows x64 is the target. Windows 10/11, CPU-only operation, Unicode paths, missing VC runtime, low resources, non-admin accounts and antivirus/SmartScreen behavior require recorded clean-VM tests before publication. No minimum RAM/VRAM figure is asserted without measurements. Download and disk requirements come from actual `distribution.json` sizes, including space for parts, assembled archive, extracted version and retained rollback copy.

## Runtime layout and ownership

```text
Aster.exe + _internal/                frozen controller and native Tk runtime
bin/aster-api/aster-api.exe           API and its independent _internal/
bin/aster-web/aster-web.exe           same-origin bridge and its _internal/
runtime/ollama/ollama.exe             exact standalone Ollama distribution
runtime/tesseract/                   executable, DLLs and English traineddata
data/models/                        pinned Qwen store and offline MiniLM
data/references/ + data/indexes/      selected immutable libraries
frontend/web/                       local HTML/CSS/JS/fonts/icons
configs/explanation_layouts.json     source-bound presentation layouts
release-manifest.json                actual files, sizes, hashes and profile
LICENSE + THIRD_PARTY_NOTICES.md      separate code and asset terms
```

API/web are separate onedir executables because they have different dependencies. The launcher supplies `ASTER_INSTALL_ROOT`; frozen resources such as prompts resolve inside `_internal` while external data resolves from the install root. Source mode retains existing configuration precedence. Packaged mode explicitly supplies every Settings field, ignores `.env`, allowlists child process environment variables and sets offline caches separately.

Loopback ports: API **8000**, workspace **8501**, private Ollama **11435**. Existing developer Ollama on 11434 is left alone. Startup refuses occupied ports. Each child is created suspended and assigned to a Windows Job Object before execution, so descendants belong to this controller. Closing signals graceful API/web shutdown, then tears down only the owned job. A controller crash also closes its job and kills owned services. No global service or startup task is installed.

Writable files live under `%LOCALAPPDATA%\Aster`: logs, cache, instance lock, installer downloads, versioned installations and `current.json`. Runtime logs record states rather than question/image contents. Diagnostic ZIPs export only allowlisted versions, feature/data metadata and OS information. Chats/uploads/tokens remain in memory and are lost on shutdown.

Native OCR creates transient image/text files in an isolated per-run temporary directory under Aster's cache. The controller removes that directory after owned services stop. A forced controller/OS crash can leave temporary files; review and remove leftover `cache/temp/aster-*` directories with Aster stopped. They are excluded from diagnostic exports. Ollama's home/key/cache state is redirected into Aster's writable runtime home; original model assets remain in the verified installation.

The pinned Windows Tesseract build rejects non-ASCII data/temp paths. Aster uses Windows short-path aliases only when they are ASCII and resolve to the same verified locations. Cleanup uses the original canonical path. If short names are unavailable, startup explains the path requirement rather than using global OCR or reporting it as ready. Move the installation to an ASCII path; a non-ASCII user cache can be redirected with `Aster.exe --writable 'an ASCII writable folder outside the installation'`. This limitation still needs testing in the clean-machine matrix. Custom writable directories contain the same transient files/cache/logs and must be included in cleanup/uninstall.

Ollama serves through a separate writable `cache/model-store` containing the exact verified model manifest/blobs. Same-volume NTFS installations use hardlinks to avoid duplicating weights; cross-volume or unsupported filesystems require a local copy and additional disk space equal to the model store. Derived Ollama metadata is written there. The original installation stays immutable, and cache manifests/blobs are hash-checked before use. If a cache mismatch is reported, close Aster, remove only its `cache/model-store` directory and relaunch to recreate it from included files; no download or different model is selected.

## Build and review

Build steps use Python on the **developer/build machine only**. End users use executables.

```powershell
cd 'your Aster source folder'
.venv\Scripts\python.exe -m pip install -r packaging\requirements-build.lock.txt
.\packaging\build-windows.ps1 -Edition ValidationOnly -Version 0.1.0-beta.1
```

The build performs dependency checks, captures exact asset hashes/sizes, runs source tests, creates a fresh minimal pinned CPU build environment, freezes all three components and copies allowlisted assets to a new immutable output. It runs the actual frozen API's offline encoder check, including a 384-dimension embedding, before accepting the build. It excludes `.env`, private uploads, backups, raw acquisition folders, additional Ollama models and optional X-ray data. PyInstaller version, hooks, runtime dependency versions and model digests are pinned. Reproducibility here means fixed inputs and verification; bit-for-bit reproducibility of timestamps/native frozen binaries has not been established.

Review `packaging/asset-rights.csv`, preserve publisher licenses and make the explicit `approved` decisions with reviewer/date/permission basis. Public/private distributable builds refuse unresolved rows and unaccounted files; there is no public bypass switch. Setup's own bundled Python/Tcl/Tk/PyInstaller runtime has an additional rights gate in its build spec, so portable approval cannot bypass installer-runtime review. Extend/trim the reviewed profile and source/index bundle before building a different edition. Full dependency/native notices must be supplied before clearing their gate. MiniLM is required when either enabled library uses hybrid search; entirely lexical profiles omit it and skip the dense-encoder gate.

```powershell
.venv\Scripts\python.exe packaging\verify-package.py 'path to portable build'
.venv\Scripts\python.exe -m aster_release.encoder_check 'path to portable build'
.venv\Scripts\python.exe scripts\verify_assets.py --release-manifest 'path to portable build\release-manifest.json' --offline
.venv\Scripts\python.exe -m aster_release.smoke --package 'path to portable build' --report 'path outside install\frozen-smoke.json'
```

The smoke runner uses the **frozen** controller, API, bridge and native OCR. It needs ports 8000/8501/11435 free; stop your own development app before running it. Its development-machine results do not satisfy `packaging/acceptance-template.json` automatically. The smoke report explicitly marks `clean_vm` and `air_gapped` false.

For a rights-cleared build:

```powershell
.venv\Scripts\python.exe packaging\create-release-assets.py --root 'verified PublicStandard portable folder' --output 'new release output folder' --tag v0.1.0-beta.1
$env:ASTER_BUILD_TRUST_FILE = (Resolve-Path 'release output folder\installer-trust.json').Path
.venv\Scripts\python.exe -m PyInstaller --distpath 'release output folder' --workpath 'setup build workspace' packaging\installer\aster-setup.spec
```

`distribution.json` records actual compressed/uncompressed sizes, archive hash, part hashes/URLs and the package-manifest hash. The setup executable embeds the generated trust file. A changed server-side manifest cannot redefine trusted files. Downloads permit only GitHub HTTPS release hosts; archive extraction rejects traversal, symlinks, Windows reserved names, ADS, duplicate/case-colliding paths and oversized extraction. Disk checks account for verified cached parts, resumable or reclaimable partial allocations, and an assembled archive that will be overwritten; cached bytes still require final checksum verification. Assets are verified before an atomic version-directory move/current pointer update. Archive parts target 1,800 MiB, below GitHub's documented 2 GiB per-asset limit.

## CI, publication and remaining gates

`windows-ci.yml` runs source tests on GitHub-hosted Windows. `release-windows.yml` accepts canonical version tags, checks that they belong to protected `main`, uses pinned action commits and isolates asset-bearing build work on a self-hosted Windows runner. Configure protected environments `aster-release-build` and `aster-release-publish`, restrict tag creation and never run untrusted pull requests on that runner.

Provision `ASTER_CLEARED_ASSET_ROOT`, `ASTER_BUILD_PYTHON` and `ASTER_ACCEPTANCE_REPORT` on the maintained runner. Public provisioning accepts only a verified `PublicStandard` asset installation and copies its selected data/configuration and Ollama/Tesseract runtime assets. Public/private builds require provisioned Tesseract files; only local `ValidationOnly` staging permits the developer's existing native OCR installation as an input. The release gate requires a reviewer/date, measurements and explicit evidence for every packaged/clean-VM case, tied to the exact manifest SHA-256. It rejects incomplete templates and source-test-only evidence. The workflow creates a **draft beta** after these gates; it never automatically marks a release stable or clinically validated. Perform install/download/offline smoke tests of the released files before final publication.

This workspace is not a Git checkout and no source push or GitHub release has been performed by these local build changes. Initialize/import the MIT-licensed source into the repository with the asset exclusions intact. Do not upload the local ValidationOnly package, source `.env` or unreviewed medical collections.

## Repair, updates, rollback and uninstall

For corrupt/missing assets or a model digest mismatch, stop Aster and rerun the exact version's setup into a clean folder. It does not substitute a newer tag or another local/cloud server. The current setup intentionally refuses overwriting an existing version; this prevents silently patching an immutable running installation. For updates use the newer version's authenticated setup, which stages/validates before switching `current.json`, retaining the old version.

From a developer/support Python environment, `aster_release.installer.rollback(install_root)` validates the previous installed version and switches the pointer back. End users can launch the retained `versions/<previous>/Aster.exe` directly without Python. Assets persist, but chats/uploads have no migration or recovery. To uninstall, close the controller and delete its installation folder and, if desired, `%LOCALAPPDATA%\Aster` downloads/cache/logs. No administrator-level services, scheduled tasks or global model installs need removing.

## Evidence and limitations

Local build inventories/logs and frozen smoke reports are under `artifacts/release` and excluded from source control. See `WINDOWS_RELEASE_EVALUATION.md` for measured results and a phase-by-phase status. Missing faculty review, handwriting accuracy, imaging validation and public redistribution permissions remain explicit boundaries; packaging does not increase medical accuracy.

Technical references: [GitHub release limits](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases), [PyInstaller frozen runtime paths](https://pyinstaller.org/en/stable/runtime-information.html), [Ollama Windows standalone runtime](https://github.com/ollama/ollama/blob/main/docs/windows.mdx).
