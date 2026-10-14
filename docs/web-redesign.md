# Figma conversation workspace implementation

The user approved building the saved Aster Figma design locally with Impeccable.
The default launcher now serves `frontend.webserver:app`, a dedicated web UI,
instead of the previous Streamlit presentation. There is no completed Replit
app: the earlier dispatch required an active Replit subscription.

The implementation uses the previously inspected Figma screen exports and layer
metadata in `artifacts/redesign/`. Figma's Starter-plan quota blocked live design
context during this turn. The saved reference fallback was disclosed; no new
Figma code export or pixel-perfect certification is claimed.

The design retains the ink canvas, sea-glass teal, Manrope headings, DM Sans body,
three-column desktop shell, stacked phone prompts and persistent composer.
Native dialogs handle image selection, connections and session clearing. On
phones, the navigation drawer hides inactive content from keyboard focus and
restores focus on Escape; evidence remains available through a disclosure.
The user can attach PNG/JPEG images with the link control in the same chat.

The existing local model, reference store, image classifier, OCR state machine,
confirmation/revision checks and specialist imaging gates remain the functional
source. The same-origin bridge only forwards allowlisted API routes to a fixed
loopback destination, with original bearer tokens and revision payloads.

## Verification

- 76 automated tests passed, including seven new bridge checks for static assets
  and headers, cross-site rejection, owned revision payloads, multipart bytes,
  route/body bounds, upstream outage and invalid host rejection. One existing
  Starlette/httpx TestClient deprecation warning remains.
- Python lint and JavaScript syntax checks passed.
- Actual browser flows used the running local model/API: file chooser selection,
  pixel classification, synthetic prescription OCR, explicit confirmation and
  reference explanation, edit invalidation, cited blood-pressure answer, pending
  draft preservation during chat, and an uncited general-model answer.
- A permitted CC0 chest image was classified as X-ray and blocked from specialist
  scoring because it has no reviewed registration. No scores or diagnosis were
  fabricated; verified specialist weights also remain absent.
- Final layout captures cover 1440×960 desktop, 390×844 phone and the actual
  approximately 494×715 browser viewport. The composer remains visible and the
  main chat scrolls at shorter heights. No horizontal overflow was observed.
- The fresh Impeccable review retained the visual design and requested one
  accessibility correction: concise completion announcements. A persistent
  polite status now reports outcomes after rendering without rereading the
  reconstructed chat history or moving focus. Targeted callback checks cover
  eight API-shaped success, review, stale and failure outcomes, including the
  bridge's service-unavailable response. These fixtures are not a live outage
  or screen-reader test; real answer/review/confirmation cues are checked in
  the browser's accessibility tree separately.
  A deliberately invalid, nonmedical upload also verified an ordinary live API
  rejection cue; the cited-answer flow retained composer focus.
  The reviewer's verdict is **ship**, scoring this single finding resolved; that
  verdict covers the listed correction rather than a new full accessibility audit.

Evidence is in `.impeccable/review/web-*.png`. The one detector run is preserved
in `web-detector.json`: static HTML analysis could not resolve the web server's
`/assets/app.css` route, so its unstyled hierarchy finding is unsupported by the
actual rendered screen. The empty-src warning refers to the hidden attachment
preview, whose src is assigned only after file selection. Typography/color
advisories compare against the prior Streamlit design documentation; the approved
Figma system replaces it through the final documentation handoff.

No clinical validation, broad classifier accuracy, full accessibility audit or
public deployment is implied by these engineering checks.
