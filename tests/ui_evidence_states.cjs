const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

test('a displayed provisional answer announces its actual evidence status', () => {
  const source = fs.readFileSync('frontend/web/app.js', 'utf8');
  const start = source.indexOf('function completionSummary(');
  const end = source.indexOf('function enabled()', start);
  const context = vm.createContext({});
  vm.runInContext(source.slice(start, end), context);
  const summary = context.completionSummary({ status: 'insufficient_evidence', provisional_explanation: { text: 'Example' } });
  assert.match(summary, /provisional/i);
  assert.doesNotMatch(summary, /could not finish/i);
});

test('provisional explanation is visibly labelled beside supported claims', () => {
  const source = fs.readFileSync('frontend/web/app.js', 'utf8');
  const start = source.indexOf('function renderAnswerBody(');
  const end = source.indexOf('function renderResult(', start);
  const seen = [];
  const el = (tag, cls, value) => ({ tag, children: [], append(...nodes) { this.children.push(...nodes); }, value });
  const context = vm.createContext({ el, text(parent, value, cls) { seen.push({ value, cls }); }, patientHeadings: {} });
  vm.runInContext(source.slice(start, end), context);
  const content = el('div');
  context.renderAnswerBody(content, { claims: [{ text: 'Supported source passage' }],
    evidence_states: { response: { label: 'Source supported — human review pending' } },
    provisional_explanation: { label: 'General model knowledge — not source verified',
      text: 'Provisional explanation', limitations: 'Check an authoritative reference.' } });
  assert.ok(seen.some(item => item.value === 'Supported source passage'));
  assert.ok(seen.some(item => item.value === 'Provisional explanation'));
  assert.ok(seen.some(item => item.value === 'Check an authoritative reference.' && item.cls === 'result-notice'));
  assert.equal(content.children.at(-1).children[0].value, 'General model knowledge — not source verified');
});
