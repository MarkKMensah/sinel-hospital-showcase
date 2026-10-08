document.querySelectorAll("[data-hero-carousel]").forEach((carousel) => {
  const slides = Array.from(carousel.querySelectorAll("[data-hero-slide]"));
  carousel.querySelectorAll("[data-hero-image]").forEach((image) => {
    const useFallback = () => { image.hidden = true; };
    image.addEventListener("error", useFallback);
    if (image.complete && image.naturalWidth === 0) useFallback();
  });
  if (slides.length < 2) return;

  const controls = carousel.querySelector("[data-hero-controls]");
  const previous = carousel.querySelector("[data-hero-previous]");
  const next = carousel.querySelector("[data-hero-next]");
  const toggle = carousel.querySelector("[data-hero-toggle]");
  const dots = Array.from(carousel.querySelectorAll("[data-hero-go]"));
  const status = carousel.querySelector("[data-hero-status]");
  if (!controls || !previous || !next || !toggle) return;

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let index = 0;
  let playing = !reducedMotion.matches;
  let hovered = false;
  let focused = carousel.contains(document.activeElement);
  let focusPlaybackOverride = false;
  let inView = true;
  let timer;
  let swipeStart;

  const clearTimer = () => { window.clearTimeout(timer); };
  const schedule = () => {
    clearTimer();
    if (playing && !hovered && (!focused || focusPlaybackOverride) && inView && !document.hidden) {
      timer = window.setTimeout(() => show(index + 1), 7000);
    }
  };
  const updateToggle = () => {
    toggle.setAttribute("aria-label", playing ? "Pause banner rotation" : "Play banner rotation");
    toggle.innerHTML = playing
      ? '<i class="bi bi-pause-fill" aria-hidden="true"></i>'
      : '<i class="bi bi-play-fill" aria-hidden="true"></i>';
  };
  const show = (destination, announce = false) => {
    index = (destination + slides.length) % slides.length;
    slides.forEach((slide, position) => {
      const current = position === index;
      slide.classList.toggle("is-current", current);
      slide.inert = !current;
      if (current) slide.removeAttribute("aria-hidden");
      else slide.setAttribute("aria-hidden", "true");
    });
    dots.forEach((dot, position) => {
      if (position === index) dot.setAttribute("aria-current", "true");
      else dot.removeAttribute("aria-current");
    });
    if (announce && status) status.textContent = `Banner ${index + 1} of ${slides.length}`;
    schedule();
  };

  previous.addEventListener("click", () => show(index - 1, true));
  next.addEventListener("click", () => show(index + 1, true));
  dots.forEach((dot) => dot.addEventListener("click", () => show(Number(dot.dataset.heroGo), true)));
  toggle.addEventListener("click", () => {
    playing = !playing;
    focusPlaybackOverride = playing;
    updateToggle();
    schedule();
  });
  controls.addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      event.preventDefault();
      show(index + (event.key === "ArrowLeft" ? -1 : 1), true);
    }
  });
  carousel.addEventListener("pointerenter", (event) => {
    if (event.pointerType === "mouse") { hovered = true; clearTimer(); }
  });
  carousel.addEventListener("pointerleave", () => { hovered = false; schedule(); });
  carousel.addEventListener("focusin", () => { focused = true; focusPlaybackOverride = false; clearTimer(); });
  carousel.addEventListener("focusout", (event) => {
    focused = carousel.contains(event.relatedTarget);
    if (!focused) focusPlaybackOverride = false;
    schedule();
  });
  carousel.addEventListener("pointerdown", (event) => {
    if (event.pointerType === "touch" && !event.target.closest("a, button")) {
      swipeStart = { x: event.clientX, y: event.clientY };
      clearTimer();
    }
  });
  carousel.addEventListener("pointerup", (event) => {
    if (!swipeStart) return;
    const dx = event.clientX - swipeStart.x;
    const dy = event.clientY - swipeStart.y;
    swipeStart = null;
    if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy)) show(index + (dx < 0 ? 1 : -1), true);
    else schedule();
  });
  carousel.addEventListener("pointercancel", () => { swipeStart = null; schedule(); });
  document.addEventListener("visibilitychange", schedule);
  reducedMotion.addEventListener("change", () => {
    playing = !reducedMotion.matches;
    updateToggle();
    schedule();
  });
  if ("IntersectionObserver" in window) {
    new IntersectionObserver((entries) => {
      inView = entries[0].isIntersecting;
      schedule();
    }).observe(carousel);
  }
  controls.hidden = false;
  updateToggle();
  schedule();
});
