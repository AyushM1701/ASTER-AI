---
name: "Aster Medical Research"
description: "A dark ambient workspace for one local conversation."
colors:
  aster-canvas: "#0c1117"
  aster-rail: "#10171f"
  aster-surface: "#131c25"
  aster-raised: "#192530"
  aster-border: "#2a3944"
  aster-text: "#e8edf2"
  aster-muted: "#aab8c5"
  aster-accent: "#7de0cb"
  aster-accent-hover: "#a5eddc"
  aster-accent-soft: "#16332d"
  aster-amber: "#e9bf7e"
  aster-amber-soft: "#30281c"
  urgent-surface: "#392227"
  urgent-text: "#ffc2c2"
  selection-surface: "#2b685c"
  selection-text: "#fff"
  hover-rule: "#415561"
  upload-rule: "#536672"
  backdrop: "#05090dc9"
typography:
  headline:
    fontFamily: "Manrope, sans-serif"
    fontSize: "40px"
    fontWeight: 400
    lineHeight: 1.22
    letterSpacing: "-0.03em"
  headline-compact:
    fontFamily: "Manrope, sans-serif"
    fontSize: "40px"
    fontWeight: 400
    lineHeight: 1.22
    letterSpacing: "-0.03em"
  headline-phone:
    fontFamily: "Manrope, sans-serif"
    fontSize: "32px"
    fontWeight: 400
    lineHeight: 1.25
    letterSpacing: "-0.03em"
  heading:
    fontFamily: "Manrope, sans-serif"
    fontSize: "24px"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "-0.025em"
  heading-compact:
    fontFamily: "Manrope, sans-serif"
    fontSize: "22px"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "-0.025em"
  subheading:
    fontFamily: "Manrope, sans-serif"
    fontSize: "18px"
    fontWeight: 600
    lineHeight: 1.4
    letterSpacing: "-0.025em"
  body:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.6
  response:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.7
  label:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.5
  button:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "14px"
    fontWeight: 500
  brand:
    fontFamily: "Manrope, sans-serif"
    fontSize: "24px"
    fontWeight: 600
  composer:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "15px"
    lineHeight: "24px"
  composer-phone:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "16px"
    lineHeight: "24px"
  field:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "15px"
    lineHeight: "22px"
rounded:
  control: "10px"
  surface: "16px"
spacing:
  step-8: "8px"
  step-12: "12px"
  step-16: "16px"
  step-20: "20px"
  step-24: "24px"
  step-28: "28px"
  step-32: "32px"
  step-48: "48px"
components:
  button-default:
    backgroundColor: "{colors.aster-surface}"
    textColor: "{colors.aster-text}"
    rounded: "{rounded.control}"
    padding: "12px 16px"
    typography: "{typography.button}"
  button-default-hover:
    backgroundColor: "{colors.aster-raised}"
    textColor: "{colors.aster-text}"
    rounded: "{rounded.control}"
    padding: "12px 16px"
    typography: "{typography.button}"
  button-primary:
    backgroundColor: "{colors.aster-accent}"
    textColor: "{colors.aster-canvas}"
    rounded: "{rounded.control}"
    padding: "12px 16px"
    typography: "{typography.button}"
  button-primary-hover:
    backgroundColor: "{colors.aster-accent-hover}"
    textColor: "{colors.aster-canvas}"
    rounded: "{rounded.control}"
    padding: "12px 16px"
    typography: "{typography.button}"
  button-text:
    textColor: "{colors.aster-text}"
    padding: "0"
    typography: "{typography.button}"
  button-text-hover:
    textColor: "{colors.aster-accent}"
    padding: "0"
    typography: "{typography.button}"
  button-attachment:
    backgroundColor: "{colors.aster-raised}"
    textColor: "{colors.aster-text}"
    rounded: "{rounded.control}"
    padding: "10px"
  button-send:
    backgroundColor: "{colors.aster-accent}"
    textColor: "{colors.aster-canvas}"
    rounded: "{rounded.control}"
    width: "40px"
    height: "40px"
  field:
    backgroundColor: "{colors.aster-canvas}"
    textColor: "{colors.aster-text}"
    rounded: "{rounded.control}"
    padding: "12px"
    typography: "{typography.field}"
  navigation-current:
    backgroundColor: "{colors.aster-accent-soft}"
    textColor: "{colors.aster-accent}"
    rounded: "{rounded.control}"
    padding: "12px"
  badge:
    backgroundColor: "{colors.aster-surface}"
    textColor: "{colors.aster-muted}"
    rounded: "{rounded.control}"
    padding: "7px 12px"
  badge-pending:
    backgroundColor: "{colors.aster-amber-soft}"
    textColor: "{colors.aster-amber}"
    rounded: "{rounded.control}"
    padding: "7px 12px"
  card-source:
    backgroundColor: "{colors.aster-surface}"
    textColor: "{colors.aster-text}"
    rounded: "{rounded.control}"
    padding: "16px 20px"
  card-starter:
    backgroundColor: "{colors.aster-surface}"
    textColor: "{colors.aster-text}"
    rounded: "{rounded.control}"
    padding: "20px"
  card-user:
    backgroundColor: "{colors.aster-surface}"
    textColor: "{colors.aster-text}"
    rounded: "{rounded.surface}"
    padding: "20px"
    typography: "{typography.response}"
  card-review:
    backgroundColor: "{colors.aster-surface}"
    textColor: "{colors.aster-text}"
    rounded: "{rounded.surface}"
    padding: "20px"
  composer:
    backgroundColor: "{colors.aster-surface}"
    textColor: "{colors.aster-text}"
    rounded: "{rounded.surface}"
    padding: "20px"
    typography: "{typography.composer}"
  notice-warning:
    backgroundColor: "{colors.aster-amber-soft}"
    textColor: "{colors.aster-amber}"
    rounded: "{rounded.control}"
    padding: "16px 20px"
  notice-urgent:
    backgroundColor: "{colors.urgent-surface}"
    textColor: "{colors.urgent-text}"
    rounded: "{rounded.control}"
    padding: "16px 20px"
  dialog:
    backgroundColor: "{colors.aster-surface}"
    textColor: "{colors.aster-text}"
    rounded: "{rounded.surface}"
    padding: "28px"
    width: "min(540px, calc(100% - 32px))"
