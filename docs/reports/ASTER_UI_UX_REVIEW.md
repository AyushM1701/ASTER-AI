# Aster conversation and answer-quality review

Date: 9 October 2026. Scope: the current local conversation UI and a focused AI regression pass. This is an engineering and usability review, not medical faculty assessment.

## Changes delivered

| Finding | Change | Verification |
|---|---|---|
| Sources duplicated inside answers and the right rail | Full reference records, supporting passages and limitations live in the evidence rail; one compact Sources action remains under each answer | Browser: no source cards inside the transcript |
| Right rail always followed the latest answer | Each answer selects its own reference set and shows its original question in the panel | Two real answers; select the older osmosis answer |
| Citation removal could lose claim traceability | Each source identifies the answer paragraph(s) it supports; JSON export retains the complete original response | Browser and code inspection |
| Mobile evidence consumed scarce conversation height | Native modal sources drawer, accessible through the answer or header | Phone test: open, Escape, focus returned to the originating answer |
| Welcome actions clipped in the supplied desktop screenshot | Smaller heading, less vertical spacing, flat starter list, bounded reading width | Desktop, phone and short-window measurements |
| Wide-screen padding squeezed the central column | Fixed region padding and centered 760px transcript/composer | 1857px screenshot; intermediate-width checks |
| Composer stayed one line while typing | Textarea grows with content to 144px; Enter sends and Shift+Enter retains multiline input | Implementation and keyboard/browser checks |
| Some controls were below the intended touch target | Send, menu, close and answer actions have 44px targets | DOM measurement for Send; computed CSS for other controls |
| All history controls became disabled during generation | Source browsing and exporting are local actions that remain available | Control-state code inspection |
| Generic preambles and repeated source labels interrupted reading | Known boilerplate preambles removed; substantive status messages and every warning preserved | Real answers and code inspection |
| Repeated generic follow-ups lost the original topic | Store the resolved educational question separately from the user's literal message; normalize punctuation/case/spacing | New route tests and live follow-up checks |
| Definition answer included an unrelated chapter mentioning the same term | Both primary retrieval and teaching fallback prefer eligible sections explicitly about the definition's subject | Synthetic lexical/hybrid/teaching tests plus live apoptosis check |

The user's dark ambient palette, local fonts, single chat, image attachment flow, prescription revision checks and local inference remain. No model weights or medical source text were changed. Important warnings remain in the answer; metadata and longer scope notes move to the panel.

## Validation

- Full Python suite: **399 passed**, one existing FastAPI/Starlette test-client deprecation warning. Evidence: `artifacts/evaluation/ui-ux-v1/pytest-release.txt`.
- JavaScript syntax check: passed using Node `--check`.
- Responsive DOM checks: **1024×768, 768×1024, 390×844, 1440×650**; no horizontal document overflow, composer remained inside the viewport, Send measured 44px. Additional screenshots cover 1440×900 and 1857×945.
- Browser interaction: actual local source-backed answers, older-answer source selection, supporting-passage expansion, phone drawer, Escape focus return. No captured browser console errors in the inspected tab.
- Final live checks: **115/115** existing teaching/context/routing probes and **9/9** new continuity, definition-relevance and policy probes (**124/124 total**). Results are recorded in `artifacts/evaluation/ui-ux-v1/live-regression-final.json` and `live-followups.json`. These are engineering checks, not a clinical accuracy percentage.
- Fresh Impeccable finish review: `finish-review.md`. Mobile safe-area padding and accessible label findings were corrected. See `finish-review-resolution.md`.

## Detector interpretation

One Impeccable detector pass was run. It could not resolve the server's `/assets/app.css` mapping from the filesystem and therefore reported a flat heading hierarchy and an off-palette default link color. The actual browser loads the CSS; screenshots and computed styles are the applicable evidence. The missing image `src` is the intentionally hidden upload preview, populated only after file selection. Typography advisory sizes are documented in DESIGN.md. The scan is not reported as a clean pass.

## Boundaries and remaining work

These results establish behavior on the tested questions and layouts. They do not establish medical accuracy, comprehensive curriculum mastery, drug coverage or clinical safety. No faculty reviewer has assessed this release. The existing faculty review pack still requires an actual reviewer.

Some answers remain full source excerpts, and follow-ups such as “tell me more” may repeat the same supported explanation. They now retain the correct topic but do not promise additional depth. Additional professionally reviewed plain-language teaching notes are still needed. The definition filter is deliberately narrow; it does not establish relevance or completeness for every clinical question.

No new OCR handwriting benchmark, X-ray diagnostic validation, model comparison or exhaustive screen-reader/device-lab evaluation was performed in this pass. Existing automated confirmation, policy and imaging-boundary tests ran with the full suite. Browsers were tested through the Codex in-app browser; phone tests emulate viewport size, not a physical device keyboard or screen reader.

The local services were restarted to load backend fixes. Existing tabs retain their displayed transcript but their old server sessions expire; start a new conversation after refreshing. The updated app is served at http://127.0.0.1:8501/.
