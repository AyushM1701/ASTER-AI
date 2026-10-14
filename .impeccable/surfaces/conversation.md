# Conversation workspace

Mode: Operate. User explicitly requested implementing the existing Figma design
locally, using Impeccable where required. The approved visual reference is
https://www.figma.com/design/bkQKRZRzwKtYCAKpo9Texv (nodes 5:8, 5:93, 8:85,
8:156 and 8:252). Saved final exports and layer evidence live in artifacts/redesign.
Live get_design_context remains blocked by the Starter-plan quota; disclose the
saved-reference fallback rather than claiming a fresh design-to-code export.

Preserve the one-chat product and real local API/inference/OCR. Replace the
Streamlit presentation with a dedicated lightweight web frontend and bounded
same-origin loopback bridge, served on the existing UI port. No cloud model fallback.

FIRST VIEWPORT: 256px navigation rail, flexible central workspace and 320px
context rail at 1440px. Ink canvas, tonal surfaces, Manrope headings, DM Sans body,
sea-glass teal. At phone width, a navigation drawer replaces the rail, the
context is accessible in a sources drawer, starter actions form a list and the composer
remains visible. Shared controls and 10/16px radii match the saved Figma design.

SIGNATURE INTERACTION: the link icon brings an actual image or authorized
selectable-text PDF into the single conversation. Image classification leads to
OCR review/confirmation or honest imaging gates. A private PDF requires a
permission declaration, page-text comparison with the locally opened original,
then explicit extraction confirmation. Confirmed current revisions alone provide
follow-up context.

QUALITY BAR: match the five approved Figma exports; readable real model and OCR
content, working keyboard-native controls, no horizontal overflow, correct service
and uncertain states, a source selector beside each answer with detailed links in its evidence panel. Motion is
limited to controls/state transitions and respects reduced motion.

Verification: desktop, phone and actual user viewport in one inspection batch,
at most one correction batch before a fresh Impeccable finish reviewer. Review
uses implementation screenshots and approved Figma exports. The approved initial
system replacement authorized updating DESIGN.md and its sidecar. Ordinary
extensions preserve that incumbent identity and tokens; record their product and
surface behavior here. No new identity workshop or concept roll is owed.

2026-10-09 refinement: compact 40px welcome, centered 760px reading/composer measure; answer-specific evidence rail and mobile modal drawer. Full citations and limitations appear only in the panel. Urgent and uncertainty notices remain in chat. The user explicitly requested this simplification, superseding the older source-card placement and oversized welcome.

2026-10-09 progressive explanations: the user requested simple explanations before detail. Render two open sections using 18px/600 headings; retain the existing reading measure, colors and responsive evidence panel. Keep source qualifications visible. Do not manufacture simple or deeper content where checked notes do not support it. Urgent and non-answer states stay direct. Presentation metadata preserves the original supported claims and citations.

2026-10-13 FR09 private-paper extension: the existing attachment dialog accepts
PDFs up to 10 MB (frontend limit and backend default) with a private-analysis
permission checkbox. Default extraction bounds are 30 pages and 240,000 characters
in a bounded local worker. Page disclosures, an original-PDF action and extraction
acknowledgement reuse the incumbent review card and controls. Exact requested
section excerpts carry an always-partial appraisal notice; Sources selects page,
section and confirmed-revision evidence in the existing rail or phone drawer.
The active paper revision is visible beside the composer. Reopening review clears
earlier paper analyses and active context; deletion also removes the attachment.
Keep image/OCR confirmation and imaging gates intact.

Private text remains in its owning temporary session, outside shared indexes,
training, public requests and saved educational exports. Safe text rendering,
source-policy and injection guards preserve explicit gaps. PDF OCR, encrypted or
textless PDFs and cross-page sections are unsupported; packaged PDF parsing is
unavailable (503), while the current source installation supports it. Confirmation
and exact extraction do not establish study quality or clinical validity.

Scoped evidence: a real synthetic PDF passed through the loopback bridge; 18
private-paper tests, 1,097 full-suite pytest tests (97.92s) and 10 Node UI tests
passed. Fresh engineering review addressed context invalidation, body source
policy and private-text cache retention. Valid finish-review captures at 1440px,
390px and the 1208px user viewport in
`artifacts/evaluation/master-2026-10-13/private-paper-v1/ui` matched the incumbent
workspace. The finish review's product/surface documentation omission is resolved
by this entry and PRODUCT.md. Existing DESIGN.md/sidecar snippet, motion and type
documentation drift is recorded without repair. This evidence covers the bounded
extension; independent clinical review and packaged acceptance remain open.

## Evidence-state extension — 14 October 2026

The existing response sections and notice styles now show a separate “General
model knowledge — not source verified” explanation where the bounded educational
route permits one. Its scope notice precedes the text. Coverage is explicitly
labelled source-backed, and Sources & context lists evidence state by claim.
The completion announcement acknowledges a displayed provisional answer without
calling it a verified or complete answer. Desktop/mobile browser checks are in
`output/playwright/inventory`; 12 Node UI tests pass. No design-system change or
new clinical validation is implied. Full implementation detail and limitations:
`docs/implementation/source_inventory_adoption.md`.
