const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "../dashboard/static/js/about_content.js"), "utf8",
);

function setup({ value = "Care for families", limit = 80, formPresent = true,
  counterPresent = true, readyState = "complete" } = {}) {
  const classes = new Set(["text-muted"]);
  const counter = { textContent: "", classList: {
    toggle(name, enabled) { enabled ? classes.add(name) : classes.delete(name); },
  } };
  const input = { id: "id_hero_title", value, listeners: {},
    getAttribute() { return String(limit); },
    addEventListener(name, callback) { this.listeners[name] = callback; },
  };
  const form = { querySelectorAll() { return [input]; } };
  const events = {};
  const document = { readyState,
    getElementById(id) {
      if (id === "about-introduction-form") return formPresent ? form : null;
      if (id === input.id + "_count") return counterPresent ? counter : null;
      return null;
    },
    addEventListener(name, callback) { events[name] = callback; },
  };
  vm.runInNewContext(source, { document });
  return { input, counter, classes, events };
}

test("saved copy and live edits update the character counter", () => {
  const { input, counter } = setup();
  assert.equal(counter.textContent, "17 / 80 characters");
  input.value = "Family care";
  input.listeners.input();
  assert.equal(counter.textContent, "11 / 80 characters");
});

test("counter uses Unicode code points and warns without truncating entered text", () => {
  const { input, counter, classes } = setup({ value: "😀éA", limit: 3 });
  assert.equal(counter.textContent, "3 / 3 characters");
  assert.equal(classes.has("text-danger"), false);
  input.value = "😀éAB";
  input.listeners.input();
  assert.equal(counter.textContent, "4 / 3 characters");
  assert.equal(input.value, "😀éAB");
  assert.equal(classes.has("text-danger"), true);
  assert.equal(classes.has("text-muted"), false);
  input.value = "";
  input.listeners.input();
  assert.equal(classes.has("text-danger"), false);
  assert.equal(counter.textContent, "0 / 3 characters");
});

test("counter initializes after DOM readiness", () => {
  const { input, counter, events } = setup({ readyState: "loading" });
  assert.equal(counter.textContent, "");
  events.DOMContentLoaded();
  assert.equal(typeof input.listeners.input, "function");
  assert.equal(counter.textContent, "17 / 80 characters");
});

test("unrelated pages and missing counters are harmless", () => {
  assert.doesNotThrow(() => setup({ formPresent: false }));
  const { input } = setup({ counterPresent: false });
  assert.equal(input.listeners.input, undefined);
});
