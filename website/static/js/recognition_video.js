(() => {
  const videoDialog = document.querySelector("#home-video-dialog");

  if (videoDialog && typeof videoDialog.showModal === "function") {
    const videoFrame = videoDialog.querySelector("iframe");
    const videoTriggers = Array.from(
      document.querySelectorAll("[data-video-trigger]")
    );
    const isLocalPreview = ["localhost", "127.0.0.1"].includes(
      window.location.hostname
    );

    videoTriggers.forEach((trigger) => {
      trigger.addEventListener("click", (event) => {
        const embedUrl = trigger.dataset.videoEmbed;
        if (!embedUrl || isLocalPreview) {
          return;
        }

        event.preventDefault();
        videoFrame.src = `${embedUrl}?autoplay=1&rel=0&modestbranding=1`;
        videoDialog.showModal();
      });
    });

    const stopVideo = () => {
      videoFrame.removeAttribute("src");
    };

    videoDialog.addEventListener("close", stopVideo);
    videoDialog.addEventListener("click", (event) => {
      if (event.target === videoDialog) {
        videoDialog.close();
      }
    });
  }

  const recognitionDialog = document.querySelector("#recognition-lightbox");

  if (
    !recognitionDialog
    || typeof recognitionDialog.showModal !== "function"
  ) {
    return;
  }

  const recognitionLinks = Array.from(
    document.querySelectorAll(".recognition-card")
  );
  const recognitionImage = recognitionDialog.querySelector(
    ".recognition-lightbox-image"
  );
  const recognitionTitle = recognitionDialog.querySelector(
    ".recognition-lightbox-title"
  );
  const recognitionCaption = recognitionDialog.querySelector(
    ".recognition-lightbox-caption"
  );
  const recognitionCounter = recognitionDialog.querySelector(
    ".recognition-lightbox-counter"
  );
  const previousButton = recognitionDialog.querySelector(
    ".recognition-lightbox-previous"
  );
  const nextButton = recognitionDialog.querySelector(
    ".recognition-lightbox-next"
  );
  let currentRecognitionIndex = 0;

  const showRecognition = (index) => {
    currentRecognitionIndex = (
      index + recognitionLinks.length
    ) % recognitionLinks.length;
    const link = recognitionLinks[currentRecognitionIndex];
    const thumbnail = link.querySelector("img");

    recognitionImage.src = link.href;
    recognitionImage.alt =
      thumbnail?.alt || "Sinel Hospital recognition";
    recognitionTitle.textContent =
      link.dataset.awardTitle || recognitionImage.alt;
    recognitionCaption.textContent =
      link.dataset.awardCaption || "";
    recognitionCounter.textContent =
      `${currentRecognitionIndex + 1} / ${recognitionLinks.length}`;
  };

  recognitionLinks.forEach((link, index) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      showRecognition(index);
      recognitionDialog.showModal();
    });
  });

  previousButton?.addEventListener("click", () => {
    showRecognition(currentRecognitionIndex - 1);
  });

  nextButton?.addEventListener("click", () => {
    showRecognition(currentRecognitionIndex + 1);
  });

  if (recognitionLinks.length < 2) {
    previousButton?.setAttribute("hidden", "");
    nextButton?.setAttribute("hidden", "");
  }

  recognitionDialog.addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      showRecognition(currentRecognitionIndex - 1);
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      showRecognition(currentRecognitionIndex + 1);
    }
  });

  recognitionDialog.addEventListener("click", (event) => {
    if (event.target === recognitionDialog) {
      recognitionDialog.close();
    }
  });
})();
