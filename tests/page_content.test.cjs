const test = require("node:test");
const assert = require("node:assert/strict");
const { normalizedCopy, countCopy, initialize } = require("../dashboard/static/js/page_content.js");

test("section counters match Unicode code-point and Python whitespace rules", () => {
  assert.equal(normalizedCopy("  Care\n\tfor\u0085\u0085everyone  "), "Care for everyone");
  assert.equal(countCopy("🩺 care"), 6);
  assert.equal(countCopy("e\u0301"), 2);
  assert.equal(countCopy("\ufefftext\ufeff"), 6);
  assert.equal(countCopy("a\u00a0\u3000b"), 3);
});

test("counter initializes, reports excess and never truncates an editorial draft", () => {
  const listeners = {};
  const attrs = {};
  let warning;
  const input = { id: "id_title", value: "Hello", dataset: { copyLimit: "5" },
    setAttribute: (key, value) => { attrs[key] = value; },
    addEventListener: (name, action) => { listeners[name] = action; } };
  const counter = { textContent: "", classList: { toggle: (_name, value) => { warning = value; } } };
  initialize({ querySelectorAll: () => [input], querySelector: () => counter, getElementById: () => ({}) });
  assert.equal(counter.textContent, "5 / 5 characters");
  assert.equal(attrs["aria-invalid"], "true");
  input.value = "Hello🩺"; listeners.input();
  assert.equal(counter.textContent, "6 / 5 characters");
  assert.equal(warning, true); assert.equal(input.value, "Hello🩺");
  input.value = "Hi"; listeners.input(); assert.equal(warning, false);
});

test("unrelated pages and absent counter elements are harmless", () => {
  initialize({ querySelectorAll: () => [] });
  initialize({ querySelectorAll: () => [{ id: "other" }], querySelector: () => null });
});
