const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function harness() {
  const nodes = new Map();
  const node = id => {
    if (!nodes.has(id)) nodes.set(id, { value: '', checked: false, hidden: false, disabled: false, textContent: '',
      removeAttribute() {}, setAttribute() {}, querySelector() { return { focus() {} }; } });
    return nodes.get(id);
  };
  const source = fs.readFileSync('frontend/web/app.js', 'utf8');
  const start = source.indexOf('function clearSelection()');
  const end = source.indexOf('async function retryAttachment', start);
  const context = { $: node, state: { token: 'synthetic', health: { private_papers: { enabled: true } }, entries: [] },
    URL: { createObjectURL: () => 'blob:synthetic', revokeObjectURL() {} }, enabled: () => true, updateControls() {},
    // The attachment dialog's "What is this PDF?" choice: these tests cover the research-paper path.
    document: { querySelector: selector => selector.includes('pdf-kind') ? { value: 'paper' } : null },
    render() {}, scrollLatest() {}, scrollToEntry() {}, trimEntries() {}, completionSummary: () => '',
    announce(message) { context.lastNotice = message; }, run: async (label, work) => work(),
    FormData: class { append() {} }, request: async (path, options) => {
      context.sent = { path, options }; return { document_id: 'paper_fixture', intent: 'paper', revision: 1, confirmed_revision: null, pages: [] };
    } };
  node('upload-dialog').close = () => {};
  node('settings-dialog').close = () => {};
  vm.createContext(context); vm.runInContext(source.slice(start, end), context);
  return { context, node };
}

test('PDF selection uses paper preview and explicit private permission', () => {
  const { context, node } = harness();
  context.selectFile({ type: 'application/pdf', size: 1000, name: 'synthetic.pdf' });
  assert.equal(context.state.selection.name, 'synthetic.pdf');
  assert.equal(node('paper-authorization').hidden, false);
  assert.equal(node('preview-image').hidden, true);
  assert.equal(node('paper-authorized').checked, false);
});

test('unapproved PDF cannot be uploaded and approved PDF uses raw body', async () => {
  const { context, node } = harness();
  const file = { type: 'application/pdf', size: 1000, name: 'synthetic.pdf' };
  await context.attachFile(file);
  assert.equal(context.sent, undefined);
  node('paper-authorized').checked = true;
  await context.attachFile(file);
  assert.equal(context.sent.path, '/v1/papers?private_analysis_authorized=true');
  assert.equal(context.sent.options.body, file);
  assert.equal(context.sent.options.contentType, 'application/pdf');
  assert.equal(context.state.entries.at(-1).paper.document_id, 'paper_fixture');
});

test('image selection hides paper permission and still uses image classifier', async () => {
  const { context, node } = harness();
  const file = { type: 'image/png', size: 1000, name: 'synthetic.png' };
  context.selectFile(file);
  assert.equal(node('paper-authorization').hidden, true);
  assert.equal(node('preview-image').hidden, false);
  await context.attachFile(file);
  assert.equal(context.sent.path, '/v1/attachments');
});

test('paper analysis remains selected evidence and is the fallback source view', () => {
  const source = fs.readFileSync('frontend/web/app.js', 'utf8');
  const analysis = { citations: [{ source_type: 'private_paper' }] };
  const entry = { role: 'assistant', result: { intent: 'paper' }, paperAnalysis: analysis };
  const context = vm.createContext({ state: { entries: [entry], evidence: { entry, result: analysis } } });
  vm.runInContext(source.slice(source.indexOf('function selectedEvidence()'), source.indexOf('function contextNode()')), context);
  assert.equal(context.selectedEvidence().result, analysis);
  context.state.evidence = null;
  assert.equal(context.selectedEvidence().result, analysis);
});

test('reopening or deleting a paper removes its earlier analyses and active context', () => {
  const source = fs.readFileSync('frontend/web/app.js', 'utf8');
  const original = { role: 'assistant', paper: { document_id: 'paper_fixture' }, paperAnalysis: { context_id: 'paper_fixture' } };
  const followup = { result: { context_id: 'paper_fixture' } }, other = { result: { context_id: 'paper_other' } };
  const context = vm.createContext({ state: { entries: [original, followup, other], activeDocument: original.paper,
    evidence: { entry: followup, result: followup.result } } });
  const start = source.indexOf('function clearPaperContext(');
  assert.notEqual(start, -1);
  vm.runInContext(source.slice(start, source.indexOf('function reviewPaper(', start)), context);
  context.clearPaperContext('paper_fixture');
  assert.equal(context.state.entries.length, 2);
  assert.equal(original.paperAnalysis, null);
  assert.equal(context.state.activeDocument, null);
  assert.equal(context.state.evidence, null);
  context.clearPaperContext('paper_fixture', true);
  assert.equal(context.state.entries.length, 1);
  assert.equal(context.state.entries[0], other);
});
