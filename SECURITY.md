# Security and privacy

Aster is a single-user medical education and research application. It is not clinically validated and is not a diagnostic or prescribing service. Do not expose its loopback API or web bridge to the public internet.

Packaged services bind to `127.0.0.1`: API 8000, workspace 8501, dedicated Ollama 11435. A port conflict stops startup without killing another program. Runtime has no telemetry, model pulls or dependency installs. Package files and release compatibility are verified before startup. Source-grounding, medicine identity, upload bounds, session tokens, Origin checks and CSP remain active.

Report security issues privately to the repository owner through GitHub's private vulnerability reporting when enabled. Otherwise request a private contact without publishing patient information, credentials, exploit payloads or medical uploads in an issue.

Bootstrapper authenticity comes from a pinned SHA-256 of the distribution manifest embedded into the executable. Get the setup program from the official repository release and verify its published hash through a trusted channel. A checksum downloaded alongside an untrusted executable does not authenticate that executable. Authenticode signing and independent clean-machine validation are release-owner responsibilities and have not been completed here.

Chats, session tokens and uploads remain in memory and disappear on service shutdown; no session recovery is promised. `%LOCALAPPDATA%\Aster` contains installations/downloads/cache and state-only logs. Diagnostic exports contain allowlisted versions/features/model hashes and OS information, not chats, environment variables or images.

Native OCR uses temporary image/text files in a per-run Aster cache folder. Normal controller shutdown removes that folder after its services stop. A forced process or Windows crash can leave temporary files; close Aster before removing leftover `cache/temp/aster-*` folders. Diagnostic exports exclude these files.

An adversary with write access to the installed executables or control of the current user account can replace code and integrity checks. Package integrity checks do not protect a compromised Windows account.
