document.querySelectorAll("[data-testimonial-shell]").forEach((shell) => {
  const carousel = shell.querySelector("[data-testimonial-carousel]");
  const previousButton = shell.querySelector("[data-testimonial-previous]");
  const nextButton = shell.querySelector("[data-testimonial-next]");
  const slides = Array.from(carousel?.children || []);
  const reduceMotion = window.matchMedia(
    "(prefers-reduced-motion: reduce)",
  ).matches;

  if (!carousel || !previousButton || !nextButton || slides.length === 0) {
    return;
  }

  let timer;

  const getStep = () => {
    const firstSlide = slides[0];
    const styles = window.getComputedStyle(carousel);
    const gap = Number.parseFloat(styles.columnGap || styles.gap) || 0;
    return firstSlide.getBoundingClientRect().width + gap;
  };

  const canScroll = () => carousel.scrollWidth > carousel.clientWidth + 2;

  const updateControls = () => {
    const disabled = !canScroll();
    previousButton.disabled = disabled;
    nextButton.disabled = disabled;
  };

  const move = (direction) => {
    if (!canScroll()) {
      return;
    }

    const maxScroll = carousel.scrollWidth - carousel.clientWidth;
    const atStart = carousel.scrollLeft <= 2;
    const atEnd = carousel.scrollLeft >= maxScroll - 2;

    if (direction < 0 && atStart) {
      carousel.scrollTo({
        left: maxScroll,
        behavior: reduceMotion ? "auto" : "smooth",
      });
      return;
    }

    if (direction > 0 && atEnd) {
      carousel.scrollTo({
        left: 0,
        behavior: reduceMotion ? "auto" : "smooth",
      });
      return;
    }

    carousel.scrollBy({
      left: direction * getStep(),
      behavior: reduceMotion ? "auto" : "smooth",
    });
  };

  const stop = () => window.clearInterval(timer);

  const start = () => {
    stop();
    if (reduceMotion || !canScroll() || document.hidden) {
      return;
    }
    timer = window.setInterval(() => move(1), 7000);
  };

  previousButton.addEventListener("click", () => move(-1));
  nextButton.addEventListener("click", () => move(1));

  carousel.addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      move(-1);
    }
    if (event.key === "ArrowRight") {
      event.preventDefault();
      move(1);
    }
  });

  shell.addEventListener("mouseenter", stop);
  shell.addEventListener("mouseleave", start);
  shell.addEventListener("focusin", stop);
  shell.addEventListener("focusout", start);
  carousel.addEventListener("pointerdown", stop);
  window.addEventListener("resize", () => {
    updateControls();
    start();
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      stop();
    } else {
      start();
    }
  });

  updateControls();
  start();
});
