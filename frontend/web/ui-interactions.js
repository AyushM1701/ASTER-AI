'use strict';

// Shared feedback primitives; neither helper stores documents or makes requests.
const AsterInteractions = (() => {
  const pending = new WeakMap();
  function withPending(button, work, label = 'Working…', stillDisabled = () => false) {
    if (pending.has(button)) return pending.get(button);
    const previous = { text: button.textContent, disabled: button.disabled };
    const doc = typeof document === 'undefined' ? null : document;
    const restoreFocus = doc?.activeElement === button;
    button.disabled = true; button.dataset.pending = 'true';
    button.setAttribute('aria-busy', 'true'); button.textContent = label;
    const task = Promise.resolve().then(work).finally(() => {
      pending.delete(button); delete button.dataset.pending;
      button.removeAttribute('aria-busy'); button.textContent = previous.text;
      button.disabled = previous.disabled || stillDisabled();
      if (restoreFocus && button.isConnected && !button.disabled && doc.activeElement === doc.body) button.focus({ preventScroll: true });
    });
    pending.set(button, task); return task;
  }
  function draftSaveState(activeId, savedId, savedText, currentText) {
    if (activeId !== savedId) return 'other_project';
    return savedText === currentText ? 'saved' : 'newer_edits';
  }
  return { withPending, draftSaveState };
})();
if (typeof module !== 'undefined' && module.exports) module.exports = AsterInteractions;
