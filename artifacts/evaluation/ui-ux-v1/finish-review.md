# Independent Impeccable finish review

Reviewed 2026-10-09. Read-only inspection of `frontend/web/index.html`, `app.css`, and `app.js`; implementation screenshots `desktop-welcome.png`, `desktop-sources.png`, `mobile-chat.png`, and `mobile-sources.png`; saved approved Figma exports `artifacts/redesign/figma-source.png` and `figma-mobile.png`. No browser actions, detector run, or clinical/faculty assessment performed by this reviewer.

## Findings

1. **P2 — Preserve the mobile safe area.** `frontend/web/app.css:36` replaces the earlier safe-area-aware `.conversation` padding at line 14 with `padding:16px`. On devices with a bottom home indicator this can place the bottom footer text in the unsafe area. Use `padding:16px 16px max(16px,env(safe-area-inset-bottom))`. The provided ordinary rectangular viewport cannot reproduce a nonzero safe-area inset; this is a directly observed CSS regression.
2. **P3 — Keep the visible source-button label in its accessible name.** `frontend/web/app.js:198` gives the visible `Sources · 1` control the name `View 1 source for: …`. In particular, the singular wording differs from the visible plural label; speech users targeting the visible label may not reliably match it. Start the accessible name with the exact visible label, then append the question. Preserve the contextual disambiguation between older answers.

## Acceptance observations

- The desktop source screenshot shows the first answer selected while a second answer exists: evidence selection is associated with the selected result object, not merely the newest answer. The selected question appears above the reference.
- Detailed source titles, provenance, excerpts, and limitations have moved out of the answer body. The narrow, quiet Sources/Export actions leave the prose readable.
- Mobile evidence uses a native modal dialog with an explicit close control, while the chat remains readable and the composer stays available in the chat screenshot.
- Warnings and urgent/uncertain statuses remain in the chat. Unverified model knowledge remains explicitly labelled. Document text still requires acknowledgement and confirmed revision before use as active context.
- User/model text still uses `textContent`, source URLs retain scheme checks, and links retain `noopener noreferrer`.
- Source and export buttons remain available during network work and expired sessions, without enabling document mutations.
- Ink surfaces, sea-glass accent, typefaces, radii, single conversation, attachment workflow, and rail structure preserve the saved Figma identity. Removing the original duplicate source card and bulky welcome elements follows the user's newer direction.

## Evidence limitation

`desktop-welcome.png` is cropped at the right and bottom, unlike the complete `desktop-sources.png`. It does not by itself establish desktop welcome fit or composer visibility; use the main agent's DOM/viewport verification or replace that capture with a correctly framed one. This is an artifact-quality limitation, not a confirmed application overflow defect.

No other blocking functional or accessibility defect was established in this bounded review. This is not a claim of complete accessibility conformance or medical accuracy.
