(function () {
  "use strict";

  function initializeCounters() {
    const form = document.getElementById("about-introduction-form");
    if (!form) return;

    form.querySelectorAll("[data-about-character-limit]").forEach(function (input) {
      const counter = document.getElementById(input.id + "_count");
      if (!counter) return;
      const limit = Number(input.getAttribute("data-about-character-limit"));
      const update = function () {
        // Count Unicode code points, matching Django's server-side length check.
        const length = Array.from(input.value).length;
        counter.textContent = length + " / " + limit + " characters";
        counter.classList.toggle("text-danger", length > limit);
        counter.classList.toggle("text-muted", length <= limit);
      };
      input.addEventListener("input", update);
      update();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeCounters);
  } else {
    initializeCounters();
  }
})();