---

# Design System: Aster Medical Research

Dropdown refinement (11 October 2026): supported browsers use native customizable
selects with raised ink menus, teal selected rows, native check marks and 44px
option targets. Keep native form/keyboard behavior and a native fallback. Fields
use the canvas fill; focused labels use teal. Checkbox controls remain 18px
inside clickable labels. Settings action groups stack on phones. See
`docs/UI_CONTROLS_REFINEMENT_2026-10-11.md` for verification.

## Overview

**Creative North Star: "Dark Ambient Operating Workspace"**

Quiet ink surfaces and restrained sea-glass teal support a focused local research workspace. The approved Figma direction now lives in a dedicated HTML/CSS/JavaScript presentation, with local Manrope headings and DM Sans body text. Tonal layers give the ambient character without decorative light effects.

The system favors legible questions, source records and review fields over ornament. Native buttons, fields, disclosures and dialogs carry the interaction; clear state cues keep uncertainty and confirmation visible within the conversation.

**Key Characteristics:**

- Deep ink canvas with tonal rails and surfaces.
- Sea-glass teal for identity, actions, selection and focus.
- Manrope headings paired with DM Sans body text.
- Shared controls, restrained borders and responsive access to context.

## Colors

The frontmatter owns the literal CSS values; names describe their use rather than a second palette.

### Primary

Sea-glass teal (`aster-accent`) marks the asterisk identity, current conversation, assistant speaker, links, caret and focus. Its pale hover companion (`aster-accent-hover`) belongs to filled primary actions. The dark teal wash (`aster-accent-soft`) supports the current navigation row.

### Secondary

Warm amber (`aster-amber`, `aster-amber-soft`) distinguishes caution, unresolved transcription and pending review. The rose urgency pair (`urgent-text`, `urgent-surface`) supports urgent guidance; the text color also marks upload errors. These are semantic states, not additional decorative accents.

### Neutral

Deep ink (`aster-canvas`) is the central canvas and field fill. Rail ink (`aster-rail`) frames navigation and evidence; `aster-surface` holds the composer and cards, while `aster-raised` defines secondary icon controls and hover surfaces. Off-white (`aster-text`) carries reading text and blue-grey (`aster-muted`) carries supporting text. `aster-border` is the shared rule; `hover-rule` strengthens hover boundaries and supplies scrollbar thumbs. `upload-rule` is the dashed file-choice boundary.

The translucent `backdrop` is shared by modal dialogs and the phone navigation scrim. Selection uses `selection-surface` and `selection-text`; its darker teal is separate from the primary action fill.

**The Context Rule.** Use teal for interaction and context; reserve amber for pending review and caution, and the urgent pair for urgent guidance or errors.

## Typography

**Display Font:** Manrope, sans-serif. **Body Font:** DM Sans, sans-serif. Both variable fonts are served locally with `font-display: swap`; no icon font or remote font request is needed.

Manrope gives headings and the brand a quiet, open character. DM Sans carries instructions, fields and longer answers. The frontmatter records explicit roles; inherited browser metrics are not fabricated.

