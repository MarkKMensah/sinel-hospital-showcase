(function (root) {
  "use strict";
  // Exactly Python str.split whitespace, rather than ECMAScript's different
  // U+0085/U+FEFF policy. Server validation remains authoritative.
  function normalizedCopy(value) {
    return String(value).split(/[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+/u).filter(Boolean).join(" ");
  }
  function countCopy(value) { return Array.from(normalizedCopy(value)).length; }
  function initialize(document) {
    document.querySelectorAll("[data-copy-limit]").forEach(function (input) {
      var counter = document.querySelector('[data-copy-counter="' + input.id + '"]');
      if (!counter) return;
      var described = [input.id + "_helptext", input.id + "_count"];
      if (document.getElementById(input.id + "_error")) {
        described.push(input.id + "_error"); input.setAttribute("aria-invalid", "true");
      }
      input.setAttribute("aria-describedby", described.join(" "));
      function update() {
        var count = countCopy(input.value);
        var maximum = Number(input.dataset.copyLimit);
        counter.textContent = count + " / " + maximum + " characters";
        counter.classList.toggle("text-danger", count > maximum);
      }
      input.addEventListener("input", update); update();
    });
  }
  if (typeof module !== "undefined" && module.exports) module.exports = { normalizedCopy, countCopy, initialize };
  if (root.document) initialize(root.document);
}(typeof globalThis === "undefined" ? window : globalThis));
