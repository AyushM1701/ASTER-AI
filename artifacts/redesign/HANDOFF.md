# Aster redesign handoff

User requested Replit and Figma to redesign the whole project. The prior single
chat and dark ambient preferences remain binding.

Figma: https://www.figma.com/design/bkQKRZRzwKtYCAKpo9Texv

Five editable screens: desktop welcome (5:8), prescription review (5:93), cited
answer (8:85), unavailable X-ray analysis (8:156), and mobile welcome (8:252).
They are assembled from local components with bound color, spacing and radius
variables, plus Manrope and DM Sans text styles. The desktop roots were read back:
84/100 descendants, including editable text, instances and vectors, with no image
fills and no flattened UI. The remaining roots return IDs/dimensions in their
construction evidence. All five final screenshots were visually inspected;
multiline text sizing was repaired before the final captures.

19 variables, seven text styles, six button variants, shared attachment controls,
composer, starter prompts and review fields. IDs and evidence are in
figma-state.json. Local component masters remain outside the final screen frames.
Icons are editable SVG imports from Iconify's Lucide collection; screenshot
exports are references, not layers in the Figma deliverable.

Figma's Starter-plan tool-call limit prevented the final consolidated read-back.
It did not prevent exporting and visually checking all five screens. No independent
full accessibility audit, component-master screenshot audit or clickable Figma
prototype wiring is claimed.

The initial Replit dispatch could not create an app because Replit required an
active subscription. `replit-dispatch.json` preserves that result; there is no
completed Replit implementation. The user subsequently requested implementing
the Figma design locally, which is now the default `start.ps1` frontend.

`frontend/web/` implements the approved dark ambient design on the existing
FastAPI/Ollama/OCR services through `frontend/webserver.py`. The live Figma design
context request remained quota-blocked, so implementation used these saved
screen exports and layer metadata. No fresh Figma code export is claimed.
Synthetic Figma examples are reference material; the running app displays actual
API responses and explicitly labels unverified model knowledge.

The Replit request covers one chat, real attachment selection, automatic four-way
classification when a vision service is available, OCR and field confirmation,
revision-aware context, cited versus uncited answers, retries and service settings,
session clearing, responsive layout, and the existing specialist imaging gates.
No publication is requested. Creation is asynchronous; completion or successful
integration must not be inferred from dispatch.
