(function () {
  "use strict";

  function initializeClearSelection() {
    const select = document.getElementById("id_doctors");
    const button = document.getElementById("clear-service-team-lead");
    if (!select || !button) return;
    button.addEventListener("click", function () {
      Array.from(select.options).forEach(function (option) {
        option.selected = false;
      });
      select.dispatchEvent(new Event("change", { bubbles: true }));
      select.focus();
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeClearSelection);
  } else {
    initializeClearSelection();
  }
})();
