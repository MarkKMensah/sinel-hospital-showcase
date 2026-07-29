const galleryDialog = document.querySelector("#gallery-lightbox");

if (galleryDialog && typeof galleryDialog.showModal === "function") {
  const galleryLinks = Array.from(document.querySelectorAll(".gallery-card"));
  const galleryImage = galleryDialog.querySelector(".gallery-lightbox__image");
  const galleryTitle = galleryDialog.querySelector(".gallery-lightbox__title");
  const galleryCaption = galleryDialog.querySelector(".gallery-lightbox__caption");
  const galleryCounter = galleryDialog.querySelector(".gallery-lightbox__counter");
  const previousButton = galleryDialog.querySelector(".gallery-lightbox__previous");
  const nextButton = galleryDialog.querySelector(".gallery-lightbox__next");
  let currentIndex = 0;

  const showImage = (index) => {
    currentIndex = (index + galleryLinks.length) % galleryLinks.length;
    const link = galleryLinks[currentIndex];
    const thumbnail = link.querySelector("img");

    galleryImage.src = link.href;
    galleryImage.alt = thumbnail?.alt || "Sinel Hospital gallery image";
    galleryTitle.textContent = link.dataset.galleryTitle || galleryImage.alt;
    galleryCaption.textContent =
      link.dataset.galleryCaption || galleryImage.alt;
    galleryCounter.textContent = `${currentIndex + 1} / ${galleryLinks.length}`;
  };

  galleryLinks.forEach((link, index) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      showImage(index);
      galleryDialog.showModal();
    });
  });

  previousButton?.addEventListener("click", () => {
    showImage(currentIndex - 1);
  });

  nextButton?.addEventListener("click", () => {
    showImage(currentIndex + 1);
  });

  if (galleryLinks.length < 2) {
    previousButton?.setAttribute("hidden", "");
    nextButton?.setAttribute("hidden", "");
  }

  galleryDialog.addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      showImage(currentIndex - 1);
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      showImage(currentIndex + 1);
    }
  });

  galleryDialog.addEventListener("click", (event) => {
    if (event.target === galleryDialog) {
      galleryDialog.close();
    }
  });
}
