# Local interface assets

The default interface loads no third-party scripts, fonts or images. The two
variable Latin fonts are self-hosted under `fonts/`, with their SIL Open Font
License files alongside them. They were obtained from Google's official font
distribution; `artifacts/redesign/font-source.css` records the font URLs.

Small SVG icons use the exact Lucide geometry imported into the approved Figma
design (Iconify/Lucide, ISC license). CSS masks apply the interface's semantic
colors. No screenshots or rasterized UI layers ship as interface components.
`icons/Lucide-LICENSE.txt` retains the upstream permission and attribution text,
including the Feather-derived icon license notices.

`/sample-prescription` serves the existing synthetic OCR fixture, explicitly
labeled in its image. Uploaded images appear only as temporary local blob
previews and as owned API session records.

Design references: `artifacts/redesign/figma-*.png` and `figma-state.json`. The
Figma live-context quota blocked a new design export during implementation;
these previously inspected references supplied the design direction.
