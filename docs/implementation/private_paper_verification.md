# Private paper development checkpoint

The authorized FR-09 extension now accepts selectable-text PDFs in the existing conversation. The owner declares permission for private analysis, reviews extracted pages against the original, and confirms the current revision. Follow-ups return exact section excerpts bound to the PDF, page, revision and character span. Appraisal remains partial; this does not establish study quality, causality, clinical correctness or a complete critical appraisal.

The source installation uses a separate bounded pypdf worker with memory, time, byte, page and character limits. Raw upload bodies avoid multipart disk spooling. The session retains extracted pages and the PDF digest, not raw PDF bytes. Papers share image upload capacity and remain outside public search, shared indexes, training and educational exports. The browser retains the selected file temporarily for local comparison. Session clear, expiry or deletion wipes held paper objects; reopening invalidates prior analysis on both server and client.

Encrypted, textless and active-script PDFs are rejected. Sections crossing pages are withheld because a continuation can contain qualifications. Tables, columns, OCR and extraction quality remain limitations. Packaged runtime PDF support returns an explicit unavailable response; no packaging acceptance is claimed.

## Reproduced defects and corrections

- An unsafe prescribing quote bypassed source policy. Paper bodies now use the established policy predicate.
- A non-success status bypassed the private-context guard. Context checks now precede every status branch.
- The public policy cache retained private text. Papers now use the shared uncached predicate; public caching remains unchanged.
- Relabelling private citations as public bypassed the guard. Private URI, source/chunk identity and paper channels require trusted context even when labels change.
- The sources panel omitted initial paper analysis. Its selection and fallback now include paper analysis.
- Reopening left old client excerpts visible. Reopening/deletion now invalidate the previous paper analyses and active context.

Each regression failed before correction. Engineering review verified the reported fixes. The Impeccable reviewer accepted the retained desktop/phone composition, required product/surface documentation repair, and subsequently scored that repair resolved. This scoped verdict does not certify the whole app or the medical content.

## Actual browser evidence

An explicitly fictional PDF went through the real same-origin bridge and real PDF worker on isolated API/frontend ports 8011/8511. The observed flow was selection → explicit permission → extraction → current-revision confirmation → section excerpts → methods/limitations follow-up → reopen at revision 3 → removal of prior analyses/context → delete. Existing owner services on 8000/8501 were preserved.

Captures are in `artifacts/evaluation/master-2026-10-13/private-paper-v1/ui`: 1440×1000 desktop, 390×843 phone and 1208×715 current browser viewport. The one mechanical detector could not resolve the runtime `/assets/app.css` route during static analysis; its default type/color findings do not describe the loaded browser view. Hidden image preview and incumbent type/radius advisories were assessed in the scoped visual review. No new design identity or assets were introduced.

## Remaining acceptance gates

FR-09 is partially implemented. Model-generated source-scoped synthesis, structured study metadata/numeric appraisal, robust table/column handling, OCR, complete critical appraisal, packaged-runtime support and qualified independent assessment remain unfinished. Private paper excerpts do not enter the staged medical source pack and do not improve its All-MDS coverage. Full source coverage, training/calibration, independent labels and clean-machine/resource gates remain open in the main requirement ledger.

Exact final test counts, code/source hashes and the frozen 111-turn MDS regression are recorded in `artifacts/evaluation/master-2026-10-13/private-paper-v1/checkpoint.json` after verification. Earlier checkpoints remain preserved.
