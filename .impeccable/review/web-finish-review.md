disposition: fix

## Direction/fidelity

The implementation retains the approved Figma world: ink canvas, tonal rails, sea-glass teal, Manrope headings, DM Sans body, restrained outlined controls, and the shared conversation. At 1440×960 the 256px navigation and 320px context rails match the contract. Desktop welcome hierarchy, attachment composer, source placement, prescription fields and imaging gate are recognizably derived from the five saved Figma exports.

The mobile and actual-user captures use the intended drawer, stacked starters and visible composer. At the shorter user viewport the third starter continues inside the scrollable conversation; it is not missing. Real OCR fields and backend limitations legitimately require more scrolling than the synthetic Figma review. The implementation does not need to remove those facts to imitate the shorter reference. Differences in starter widths, vertical spacing and helper copy do not undermine the approved task or visual hierarchy. This is a saved-export fidelity review, not a fresh Figma code export or pixel-perfect certification.

## Craft-floor assessment

The captures are valid, loaded and readable. Local font declarations, explicit heading sizes, consistent authored SVG icons, restrained surface elevation, 10/16px radii, clear primary actions, wrapped response text, themed selection/caret/scrollbars and visible focus styling meet the relevant floor. Muted body and placeholder colors remain readable against the ink and tonal surfaces. Approved Figma headings and introductory labels remain the governing visual authority.

Both non-advisory detector findings are false positives on the rendered artifact: the preview image is hidden until JavaScript assigns its selected blob URL, and the CSS declares 48px/32px h1 and 24px h2 rather than the parser's unresolved 16px roles. DESIGN.md palette/type advisories reflect the pending approved-system documentation update; they do not indicate visible drift from the saved Figma system. No second detector was run.

## Behavioral/accessibility assessment

Code supports one conversation, pixel-based attachment routing, editable OCR drafts, explicit required acknowledgment, revision-aware confirmation, confirmed context removal on edit, adjacent reference links, honest unverified model labels, and imaging eligibility gates. The supplied browser verification covers real OCR/classification, source-backed and general questions, revision changes, the unavailable imaging gate, and drawer keyboard behavior. Native dialogs, labels, reduced-motion handling, inert inactive phone regions and the drawer Escape return are present.

The supplied 76 passing tests, Ruff and JavaScript syntax checks support the bridge and API behavior. They do not establish clinical validation or a complete accessibility audit. One concrete asynchronous accessibility defect remains below.

## Material findings

1. **[P2] Announce asynchronous completion and failure.** `frontend/web/index.html:45` renders the conversation without a live/completion mechanism. The routine request announcement is `#pending` at line 46; `frontend/web/app.js:50` hides it and replaces the history when a request finishes. Ordinary answers, attachment classification, successful transcription confirmation, and non-urgent result errors are then inserted as static content. `aria-busy` alone does not announce those results. A screen-reader user receives the thinking/examining cue but no corresponding ready, review-required, unavailable or failed cue. Add a persistent polite status mechanism with a concise, outcome-specific completion announcement after rendering. Preserve the detailed result for normal document navigation. Do not make the entirely recreated history a live region that repeats previous turns. Verify answer, attachment review, confirmation and service-failure completion cues without stealing composer focus. Visual layout should remain unchanged.

## Disposition/limits

**fix** — resolve the single material finding in one batch, recapture the required desktop, mobile and actual-user viewports, and return the change with completion-announcement verification for a verdict on that finding. All required workflow captures were inspected: `web-source.png`, `web-review.png`, `web-review-fields.png` and `web-xray.png`. No recapture is owed for malformed evidence and no visual rebuild is warranted.

This review uses screenshots and source code; it did not operate a browser, test a screen reader, validate medical behavior, or perform an exhaustive accessibility/security audit. The older `web-general-live.png` was not used as final fidelity evidence. DESIGN.md and its sidecar still need the approved-system documentation handoff after the final fix.
