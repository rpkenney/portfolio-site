(function () {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /** Must match `resume.css` height transition on `.resume-section-body--animating` (open). */
  const OPEN_HEIGHT_MS = 350;
  const VIEWPORT_BOTTOM_MARGIN_PX = 20;

  /** Which section is expanded, or null. Source of truth after init (synced from DOM once). */
  let expandedSection = document.querySelector("section.resume-section--web-active") || null;

  let transitioning = false;

  function getSlides(carousel) {
    return Array.from(carousel.querySelectorAll(".resume-carousel-slide"));
  }

  function goToSlide(carousel, index) {
    const list = getSlides(carousel);
    if (!list.length) return;
    const n = list.length;
    const i = ((index % n) + n) % n;
    carousel.dataset.slideIndex = String(i);

    list.forEach((slide, j) => {
      const on = j === i;
      slide.hidden = !on;
      slide.setAttribute("aria-hidden", on ? "false" : "true");
      slide.classList.toggle("resume-carousel-slide--current", on);
    });

    const dots = carousel.querySelectorAll(".resume-carousel-dot");
    dots.forEach((dot, j) => {
      const on = j === i;
      dot.classList.toggle("resume-carousel-dot--current", on);
      dot.setAttribute("aria-selected", on ? "true" : "false");
      dot.tabIndex = on ? 0 : -1;
    });

    const vp = carousel.querySelector(".resume-carousel-viewport");
    if (vp && typeof vp.scrollTo === "function") {
      vp.scrollTo({
        top: 0,
        behavior: reduceMotion ? "auto" : "smooth",
      });
    }
  }

  function setExpandLabel(btn, open) {
    if (!btn) return;
    const base = btn.getAttribute("data-expand-label") || "More";
    const alt = btn.getAttribute("data-collapse-label") || "Back";
    btn.textContent = open ? alt : base;
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    const title = btn.closest("section.resume-section")?.querySelector("h2")?.textContent?.trim();
    if (title) {
      btn.setAttribute(
        "aria-label",
        open ? `Back to main ${title} content` : `Show more about ${title}`
      );
    }
  }

  function releaseWrapper(wrapper) {
    if (!wrapper) return;
    wrapper.style.height = "";
    wrapper.style.overflow = "";
    wrapper.classList.remove("resume-section-body--animating", "resume-section-body--shrinking");
  }

  /** Natural block size of `wrapper` for its *current* visible children (after DOM swap). */
  function measureWrapperNaturalHeight(wrapper) {
    wrapper.style.height = "auto";
    wrapper.style.overflow = "visible";
    void wrapper.offsetHeight;
    const h = wrapper.offsetHeight;
    return h;
  }

  function afterHeightTransition(wrapper, onDone, fallbackMs = 450) {
    let finished = false;
    const done = () => {
      if (finished) return;
      finished = true;
      wrapper.removeEventListener("transitionend", onEnd);
      clearTimeout(fallbackTimer);
      onDone();
    };
    const onEnd = (e) => {
      if (e.target === wrapper && e.propertyName === "height") done();
    };
    wrapper.addEventListener("transitionend", onEnd);
    const fallbackTimer = setTimeout(done, fallbackMs);
  }

  /**
   * One-shot scroll (reduced motion, or when there is no height transition).
   */
  function scrollExpandedRegionIntoView(section) {
    const carousel = section.querySelector("[data-resume-carousel]");
    if (!carousel || carousel.hidden) return;
    const behavior = reduceMotion ? "auto" : "smooth";
    carousel.scrollIntoView({ behavior, block: "nearest", inline: "nearest" });
  }

  /**
   * While the section body grows in height, keep the document scrolled so the
   * expanding bottom edge stays in view — reads like the page moves with the
   * expansion instead of a separate smooth-scroll after the fact.
   */
  function followExpandBottomEdgeDuringHeightTransition(wrapper, durationMs) {
    const start = performance.now();
    const margin = VIEWPORT_BOTTOM_MARGIN_PX;

    function tick(now) {
      const bottom = wrapper.getBoundingClientRect().bottom;
      const limit = window.innerHeight - margin;
      if (bottom > limit) {
        window.scrollBy({ top: bottom - limit, left: 0, behavior: "auto" });
      }
      if (now - start < durationMs + 80) {
        requestAnimationFrame(tick);
      } else {
        const b = wrapper.getBoundingClientRect().bottom;
        const lim = window.innerHeight - margin;
        if (b > lim) {
          window.scrollBy({ top: b - lim, left: 0, behavior: "auto" });
        }
      }
    }

    requestAnimationFrame(tick);
  }

  function focusExpandedCarousel(section) {
    const carousel = section.querySelector("[data-resume-carousel]");
    if (!carousel) return;
    const closeBtn = carousel.querySelector("[data-resume-carousel-close]");
    const target = closeBtn || carousel.querySelector(".resume-carousel-prev");
    if (!target) return;
    target.focus({ preventScroll: true });
  }

  /**
   * State: null = no section expanded; HTMLElement = that section expanded.
   * No-op: next === expandedSection (already in that state).
   * No-op: next === null && expandedSection === null.
   */
  function transitionTo(nextSection, options) {
    const restoreFocusOnClose = options?.restoreFocusOnClose !== false;

    if (transitioning) return;

    if (nextSection === null && expandedSection === null) return;

    if (nextSection !== null && nextSection === expandedSection) return;

    const from = expandedSection;
    const to = nextSection;

    if (reduceMotion) {
      if (from) applyCollapsed(from);
      if (to) applyExpanded(to);
      expandedSection = to;
      if (to) {
        scrollExpandedRegionIntoView(to);
        focusExpandedCarousel(to);
      } else if (from && restoreFocusOnClose) from.querySelector("[data-resume-carousel-expand]")?.focus();
      return;
    }

    transitioning = true;

    if (!from && to) {
      animateOpen(to, () => {
        expandedSection = to;
        transitioning = false;
        focusExpandedCarousel(to);
      });
      return;
    }

    if (from && !to) {
      animateClose(from, restoreFocusOnClose, () => {
        expandedSection = null;
        transitioning = false;
      });
      return;
    }

    /* Switch: animate from and to in parallel */
    let pending = 2;
    const doneOne = () => {
      pending -= 1;
      if (pending !== 0) return;
      expandedSection = to;
      transitioning = false;
      focusExpandedCarousel(to);
    };
    animateClose(from, false, doneOne);
    animateOpen(to, doneOne);
  }

  function applyExpanded(section) {
    const wrapper = section.querySelector(".resume-section-body");
    const def = section.querySelector(".resume-section-default");
    const carousel = section.querySelector("[data-resume-carousel]");
    const expand = section.querySelector("[data-resume-carousel-expand]");
    if (!carousel) return;
    releaseWrapper(wrapper);
    carousel.hidden = false;
    if (def) def.hidden = true;
    section.classList.add("resume-section--web-active");
    setExpandLabel(expand, true);
    goToSlide(carousel, parseInt(carousel.dataset.slideIndex || "0", 10));
  }

  function applyCollapsed(section) {
    const wrapper = section.querySelector(".resume-section-body");
    const def = section.querySelector(".resume-section-default");
    const carousel = section.querySelector("[data-resume-carousel]");
    const expand = section.querySelector("[data-resume-carousel-expand]");
    if (!carousel) return;
    releaseWrapper(wrapper);
    carousel.hidden = true;
    if (def) def.hidden = false;
    section.classList.remove("resume-section--web-active");
    setExpandLabel(expand, false);
    goToSlide(carousel, 0);
  }

  function animateOpen(section, onDone) {
    const wrapper = section.querySelector(".resume-section-body");
    const def = section.querySelector(".resume-section-default");
    const carousel = section.querySelector("[data-resume-carousel]");
    const expand = section.querySelector("[data-resume-carousel-expand]");
    if (!wrapper || !carousel) {
      applyExpanded(section);
      scrollExpandedRegionIntoView(section);
      onDone();
      return;
    }

    requestAnimationFrame(() => {
      const h0 = wrapper.offsetHeight;
      wrapper.style.overflow = "hidden";
      wrapper.style.height = `${h0}px`;
      wrapper.classList.add("resume-section-body--animating");

      carousel.hidden = false;
      if (def) def.hidden = true;
      section.classList.add("resume-section--web-active");
      setExpandLabel(expand, true);
      goToSlide(carousel, parseInt(carousel.dataset.slideIndex || "0", 10));

      void wrapper.offsetHeight;

      requestAnimationFrame(() => {
        /* carousel.offsetHeight misses margins / min-height stack vs wrapper’s real column height */
        const h1 = measureWrapperNaturalHeight(wrapper);
        wrapper.style.overflow = "hidden";
        wrapper.style.height = `${h0}px`;
        void wrapper.offsetHeight;

        if (Math.abs(h1 - h0) < 0.5) {
          releaseWrapper(wrapper);
          scrollExpandedRegionIntoView(section);
          onDone();
          return;
        }
        afterHeightTransition(wrapper, () => {
          releaseWrapper(wrapper);
          onDone();
        });
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            wrapper.style.height = `${h1}px`;
            followExpandBottomEdgeDuringHeightTransition(wrapper, OPEN_HEIGHT_MS);
          });
        });
      });
    });
  }

  function animateClose(section, restoreFocus, onDone) {
    const wrapper = section.querySelector(".resume-section-body");
    const def = section.querySelector(".resume-section-default");
    const carousel = section.querySelector("[data-resume-carousel]");
    const expand = section.querySelector("[data-resume-carousel-expand]");
    if (!wrapper || !carousel) {
      applyCollapsed(section);
      if (restoreFocus && expand) expand.focus();
      onDone();
      return;
    }

    const h1 = wrapper.offsetHeight;
    wrapper.style.overflow = "hidden";
    wrapper.style.height = `${h1}px`;
    wrapper.classList.add("resume-section-body--animating", "resume-section-body--shrinking");

    carousel.hidden = true;
    if (def) def.hidden = false;
    section.classList.remove("resume-section--web-active");
    setExpandLabel(expand, false);

    void wrapper.offsetHeight;
    const h0 = measureWrapperNaturalHeight(wrapper);
    wrapper.style.overflow = "hidden";
    wrapper.style.height = `${h1}px`;
    void wrapper.offsetHeight;

    if (Math.abs(h0 - h1) < 0.5) {
      releaseWrapper(wrapper);
      goToSlide(carousel, 0);
      if (restoreFocus && expand) expand.focus();
      onDone();
      return;
    }

    afterHeightTransition(
      wrapper,
      () => {
        releaseWrapper(wrapper);
        goToSlide(carousel, 0);
        if (restoreFocus && expand) expand.focus();
        onDone();
      },
      600
    );

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        wrapper.style.height = `${h0}px`;
      });
    });
  }

  function wireCarousel(carousel) {
    const section = carousel.closest("section.resume-section");
    if (!section) return;

    const prev = carousel.querySelector(".resume-carousel-prev");
    const next = carousel.querySelector(".resume-carousel-next");

    prev?.addEventListener("click", () => {
      goToSlide(carousel, parseInt(carousel.dataset.slideIndex || "0", 10) - 1);
    });
    next?.addEventListener("click", () => {
      goToSlide(carousel, parseInt(carousel.dataset.slideIndex || "0", 10) + 1);
    });

    carousel.querySelectorAll(".resume-carousel-dot").forEach((dot, idx) => {
      dot.addEventListener("click", () => goToSlide(carousel, idx));
    });

    carousel.querySelector("[data-resume-carousel-close]")?.addEventListener("click", () => {
      transitionTo(null, { restoreFocusOnClose: true });
    });
  }

  document.querySelectorAll("[data-resume-carousel]").forEach(wireCarousel);

  document.querySelectorAll("[data-resume-carousel-expand]").forEach((btn) => {
    btn.setAttribute("data-expand-label", btn.textContent.trim() || "More");
    btn.setAttribute("data-collapse-label", "Back");
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("aria-controls");
      const carousel = id && document.getElementById(id);
      const section = btn.closest("section.resume-section");
      if (!carousel || !section) return;
      if (carousel.hidden) transitionTo(section);
      else transitionTo(null, { restoreFocusOnClose: true });
    });
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (expandedSection) {
        transitionTo(null, { restoreFocusOnClose: true });
        e.preventDefault();
      }
      return;
    }

    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight" && e.key !== "Home" && e.key !== "End") return;

    const activeCarousel = document.querySelector(
      ".resume-section--web-active [data-resume-carousel]:not([hidden])"
    );
    if (!activeCarousel) return;

    const list = getSlides(activeCarousel);
    const n = list.length;
    const i = parseInt(activeCarousel.dataset.slideIndex || "0", 10);

    if (e.key === "ArrowLeft") {
      goToSlide(activeCarousel, i - 1);
      e.preventDefault();
    } else if (e.key === "ArrowRight") {
      goToSlide(activeCarousel, i + 1);
      e.preventDefault();
    } else if (e.key === "Home") {
      goToSlide(activeCarousel, 0);
      e.preventDefault();
    } else if (e.key === "End") {
      goToSlide(activeCarousel, n - 1);
      e.preventDefault();
    }
  });

  if (!reduceMotion) {
    document.documentElement.classList.add("resume-carousel-motion-ok");
  }
})();

