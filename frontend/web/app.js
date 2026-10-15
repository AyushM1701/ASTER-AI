'use strict';

// Model output and document text only enter the DOM through textContent.
const $ = id => document.getElementById(id);
const state = { token: null, health: {}, entries: [], activeDocument: null, busy: false, expired: false, selection: null, selectionURL: null, controller: null, starting: false, evidence: null, vivaQuestionId: null };
let workspaceKey = null, educationalSaving = false, editingProject = null;
const libraryState = { adding: false, timer: null, maxBytes: null, processing: 0 };
let editLoadVersion = 0;
const unsavedDrafts = new Map();
try { workspaceKey = localStorage.getItem('aster.education.key'); educationalSaving = localStorage.getItem('aster.education.enabled') === 'true' && /^[a-f0-9]{64}$/.test(workspaceKey || ''); } catch { /* Private browser modes may disable local storage. */ }
const kindNames = { prescription: 'Prescription', xray: 'X-ray', other: 'Other image', uncertain: 'Unclear image' };
const fieldNames = { medication_name: 'Medicine name', medicine_name: 'Medicine name', strength: 'Strength', formulation: 'Formulation', route: 'Route', frequency: 'Frequency', duration: 'Duration', document_text: 'Document text' };

function el(tag, cls, text) { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; }
function icon(name) { const n = el('span', 'icon icon-' + name); n.setAttribute('aria-hidden', 'true'); return n; }
function text(parent, content, cls = 'response-text') { if (content) parent.append(el('p', cls, content)); }
function action(label, fn, primary = false) {
  const n = el('button', 'button' + (primary ? ' primary' : ''), label); n.type = 'button'; n.disabled = state.busy;
  n.addEventListener('click', () => AsterInteractions.withPending(n, fn, 'Working…', () => !enabled()).catch(() => announce('This action could not finish. Check connections and retry.')));
  return n;
}
function disclosure(parent, label, content, open = false) { const n = el('details', 'disclosure'); n.open = open; n.append(el('summary', '', label)); const body = el('div'); content(body); n.append(body); parent.append(n); return n; }
function safeURL(value) { try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null; } catch { return null; } }
function link(parent, label, href) { const value = safeURL(href); if (!value) return; const n = el('a', '', label); n.href = value; n.target = '_blank'; n.rel = 'noopener noreferrer'; parent.append(n); }
function announce(message) { $('notice').textContent = message || ''; $('notice').hidden = !message; }
function completionSummary(result, fallback = 'The result is ready in the conversation.') {
  if (!result) return fallback;
  if (result.provisional_explanation) return 'A provisional explanation is ready. It is not source verified; source-backed coverage remains incomplete.';
  if (['error', 'busy', 'unsupported_input', 'quality_rejected', 'insufficient_evidence'].includes(result.status)) return 'Action could not finish. ' + (result.message || 'Review the result and retry.').slice(0, 240);
  if (result.status === 'urgent_guidance') return 'Urgent guidance is available in the conversation.';
  if (result.intent === 'paper' && result.status === 'needs_confirmation') return 'The paper extraction needs review and confirmation.';
  if (result.answer_method === 'private_document_exact_extraction') return 'Confirmed paper excerpts are ready. Critical appraisal remains incomplete.';
  if (result.status === 'needs_confirmation' && !result.classification) return 'The current transcription needs review and confirmation.';
  const kind = result.classification?.kind;
  if (kind === 'prescription') return 'Prescription transcription is ready for review. Compare and confirm its fields in the conversation.';
  if (kind) return 'Image classified as ' + (kindNames[kind] || 'unclear image') + '. Review the workflow result in the conversation.';
  if (result.answer_method === 'ollama_model_knowledge') return 'Aster’s answer is ready. It uses unverified model knowledge.';
  if (result.citations?.length) return 'Aster’s answer is ready with cited references.';
  return fallback;
}
function enabled() { return Boolean(state.token) && !state.expired && !state.busy; }
function updateControls() {
  document.querySelectorAll('#education-panel button, #education-panel input, #education-panel select, #education-panel textarea').forEach(control => { control.disabled = state.busy || !state.token || control.dataset.pending === 'true'; });
  for (const id of ['export-education', 'delete-education', 'save-draft']) $(id).disabled = state.busy || !state.token || !educationalSaving || $(id).dataset.pending === 'true';
  $('clear-topic-filter').disabled = !enabled() || !$('topic-filter').value;
  for (const id of ['message', 'attach', 'upload-submit', 'sample', 'starter-question', 'starter-prescription', 'starter-xray']) $(id).disabled = !enabled() || (id === 'upload-submit' && !state.selection);
  $('send').disabled = !enabled() || !$('message').value.trim();
  $('paper-authorized').disabled = !enabled();
  if (isPaperFile(state.selection)) $('upload-submit').disabled = !enabled() || !$('paper-authorized').checked;
  $('library-submit').disabled = !state.token || state.expired || libraryState.adding || !$('library-file').files.length || !$('library-rights').checked;
  $('new-chat').disabled = state.busy || state.starting;
  $('clear-session').disabled = state.busy || !state.token;
  $('confirm-clear').disabled = state.busy;
  document.querySelectorAll('.messages button:not(.local-action), .messages input').forEach(control => { control.disabled = !enabled() || control.dataset.pending === 'true'; });
  $('session-label').textContent = state.expired ? 'Session expired · start a new conversation' : state.starting ? 'Connecting locally…' : state.token ? 'Active · temporary local session' : 'No active session';
  $('active-context').hidden = !state.activeDocument;
  $('active-context-label').textContent = state.activeDocument ? (state.activeDocument.intent === 'paper' ? 'Confirmed private paper' : 'Confirmed transcription') + ' · revision ' + state.activeDocument.revision : '';
  $('pending').hidden = !state.busy;
  $('messages').setAttribute('aria-busy', String(state.busy));
}
async function request(path, { method = 'GET', json, body, signal, responseType = 'json', contentType } = {}) {
  const headers = { 'X-Aster-Client': '1' };
  if (state.token) headers.Authorization = 'Bearer ' + state.token;
  if (educationalSaving && workspaceKey && /^\/v1\/(?:education|study\/progress|research\/projects)/.test(path)) headers['X-Aster-Workspace'] = workspaceKey;
  if (json !== undefined) { headers['Content-Type'] = 'application/json'; body = JSON.stringify(json); }
  else if (contentType) headers['Content-Type'] = contentType;
  try {
    const response = await fetch('/api' + path, { method, headers, body, signal, cache: 'no-store' });
    const result = responseType === 'text' ? { status: response.ok ? 'ok' : 'error', text: await response.text() } : await response.json(); result._http_status = response.status;
    if (response.status === 401) { state.expired = true; state.activeDocument = null; announce('This session expired. Start a new conversation to continue.'); }
    return result;
  } catch (error) {
    if (error.name === 'AbortError') return { status: 'error', message: 'The request was interrupted. Start a new conversation or retry.' };
    return { status: 'error', message: 'The local service could not be reached. Check connections and retry.' };
  }
}
function setBusy(value, label = 'Aster is thinking…') { state.busy = value; $('chat-form').setAttribute('aria-busy', String(value)); $('pending-text').textContent = label; updateControls(); }
async function run(label, fn) {
  if (state.busy) return;
  $('completion-status').textContent = '';
  setBusy(true, label); state.controller = new AbortController();
  let completion = 'Action finished. Review the latest result in the conversation.';
  try { completion = await fn(state.controller.signal) || completion; }
  catch { completion = 'This action could not finish. Check connections and retry.'; announce(completion); }
  finally { state.controller = null; setBusy(false); render(); $('completion-status').textContent = completion; }
}
async function refreshHealth() {
  $('refresh-services').disabled = true;
  state.health = await request('/health/ready'); renderServices();
  $('refresh-services').disabled = false;
  if (state.health.status === 'ready') announce('');
  else announce(state.health.message || 'A local service is unavailable. Policy checks still work when reference records are loaded. Check connections to restore model answers.');
  return state.health.status === 'ready' || Boolean(state.health.references?.records);
}
async function startSession() {
  if (state.starting) return; state.starting = true; updateControls();
  const result = await request('/v1/sessions', { method: 'POST' });
  if (result.token) { state.token = result.token; state.expired = false; }
  else announce(result.message || 'A session could not be started. Refresh connections and try again.');
  state.starting = false; updateControls();
  if (state.token && !$('education-panel').hidden) await loadEducation();
}
function revokePreviews() { for (const entry of state.entries) { if (entry.preview) URL.revokeObjectURL(entry.preview); revokeCrops(entry); } }
async function newConversation() {
  if (state.busy) return;
  await run('Clearing the current session…', async signal => {
    if (state.token && !state.expired) {
      const result = await request('/v1/sessions/current', { method: 'DELETE', signal });
      if (result.status !== 'ok' && result._http_status !== 401) { announce(result.message); return completionSummary(result); }
    }
    revokePreviews(); state.entries = []; state.evidence = null; state.activeDocument = null; state.token = null; state.expired = false; state.vivaQuestionId = null;
    $('message').value = ''; resizeComposer(); clearSelection(); await startSession(); closeNavigation();
    $('clear-dialog').close(); $('message').focus(); if (state.token) announce('');
    return state.token ? 'A new conversation is ready.' : 'A new session could not be started. Refresh connections and retry.';
  });
}
async function sendQuestion(question) {
  question = question.trim(); if (!question || !enabled()) return;
  const user = { role: 'user', text: question }; state.entries.push(user); $('message').value = ''; resizeComposer(); render(); scrollLatest();
  await run('Aster is thinking…', async signal => {
    const chosen = $('audience').value;
    const payload = { question, audience: chosen === 'auto' ? 'understand' : chosen, task_explicit: chosen !== 'auto' };
    if (state.vivaQuestionId && !/^(?:explain|define|compare|what|why|how|find|search|start|ask|give|viva|restart|exit|stop|end)\b/i.test(question)) payload.viva_question_id = state.vivaQuestionId;
    const doc = state.activeDocument;
    if (doc && doc.confirmed_revision === doc.revision) Object.assign(payload, { context_id: doc.document_id, expected_revision: doc.revision });
    const result = await request('/v1/chat', { method: 'POST', json: payload, signal });
    state.vivaQuestionId = result.viva?.stage === 'await_answer' ? result.viva.question_id : null;
    const entry = { role: 'assistant', result, question, retryPayload: payload, retryQuestion: result.status === 'error' || result.status === 'busy' ? question : null };
    state.entries.push(entry); state.evidence = { entry, result };
    trimEntries();
    return completionSummary(result);
  });
  scrollToEntry(state.entries.at(-1)); $('message').focus({ preventScroll: true });
}
function trimEntries() { while (state.entries.length > 40) { const entry = state.entries.shift(); if (entry.preview) URL.revokeObjectURL(entry.preview); revokeCrops(entry); } }
async function retryQuestion(entry) {
  await run('Retrying your question…', async signal => {
    const payload = entry.retryPayload || { question: entry.retryQuestion };
    entry.result = await request('/v1/chat', { method: 'POST', json: payload, signal }); state.evidence = { entry, result: entry.result };
    if (!['error', 'busy'].includes(entry.result.status)) entry.retryQuestion = null;
    return completionSummary(entry.result);
  });
}
function clearSelection() { if (state.selectionURL) URL.revokeObjectURL(state.selectionURL); state.selection = null; state.selectionURL = null; $('file').value = ''; $('preview-image').removeAttribute('src'); $('preview-image').hidden = false; $('paper-authorization').hidden = true; $('pdf-kind').hidden = true; $('paper-authorized').checked = false; $('upload-preview').hidden = true; $('upload-error').hidden = true; updateControls(); }
function isPdfFile(file) { return Boolean(file && (file.type === 'application/pdf' || (!file.type && /\.pdf$/i.test(file.name || '')))); }
function isPaperFile(file) { return isPdfFile(file) && document.querySelector('input[name="pdf-kind"]:checked')?.value === 'paper'; }
function syncPdfKind() { const file = state.selection; const paper = isPaperFile(file); $('pdf-kind').hidden = !isPdfFile(file); $('paper-authorization').hidden = !paper; updateControls(); }
function selectFile(file) {
  clearSelection(); if (!file) return;
  const pdf = isPdfFile(file);
  if ((!pdf && !['image/png', 'image/jpeg'].includes(file.type)) || file.size > 10 * 1024 * 1024 || !file.size) {
    $('upload-error').textContent = 'Choose a non-empty PDF, PNG or JPEG smaller than 10 MB.'; $('upload-error').hidden = false; return;
  }
  state.selection = file; state.selectionURL = URL.createObjectURL(file); $('preview-image').hidden = pdf;
  syncPdfKind();
  if (!pdf) $('preview-image').src = state.selectionURL;
  $('preview-name').textContent = file.name; $('upload-preview').hidden = false; updateControls();
}
function openUpload() { if (!enabled()) return; $('upload-dialog').showModal(); }
async function attachFile(file) {
  if (!enabled() || !file) return;
  const paper = isPaperFile(file);
  if (paper && !$('paper-authorized').checked) { announce('Confirm private-analysis permission before uploading the paper.'); return; }
  const entry = { role: 'assistant', result: null, document: null, isPaper: paper, preview: URL.createObjectURL(file), filename: file.name };
  state.activeDocument = null; state.entries.push({ role: 'user', text: 'Attached ' + file.name }); state.entries.push(entry);
  $('upload-dialog').close(); $('settings-dialog').close(); clearSelection(); render(); scrollLatest();
  await run(paper ? 'Reading the private PDF…' : 'Examining the image and choosing its workflow…', async signal => {
    let result;
    if (paper) result = await request('/v1/papers?private_analysis_authorized=true', { method: 'POST', body: file, contentType: 'application/pdf', signal });
    else { const body = new FormData(); body.append('file', file, isPdfFile(file) ? 'attachment.pdf' : 'attachment.png'); result = await request('/v1/attachments', { method: 'POST', body, signal }); }
    entry.result = result; state.evidence = null;
    if (result.intent === 'paper' && result.document_id) entry.paper = result;
    if (result.classification?.kind === 'prescription') entry.document = result;
    trimEntries();
    return completionSummary(result);
  });
  scrollToEntry(entry);
}
async function retryAttachment(entry) {
  await run('Examining the attachment again…', async signal => {
    const result = await request('/v1/attachments/' + encodeURIComponent(entry.result.document_id) + '/classify', { method: 'POST', signal });
    entry.result = result; state.evidence = null; if (result.classification?.kind === 'prescription') entry.document = result;
    return completionSummary(result);
  });
}
function sourceCards(parent, result) {
  for (const [index, source] of (result.citations || []).entries()) {
    const card = el('div', 'source-card');
    const title = (index + 1) + '  ' + source.publisher + ' · ' + source.title;
    if (source.source_type === 'private_paper' || source.source_type === 'library_user') text(card, title);
    else link(card, title, source.url);
    if (source.source_type === 'library_user') text(card, 'Your document in My Library · not reviewed by Aster' + (source.extraction_reliability === 'pdf_ocr' ? ' · scanned page, machine-read (OCR): check words and numbers in your original' : ''), 'result-caption');
    const statements = (result.claims || []).flatMap((claim, i) => (claim.citation_ids || []).includes(source.chunk_id) ? [i + 1] : []);
    const layers = result.explanation_layers;
    const supportedLayers = layers ? [['simple', 'simple explanation'], ['deeper', 'deeper explanation'], ['context', 'research context']].filter(([key]) => (layers[key] || []).some(part => (part.citation_ids || []).includes(source.chunk_id))).map(([, label]) => label) : [];
    if (supportedLayers.length) text(card, 'Supports ' + supportedLayers.join(' and '), 'source-support');
    else if (statements.length) text(card, 'Supports answer paragraph' + (statements.length === 1 ? ' ' : 's ') + statements.join(', '), 'source-support');
    text(card, source.source_type === 'private_paper' ? source.section + ' · Confirmed paper revision ' + result.context_revision : [source.section, source.jurisdiction, source.source_date ? 'Source date ' + source.source_date : 'Source date unavailable', source.text_revision].filter(Boolean).join(' · '), 'result-caption');
    if (source.source_type === 'retailer_monograph') text(card, 'Retailer reference · verification and licensing confirmed by the user', 'result-caption');
    if (source.source_type === 'unverified_secondary') text(card, 'Unverified secondary data', 'result-caption');
    if (source.material_type === 'research') text(card, ['Research reference', source.study_design || source.study_type, source.study_context].filter(Boolean).join(' · '), 'result-caption');
    if (source.source_review_notice) text(card, 'Source wording under review: ' + source.source_review_notice, 'result-caption');
    if (source.source_type === 'patient_information') {
      text(card, source.original_attribution, 'result-caption');
      text(card, 'Original reference. Aster’s adapted explanation has not received independent clinical review.', 'result-caption');
      if (source.next_review_due) text(card, 'Publisher review due ' + source.next_review_due, 'result-caption');
    }
    const spans = (result.claim_evidence || []).filter(item => item.span?.chunk_id === source.chunk_id).map(item => item.span);
    const coordinates = [...new Set(spans.map(span => 'characters ' + span.start + '–' + span.end))];
    const location = source.source_type === 'private_paper' ? 'Page ' + source.page + ' · ' + source.section + ' · revision ' + result.context_revision : [source.section_id || source.section, source.snapshot_id, ...coordinates].filter(Boolean).join(' · ');
    disclosure(card, 'View supporting passage' + (location ? ' · ' + location : ''), body => {
      text(body, location, 'result-caption'); text(body, source.excerpt);
    }); parent.append(card);
  }
}
function exportResponse(result) {
  const clean = Object.fromEntries(Object.entries(result).filter(([key]) => !key.startsWith('_')));
  const url = URL.createObjectURL(new Blob([JSON.stringify(clean, null, 2)], { type: 'application/json' }));
  const a = el('a'); a.href = url; a.download = 'aster-response.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
const patientHeadings = {
  possible_causes: 'Possible causes', specific_context: 'About the symptom you mentioned',
  uncertainty: 'What symptoms alone cannot tell us', professional_followup: 'When to get checked',
  warning_signs: 'When to get urgent help',
};
function citedParagraph(parent, result, indices, tag = 'p') {
  // Each verified sentence is followed by its source numbers (matching Sources).
  const order = (result.citations || []).map(source => source.chunk_id);
  const node = el(tag, tag === 'li' ? 'response-text grounded-item' : 'response-text');
  for (const index of indices) {
    const claim = result.claims?.[index]; if (!claim) continue;
    node.append(document.createTextNode((node.childNodes.length ? ' ' : '') + claim.text));
    const numbers = (claim.citation_ids || []).map(id => order.indexOf(id) + 1).filter(n => n > 0);
    if (numbers.length) {
      const sup = el('sup', 'citation-marker', '[' + numbers.join(', ') + ']');
      sup.title = 'Supported by source ' + numbers.join(', ');
      node.append(sup);
    }
  }
  parent.append(node);
}
function renderPrescriptionExplanation(content, result) {
  const notes = { ingredient_not_verified: 'Not explained: Aster could not verify which ingredient this name refers to. Ask your pharmacist; brand names are not guessed.', no_reference: 'No applicable reference passage was found for this ingredient.', model_unavailable: 'The local model did not respond; retry the explanation.' };
  for (const medicine of result.prescription_explanation.medicines || []) {
    const section = el('section', 'explanation-section');
    section.append(el('h3', 'explanation-heading', (medicine.medicine || 'Medicine') + (medicine.verified_ingredient && medicine.verified_ingredient.toLowerCase() !== (medicine.medicine || '').toLowerCase() ? ' · ingredient ' + medicine.verified_ingredient : '')));
    if (medicine.written_instructions) text(section, 'Your confirmed prescription says: ' + medicine.written_instructions + '. These are your prescriber’s instructions; Aster does not assess or change them.', 'result-caption');
    if (medicine.status === 'explained') renderGrounded(section, result, medicine.blocks);
    else text(section, notes[medicine.status] || 'Not explained.', 'result-notice');
    content.append(section);
  }
}
function renderGrounded(content, result, blocks = null) {
  let list = null;
  for (const block of blocks || result.grounded_answer.blocks || []) {
    if (block.type === 'heading') { list = null; content.append(el('h3', 'explanation-heading', block.text)); continue; }
    if (block.type === 'structural') { list = null; text(content, block.text, 'response-text practice-structure'); continue; }
    if (block.type === 'bullet') { if (!list) { list = el('ul', 'grounded-list'); content.append(list); } citedParagraph(list, result, block.claim_indices, 'li'); continue; }
    list = null; citedParagraph(content, result, block.claim_indices);
  }
  if (!blocks && result.removed_statements) text(content, result.removed_statements + (result.removed_statements === 1 ? ' generated statement was' : ' generated statements were') + ' removed because the sources did not support ' + (result.removed_statements === 1 ? 'it.' : 'them.'), 'result-caption');
}
function followupButtons(content, result) {
  const options = (result.suggested_followups || []).filter(Boolean).slice(0, 3);
  if (!options.length) return;
  const row = el('div', 'followup-row');
  for (const question of options) { const button = action(question, () => sendQuestion(question)); button.classList.add('followup-chip'); row.append(button); }
  content.append(row);
}
function renderAnswerBody(content, result) {
  if (result.evidence_states?.response?.label) text(content, result.evidence_states.response.label, 'result-caption');
  if (result.grounded_answer) {
    renderGrounded(content, result);
  } else if (result.prescription_explanation) {
    renderPrescriptionExplanation(content, result);
  } else if (result.clarifying_question || result.nearby_topics?.length) {
    if (result.clarifying_question) text(content, result.clarifying_question);
  } else if (result.viva) {
    const viva = result.viva;
    if (viva.feedback) {
      text(content, 'Provisional educational feedback', 'result-caption');
      for (const point of viva.feedback.rubric || []) text(content, point, 'result-caption');
      if (viva.feedback.matched_source_terms?.length) text(content, 'Source terms mentioned: ' + viva.feedback.matched_source_terms.join(', '));
      if (viva.feedback.missed_source_terms?.length) text(content, 'Source terms to review: ' + viva.feedback.missed_source_terms.join(', '));
      for (const claim of result.claims || []) text(content, claim.text);
    }
    if (viva.question) { content.append(el('h3', 'explanation-heading', 'Viva question ' + viva.number)); text(content, viva.question); }
    if (viva.stage === 'completed') text(content, 'This source-based practice is complete. Start or restart a viva to practise again.', 'result-caption');
  } else if (result.component_answers?.length) {
    for (const component of result.component_answers) {
      const section = el('section', 'explanation-section');
      section.append(el('h3', 'explanation-heading', component.question));
      renderAnswerBody(section, component.response); content.append(section);
    }
  } else if (result.patient_response) {
    for (const part of result.patient_response.parts || []) {
      const claim = result.claims?.[part.claim_index]; if (!claim) continue;
      const section = el('section', 'explanation-section');
      if (patientHeadings[part.role]) section.append(el('h3', 'explanation-heading', patientHeadings[part.role]));
      text(section, claim.text); content.append(section);
    }
  } else if (result.practice_item) {
    text(content, result.practice_item.question);
    const rubric = el('details', 'practice-rubric'); rubric.append(el('summary', '', 'Self-assessment rubric and reference answer'));
    for (const criterion of result.practice_item.rubric) text(rubric, criterion);
    for (const claim of result.claims || []) text(rubric, claim.text);
    text(rubric, 'Faculty review pending. This is a source-based practice activity.'); content.append(rubric);
  } else if (result.comparison) {
    const comparedFacets = new Set((result.comparison.axes || []).map(axis => axis.facet));
    for (const part of result.structured_answer?.sections || []) {
      if (comparedFacets.has(part.facet)) continue;
      const section = el('section', 'explanation-section'); section.append(el('h3', 'explanation-heading', part.heading));
      for (const index of part.claim_indices) { const claim = result.claims[index]; if (claim) text(section, claim.text); }
      if (!part.claim_indices.length) text(section, part.state === 'contradictory' ? 'Conflicting evidence withheld; source review needed.' : 'Evidence missing', 'result-caption');
      content.append(section);
    }
    text(content, result.comparison.scope, 'result-caption');
    const table = el('table', 'comparison-table'); table.append(el('caption', 'sr-only', 'Source-bound concept comparison'));
    const head = el('tr');
    if (result.comparison.axes) {
      head.append(el('th', '', 'Feature')); for (const entity of result.comparison.entities) head.append(el('th', '', entity)); table.append(head);
      for (const axis of result.comparison.axes) {
        const tr = el('tr'); tr.append(el('th', '', axis.label));
        for (const cell of axis.cells) {
          const td = el('td');
          for (const index of cell.claim_indices) { const claim = result.claims[index]; if (claim) text(td, claim.text); }
          if (!cell.claim_indices.length) text(td, 'Evidence missing', 'result-caption');
          tr.append(td);
        }
        table.append(tr);
      }
    } else {
      head.append(el('th', '', 'Concept'), el('th', '', 'Definition & properties')); table.append(head);
      for (const row of result.comparison.rows) { const tr = el('tr'); tr.append(el('th', '', row.topic), el('td', '', result.claims[row.claim_index].text)); table.append(tr); }
    }
    const scrolling = el('div', 'comparison-scroll'); scrolling.tabIndex = 0; scrolling.append(table); content.append(scrolling);
  } else if (result.paper_sections) {
    for (const part of result.paper_sections) {
      const section = el('section', 'explanation-section'); section.append(el('h3', 'explanation-heading', part.heading));
      for (const index of part.claim_indices) { const claim = result.claims[index]; if (claim) text(section, claim.text); }
      if (!part.claim_indices.length) text(section, 'No safe complete section was extracted. Review this part in the original PDF.', 'result-caption');
      content.append(section);
    }
    for (const item of result.appraisal_checklist || []) text(content, item, 'result-caption');
  } else if (result.structured_answer) {
    const shown = new Set();
    for (const part of result.structured_answer.sections) {
      const section = el('section', 'explanation-section'); section.append(el('h3', 'explanation-heading', part.heading));
      for (const index of part.claim_indices) {
        const claim = result.claims[index]; if (!claim) continue;
        if (shown.has(index)) text(section, 'Also supported by paragraph ' + (index + 1) + ' above.', 'result-caption');
        else { text(section, claim.text); shown.add(index); }
      }
      if (!part.claim_indices.length) text(section, part.state === 'contradictory' ? 'Conflicting evidence withheld; source review needed.' : 'Evidence missing', 'result-caption');
      content.append(section);
    }
  } else if (result.answer_review) {
    const review = result.answer_review;
    if (review.submitted_answer) disclosure(content, 'Your answer — unverified', body => text(body, review.submitted_answer));
    text(content, review.fictional_prompt);
    for (const criterion of review.criteria) text(content, criterion);
    disclosure(content, 'Source-based reference', body => { for (const claim of result.claims || []) text(body, claim.text); });
  } else if (result.report_explanation) {
    for (const term of result.report_explanation.terms) { content.append(el('h3', 'explanation-heading', term.label)); text(content, result.claims[term.claim_index].text); }
    text(content, result.report_explanation.limitations, 'result-caption');
  } else if (result.research_project) {
    const project = result.research_project;
    text(content, project.papers.length + ' bibliographic records. ' + project.papers.filter(p => p.access === 'permitted_full_text_inspected').length + ' permitted full texts inspected.');
    text(content, 'The evidence table is beside this answer. Review the papers before drawing conclusions; the editable scaffold has gaps marked explicitly.', 'result-caption');
  } else if (result.explanation_layers) {
    const layers = result.explanation_layers;
    for (const [key, title] of [['simple', 'Simple explanation'], ['deeper', 'Deeper explanation']]) {
      const section = el('section', 'explanation-section'); section.append(el('h3', 'explanation-heading', title));
      if (key === 'simple') for (const part of layers.context || []) text(section, part.text, 'result-caption');
      for (const part of layers[key] || []) text(section, part.text);
      if (layers[key + '_notice']) text(section, layers[key + '_notice'], 'result-caption');
      content.append(section);
    }
  } else {
    if (result.answer) text(content, result.answer);
    for (const claim of result.claims || []) text(content, claim.text);
  }
  if (result.provisional_explanation) {
    const provisional = result.provisional_explanation;
    const section = el('section', 'explanation-section');
    section.append(el('h3', 'explanation-heading', provisional.label));
    text(section, provisional.limitations, 'result-notice');
    text(section, provisional.text); content.append(section);
  }
  if (result.missing_response_elements?.length) text(content, 'Evidence is missing for: ' + result.missing_response_elements.map(value => value.replaceAll('_', ' ')).join(', '), 'result-caption');
  if (result.grounded_answer && result.status !== 'insufficient_evidence') followupButtons(content, result);
}
function renderResult(parent, result, exportable = true, entry = null) {
  if (!result) return;
  const content = el('div', 'result-content'); parent.append(content);
  if (result.message) {
    const status = result.status;
    if (['partial', 'error', 'busy', 'unsupported_input', 'quality_rejected', 'insufficient_evidence', 'needs_confirmation', 'urgent_guidance'].includes(status)) {
      const notice = el('div', 'result-notice' + (status === 'urgent_guidance' ? ' urgent' : status === 'needs_confirmation' ? ' info' : ''), result.message);
      if (status === 'urgent_guidance') notice.setAttribute('role', 'alert'); content.append(notice);
    } else if (!(result.claims?.length || result.answer) || ![
      'Relevant reference notes', 'Source-backed explanation',
      "Let's break this down, starting with what the references explain.",
    ].includes(result.message)) text(content, result.message, 'result-caption');
  }
  renderAnswerBody(content, result);
  if (result.coverage_status && !result.viva) text(content, 'Source-backed coverage: ' + result.coverage_status.replaceAll('_', ' ') + '. Independent clinical review pending.', 'result-caption');
  if (result.unsupported_parts?.length) text(content, 'Not covered: ' + result.unsupported_parts.join('; '), 'result-caption');
  for (const warning of result.warnings || []) text(content, warning, 'result-caption');
  if (result.findings?.length) {
    const table = el('table', 'score-table'); const caption = el('caption', '', 'Research scores — not diagnostic probabilities'); table.append(caption);
    const head = el('tr'); head.append(el('th', '', 'Finding'), el('th', '', 'Research score')); table.append(head);
    for (const f of result.findings) { const row = el('tr'); row.append(el('td', '', f.name), el('td', '', String(f.score))); table.append(row); } content.append(table);
    text(content, result.score_semantics, 'result-caption');
  }
  const actions = el('div', 'response-actions');
  const count = result.citations?.length || 0;
  const sourceButton = localAction(count ? 'Sources · ' + count : 'Answer context', () => {
    state.evidence = { entry, result }; updateContext();
    if (window.matchMedia('(max-width:1023px)').matches) $('evidence-dialog').showModal();
    else { $('context-content').querySelector('h2').focus(); document.querySelector('.context-rail').scrollTop = 0; }
  });
  sourceButton.classList.add('source-action'); sourceButton._evidenceResult = result;
  sourceButton.setAttribute('aria-label', sourceButton.textContent + (entry?.question ? ' for: ' + entry.question : ''));
  actions.append(sourceButton);
  if (exportable && (result.answer || result.claims?.length || result.findings?.length)) actions.append(localAction('Export', () => exportResponse(result)));
  if (result.research_setup) actions.append(action('Set up literature search', () => openEducation('research', result.research_setup.question)));
  if (result.question_plan?.medical_audience === 'student' && result.claims?.length && !entry?.document) actions.append(action('Record study attempt', () => openEducation('progress', studyTopic(result))));
  if (result.research_project) {
    actions.append(action('Edit review draft', () => editProject(result.research_project)));
    actions.append(action('Export review (.md)', () => exportProject(result.research_project, 'markdown')));
    actions.append(action('Export references (.bib)', () => exportProject(result.research_project, 'bibtex')));
  }
  content.append(actions);
}
function localAction(label, handler) {
  const button = action(label, handler); button.className = 'text-button local-action'; button.disabled = false; return button;
}
function original(parent, entry) {
  if (!entry.preview) return;
  disclosure(parent, 'View original image', body => { const image = el('img', 'image-preview'); image.src = entry.preview; image.alt = 'Original attachment: ' + entry.filename; body.append(image); });
}
async function loadCrop(entry, doc, fieldId) {
  entry.crops ||= {};
  const key = doc.revision + ':' + fieldId;
  if (entry.crops[key]) return entry.crops[key];
  try {
    const response = await fetch('/api/v1/documents/' + encodeURIComponent(doc.document_id) + '/fields/' + encodeURIComponent(fieldId) + '/crop', { headers: { 'X-Aster-Client': '1', Authorization: 'Bearer ' + state.token }, cache: 'no-store' });
    if (!response.ok) return null;
    entry.crops[key] = URL.createObjectURL(await response.blob());
    return entry.crops[key];
  } catch { return null; }
}
function revokeCrops(entry) { for (const url of Object.values(entry.crops || {})) URL.revokeObjectURL(url); entry.crops = {}; }
function reviewDocument(parent, entry, index) {
  const doc = entry.document; if (!doc) return;
  const confirmed = doc.confirmed_revision === doc.revision;
  if (confirmed) {
    disclosure(parent, 'Confirmed transcription · revision ' + doc.revision, body => {
      const fields = el('dl', 'confirmed-fields');
      for (const f of doc.fields || []) { fields.append(el('dt', '', fieldNames[f.kind] || f.kind.replaceAll('_', ' ')), el('dd', '', f.value || 'Unreadable / unspecified')); } body.append(fields);
      body.append(action('Edit transcription', async () => {
        await run('Opening the transcription for review…', async signal => {
          const result = await request('/v1/documents/' + encodeURIComponent(doc.document_id) + '/edit', { method: 'POST', json: { expected_revision: doc.revision }, signal });
          if (result.document_id) { entry.document = result; entry.explanation = null; entry.drafts = null; entry.draftAcknowledged = false; entry.feedback = null; entry.result.status = 'needs_confirmation'; entry.result.message = 'Review and confirm the current revision.'; if (state.activeDocument?.document_id === doc.document_id) state.activeDocument = null; }
          else { announce(result.message); return completionSummary(result); }
          return 'Transcription reopened for review. Confirmation and document context have been reset.';
        });
      }));
    });
  } else {
    const form = el('form', 'review-card'); form.setAttribute('aria-label', 'Review transcription');
    const heading = el('div', 'review-heading'); heading.append(el('h3', '', 'Review transcription'), el('span', '', 'Needs your review')); form.append(heading);
    text(form, 'Revision ' + doc.revision + ' · Blank fields remain unreadable or unspecified.', 'result-caption');
    original(form, entry);
    disclosure(form, 'Raw OCR text', body => text(body, doc.raw_text || 'No readable text found.'));
    for (const warning of doc.quality?.warnings || []) text(form, warning, 'result-notice');
    if (doc.rotation_applied) text(form, 'The image was rotated ' + doc.rotation_applied + '° to read it upright.', 'result-caption');
    const fields = el('div', 'review-fields'); const inputs = [];
    let group = null;
    for (const [i, f] of (doc.fields || []).entries()) {
      const prefix = f.field_id.split('_').slice(0, 2).join('_');
      if (prefix !== group && f.kind !== 'document_text') { group = prefix; fields.append(el('h4', 'review-group', 'Medicine ' + prefix.split('_')[1])); }
      const label = el('label', 'field'); const input = el('input'); input.type = 'text'; input.maxLength = f.field_id === 'document_text' ? 12000 : 500;
      input.id = 'field-' + index + '-' + i; input.value = entry.drafts?.[f.field_id] ?? (f.value || f.candidate_value || ''); input.placeholder = 'Unreadable / unspecified'; input.autocomplete = 'off'; input.disabled = state.busy;
      input.addEventListener('input', () => { entry.drafts ||= {}; entry.drafts[f.field_id] = input.value; });
      const row = el('div', 'field-row'); row.append(input);
      if (f.bbox) {
        const crop = el('img', 'field-crop'); crop.alt = 'Source text for ' + (fieldNames[f.kind] || f.kind); row.append(crop);
        loadCrop(entry, doc, f.field_id).then(url => { if (url) crop.src = url; else crop.remove(); });
      }
      label.append(el('span', '', fieldNames[f.kind] || f.kind.replaceAll('_', ' ')), row);
      if (f.normalized) label.append(el('small', 'result-caption', 'Reads as: ' + f.normalized + ' (check against the original)'));
      if (f.kind === 'ingredient' && f.status === 'reference_match') label.append(el('small', 'result-caption', 'Exact match to a US generic name. Confirm it against the package; brands are never matched automatically.'));
      if (typeof f.engine_score === 'number' && f.engine_score >= 0) label.append(el('small', 'result-caption' + (f.engine_score < 60 ? ' low-signal' : ''), (f.engine_score < 60 ? 'Low OCR signal — read the original carefully. ' : '') + 'OCR engine signal ' + Math.round(f.engine_score) + ' (not a probability of being correct).'));
      fields.append(label); inputs.push(input);
    }
    form.append(fields);
    const acknowledge = el('label', 'acknowledge'); const checkbox = el('input'); checkbox.type = 'checkbox'; checkbox.required = true; checkbox.disabled = state.busy; checkbox.checked = Boolean(entry.draftAcknowledged);
    checkbox.addEventListener('change', () => { entry.draftAcknowledged = checkbox.checked; });
    acknowledge.append(checkbox, el('span', '', 'I compared every field with the original. Blank fields remain unresolved.')); form.append(acknowledge);
    const feedback = el('p', 'review-feedback'); feedback.setAttribute('role', 'status'); form.append(feedback);
    const submit = el('button', 'button primary', 'Confirm & explain'); submit.type = 'submit'; submit.disabled = !enabled(); form.append(submit);
    text(form, 'Confirmation records the text you reviewed, not medical approval.', 'result-caption');
    form.addEventListener('submit', async event => {
      event.preventDefault(); if (!checkbox.checked || !enabled()) return;
      const payload = { expected_revision: doc.revision, confirmation_acknowledged: true, fields: doc.fields.map((f, i) => ({ field_id: f.field_id, value: inputs[i].value.trim() || null, status: inputs[i].value.trim() ? 'confirmed_by_user' : 'unreadable' })) };
      await run('Confirming and explaining the reviewed text…', async signal => {
        const result = await request('/v1/documents/' + encodeURIComponent(doc.document_id) + '/confirm', { method: 'PUT', json: payload, signal });
        if (result.document_id && result.confirmed_revision === result.revision) {
          entry.document = result; entry.drafts = null; entry.draftAcknowledged = false; entry.feedback = null; state.activeDocument = result; entry.result.status = 'ok'; entry.result.message = 'Prescription transcription confirmed.';
          entry.explanation = await request('/v1/documents/' + encodeURIComponent(doc.document_id) + '/explain', { method: 'POST', json: { expected_revision: result.revision }, signal });
          state.evidence = { entry, result: entry.explanation };
          return 'Transcription confirmed. ' + completionSummary(entry.explanation, 'The reference explanation result is available in the conversation.');
        } else {
          entry.feedback = result.message || 'Confirmation could not be saved. Retry with the current revision.';
          if (result._http_status === 409) { const current = await request('/v1/documents/' + encodeURIComponent(doc.document_id), { signal }); if (current.document_id) { entry.document = current; entry.drafts = null; entry.draftAcknowledged = false; } }
          return 'Confirmation could not be saved. ' + entry.feedback.slice(0, 240);
        }
      });
      scrollToEntry(entry);
    });
    if (entry.feedback) feedback.textContent = entry.feedback;
    parent.append(form);
  }
  if (entry.explanation) {
    const explanation = el('div', 'result-content'); text(explanation, 'Reference information for confirmed text', 'result-caption'); renderResult(explanation, entry.explanation, true, entry); parent.append(explanation);
    if (['error', 'busy'].includes(entry.explanation.status)) parent.append(action('Retry document explanation', async () => {
      await run('Explaining the current confirmed text…', async signal => { entry.explanation = await request('/v1/documents/' + encodeURIComponent(entry.document.document_id) + '/explain', { method: 'POST', json: { expected_revision: entry.document.revision }, signal }); return completionSummary(entry.explanation, 'The reference explanation result is available in the conversation.'); });
    }));
  }
}
function clearPaperContext(identity, removeAttachment = false) {
  state.entries = state.entries.filter(item => item.result?.context_id !== identity &&
    !(removeAttachment && item.paper?.document_id === identity));
  for (const item of state.entries) if (item.paper?.document_id === identity) item.paperAnalysis = null;
  if (state.activeDocument?.document_id === identity) state.activeDocument = null;
  if (state.evidence?.result?.context_id === identity || !state.entries.includes(state.evidence?.entry)) state.evidence = null;
}
function reviewPaper(parent, entry, index) {
  const paper = entry.paper; if (!paper) return;
  const confirmed = paper.confirmed_revision === paper.revision;
  const form = el('form', 'review-card'); form.setAttribute('aria-label', 'Review private paper');
  const heading = el('div', 'review-heading'); heading.append(el('h3', '', confirmed ? 'Confirmed private paper' : 'Review private paper')); form.append(heading);
  text(form, (paper.pages || []).length + ' extracted pages · revision ' + paper.revision + '. Text stays in this temporary conversation.', 'result-caption');
  disclosure(form, 'Extracted page text', body => {
    for (const page of paper.pages || []) disclosure(body, 'Page ' + page.page, pageBody => {
      text(pageBody, page.text || 'No selectable text on this page.', 'response-text paper-page-text');
    }, page.page === 1);
  }, !confirmed);
  if (entry.preview) form.append(action('Open selected PDF locally', () => { window.open(entry.preview, '_blank', 'noopener,noreferrer'); }));
  if (!confirmed) {
    const label = el('label', 'acknowledge'), checkbox = el('input'); checkbox.type = 'checkbox'; checkbox.required = true;
    checkbox.id = 'paper-ack-' + index; checkbox.checked = Boolean(entry.paperAcknowledged); checkbox.disabled = !enabled();
    checkbox.addEventListener('change', () => { entry.paperAcknowledged = checkbox.checked; });
    label.append(checkbox, el('span', '', 'I checked the extracted pages against my PDF. This confirms extraction, not the study’s validity.')); form.append(label);
    const submit = el('button', 'button primary', 'Confirm & inspect paper'); submit.type = 'submit'; submit.disabled = !enabled(); form.append(submit);
    form.addEventListener('submit', async event => {
      event.preventDefault(); if (!checkbox.checked || !enabled()) return;
      await run('Confirming the private paper…', async signal => {
        const current = await request('/v1/papers/' + encodeURIComponent(paper.document_id) + '/confirm', {
          method: 'POST', json: { expected_revision: paper.revision, extraction_reviewed: true }, signal });
        if (current.document_id && current.confirmed_revision === current.revision) {
          entry.paper = current; entry.result = current; entry.paperAcknowledged = false; state.activeDocument = current;
          entry.paperAnalysis = await request('/v1/chat', { method: 'POST', json: { question: 'Appraise this paper.', audience: 'research',
            context_id: current.document_id, expected_revision: current.revision }, signal });
          state.evidence = { entry, result: entry.paperAnalysis };
          return completionSummary(entry.paperAnalysis, 'Confirmed paper excerpts are available.');
        }
        if (current._http_status === 409) {
          const refreshed = await request('/v1/papers/' + encodeURIComponent(paper.document_id), { signal });
          if (refreshed.document_id) { entry.paper = refreshed; entry.result = refreshed; entry.paperAcknowledged = false; }
        }
        announce(current.message); return completionSummary(current);
      });
      scrollToEntry(entry);
    });
  } else {
    form.append(action('Use this paper for follow-ups', () => { state.activeDocument = paper; updateControls(); $('message').focus(); }));
    form.append(action('Review extraction again', async () => {
      await run('Reopening paper review…', async signal => {
        const current = await request('/v1/papers/' + encodeURIComponent(paper.document_id) + '/reopen', {
          method: 'POST', json: { expected_revision: paper.revision }, signal });
        if (current.document_id) { clearPaperContext(paper.document_id); entry.paper = current; entry.result = current; entry.paperAcknowledged = false; }
        return completionSummary(current);
      });
    }));
  }
  form.append(action('Delete private paper', async () => {
    await run('Deleting the private paper…', async signal => {
      const result = await request('/v1/papers/' + encodeURIComponent(paper.document_id), { method: 'DELETE', signal });
      if (result.status === 'ok') {
        clearPaperContext(paper.document_id, true);
        if (entry.preview) URL.revokeObjectURL(entry.preview); state.evidence = null;
      }
      return completionSummary(result, 'Private paper and its analysis context deleted.');
    });
  }));
  parent.append(form);
  if (entry.paperAnalysis) renderResult(parent, entry.paperAnalysis, true, entry);
}
function render() {
  const messages = $('messages'); messages.replaceChildren(); $('welcome').hidden = state.entries.length > 0 || !$('education-panel').hidden;
  $('breadcrumb').textContent = state.entries.length ? 'Conversation / ' + (state.entries.some(e => e.document || e.paper) ? 'Document review' : 'Questions & images') : 'Workspace / New conversation';
  for (const [index, entry] of state.entries.entries()) {
    const article = el('article', 'message' + (entry.role === 'user' ? ' user-message' : ' assistant-message')); article.id = 'entry-' + index;
    const speaker = el('div', 'speaker'); if (entry.role !== 'user') speaker.append(icon('asterisk'));
    let label = entry.role === 'user' ? 'You' : 'Aster';
    if (entry.result?.answer_method === 'ollama_model_knowledge') label += ' · unverified model knowledge';
    speaker.append(el('span', '', label)); article.append(speaker);
    if (entry.text) text(article, entry.text);
    if (entry.filename) {
      const kind = entry.result?.classification?.kind; const card = el('div', 'attachment-card'); card.append(icon(kind === 'xray' ? 'scan' : 'file'));
      const info = el('div', 'attachment-details'); info.append(el('strong', '', entry.filename), el('span', 'small muted', entry.isPaper ? 'Private PDF paper' : 'Image attachment')); card.append(info);
      if (kind) card.append(el('span', 'badge' + (kind === 'prescription' && entry.document?.confirmed_revision !== entry.document?.revision ? ' pending-badge' : ''), kindNames[kind] || 'Unclear image'));
      article.append(card); if (!entry.isPaper && (!entry.document || entry.document.confirmed_revision === entry.document.revision)) original(article, entry);
    }
    renderResult(article, entry.result, true, entry);
    if (entry.result?.imaging_result) renderResult(article, entry.result.imaging_result, true, entry);
    if (entry.result?.imaging_result?.xray_upload_available && !entry.xrayAnalysis) xrayConfirm(article, entry);
    if (entry.xrayAnalysis) renderXray(article, entry.xrayAnalysis, entry);
    if (entry.result?.document_id && !entry.result.classification && !entry.document && !entry.paper) article.append(action('Retry attachment classification', () => retryAttachment(entry)));
    if (entry.retryQuestion) article.append(action('Retry answer', () => retryQuestion(entry)));
    reviewDocument(article, entry, index); reviewPaper(article, entry, index); messages.append(article);
  }
  updateContext(); updateControls();
}
function xrayConfirm(parent, entry) {
  const form = el('form', 'review-card'); form.setAttribute('aria-label', 'X-ray analysis confirmation');
  form.append(el('h3', '', 'Research X-ray assistance'));
  text(form, 'Supported: adult frontal (PA/AP) chest X-rays only. Other images — children, side views, dental, limb, CT/MRI or photos — are declined after automated checks. Results are research scores for a clinician or radiologist to review; they are not a diagnosis and cannot show that an X-ray is normal.', 'result-caption');
  const label = el('label', 'acknowledge'); const box = el('input'); box.type = 'checkbox'; box.required = true;
  label.append(box, el('span', '', 'This is a chest X-ray of an adult (18 years or older).')); form.append(label);
  const submit = el('button', 'button primary', 'Run input checks and research model'); submit.type = 'submit'; submit.disabled = !enabled(); form.append(submit);
  form.addEventListener('submit', async event => {
    event.preventDefault(); if (!box.checked || !enabled()) return;
    await run('Checking the image and running the research model…', async signal => {
      entry.xrayAnalysis = await request('/v1/attachments/' + encodeURIComponent(entry.result.document_id) + '/xray', { method: 'POST', json: { adult_confirmed: true }, signal });
      state.evidence = { entry, result: entry.xrayAnalysis };
      return completionSummary(entry.xrayAnalysis, 'The X-ray result is in the conversation.');
    });
  });
  parent.append(form);
}
function renderXray(parent, result, entry) {
  renderResult(parent, result, true, entry);
  const checks = result.input_checks;
  if (checks) disclosure(parent, 'Automated input checks', body => {
    for (const reason of checks.reasons || []) text(body, reason.message, 'result-caption');
    const m = checks.measurements || {};
    if (m.frontal_probability !== undefined) text(body, 'View model: frontal ' + Math.round(m.frontal_probability * 100) + '% / lateral ' + Math.round(m.lateral_probability * 100) + '% (model output, not certainty). Image-similarity score ' + m.ae_error + ' (accepted range ≤ ' + checks.thresholds?.max_ae_error + ').', 'result-caption');
  });
}
function scrollBehavior() { return window.matchMedia('(prefers-reduced-motion:reduce)').matches ? 'instant' : 'smooth'; }
function scrollLatest() { requestAnimationFrame(() => $('scroll-region').scrollTo({ top: $('scroll-region').scrollHeight, behavior: scrollBehavior() })); }
function scrollToEntry(entry) {
  requestAnimationFrame(() => {
    const node = $('entry-' + state.entries.indexOf(entry)), region = $('scroll-region');
    if (node) region.scrollTo({ top: region.scrollTop + node.getBoundingClientRect().top - region.getBoundingClientRect().top - 12, behavior: scrollBehavior() });
  });
}
function selectedEvidence() {
  const selected = state.evidence;
  if (selected?.entry && state.entries.includes(selected.entry) &&
      [selected.entry.result, selected.entry.explanation, selected.entry.paperAnalysis, selected.entry.result?.imaging_result].includes(selected.result)) return selected;
  const entry = [...state.entries].reverse().find(e => e.role === 'assistant' && e.result);
  return { entry, result: entry?.paperAnalysis || entry?.explanation || entry?.result?.imaging_result || entry?.result };
}
function contextNode() {
  const wrap = el('div', 'context-content');
  const { entry, result } = selectedEvidence();
  const heading = el('h2', '', 'Sources & context'); heading.tabIndex = -1; wrap.append(heading);
  if (!result) {
    text(wrap, 'A place for the evidence.', 'context-intro');
    text(wrap, 'References and supporting passages will appear here when Aster answers. Select Sources under any answer to revisit its references.', 'muted');
    const help = el('div', 'context-bottom');
    help.append(el('strong', '', 'Start in your own words.'));
    text(help, 'Ask about a health concept, a medicine or your studies. Use the link icon to attach a paper or image.');
    wrap.append(help); return wrap;
  }
  if (entry?.question || entry?.filename) text(wrap, entry.question || entry.filename, 'evidence-question');
  if (result.research_project) { researchEvidence(wrap, result.research_project); return wrap; }
  const sources = result.citations || [];
  text(wrap, sources.length ? sources.length + (sources.length === 1 ? ' reference for this answer' : ' references for this answer') : 'No references cited for this answer.', 'result-caption');
  if (sources.length) sourceCards(wrap, result);
  const notices = [result, ...(result.component_answers || []).map(c => c.response)].filter(r => r.reuse_notice);
  if (notices.length) {
    text(wrap, notices[0].reuse_notice, 'result-caption');
    link(wrap, 'Open Government Licence v3.0', 'https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/');
    text(wrap, 'Adapted by Aster. Independent clinical review pending.', 'result-caption');
  }
  if (result.answer_method === 'ollama_model_knowledge') text(wrap, 'Unverified model knowledge. This answer has no verified local reference.', 'result-notice');
  if (result.provisional_explanation) text(wrap, result.provisional_explanation.label + '. ' + result.provisional_explanation.limitations, 'result-notice');
  if (result.evidence_states?.claims?.length) disclosure(wrap, 'Evidence status by claim', body => {
    for (const item of result.evidence_states.claims) {
      text(body, 'Claim ' + (item.claim_index + 1) + ': ' + item.label, 'result-caption');
      text(body, result.claims[item.claim_index]?.text || '');
    }
  });
  if (result.answer_method === 'quarantined_catalogue') text(wrap, 'Unverified catalogue entry. Match the product against its original packaging and an authoritative Indian label. Agreement between datasets does not verify it.', 'result-notice');
  for (const warning of result.warnings || []) text(wrap, warning, 'result-caption');
  const doc = entry?.document;
  if (doc) text(wrap, doc.confirmed_revision === doc.revision ? 'Transcription confirmed at revision ' + doc.revision + '. Confirmation records reviewed text, not medical approval.' : 'Transcription needs review. Check every name, number and unit against the original; leave unreadable fields unresolved.', 'result-caption');
  if (entry?.result?.classification?.kind === 'xray') text(wrap, 'Image classification and research scores are not a diagnosis.', 'result-caption');
  if (result.limitations?.length) disclosure(wrap, 'Scope & limitations', body => result.limitations.forEach(value => text(body, value, 'result-caption')));
  return wrap;
}
function updateContext() {
  $('context-content').replaceChildren(contextNode()); $('mobile-context-content').replaceChildren(contextNode());
  const selected = selectedEvidence().result;
  document.querySelectorAll('.source-action').forEach(button => button.setAttribute('aria-pressed', String(button._evidenceResult === selected)));
}
function resizeComposer() {
  const input = $('message'); input.style.height = 'auto'; input.style.height = Math.min(input.scrollHeight, 144) + 'px';
}

function studyTopic(result) { return result.answer_review?.topic || result.practice_item?.topic || result.question_plan?.topic.replace(/^(?:what is|what are|define|explain)\s+/i, '').replace(/[.?!]+$/, '') || ''; }
function downloadText(name, value, type = 'text/plain') {
  const url = URL.createObjectURL(new Blob([value], { type })); const a = el('a'); a.href = url; a.download = name; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  $('completion-status').textContent = 'Download prepared: ' + name;
}
function educationNotice(message) { $('education-status').textContent = message; }
function confirmRowDelete(row, message, work) {
  const existing = row.querySelector('.delete-row-confirm');
  if (existing) { existing.querySelector('button:last-child').focus(); return; }
  const trigger = document.activeElement, confirm = el('div', 'delete-row-confirm'); text(confirm, message, 'small muted');
  const keep = action('Keep', () => { confirm.remove(); trigger?.focus(); });
  const remove = action('Delete', async () => { keep.disabled = true; try { await work(); } finally { keep.disabled = !enabled(); } });
  const actions = el('div', 'response-actions'); actions.append(remove, keep); confirm.append(actions); row.append(confirm); keep.focus();
}
function filterTopics() {
  const query = $('topic-filter').value.trim().toLocaleLowerCase();
  const rows = [...$('topic-list').querySelectorAll('.topic-row')]; let shown = 0;
  for (const row of rows) { row.hidden = Boolean(query) && !row.dataset.search.includes(query); if (!row.hidden) shown++; }
  $('topic-count').textContent = shown ? shown + ' of ' + rows.length + ' topics' : 'No matching topic. Try a shorter term or clear the filter.';
  $('clear-topic-filter').disabled = !enabled() || !$('topic-filter').value;
}
async function openEducation(mode, topic = '', forEdit = false) {
  if (!forEdit) editLoadVersion++;
  closeNavigation(); $('education-panel').hidden = false; $('open-education').setAttribute('aria-expanded', 'true'); $('welcome').hidden = true;
  $('save-education').checked = educationalSaving;
  if (mode === 'research') { $('progress-form').hidden = true; $('research-builder').open = true; if (topic) $('research-question').value = topic.slice(0, 500); }
  if (mode === 'progress') { $('research-builder').open = false; $('research-editor').hidden = true; $('progress-form').hidden = false; $('progress-topic').value = topic.slice(0, 200); }
  $('education-title').tabIndex = -1; $('education-title').focus(); $('scroll-region').scrollTop = 0;
  await loadEducation();
}
async function loadEducation() {
  if (!enabled()) { educationNotice('Start a conversation to open this workspace.'); return; }
  if ($('education-status').textContent === 'Start a conversation to open this workspace.') educationNotice('');
  const [topics, curriculum] = await Promise.all([request('/v1/study/topics'), request('/v1/study/curriculum')]); const list = $('topic-list'); list.replaceChildren();
  if (curriculum.status === 'ok') {
    disclosure(list, 'National MDS curriculum scope · ' + curriculum.version, body => {
      text(body, curriculum.readiness, 'small muted');
      text(body, 'Official 2017 base; amendment reconciliation pending. National curriculum only. Independent faculty review pending.', 'small muted');
      text(body, Object.values(curriculum.families || {}).join(' · '), 'small muted');
      text(body, Object.values(curriculum.specialties || {}).join(' · '), 'small muted');
    });
  } else text(list, curriculum.message || 'National curriculum scope could not be loaded. Check the local API connection.', 'small muted');
  text(list, topics.coverage_scope, 'small muted');
  if (!topics.topics?.length) text(list, 'No prepared topic pack is available. Check the teaching library in connections.', 'small muted');
  for (const topic of topics.topics || []) {
    const row = el('div', 'topic-row'); row.dataset.search = [topic.topic, ...(topic.aliases || [])].join(' ').toLocaleLowerCase(); row.append(el('strong', '', topic.topic));
    disclosure(row, 'Supported activities', body => text(body, Object.entries(topic.operations).map(([op, value]) => op.replaceAll('_', ' ') + ': ' + value.replaceAll('_', ' ')).join(' · '), 'small muted'));
    text(row, 'Faculty review pending · ' + (topic.pilot ? 'Oral Pathology pilot · ' : '') + 'Curriculum: ' + (topic.curriculum_ids.join(', ') || 'mapping pending'), 'small muted');
    const actions = el('div', 'response-actions');
    for (const [label, prompt] of [['Explain', 'What is ' + topic.topic + '?'], ['Viva', 'Ask me a viva question on ' + topic.topic]]) actions.append(action(label, () => { $('audience').value = 'study'; closeEducation(); sendQuestion(prompt); }));
    row.append(actions); list.append(row);
  }
  filterTopics();
  const saved = $('saved-work'); saved.replaceChildren();
  for (const id of ['export-education', 'delete-education', 'save-draft']) $(id).disabled = !educationalSaving || state.busy || $(id).dataset.pending === 'true';
  if (!educationalSaving) { text(saved, 'Local saving is off. You can browse topics without saving progress.', 'small muted'); return; }
  const [progress, research] = await Promise.all([request('/v1/study/progress'), request('/v1/research/projects')]);
  if (progress.status !== 'ok' || research.status !== 'ok') { educationNotice(progress.message || research.message || 'Saved work could not be loaded. Retry.'); return; }
  saved.append(el('h3', '', 'Saved study attempts'));
  if (!progress.records.length) text(saved, 'After a study answer, choose Record study attempt to keep your own progress.', 'small muted');
  for (const record of progress.records) {
    const row = el('div', 'saved-row'); row.append(el('strong', '', record.topic));
    text(row, record.attempts + ' attempts · ' + record.self_assessment + ' · revisit ' + record.revisit_on, 'small muted');
    text(row, record.weak_concepts.join(' · '), 'small muted');
    const actions = el('div', 'response-actions'); actions.append(action('Study again', () => { $('audience').value = 'study'; closeEducation(); sendQuestion('What is ' + record.topic + '?'); }), action('Delete attempt history…', () => confirmRowDelete(row, 'Delete the saved attempts for ' + record.topic + '?', async () => { const r = await request('/v1/study/progress/' + record.id, { method: 'DELETE' }); if (r.status === 'ok') { await loadEducation(); $('education-title').focus(); } else educationNotice(r.message); }))); row.append(actions); saved.append(row);
  }
  saved.append(el('h3', '', 'Research projects'));
  if (!research.projects.length) text(saved, 'Set up a focused question above to create a source-linked review scaffold.', 'small muted');
  for (const project of research.projects) {
    const row = el('div', 'saved-row'); row.append(el('strong', '', project.question)); text(row, project.created_at.slice(0, 10) + ' · appraisal pending', 'small muted');
    const actions = el('div', 'response-actions'); actions.append(action('Open project', async () => { const r = await request('/v1/research/projects/' + project.id); if (r.project) { $('audience').value = 'research'; addResearchResult(r.project); closeEducation(); scrollLatest(); } else educationNotice(r.message); }), action('Delete project…', () => confirmRowDelete(row, 'Delete this research project and its draft?', async () => { const r = await request('/v1/research/projects/' + project.id, { method: 'DELETE' }); if (r.status === 'ok') { editLoadVersion++; unsavedDrafts.delete(project.id); if (editingProject?.id === project.id) { editingProject = null; $('research-editor').hidden = true; } await loadEducation(); $('education-title').focus(); } else educationNotice(r.message); }))); row.append(actions); saved.append(row);
  }
}
function closeEducation() { editLoadVersion++; $('education-panel').hidden = true; $('open-education').setAttribute('aria-expanded', 'false'); render(); $('message').focus(); }
function addResearchResult(project) {
  const result = { status: project.evidence_table.length ? 'partial' : 'insufficient_evidence', route: 'research_assistance', message: 'Limited literature search complete. Medical synthesis, critical appraisal and manual screening remain pending.', research_project: project, citations: [], task_completion: false };
  const entry = { role: 'assistant', result, question: project.question }; state.entries.push(entry); state.evidence = { entry, result }; trimEntries(); render();
}
function researchEvidence(parent, project) {
  text(parent, project.search.provider + ' · ' + project.search.date_utc.slice(0, 10) + ' UTC', 'result-caption');
  text(parent, 'Query: ' + project.search.query, 'small muted'); text(parent, project.search.pagination + ' ' + project.search.screening, 'small muted');
  text(parent, project.contradictions, 'result-caption');
  for (const paper of project.papers) {
    const block = el('section', 'research-paper'); link(block, paper.title, paper.url);
    text(block, paper.authors + ' · ' + paper.year, 'small muted');
    text(block, paper.access.replaceAll('_', ' ') + ' · ' + paper.publication_status.replaceAll('_', ' '), 'small muted');
    text(block, paper.license, 'small muted');
    const row = project.evidence_table.find(item => item.paper_id === paper.id);
    if (row) disclosure(block, 'Evidence table & supporting passages', body => {
      text(body, 'Study design: ' + row.study_design.join(', '), 'small muted');
      for (const name of ['question', 'population_model', 'methods', 'findings', 'limitations']) { body.append(el('strong', '', name.replaceAll('_', ' '))); text(body, row[name].text, 'small muted'); }
      text(body, row.applicability, 'small muted');
      for (const passage of row.supporting_passages) disclosure(body, passage.section + (passage.fragment ? ' — incomplete fragment' : '') + ' · ' + passage.id, detail => text(detail, passage.text, 'small muted'));
    });
    else text(block, 'Excluded from draft evidence; review the record and its publication notices.', 'result-caption');
    for (const warning of paper.warnings) text(block, warning, 'small muted'); parent.append(block);
  }
}
async function exportProject(project, format) {
  const r = await request('/v1/research/projects/' + project.id + '/export?format=' + format, { responseType: 'text' });
  if (r.status === 'ok') downloadText('aster-review-' + project.id + (format === 'bibtex' ? '.bib' : '.md'), r.text);
  else announce('Export failed. Enable local saving and reopen the project to retry.');
}
async function editProject(project) {
  const generation = ++editLoadVersion; $('research-editor').hidden = true;
  await openEducation('research', '', true); if (generation !== editLoadVersion) return;
  if (!educationalSaving) { educationNotice('Enable local saving to reopen and edit a saved project.'); return; }
  educationNotice('Opening review draft…');
  const latest = await request('/v1/research/projects/' + project.id);
  if (generation !== editLoadVersion) return;
  if (!latest.project) { educationNotice(latest.message); return; }
  const selectedProject = latest.project;
  const draft = await request('/v1/research/projects/' + selectedProject.id + '/export?format=markdown', { responseType: 'text' });
  if (generation !== editLoadVersion) return;
  if (draft.status !== 'ok') { educationNotice('Draft could not be loaded. Reopen the project.'); return; }
  editingProject = selectedProject;
  $('research-draft').value = unsavedDrafts.get(editingProject.id) ?? editingProject.user_draft ?? (draft.text.length <= 30000 ? draft.text : '# ' + editingProject.question + '\n\n[Write your review here. Export the full evidence scaffold separately; it exceeds the editor limit.]'); $('research-editor').hidden = false; $('research-draft').focus();
  $('research-builder').open = false;
  educationNotice(unsavedDrafts.has(editingProject.id) ? 'Unsaved edits restored. Save the draft to retain them after closing the browser.' : 'Draft opened. Save edits before closing the browser.');
}
function renderLibraryServices(health, services) {
  const library = health.library || {}, missing = 'Unavailable · choose Repair Aster';
  const rows = [['Medical library', library.status === 'ready' ? 'Ready' + (library.used_last_known_good ? ' · using the previous library version' : '') : missing],
    ['Local AI model', health.ollama?.available ? 'Ready · ' + health.ollama.model : missing],
    ['Statement checker', health.claim_verifier?.available ? 'Ready' : 'Unavailable · answers fall back to stricter checks'],
    ['Prescription reading', health.ocr?.available ? 'Ready' + (health.ocr.handwriting_enabled ? ' · handwriting experimental' : '') : missing],
    ['X-ray assistance', health.xray?.uploads_available ? 'Ready · adult frontal chest X-rays only · research use' : 'Not available']];
  for (const [title, value] of rows) services.append(el('dt', '', title), el('dd', '', value));
  if (library.user_library) services.append(el('dt', '', 'My Library'), el('dd', '', library.user_library.documents ? Number(library.user_library.documents).toLocaleString() + ' documents · ' + Number(library.user_library.units).toLocaleString() + ' passages' : 'Empty · add your own documents from My Library'));
  for (const pack of library.packs || []) services.append(el('dt', '', pack.edition === 'nc' ? 'Noncommercial study pack' : 'Core library'), el('dd', '', Number(pack.documents).toLocaleString() + ' documents · ' + Number(pack.units).toLocaleString() + ' passages · built ' + String(pack.created || '').slice(0, 10)));
  for (const [kind, info] of Object.entries(library.freshness || {})) if (info.state !== 'current') services.append(el('dt', '', kind.replace('_', ' ') + ' information'), el('dd', '', info.state === 'outdated_warning' ? 'Older than its freshness limit · check for updates' : 'Update recommended'));
  if (health.release) services.append(el('dt', '', 'Installed version'), el('dd', '', health.release.app_version + (health.release.profile ? ' · ' + health.release.profile + ' profile' : '')));
  services.append(el('dt', '', 'Clinical validation'), el('dd', '', 'Not completed. Faculty and clinician review pending.'));
}
// ---------------------------------------------------------------- My Library
function libraryNotice(message) { $('library-status').textContent = message || ''; }
function libraryError(message) { $('library-error').textContent = message || ''; $('library-error').hidden = !message; }
function formatBytes(value) { return value >= 1048576 ? (value / 1048576).toFixed(1) + ' MB' : Math.max(1, Math.round(value / 1024)) + ' KB'; }
function renderLibrary(result) {
  const list = $('library-docs'); list.replaceChildren();
  const documents = result.documents || [];
  if (result.limits) libraryState.maxBytes = result.limits.max_bytes;
  if (result.limits) $('library-limits').textContent = 'PDF (text or scanned), Word (.docx), text or Markdown · up to ' + Math.round(result.limits.max_bytes / 1048576) + ' MB · ' + Number(result.limits.max_pages).toLocaleString() + ' pages';
  if (!documents.length) { list.append(el('li', 'small muted', 'No documents yet. Add your first article, notes or book above.')); return; }
  for (const doc of documents) {
    const item = el('li', 'library-doc'), details = el('div', 'library-doc-details');
    details.append(el('strong', '', doc.title));
    const facts = [doc.filename, doc.kind ? doc.kind.toUpperCase() : '', doc.pages ? doc.pages + ' pages' : '', formatBytes(doc.bytes || 0), 'added ' + String(doc.added || '').slice(0, 10)].filter(Boolean).join(' · ');
    details.append(el('span', 'small muted', facts));
    if (doc.status === 'ready') {
      details.append(el('span', 'small', Number(doc.units).toLocaleString() + ' passages · ready to use in answers'));
      if (doc.note) details.append(el('span', 'small muted', doc.note));
    } else if (doc.status === 'processing') {
      const bar = el('progress'); bar.max = 1; bar.value = doc.progress || 0; bar.setAttribute('aria-label', 'Indexing ' + doc.title);
      details.append(el('span', 'small', doc.note ? doc.note + '…' : (doc.progress || 0) < 0.1 ? 'Reading the document…' : 'Indexing passages · ' + Math.round((doc.progress || 0) * 100) + '%'), bar);
    } else details.append(el('span', 'error-text', 'Not added · ' + (doc.error || 'The document could not be processed.')));
    const remove = el('button', 'text-button', doc.status === 'failed' ? 'Dismiss' : 'Remove'); remove.type = 'button';
    remove.setAttribute('aria-label', 'Remove ' + doc.title + ' from My Library');
    remove.addEventListener('click', () => removeLibraryDocument(doc, remove));
    item.append(details, remove); list.append(item);
  }
}
async function loadLibrary() {
  clearTimeout(libraryState.timer);
  if (!state.token) { libraryNotice('Connecting locally…'); return; }
  const result = await request('/v1/library/documents');
  if (result.status !== 'ok') { libraryNotice(result.message || 'My Library is unavailable.'); renderLibrary({}); return; }
  const summary = result.summary || {};
  libraryNotice(summary.documents ? Number(summary.documents).toLocaleString() + ' document' + (summary.documents === 1 ? '' : 's') + ' · ' + Number(summary.units).toLocaleString() + ' passages searchable' : '');
  renderLibrary(result);
  // Indexing finished since the last poll: the settings panel's document and passage counts changed.
  if (libraryState.processing && !summary.processing) refreshHealth();
  libraryState.processing = summary.processing || 0;
  if (summary.processing && $('library-dialog').open) libraryState.timer = setTimeout(loadLibrary, 2000);
}
async function openLibrary() { libraryError(''); $('library-dialog').showModal(); updateControls(); await loadLibrary(); }
async function addLibraryDocument(event) {
  event.preventDefault();
  const file = $('library-file').files[0];
  if (!file || !$('library-rights').checked || libraryState.adding) return;
  if (libraryState.maxBytes && file.size > libraryState.maxBytes) { libraryError('This file is ' + formatBytes(file.size) + '. Files for My Library can be up to ' + formatBytes(libraryState.maxBytes) + '; split it and add the parts.'); return; }
  libraryError(''); libraryState.adding = true; updateControls(); libraryNotice('Uploading ' + file.name + '…');
  try {
    const query = '?filename=' + encodeURIComponent(file.name) + '&title=' + encodeURIComponent($('library-title-input').value.trim()) + '&rights_confirmed=true';
    const result = await request('/v1/library/documents' + query, { method: 'POST', body: file, contentType: 'application/octet-stream' });
    if (result.status !== 'ok') { libraryError(result.message || 'The document could not be added.'); libraryNotice(''); return; }
    $('library-form').reset(); $('library-title-input').placeholder = 'e.g. Shafer’s Oral Pathology, chapter 3'; announce(result.message); await loadLibrary(); await refreshHealth();
  } finally { libraryState.adding = false; updateControls(); }
}
async function removeLibraryDocument(doc, button) {
  if (doc.status !== 'failed' && !window.confirm('Remove “' + doc.title + '” from My Library? Aster will stop using it in answers. Your original file is not affected.')) return;
  button.disabled = true;
  const result = await request('/v1/library/documents/' + encodeURIComponent(doc.doc_id), { method: 'DELETE' });
  if (result.status !== 'ok') { libraryError(result.message || 'The document could not be removed.'); button.disabled = false; return; }
  libraryNotice(result.message); renderLibrary(result); await refreshHealth();
}
async function updateLibrary(button) {
  if (!window.confirm('Check for a newer medical library? Aster will contact the GitHub release server and download signed reference packs (several hundred MB). No questions, documents or images are sent.')) return;
  button.disabled = true; announce('Checking for library updates…');
  const result = await request('/v1/library/update', { method: 'POST', json: { network_consent: true, include_noncommercial: true } });
  announce(result.message || 'The update check finished.'); button.disabled = false; await refreshHealth();
}
function renderServices() {
  const health = state.health, services = $('services'); services.replaceChildren();
  if (health.answer_engine === 'grounded') { renderLibraryServices(health, services); return; }
  const packaged = Boolean(health.release), missing = packaged ? 'Unavailable · repair installation' : 'Setup required';
  for (const [title, value] of [['Research API', health.references?.records ? 'Ready' : 'Unavailable'], ['Conversational model', health.ollama?.available ? 'Ready' : missing], ['Image classification', health.attachment_classifier?.available ? 'Ready' : missing], ['Prescription OCR', health.ocr?.available ? 'Ready' : missing], ['Specialist X-ray scores', health.xray?.available ? 'Ready' : packaged && !health.release.features?.xray_scores ? 'Not included in this edition' : 'Setup required']]) services.append(el('dt', '', title), el('dd', '', value));
  if (packaged) {
    services.append(el('dt', '', 'Installed edition'), el('dd', '', health.release.edition + ' · ' + health.release.app_version));
    if (health.release.model) services.append(el('dt', '', 'Included model'), el('dd', '', health.release.model.tag + ' · SHA-256 ' + health.release.model.digest));
    for (const [name, item] of Object.entries(health.release.data || {})) {
      const description = item.included === false ? 'Not included · ' + item.reason : [item.release, item.records !== undefined ? Number(item.records).toLocaleString() + ' reference sections' : null].filter(Boolean).join(' · ');
      services.append(el('dt', '', name.charAt(0).toUpperCase() + name.slice(1) + ' data'), el('dd', '', description));
    }
    services.append(el('dt', '', 'Clinical validation'), el('dd', '', 'Not completed. Faculty review pending.'));
  }
}
const phoneLayout = window.matchMedia('(max-width:639px)');
function syncNavigation() {
  const open = phoneLayout.matches && $('navigation').classList.contains('open');
  $('navigation').inert = phoneLayout.matches && !open;
  document.querySelector('.conversation').inert = open;
  $('nav-scrim').hidden = !open; $('menu').setAttribute('aria-expanded', String(open));
}
function closeNavigation() { $('navigation').classList.remove('open'); syncNavigation(); }
$('menu').addEventListener('click', () => { const open = !$('navigation').classList.contains('open'); $('navigation').classList.add('drawer-ready'); $('navigation').classList.toggle('open', open); syncNavigation(); if (open) $('new-chat').focus(); });
phoneLayout.addEventListener('change', () => { $('navigation').classList.remove('drawer-ready'); closeNavigation(); }); syncNavigation();
$('nav-scrim').addEventListener('click', () => { closeNavigation(); $('menu').focus(); });
document.addEventListener('keydown', event => {
  if (!$('navigation').classList.contains('open')) return;
  if (event.key === 'Escape') { closeNavigation(); $('menu').focus(); }
  if (event.key === 'Tab') {
    const controls = [...$('navigation').querySelectorAll('a,button')].filter(n => !n.disabled);
    const first = controls[0], last = controls[controls.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }
});
document.querySelectorAll('[data-close]').forEach(button => button.addEventListener('click', () => $(button.dataset.close).close()));
$('new-chat').addEventListener('click', () => { if (state.entries.length) $('clear-dialog').showModal(); else newConversation(); });
$('clear-session').addEventListener('click', () => $('clear-dialog').showModal()); $('confirm-clear').addEventListener('click', newConversation);
$('connections').addEventListener('click', () => { closeNavigation(); $('settings-dialog').showModal(); renderServices(); });
$('open-education').addEventListener('click', () => openEducation());
$('close-education').addEventListener('click', closeEducation);
$('save-education').checked = educationalSaving;
$('save-education').addEventListener('change', async () => {
  try {
    if ($('save-education').checked && !workspaceKey) { const bytes = new Uint8Array(32); crypto.getRandomValues(bytes); workspaceKey = Array.from(bytes, v => v.toString(16).padStart(2, '0')).join(''); localStorage.setItem('aster.education.key', workspaceKey); }
    educationalSaving = $('save-education').checked; localStorage.setItem('aster.education.enabled', String(educationalSaving)); educationNotice(educationalSaving ? 'Local saving enabled. Only actions you explicitly save are retained.' : 'Saving disabled. Previously saved work remains until you delete it.'); await loadEducation();
  } catch { educationalSaving = false; $('save-education').checked = false; educationNotice('Browser storage is unavailable. Allow local storage to enable saving.'); }
});
$('progress-form').addEventListener('submit', async event => {
  event.preventDefault(); if (!educationalSaving) { educationNotice('Enable local saving first.'); return; }
  await run('Saving your study attempt…', async () => {
    const r = await request('/v1/study/progress', { method: 'POST', json: { topic: $('progress-topic').value.trim(), self_assessment: $('progress-rating').value, weak_concepts: $('progress-weak').value.split('\n').map(s => s.trim()).filter(Boolean) } });
    educationNotice(r.status === 'ok' ? 'Study attempt saved as self-assessment.' : r.message); return completionSummary(r, 'Study attempt saved.');
  }); await loadEducation();
});
$('research-form').addEventListener('submit', async event => {
  event.preventDefault(); if (!educationalSaving) { educationNotice('Enable local saving before creating a research project.'); return; }
  if (!$('research-public').checked) return;
  const payload = { question: $('research-question').value.trim(), population: $('research-population').value.trim(), article_type: $('research-type').value, query: $('research-query').value.trim(), inclusion: $('research-inclusion').value.trim(), exclusion: $('research-exclusion').value.trim(), limit: Number($('research-limit').value), inspect_full_text: $('research-full-text').checked, public_query_confirmed: true };
  await run('Searching public literature and checking source access…', async signal => {
    const r = await request('/v1/research/projects', { method: 'POST', json: payload, signal });
    if (r.project) { addResearchResult(r.project); $('research-public').checked = false; closeEducation(); return 'Limited literature search complete. Evidence and review scaffold are ready; appraisal is pending.'; }
    educationNotice(r.message || 'The search could not finish. Retry.'); return completionSummary(r);
  }); scrollToEntry(state.entries.at(-1));
});
$('save-draft').addEventListener('click', () => AsterInteractions.withPending($('save-draft'), async () => {
  if (!editingProject || !educationalSaving) return;
  const savingProject = editingProject, draft = $('research-draft').value;
  const r = await request('/v1/research/projects/' + savingProject.id + '/writing', { method: 'PUT', json: { expected_revision: savingProject.version, draft } });
  if (r.project) {
    const outcome = AsterInteractions.draftSaveState(editingProject?.id, savingProject.id, draft, unsavedDrafts.get(savingProject.id) ?? draft);
    if (outcome !== 'other_project') editingProject = r.project;
    if (outcome === 'saved') unsavedDrafts.delete(savingProject.id);
    educationNotice(outcome === 'newer_edits' ? 'Earlier draft saved. Your newer edits are still unsaved.' : 'Draft saved as unverified writing.');
  } else educationNotice(r.message || 'Draft could not be saved. Keep a copy and reopen the project.');
}, 'Saving…', () => !enabled() || !educationalSaving).catch(() => educationNotice('Draft could not be saved. Your edits remain here; retry.')));
$('research-draft').addEventListener('input', () => { if (editingProject) { unsavedDrafts.set(editingProject.id, $('research-draft').value); educationNotice('Unsaved draft changes. Save before closing the browser.'); } });
window.addEventListener('beforeunload', event => { if (unsavedDrafts.size) { event.preventDefault(); event.returnValue = ''; } });
$('export-education').addEventListener('click', () => AsterInteractions.withPending($('export-education'), async () => { const r = await request('/v1/education/export'); if (r.status === 'ok') { downloadText('aster-educational-work.json', JSON.stringify(r, null, 2), 'application/json'); educationNotice('Saved-work export prepared. Check your browser downloads.'); } else educationNotice(r.message); }, 'Preparing export…', () => !enabled() || !educationalSaving).catch(() => educationNotice('Export could not finish. Retry.')));
$('topic-filter').addEventListener('input', filterTopics);
$('clear-topic-filter').addEventListener('click', () => { $('topic-filter').value = ''; filterTopics(); $('topic-filter').focus(); });
$('topic-filter').addEventListener('keydown', event => { if (event.key === 'Escape' && $('topic-filter').value) { event.preventDefault(); event.stopPropagation(); $('clear-topic-filter').click(); } });
$('delete-education').addEventListener('click', () => { $('education-delete-confirm').hidden = false; $('cancel-delete-education').focus(); });
$('cancel-delete-education').addEventListener('click', () => { $('education-delete-confirm').hidden = true; });
$('confirm-delete-education').addEventListener('click', () => AsterInteractions.withPending($('confirm-delete-education'), async () => {
  $('cancel-delete-education').disabled = true;
  try {
    const r = await request('/v1/education', { method: 'DELETE' });
    if (r.status === 'ok') { editLoadVersion++; $('education-delete-confirm').hidden = true; unsavedDrafts.clear(); editingProject = null; $('research-editor').hidden = true; educationNotice('Saved educational work deleted. Downloaded files remain.'); await loadEducation(); $('education-title').focus(); }
    else educationNotice(r.message);
  } finally { $('cancel-delete-education').disabled = !enabled(); }
}, 'Deleting…', () => !enabled() || !educationalSaving).catch(() => educationNotice('Deletion could not finish. Reopen saved work to check its status before retrying.')));
$('audience').addEventListener('change', () => { if ($('audience').value === 'research') openEducation('research'); });
$('refresh-services').addEventListener('click', async () => { const connected = await refreshHealth(); if (!state.token && connected) await startSession(); updateControls(); });
$('attach').addEventListener('click', openUpload); $('starter-prescription').addEventListener('click', openUpload); $('starter-xray').addEventListener('click', openUpload);
$('file').addEventListener('change', event => selectFile(event.target.files[0])); $('remove-upload').addEventListener('click', clearSelection); $('upload-submit').addEventListener('click', () => attachFile(state.selection));
$('paper-authorized').addEventListener('change', updateControls);
$('starter-question').addEventListener('click', () => { $('message').value = 'What does blood pressure mean?'; $('message').focus(); updateControls(); });
$('sample').addEventListener('click', async () => {
  if (!enabled()) return; $('sample').disabled = true;
  try { const response = await fetch('/sample-prescription', { cache: 'no-store' }); if (!response.ok) throw new Error(); const file = new File([await response.blob()], 'synthetic-prescription.png', { type: 'image/png' }); await attachFile(file); }
  catch { announce('The synthetic sample is unavailable. Choose your own permitted image.'); } finally { updateControls(); }
});
$('detach-context').addEventListener('click', () => { state.activeDocument = null; updateControls(); $('message').focus(); });
$('message').addEventListener('input', () => { resizeComposer(); updateControls(); });
$('open-evidence').addEventListener('click', () => { updateContext(); $('evidence-dialog').showModal(); });
$('message').addEventListener('keydown', event => { if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); if (enabled() && $('message').value.trim()) $('chat-form').requestSubmit(); } });
$('chat-form').addEventListener('submit', event => { event.preventDefault(); sendQuestion($('message').value); });
window.addEventListener('pagehide', () => { state.controller?.abort(); revokePreviews(); if (state.selectionURL) URL.revokeObjectURL(state.selectionURL); });
async function initialize() { updateControls(); render(); const connected = await refreshHealth(); if (connected) await startSession(); render(); }
initialize();
document.querySelectorAll('input[name="pdf-kind"]').forEach(radio => radio.addEventListener('change', syncPdfKind));
$('update-library').addEventListener('click', event => updateLibrary(event.currentTarget));
$('open-library').addEventListener('click', openLibrary);
$('library-form').addEventListener('submit', addLibraryDocument);
$('library-file').addEventListener('change', () => { libraryError(''); if ($('library-file').files[0]) $('library-title-input').placeholder = $('library-file').files[0].name.replace(/\.[^.]+$/, ''); updateControls(); });
$('library-rights').addEventListener('change', updateControls);
$('library-dialog').addEventListener('close', () => clearTimeout(libraryState.timer));
