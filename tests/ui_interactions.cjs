const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { withPending, draftSaveState } = require('../frontend/web/ui-interactions.js');

function button() {
  return { disabled: false, textContent: 'Save draft', dataset: {},
    attrs: {}, setAttribute(k, v) { this.attrs[k] = v; },
    removeAttribute(k) { delete this.attrs[k]; } };
}

test('repeated activation shares one in-flight action and restores its control', async () => {
  const control = button(); let finish; let calls = 0;
  const work = () => { calls++; return new Promise(resolve => { finish = resolve; }); };
  const first = withPending(control, work, 'Saving…');
  const second = withPending(control, work, 'Saving…');
  assert.equal(control.disabled, true);
  assert.equal(control.attrs['aria-busy'], 'true');
  assert.equal(control.textContent, 'Saving…');
  await Promise.resolve();
  finish('saved');
  assert.deepEqual(await Promise.all([first, second]), ['saved', 'saved']);
  assert.equal(calls, 1);
  assert.equal(control.textContent, 'Save draft');
  assert.equal(control.disabled, false);
  assert.equal(control.attrs['aria-busy'], undefined);
});

test('failed actions restore the button but preserve a newly imposed disabled state', async () => {
  const control = button();
  await assert.rejects(withPending(control, async () => { throw new Error('offline'); }, 'Saving…', () => true), /offline/);
  assert.equal(control.textContent, 'Save draft');
  assert.equal(control.disabled, true);
  assert.equal(control.dataset.pending, undefined);
});

test('saving an earlier draft never clears newer edits or changes another project', () => {
  assert.equal(draftSaveState('a', 'a', 'old', 'new'), 'newer_edits');
  assert.equal(draftSaveState('a', 'a', 'old', 'old'), 'saved');
  assert.equal(draftSaveState('a', 'b', 'old', 'old'), 'other_project');
});

test('pending control restores lost focus without taking it from another field', async () => {
  const control = button(), body = {}, otherField = {};
  const doc = { activeElement: control, body }; global.document = doc;
  control.isConnected = true; control.focus = () => { doc.activeElement = control; };
  try {
    await withPending(control, async () => { doc.activeElement = body; });
    assert.equal(doc.activeElement, control);
    await withPending(control, async () => { doc.activeElement = otherField; });
    assert.equal(doc.activeElement, otherField);
  } finally { delete global.document; }
});

test('out-of-order project loads keep the latest selected project and its text together', async () => {
  const source = fs.readFileSync(require.resolve('../frontend/web/app.js'), 'utf8');
  const editFunction = source.slice(source.indexOf('async function editProject('), source.indexOf('\nfunction renderServices('));
  const nodes = new Map();
  const $ = id => { if (!nodes.has(id)) nodes.set(id, { value: '', hidden: false, focus() {} }); return nodes.get(id); };
  let finishA, finishB, startedA, startedB;
  const aStarted = new Promise(resolve => { startedA = resolve; });
  const bStarted = new Promise(resolve => { startedB = resolve; });
  const context = vm.createContext({ $, editingProject: null, editLoadVersion: 0,
    educationalSaving: true, unsavedDrafts: new Map(), educationNotice() {},
    openEducation: async () => {},
    request: async path => {
      const id = path.split('/')[4];
      if (!path.includes('/export')) return { project: { id } };
      return new Promise(resolve => { if (id === 'a') { finishA = resolve; startedA(); } else { finishB = resolve; startedB(); } });
    } });
  vm.runInContext(editFunction, context);
  const first = context.editProject({ id: 'a' }); await aStarted;
  const second = context.editProject({ id: 'b' }); await bStarted;
  finishB({ status: 'ok', text: 'B markdown' }); await second;
  finishA({ status: 'ok', text: 'A markdown' }); await first;
  assert.equal(context.editingProject.id, 'b');
  assert.equal($('research-draft').value, 'B markdown');
});
