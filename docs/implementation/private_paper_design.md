# Authorized private-paper analysis

The adopted master plan requires useful local research-paper assistance and authorized private uploads. Extend Aster's existing temporary sessions and single conversation. Keep `/v1` compatibility, ownership/revision checks and the common terminal guard. Do not route private papers into public literature search, shared indexes, saved educational projects or model training. This is an architectural extension within the already authorized master scope, not a model or storage migration.

## Data and processing

Add `Session.papers`, sharing the existing document count and byte budgets. Session deletion/expiry wipes paper text and any response context. A paper has a random ID, original PDF SHA-256, extracted page texts and hashes, a revision, confirmation state, a declared private-analysis permission and a lock. Names and content are absent from routine logs. No raw PDF is written to disk; the client retains its selected-file preview.

Accept a nonempty PDF within the configured upload limit only with explicit private-analysis authorization. Extract selectable text in a separate Python worker using the already installed pypdf dependency, no external access, a deadline, page/text limits and worker memory limits. Reject encrypted, malformed, oversized, corrupt or textless PDFs; do not manufacture OCR text. Unsupported parser/platform availability returns an honest limitation. Do not execute PDF scripts or follow links. Published packaging is not considered updated until its separate clean-machine gate passes.

## API and confirmation

Add `/v1/papers` upload, owned state, confirm, reopen/edit and delete routes. Confirmation binds the current revision and complete extracted page hashes; it does not certify medical accuracy. Every analysis checks the owning session, authorization, current confirmed revision and live session after processing. Stale or foreign context fails. A text correction, if supported, becomes a separately identified user-confirmed transcription; it never impersonates the original PDF. Initial implementation confirms exact extracted text and can reopen review.

Chat recognizes a confirmed paper context before ordinary answering. It supplies bounded exact document excerpts for requested article sections and a structured appraisal checklist with explicit missing/not-assessed items. Methods/results/limitations excerpts are source evidence, not automatic study-quality judgments. Never infer randomization, causality, sample size, effect estimates, certainty or applicability from missing text. The first version is exact extraction with a partial appraisal status, without model-generated medical paraphrases or a weaker fallback.

## Terminal validation

Extend the common finalizer with an out-of-band trusted paper context. Request JSON cannot create this context. Validate current confirmation, private-use authorization, document/version identity, page/span offsets and hashes, exact claim text, requested excerpt binding, unsupported instructions/corruption and personal-medical boundaries. Generated IDs, altered citations or changed text cannot inherit approval. Safety-rejected source units remain gaps. No result is labelled a complete qualified critical appraisal or clinical recommendation.

## Existing frontend

Extend the attachment dialog to PDFs with a private-analysis permission checkbox. Preserve image classification and prescription confirmation. Render paper page text and confirmation controls in the conversation, offer bounded document appraisal, and attach only the confirmed revision to follow-ups. Render all text through existing safe DOM helpers. Remove/reopen context and clear session explicitly reset paper state. Do not store paper text or tokens in localStorage or educational exports. Explain missing selectable text, stale revisions and incomplete appraisal without product claims of clinical validation.

## Acceptance and remaining limits

Tests must exercise actual valid selectable-text PDF parsing, foreign/stale/unconfirmed contexts, source-span/citation tampering, prompt injection, encryption/textless/size/deadline limits, shared capacity, expiry/delete and no pooling. Browser/API walkthrough uses a synthetic or licensed paper, not fabricated research results or private patient materials. Full independent appraisal, scanned-PDF OCR, table-quality reconstruction, model paraphrase validation and clean packaged Windows acceptance remain separate gates; unknown stays unknown.
