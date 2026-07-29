(() => {
  const cards = Array.from(document.querySelectorAll("[data-team-card]"));
  const searchInput = document.querySelector("#team-search-input");
  const specialtySelect = document.querySelector("#team-specialty-select");
  const visibleCount = document.querySelector("#team-visible-count");
  const clearButton = document.querySelector("#team-clear-filters");
  const noResults = document.querySelector("#team-no-results");
  const noResultsClear = document.querySelector("#team-no-results-clear");

  const normalize = (value) => value.trim().toLocaleLowerCase();

  const clearFilters = () => {
    if (searchInput) searchInput.value = "";
    if (specialtySelect) specialtySelect.value = "";
    applyFilters();
    searchInput?.focus();
  };

  const applyFilters = () => {
    const query = normalize(searchInput?.value || "");
    const specialty = specialtySelect?.value || "";
    let shown = 0;

    cards.forEach((card) => {
      const name = normalize(card.dataset.teamName || "");
      const role = normalize(card.dataset.teamSpecialty || "");
      const matchesQuery = !query || name.includes(query) || role.includes(query);
      const matchesSpecialty =
        !specialty || card.dataset.teamSpecialty === specialty;
      const visible = matchesQuery && matchesSpecialty;

      card.hidden = !visible;
      if (visible) shown += 1;
    });

    if (visibleCount) visibleCount.textContent = String(shown);
    if (noResults) noResults.hidden = shown !== 0;
    if (clearButton) clearButton.hidden = !query && !specialty;
  };

  searchInput?.addEventListener("input", applyFilters);
  specialtySelect?.addEventListener("change", applyFilters);
  clearButton?.addEventListener("click", clearFilters);
  noResultsClear?.addEventListener("click", clearFilters);

  const dialog = document.querySelector("#team-profile-dialog");
  if (!dialog || typeof dialog.showModal !== "function") return;

  const dialogImage = dialog.querySelector(".team-profile-dialog__photo img");
  const dialogName = dialog.querySelector(".team-profile-dialog__name");
  const dialogSpecialty = dialog.querySelector(
    ".team-profile-dialog__specialty",
  );
  const dialogBio = dialog.querySelector(".team-profile-dialog__bio");
  const dialogLinkedIn = dialog.querySelector(
    ".team-profile-dialog__linkedin",
  );

  document.querySelectorAll("[data-team-profile]").forEach((button) => {
    button.addEventListener("click", () => {
      dialogImage.src = button.dataset.teamPhoto || "";
      dialogImage.alt = `Portrait of ${button.dataset.teamName || "team member"}`;
      dialogName.textContent = button.dataset.teamName || "";
      dialogSpecialty.textContent = button.dataset.teamSpecialty || "";
      dialogBio.textContent = button.dataset.teamBio || "";

      const linkedIn = button.dataset.teamLinkedin || "";
      dialogLinkedIn.hidden = !linkedIn;
      dialogLinkedIn.href = linkedIn || "#";
      dialog.showModal();
    });
  });

  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });
})();
