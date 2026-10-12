const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "../dashboard/static/js/service_form.js"), "utf8",
);

test("Clear selection removes every lead without submitting the form", () => {
  let click;
  let change;
  let focused = false;
  const select = {
    options: [{ selected: true }, { selected: false }, { selected: true }],
    dispatchEvent(event) { change = event; },
    focus() { focused = true; },
  };
  const button = { addEventListener(type, callback) { assert.equal(type, "click"); click = callback; } };
  const document = { readyState: "complete", getElementById(id) {
    return id === "id_doctors" ? select : button;
  } };
  class Event { constructor(type, options) { this.type = type; this.bubbles = options.bubbles; } }
  vm.runInNewContext(source, { document, Event });
  assert.equal(select.options[0].selected, true);
  click();
  assert.equal(select.options.every(option => !option.selected), true);
  assert.equal(change.type, "change");
  assert.equal(change.bubbles, true);
  assert.equal(focused, true);
});

test("unrelated pages and deferred initialization are safe", () => {
  assert.doesNotThrow(() => vm.runInNewContext(source, {
    document: { readyState: "complete", getElementById() { return null; } },
  }));
  let ready;
  const document = { readyState: "loading", addEventListener(type, callback) {
    assert.equal(type, "DOMContentLoaded"); ready = callback;
  }, getElementById() { return null; } };
  vm.runInNewContext(source, { document });
  assert.doesNotThrow(() => ready());
});
