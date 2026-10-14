# Dropdown and form refinement — 11 October 2026

Aster's native Windows dropdown used a bright selection strip and a separate
grey arrow area. The task picker, study self-assessment, research article type,
and record limit now share the dark ambient control treatment.

## Implementation

- Use native customizable selects (`appearance: base-select`) inside a CSS
  feature query. The browser still owns selection, keyboard interaction,
  dismissal, focus, form values and popup positioning. No custom JavaScript
  combobox, dependencies or duplicate form state were introduced.
- Dark raised menus, 44px option rows, teal selected options and native check
  marks. The native arrow rotates when the menu opens. Focus outlines match
  other controls. Popup height is bounded and scrollable.
- Unsupported browsers retain their native select presentation and behavior.
  The custom menu is not claimed to be available on every browser version.
- Study/research inputs, transcription fields, topic search and the draft editor
  now share ink field fills and clearer label/focus/hover feedback. Invalid
  text fields gain an amber border after interaction; native validation remains.
- Fixed a general input minimum-height rule that stretched research checkboxes
  to 44px. Checkboxes are 18px with clickable labels and a label-level focus ring.
- Settings connection rows have consistent separators. Dialog actions form a
  spaced horizontal group on desktop and full-width vertical buttons on phones.
- Selected document context has a quiet separator; review drafts have a
  consistent reading line-height and vertical resizing.

Only `frontend/web/app.css` and `frontend/web/index.html` changed in application
code. Medical processing, research permissions, saved records and APIs are
unchanged. The existing dark palette, fonts, source rail and single chat remain.

## Verification

- 13 scoped Python web/education/presentation tests passed (5.82 seconds).
  Existing Starlette/httpx deprecation warning remains.
- All 5 existing JavaScript interaction tests passed (73.85 ms).
- In-app Chromium: inspected desktop 1280 × 720 and phone 390 × 844 together.
  Confirmed `base-select` support and rendered dark menus. No page horizontal
  overflow on either viewport; phone task control is 44px tall with 16px text.
- Native Arrow Down + Enter committed `Understand`; Escape dismissed the menu
  without changing selection and kept focus on the task control. Pointer
  selection of Research & Write opened the existing research workspace.
- Article type changed to scoping review planning; maximum records changed to
  5. These were unsaved UI selections; no public query or deletion was submitted.
- Research checkboxes measured 18px. Mobile settings actions fit within the
  dialog. Browser console reported no errors.

Proof: `.impeccable/review/dropdowns-2026-10-11/desktop-dropdown.png`,
`mobile-dropdown.png`, `mobile-research.png` and `mobile-settings.png`.

No new implementation-mirroring tests were added for this reversible styling
change. No full medical benchmark, real-device test or unsupported-browser
simulation was performed. Reduced motion continues to suppress transitions;
the picker arrow explicitly follows that preference. Existing Impeccable
sidecar drift was not repaired as a side effect.
