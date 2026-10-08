const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "../website/static/js/hero_carousel.js"),
  "utf8",
);

class EventTarget {
  constructor() { this.listeners = new Map(); }
  addEventListener(type, callback) {
    if (!this.listeners.has(type)) this.listeners.set(type, []);
    this.listeners.get(type).push(callback);
  }
  emit(type, properties = {}) {
    const event = {
      target: this,
      defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; },
      ...properties,
    };
    for (const callback of this.listeners.get(type) || []) callback(event);
    return event;
  }
}

class Element extends EventTarget {
  constructor(tag = "div", attributes = {}) {
    super();
    this.tag = tag;
    this.attributes = new Map(Object.entries(attributes));
    this.children = [];
    this.dataset = {};
    this.hidden = false;
    this.inert = false;
    this.textContent = "";
    const classes = new Set();
    this.classList = {
      contains: (name) => classes.has(name),
      toggle: (name, enabled) => enabled ? classes.add(name) : classes.delete(name),
    };
  }
  append(child) { child.parent = this; this.children.push(child); return child; }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  getAttribute(name) { return this.attributes.get(name) ?? null; }
  removeAttribute(name) { this.attributes.delete(name); }
  contains(target) {
    return target === this || this.children.some((child) => child.contains(target));
  }
  matches(selector) {
    return selector.startsWith("[")
      ? this.attributes.has(selector.slice(1, -1))
      : this.tag === selector;
  }
  querySelectorAll(selector) {
    return this.children.flatMap((child) => [
      ...(child.matches(selector) ? [child] : []),
      ...child.querySelectorAll(selector),
    ]);
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
  closest(selectors) {
    if (selectors.split(",").some((selector) => this.matches(selector.trim()))) return this;
    return this.parent ? this.parent.closest(selectors) : null;
  }
}

function buildCarousel({ count = 3, reduced = false, missingControls = false, observer = true, failedImage = false } = {}) {
  const document = new Element("document");
  document.hidden = false;
  document.activeElement = null;
  const carousel = document.append(new Element("section", { "data-hero-carousel": "" }));
  const slides = [];
  const images = [];
  const links = [];
  for (let index = 0; index < count; index += 1) {
    const slide = carousel.append(new Element("article", { "data-hero-slide": "" }));
    slide.classList.toggle("is-current", index === 0);
    slide.inert = index !== 0;
    if (index !== 0) slide.setAttribute("aria-hidden", "true");
    const image = slide.append(new Element("img", { "data-hero-image": "" }));
    image.complete = true;
    image.naturalWidth = failedImage && index === 0 ? 0 : 1200;
    images.push(image);
    links.push(slide.append(new Element("a")));
    slides.push(slide);
  }
  let controls;
  let previous;
  let next;
  let toggle;
  const dots = [];
  if (count > 1 && !missingControls) {
    controls = carousel.append(new Element("div", { "data-hero-controls": "" }));
    controls.hidden = true;
    previous = controls.append(new Element("button", { "data-hero-previous": "" }));
    for (let index = 0; index < count; index += 1) {
      const dot = controls.append(new Element("button", { "data-hero-go": String(index) }));
      dot.dataset.heroGo = String(index);
      if (index === 0) dot.setAttribute("aria-current", "true");
      dots.push(dot);
    }
    next = controls.append(new Element("button", { "data-hero-next": "" }));
    toggle = controls.append(new Element("button", { "data-hero-toggle": "" }));
  }
  const status = carousel.append(new Element("span", { "data-hero-status": "" }));
  const motion = new EventTarget();
  motion.matches = reduced;
  let now = 0;
  let nextTimer = 0;
  const timers = new Map();
  const window = {
    matchMedia: () => motion,
    setTimeout(callback, delay) { timers.set(++nextTimer, { callback, at: now + delay }); return nextTimer; },
    clearTimeout(id) { timers.delete(id); },
  };
  const observers = [];
  class IntersectionObserver {
    constructor(callback) { this.callback = callback; observers.push(this); }
    observe(target) { this.target = target; }
  }
  if (observer) window.IntersectionObserver = IntersectionObserver;
  vm.runInNewContext(source, { document, window, IntersectionObserver });

  const advance = (duration) => {
    const until = now + duration;
    for (let steps = 0; steps < 1000; steps += 1) {
      const pending = [...timers].sort((left, right) => left[1].at - right[1].at)[0];
      if (!pending || pending[1].at > until) { now = until; return; }
      now = pending[1].at;
      timers.delete(pending[0]);
      pending[1].callback();
    }
    throw new Error("Unexpected runaway timer loop");
  };
  const focus = (target) => {
    document.activeElement = target;
    carousel.emit("focusin", { target });
  };
  const blur = (relatedTarget = null) => {
    document.activeElement = relatedTarget;
    carousel.emit("focusout", { relatedTarget });
  };
  const visibility = (hidden) => { document.hidden = hidden; document.emit("visibilitychange"); };
  const preference = (matches) => { motion.matches = matches; motion.emit("change", { matches }); };
  const inView = (isIntersecting) => observers[0].callback([{ target: carousel, isIntersecting }]);
  const assertCurrent = (index) => {
    assert.deepEqual(slides.map((slide) => slide.classList.contains("is-current")), slides.map((_, position) => position === index));
    slides.forEach((slide, position) => {
      assert.equal(slide.inert, position !== index);
      assert.equal(slide.getAttribute("aria-hidden"), position === index ? null : "true");
    });
    dots.forEach((dot, position) => assert.equal(dot.getAttribute("aria-current"), position === index ? "true" : null));
  };
  return { carousel, slides, images, links, controls, previous, next, toggle, dots, status, advance, focus, blur, visibility, preference, inView, assertCurrent, timers };
}

test("visible banners rotate every seven seconds, loop, and expose only the current slide", () => {
  const hero = buildCarousel();
  assert.equal(hero.controls.hidden, false);
  hero.assertCurrent(0);
  hero.advance(6999);
  hero.assertCurrent(0);
  hero.advance(1);
  hero.assertCurrent(1);
  hero.advance(7000);
  hero.assertCurrent(2);
  hero.advance(7000);
  hero.assertCurrent(0);
  assert.equal(hero.status.textContent, "", "Autoplay should not repeatedly announce slide changes");
});

test("Pause stops rotation and explicit Play resumes while its button retains focus", () => {
  const hero = buildCarousel();
  hero.focus(hero.toggle);
  hero.toggle.emit("click");
  assert.equal(hero.toggle.getAttribute("aria-label"), "Play banner rotation");
  hero.advance(21000);
  hero.assertCurrent(0);
  hero.toggle.emit("click");
  assert.equal(hero.toggle.getAttribute("aria-label"), "Pause banner rotation");
  hero.advance(7000);
  hero.assertCurrent(1);
  hero.focus(hero.links[1]);
  hero.advance(14000);
  hero.assertCurrent(1);
});

test("focus within the banner pauses playback until focus leaves", () => {
  const hero = buildCarousel();
  hero.advance(3000);
  hero.focus(hero.links[0]);
  hero.advance(14000);
  hero.assertCurrent(0);
  hero.blur(hero.next);
  hero.advance(7000);
  hero.assertCurrent(0);
  hero.blur();
  hero.advance(6999);
  hero.assertCurrent(0);
  hero.advance(1);
  hero.assertCurrent(1);
});

test("mouse hover pauses even after explicit Play and leaving restores playback", () => {
  const hero = buildCarousel();
  hero.focus(hero.toggle);
  hero.toggle.emit("click");
  hero.toggle.emit("click");
  hero.carousel.emit("pointerenter", { pointerType: "mouse" });
  hero.advance(14000);
  hero.assertCurrent(0);
  hero.carousel.emit("pointerleave", { pointerType: "mouse" });
  hero.advance(7000);
  hero.assertCurrent(1);
});

test("hidden tabs and offscreen banners pause timers and resume at a full interval", () => {
  const hero = buildCarousel();
  hero.visibility(true);
  hero.advance(21000);
  hero.assertCurrent(0);
  hero.visibility(false);
  hero.advance(7000);
  hero.assertCurrent(1);
  hero.inView(false);
  hero.advance(14000);
  hero.assertCurrent(1);
  hero.inView(true);
  hero.advance(6999);
  hero.assertCurrent(1);
  hero.advance(1);
  hero.assertCurrent(2);
});

test("reduced motion begins paused and preference changes update playback", () => {
  const hero = buildCarousel({ reduced: true });
  assert.equal(hero.toggle.getAttribute("aria-label"), "Play banner rotation");
  hero.advance(14000);
  hero.assertCurrent(0);
  hero.next.emit("click");
  hero.assertCurrent(1);
  hero.preference(false);
  hero.advance(7000);
  hero.assertCurrent(2);
  hero.preference(true);
  hero.advance(14000);
  hero.assertCurrent(2);
  assert.equal(hero.toggle.getAttribute("aria-label"), "Play banner rotation");
});

test("visitors can explicitly start rotation with a reduced-motion preference", () => {
  const hero = buildCarousel({ reduced: true });
  hero.focus(hero.toggle);
  hero.toggle.emit("click");
  hero.advance(7000);
  hero.assertCurrent(1);
});

test("previous, next, dots and keyboard controls select banners and announce manual changes", () => {
  const hero = buildCarousel();
  hero.previous.emit("click");
  hero.assertCurrent(2);
  assert.equal(hero.status.textContent, "Banner 3 of 3");
  hero.next.emit("click");
  hero.assertCurrent(0);
  hero.dots[1].emit("click");
  hero.assertCurrent(1);
  assert.equal(hero.controls.emit("keydown", { key: "ArrowRight" }).defaultPrevented, true);
  hero.assertCurrent(2);
  assert.equal(hero.controls.emit("keydown", { key: "ArrowLeft" }).defaultPrevented, true);
  hero.assertCurrent(1);
  assert.equal(hero.controls.emit("keydown", { key: "Tab" }).defaultPrevented, false);
  hero.assertCurrent(1);
});

test("zero or one banner needs no controls or animation", () => {
  for (const count of [0, 1]) {
    const hero = buildCarousel({ count });
    assert.equal(hero.timers.size, 0);
    hero.advance(21000);
    if (count === 1) hero.assertCurrent(0);
  }
});

test("missing controls preserve the initial usable banner", () => {
  const hero = buildCarousel({ missingControls: true });
  hero.advance(21000);
  hero.assertCurrent(0);
  assert.equal(hero.timers.size, 0);
});

test("image failures use the fallback without stopping navigation", () => {
  const hero = buildCarousel({ failedImage: true });
  assert.equal(hero.images[0].hidden, true);
  hero.images[1].emit("error");
  assert.equal(hero.images[1].hidden, true);
  hero.next.emit("click");
  hero.assertCurrent(1);
});

test("horizontal touch swipes navigate, while vertical scrolling and button gestures do not", () => {
  const hero = buildCarousel();
  hero.carousel.emit("pointerdown", { pointerType: "touch", target: hero.slides[0], clientX: 180, clientY: 90 });
  hero.carousel.emit("pointerup", { pointerType: "touch", clientX: 80, clientY: 95 });
  hero.assertCurrent(1);
  hero.carousel.emit("pointerdown", { pointerType: "touch", target: hero.slides[1], clientX: 80, clientY: 90 });
  hero.carousel.emit("pointerup", { pointerType: "touch", clientX: 100, clientY: 200 });
  hero.assertCurrent(1);
  hero.carousel.emit("pointerdown", { pointerType: "touch", target: hero.next, clientX: 180, clientY: 90 });
  hero.carousel.emit("pointerup", { pointerType: "touch", clientX: 80, clientY: 95 });
  hero.assertCurrent(1);
  hero.carousel.emit("pointerdown", { pointerType: "touch", target: hero.slides[1], clientX: 80, clientY: 90 });
  hero.carousel.emit("pointercancel");
  hero.advance(7000);
  hero.assertCurrent(2);
});

test("rotation still works when IntersectionObserver is unavailable", () => {
  const hero = buildCarousel({ observer: false });
  hero.advance(7000);
  hero.assertCurrent(1);
});