/** §4 — mobile drawer: open/close, focus, Escape (capture so it runs before carousel Escape). */
(function initSiteNav() {
  const root = document.querySelector("[data-site-root]");
  const toggle = document.querySelector("[data-site-nav-toggle]");
  const drawer = document.querySelector("[data-site-nav-drawer]");
  const backdrop = document.querySelector("[data-site-nav-backdrop]");
  if (!root || !toggle || !drawer) return;

  const mqMobile = window.matchMedia("(max-width: 767px)");

  function isDrawerInteractive() {
    return mqMobile.matches;
  }

  function open() {
    if (!isDrawerInteractive()) return;
    root.classList.add("site--nav-open");
    toggle.setAttribute("aria-expanded", "true");
    backdrop?.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    drawer.querySelector("a[href]")?.focus();
  }

  function close() {
    root.classList.remove("site--nav-open");
    toggle.setAttribute("aria-expanded", "false");
    backdrop?.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
    if (drawer.contains(document.activeElement)) {
      toggle.focus();
    }
  }

  function isOpen() {
    return root.classList.contains("site--nav-open");
  }

  toggle.addEventListener("click", () => {
    if (!isDrawerInteractive()) return;
    if (isOpen()) close();
    else open();
  });

  backdrop?.addEventListener("click", () => {
    if (isOpen()) close();
  });

  drawer.querySelectorAll("a").forEach((a) => {
    a.addEventListener("click", () => {
      if (mqMobile.matches) close();
    });
  });

  function onMqChange() {
    if (!mqMobile.matches && isOpen()) close();
  }
  if (typeof mqMobile.addEventListener === "function") {
    mqMobile.addEventListener("change", onMqChange);
  } else if (typeof mqMobile.addListener === "function") {
    mqMobile.addListener(onMqChange);
  }

  document.addEventListener(
    "keydown",
    (e) => {
      if (e.key !== "Escape" || !isOpen()) return;
      close();
      e.preventDefault();
      e.stopPropagation();
    },
    true
  );
})();
