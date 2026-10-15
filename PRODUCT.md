# Product
<!-- impeccable:product-schema 1 -->

## Platform
web

## Stack
Python, FastAPI, dedicated HTML/CSS/JavaScript web frontend, local inference
adapters. The original Streamlit presentation remains a legacy fallback.

## Users
Patients seeking understandable education and MBBS/MDS students studying or
working with research evidence, in a single-user local development pilot.
Clinical deployment and independently validated medical accuracy remain outside
the current release evidence.

## Product Purpose
Keep health questions, image attachments and authorized private papers in one
conversation. Explain cited reference information or explicitly qualified
pretrained-model knowledge, review prescription transcription, inspect confirmed
paper excerpts, and expose eligible research imaging outputs.

## Positioning
One local workspace that serves two audiences, patient education and MBBS/MDS
research-paper study, through a mechanism a general health chatbot cannot
honestly copy: inference stays on the device with no cloud fallback, claims
trace to local cited records, unverified model knowledge is labelled as such,
and documents (prescriptions, private papers) are explained only after the
user confirms the extraction.

## Operating Context
Windows desktop, loopback services, English first. Same-origin browser requests
through a bounded server-side web bridge.
Reference corpus persists; document and session state expire in memory.
Opt-in educational progress/projects persist separately on local disk, with
export/delete controls. Public literature queries go to Europe PMC only after
explicit confirmation; there is no cloud inference fallback.

## Capabilities and Constraints
One transcript and a link-icon attachment control accept PNG/JPEG images and
selectable-text PDFs up to 10 MB (the frontend limit and backend default).
A local pretrained Qwen3-VL 2B Instruct model examines image pixels and routes
prescription, X-ray, other or uncertain images; this is inference, not custom
training, authenticity verification or medical interpretation.

Prescriptions use Tesseract OCR and require explicit field confirmation before
explanation. Missing or unreadable fields remain unresolved. Confirmed text can
support follow-up questions; editing requires confirmation again.

Private PDFs require an explicit declaration of permission for private analysis.
A bounded local worker extracts at most 30 pages and 240,000 characters by default.
The user compares extracted page text with the original PDF, then confirms the
current revision. Confirmed papers support exact section excerpts and follow-ups
with page and revision evidence; critical appraisal always remains partial.
Confirmation verifies extraction review, not study quality or medical accuracy.

Paper text stays in the owning temporary session, without shared indexing,
training, public search requests or saved educational exports. Reopening review
invalidates confirmation and clears prior analyses and active context; deletion
also removes the paper. Source-policy and injection checks withhold unsafe units
and leave explicit gaps. PDF OCR, encrypted/textless PDFs and sections continuing
across pages are unsupported. Parsing works in the current source installation;
the packaged runtime returns an unavailable response (503). Independent appraisal,
validated medical paraphrase and packaged acceptance remain separate gates.

X-ray category routing does not authorize scoring. Specialist research scoring
remains unavailable until specialist weights and a reviewed, registered, permitted
adult frontal chest image satisfy the existing gates. No clinical validation,
universal accuracy claims, diagnosis, prescription generation, personal dosing,
X-ray normality verdicts or calibrated probabilities.

Urgent guidance runs independently of model availability. Ownership, current
revisions, source sufficiency, retry and honest unavailable states remain explicit.
Session controls clear the conversation or start a new session; image and document
state stay temporary. Local inference has no cloud fallback.

## Brand Commitments
User explicitly requested Impeccable and dark ambient mode on 6 October 2026.
The user subsequently approved implementing the saved Figma Aster conversation
workspace design locally, replacing the default presentation. That approval
covers refreshing the visual system documentation to match the implementation.
Working product name: Aster Medical Research (implementation choice).

## Evidence on Hand
Internal repository artifacts only: pilot and baseline outputs under `artifacts/`
(including `artifacts/baselines/`), the saved Figma Aster exports, and Playwright
captures under `output/playwright/`. There are no testimonials, external users,
public accuracy figures, press or independent validation; future work must not
fabricate or imply any.

## Product Principles
Trace source-backed claims to the local reference records and show their citations.
When enabled, uncovered questions can use pretrained-model knowledge: explicitly
label it as unverified against local sources, potentially inaccurate or outdated,
and without local citations. Never invent citation support or research results.
For eligible educational concepts, the local teaching profile now shows that
provisional explanation as a separately labelled section after source retrieval.
Source-backed coverage remains separate; an unverified explanation cannot make
a task complete. Unknown extra subjects, medicine decisions, personal care and
image interpretation do not enter this bounded fallback. Each admitted claim's
evidence state is available in Sources & context. These checks are not clinical
validation, and the small local model can still give incomplete explanations.
Keep uncertainty and scope visible. Require confirmation before document
explanations. Make setup, outage, unsupported and uncertain states useful.

## Accessibility & Inclusion
Target WCAG 2.2 AA: full keyboard operation, visible focus, readable contrast
in the dark ambient theme, and respect for reduced-motion preferences.