- **Headline:** light weight (400), desktop (40px), compact (40px) and phone (32px). Line height moves from 1.22 to 1.25 on phones; tracking stays at -0.03em.
- **Heading:** section and dialog titles (24px, 600, 1.35), compact variants (22px); **Subheading:** review titles (18px, 600, 1.4). Both use -0.025em tracking.
- **Body:** explanatory copy (15px, 400, 1.6). **Response:** preserved line breaks, wrapping at any long word, relaxed leading (1.7), maximum measure (74ch).
- **Label:** supporting text (12px, 1.5); buttons use (14px, 500). Result captions use body leading and compact text; response action buttons reduce to 12px.
- **Composer:** (15px, 24px line height), increasing to 16px on phones. **Fields:** (15px, 22px line height). Strong text uses weight 500. Score tables use tabular numbers.

## Layout

At desktop width, the full-height workspace uses navigation (256px), a flexible central column and evidence context (320px). The central column has 28px vertical and 36px horizontal padding; welcome, transcript and composer share a centered 760px maximum width. The scroll region flexes while the composer stays in the column outside that region. The workspace fits the dynamic viewport without a fixed minimum height.

Spacing follows the extracted steps in the frontmatter: compact 8/12px gaps, 16/20px component padding, 24/28px region rhythm, and 32/48px outer spacing. Starter actions form a single list separated by thin rules; review fields form two columns.

- At widths up to 1199px, rails become 232px and 280px; central padding becomes 32px vertically and 28px horizontally. The headline drops to 40px.
- At widths up to 1023px, the grid uses a 220px navigation column and flexible content. The context rail becomes a native modal sources drawer opened from an answer or the header. Escape closes it and returns focus to its opener. Starter prompts stack and composer padding becomes 16px.
- At widths up to 639px, a 280px navigation drawer replaces the rail. Central gutters become 20px with safe-area bottom padding; the headline becomes 32px. Review fields stack, attachment rows wrap, and the composer remains outside the scrolling history.
- At wide widths, fixed region padding and a centered 760px content measure avoid squeezing the conversation. At short heights, compact spacing keeps the composer visible.

## Elevation & Depth

Depth is tonal and flat: the shipped web stylesheet has no box shadows or canvas gradient. Rails and cards are distinguished by fill and thin borders. Native dialogs and the phone drawer use the shared translucent backdrop; the drawer and scrim occupy z-index 20 and 19, and the skip link uses 30.

**The Flat Surface Rule.** Use tonal fills and thin borders for depth. Keep decorative glow and shadows out of controls.

## Shapes

Control corners use the shared control radius (10px): buttons, attachment cards, fields, tags and image previews. Larger surfaces use the shared surface radius (16px): user messages, composer, transcription review and dialogs. Boundaries are generally 1px solid; the upload choice uses a dashed boundary. Tags retain the same restrained corners rather than a separate pill system.

## Components

### Buttons

Default buttons use the surface fill, shared border, body text and control radius; padding is 12px 16px with a 44px minimum height. Hover raises the fill and strengthens the rule. Primary buttons use teal with ink text, then the lighter teal on hover. Text actions keep their plain text treatment and turn teal on hover. Disabled buttons retain their native disabled behavior, reduce opacity to .45 and use the blocked cursor.

Background and border transitions last .16s with CSS default easing. Keyboard focus uses a 2px teal outline with 4px offset. The reduced-motion preference removes transitions and enforces automatic scrolling.

### Tags

Neutral tags use surface fill and muted text with 7px 12px padding. Pending tags use the amber pair. Tags identify scope or document state; they do not suggest calibrated confidence.

### Cards / Containers

Source records live only in the evidence panel, separated by horizontal rules. Each retains its supporting passage, jurisdiction, version, review status and paragraph association. Starter actions use the same flat list treatment. A compact Sources action under each answer selects its own evidence, including older answers; source browsing and export remain available while generation is busy. User turns use larger surface corners, 20px desktop or 16px phone padding; assistant answers remain open on the canvas. Review cards use surface corners and a visible border, with 20px desktop or 16px phone padding.

### Inputs / Fields

Labeled review fields use the ink fill, shared border and control corners with 12px padding. Placeholder and label text remain muted; carets and checkbox accents use teal. Confirmation includes a native acknowledgement checkbox, revision context and unresolved-field feedback. Unknown transcription stays unresolved until the user reviews and confirms it.

### Navigation

The current conversation uses a dark teal wash with teal text and 12px padding. Session controls sit below the identity and current context; supporting controls sit at the foot of the rail. The phone drawer has a .2s ease-out transform transition, scrim dismissal, Escape handling and a wrapped Tab sequence. Closed phone navigation is inert; opening it makes the conversation inert, focuses its New conversation control and updates the menu's expanded state. Escape returns focus to the menu. Native dialogs handle modal behavior.

