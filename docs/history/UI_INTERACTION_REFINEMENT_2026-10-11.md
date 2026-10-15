# UI and interaction refinement — 11 October 2026

The user requested analysis and refinement of the existing dark ambient interface. The one-chat layout, evidence panel, typography, palette, medical claims and API contracts are retained.

## Findings and changes

- The task label and full-width selector occupied separate composer rows, leaving a roughly 235-pixel composer and clipping starter actions at 1280 × 720. They now share one compact row. The composer measures 159.2 pixels on desktop and 163.2 pixels on the tested phone viewport. All three desktop starter actions fit above it.
- The 43-topic list required scanning dense activity descriptions. A local topic/alias filter now gives matching counts, a useful empty state, a Clear action and Escape to reset. Detailed activity declarations remain available under native disclosure controls; faculty-review qualifications remain visible.
- Buttons, fields, disclosures, upload controls and navigation now have consistent hover, active, disabled and focus treatments. Controls use 140 ms feedback; dialogs use 220 ms arrivals. Phone evidence enters from its actual drawer edge. Drawer transitions activate only for user interaction, avoiding a navigation sweep when the viewport changes.
- Reading scroll transitions respect the reduced-motion preference. CSS removes animation/transitions when reduced motion is requested; status text and immediate state changes remain visible. No new animation library or persistent visual effect was added.
- Shared pending feedback supplies disabled controls, busy labels and `aria-busy`, suppressing repeated activations. When disabling a control causes focus to be lost, completion restores it only if the user has not moved to another field.
- Draft saving captures the submitted text and project revision. Edits made during the request remain unsaved, and switching projects cannot overwrite the active editor with another save response.
- Independent review found that two overlapping draft loads could pair project B with project A's text. A load-generation guard now rejects stale results and cancels pending editor loads on navigation or deletion. The actual-function regression test first reproduced this failure and then passed after repair.
- Delete-all had no pending lock. It now shows Deleting… and suppresses repeated requests. Individual study-history and project deletions require inline confirmation; Keep receives initial focus and is disabled while the committed deletion request is running. Opening a confirmation does not delete data. The browser cancellation check retained both the study attempts and the research project.
- Export controls announce prepared downloads. The educational workspace has a sticky title/return control, grouped forms and consistent input sizes. Phone text inputs use 16-pixel text and key controls have 44-pixel touch targets.

## Verification

- Five Node interaction tests pass: repeated activation, failure-state restoration, newer-edit preservation, focus restoration without stealing it, and out-of-order project loading.
- Thirteen scoped Python tests pass for the web bridge, educational API and presentation bindings. One existing Starlette/httpx deprecation warning remains. The full 664-test source suite from the preceding implementation is historical evidence; it was not rerun for this frontend-only pass.
- Both JavaScript files pass syntax checks; scoped Ruff checks pass.
- Real-browser checks: Enter sends a study question, source-backed Simple/Deeper sections render, filtering epithelium gives 3 of 43 topics, an unknown term gives an empty state, Escape resets to 43, existing projects/drafts reopen and explicitly save, and the phone sources dialog receives focus and restores it to Sources on Escape.
- Desktop 1280 × 720 and phone 390 × 844 show no horizontal document overflow. Phone task selector and send control measure 44 pixels. The sources dialog uses the intended 0.22-second animation. No console errors were captured.
- A fresh focused code reviewer found the two load/delete issues above, then confirmed their fixes without remaining blocking findings. The focus repair also has its own passing regression test.

Screenshots: [desktop](../../.impeccable/review/interactions-2026-10-11/desktop.jpg), [phone answer](../../.impeccable/review/interactions-2026-10-11/mobile.jpg).

The selected browser did not expose media-preference emulation; the reduced-motion branch was inspected in CSS rather than tested by changing the user's system preference. This pass does not claim Safari/Firefox or real-device testing. The static detector could not resolve the root-relative stylesheet and reported the intentionally empty hidden upload preview; its report is not a clean visual certification. Actual DOM, computed sizes and screenshots were used for verification. Existing Impeccable design-sidecar drift remains separately pending.

The original user tab is preserved. Refresh the application to load the changed static files; the backend does not need restarting. Medical validation and curriculum/research coverage are unchanged by this interface refinement.