### Conversation composer and attachment

The composer uses the surface fill, shared border, surface corners and 20px desktop padding. Its border becomes teal on focus within; the textarea avoids an additional outline. The link-icon attachment control uses a raised fill, border and 44px minimum hit area. The send control is a separate teal 40px square. Local SVG paths provide the icons.

The attachment dialog uses native file selection, image preview and explicit attachment submission. An actual PNG/JPEG up to 10 MB enters the single transcript, then local classification leads to OCR review or eligible imaging gates. Context follows only a confirmed current transcription revision. Native disclosures expose supporting passages and limitations inside the evidence panel, and original images inside the conversation. Clinical warnings and urgent guidance remain visible in the answer. Multiline message entry grows up to 144px; Send and close controls have 44px targets.

A persistent visually hidden polite, atomic status announces concise asynchronous outcomes after rendering. History stays static outside that live region. Busy state and useful failure text remain visible; the implementation evidence confirms accessibility-tree exposure, not an actual screen-reader audit.

## Do's and Don'ts

### Do:

- **Do** reuse the control and surface radii, tonal fills and shared button treatments.
- **Do** retain visible labels, native controls, keyboard focus and reduced-motion behavior.
- **Do** keep source selection beside its answer, with detailed citations in the right panel or mobile drawer. Keep uncertainty and confirmation cues in the conversation.
- **Do** preserve one conversation and the link-icon attachment entry point.

### Don't:

- **Don't** add glowing controls or decorative animations.
- **Don't** add decorative medical illustrations, invented health metrics, confidence badges or fake activity charts.
- **Don't** render user or model content as unsafe HTML.
- **Don't** imply that category routing or confirmed transcription establishes clinical validity.

Extraction authority: `frontend/web/app.css`, `frontend/web/index.html` and `frontend/web/app.js`; `frontend/webserver.py` serves the default presentation. `PRODUCT.md` records the approved system replacement. The Streamlit presentation remains a legacy fallback and does not supply normative tokens here. Approved saved Figma references live in `artifacts/redesign`; implementation review screenshots live in `.impeccable/review`. Live Figma context was quota-blocked, so this extraction claims no fresh design export.

The introductory and context labels are specific copy and treatment from the approved Figma conversation surface. They are not promoted to a reusable convention for new screens. This documentation pass makes no UI correction. Sidecar tonal ramps are synthesized previews, not added implementation palette values.

## Conversation refinement · 2026-10-09

Informational responses progress through two visible sections: **Simple explanation** and **Deeper explanation**. Their 18px/600 headings sit over existing 15px body text, with 10px internal gaps and 24px between sections. No nested cards or extra toggles. Research qualifications remain visible before the affected explanation. Sources in the evidence panel identify which explanation layer they support. Urgent guidance, missing evidence and confirmation requests remain direct. Original claims remain intact in exported responses; presentation sections add no unsupported medical detail.

2026-10-10 F21 exception: general symptom information starts with its plain meaning, then uses the existing section typography for possible causes, relevant context, uncertainty, professional follow-up and urgent warning signs. It does not use the student Simple/Deeper headings. Multipart answers retain each component's response type. Original passages, dated attribution, reuse licence and pending independent clinical review remain in the evidence panel. Missing components and urgent action remain visible in the conversation. Dark ambient styling, reading measure, source drawer and student presentation are preserved.

User-authorized answer-first refinement. The prior Figma identity remains; its oversized introduction, source duplication and numbered generic context are superseded. The evidence heading uses 20px Manrope; supporting passages use 13px, with 12px metadata and existing 11px compact footnotes. Source links use descriptive titles without calling retailer datasets primary references. Phone layouts preserve safe-area bottom padding. Verification and known limits: `ASTER_UI_UX_REVIEW.md`; screenshots and test outputs: `artifacts/evaluation/ui-ux-v1`.

## Interaction refinement · 2026-10-11

The composer groups its task label and selector in one compact row, with 14/18px desktop padding and 10px internal gaps. It keeps the existing 10/16px radii and ambient palette. Native disclosure arrows use restrained rotation, controls use 140ms feedback and dialogs use 220ms arrivals with `cubic-bezier(.16,1,.3,1)`. Reduced-motion styling removes animated movement while retaining immediate feedback. The phone evidence drawer moves from its edge; navigation movement occurs only on user open/close actions. No decorative loops or lighting effects.

Prepared study topics have a local filter, result count and collapsible activity declarations. Workspace headings remain reachable while scrolling. Busy controls announce their action and suppress repeated submissions; saving preserves newer edits. Destructive saved-work actions require inline confirmation. Evidence and medical qualifications retain their existing placement and wording. Verification and constraints: `docs/UI_INTERACTION_REFINEMENT_2026-10-11.md`.
