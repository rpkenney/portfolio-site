(function () {
  function readSiteUiConfig() {
    const el = document.getElementById("site-ui-config");
    if (!el) return null;
    const raw = el.textContent?.trim();
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  const CFG = readSiteUiConfig() || {};
  const LOGICAL_W =
    typeof CFG.contentFrameLogicalWidthPx === "number" ? CFG.contentFrameLogicalWidthPx : 768;
  const MAX_SCALE =
    typeof CFG.contentFrameMaxScale === "number" ? CFG.contentFrameMaxScale : 8;
  const FIT_GUTTER_PX =
    typeof CFG.contentFrameFitGutterPx === "number" ? CFG.contentFrameFitGutterPx : 48;
  const modalMax =
    typeof CFG.resumeModalMaxWidthPx === "number" ? CFG.resumeModalMaxWidthPx : 767;
  const mobileMq = window.matchMedia(`(max-width: ${modalMax}px)`);

  const frame = document.querySelector("[data-content-frame]");
  const stage = document.querySelector("[data-content-frame-stage]");
  if (!frame || !stage) return;

  const finePointer = window.matchMedia("(pointer: fine)").matches;

  let scale = 1;
  let tx = 0;
  let ty = 0;
  let fitScale = 1;

  const pointers = new Map();
  let pinchStart = null;
  let dragPan = null;
  let touchPan = null;
  /** Pan/zoom saved when a mobile modal opens — restored on close instead of refitting. */
  let modalViewSnapshot = null;

  function modalModeEnabled() {
    return mobileMq.matches;
  }

  function panHasSlack() {
    const { w, h } = scaledSize();
    const fw = frame.clientWidth;
    const fh = frame.clientHeight;
    return w > fw + 1 || h > fh + 1;
  }

  function modalOpen() {
    return document.documentElement.classList.contains("resume-web-modal-open");
  }

  function inlineExpanded() {
    if (modalModeEnabled()) return false;
    return (
      document.querySelector("section.resume-section--web-active") !== null && !modalOpen()
    );
  }

  function interactionsBlocked() {
    return modalOpen() || inlineExpanded();
  }

  function shouldIgnorePointer(target) {
    if (!(target instanceof Element)) return false;
    return !!target.closest(
      "button, a, input, select, textarea, label, [data-resume-carousel-expand], .resume-carousel-toolbar, .resume-carousel-dot"
    );
  }

  function stageHeight() {
    return stage.offsetHeight;
  }

  function scaledSize() {
    return { w: LOGICAL_W * scale, h: stageHeight() * scale };
  }

  function clampPan() {
    const { w, h } = scaledSize();
    const fw = frame.clientWidth;
    const fh = frame.clientHeight;

    /* No pan slack when the paper already fits — avoids scrolling through empty space. */
    if (w <= fw) {
      tx = (fw - w) / 2;
    } else {
      tx = Math.min(0, Math.max(fw - w, tx));
    }

    if (h <= fh) {
      ty = 0;
    } else {
      ty = Math.min(0, Math.max(fh - h, ty));
    }
  }

  /** Horizontally centered, vertically top-aligned. */
  function resetViewPosition() {
    const { w } = scaledSize();
    const fw = frame.clientWidth;
    tx = (fw - w) / 2;
    ty = 0;
    clampPan();
  }

  function applyTransform() {
    if (inlineExpanded()) {
      stage.style.transform = "";
      return;
    }
    clampPan();
    stage.style.transform = `translate(${tx}px, ${ty}px) scale(${scale})`;
  }

  function measureFitScale() {
    stage.style.width = `${LOGICAL_W}px`;
    stage.style.transform = "none";
    void stage.offsetHeight;
    const fw = frame.clientWidth;
    if (!fw) return 1;
    const inner = Math.max(1, fw - FIT_GUTTER_PX * 2);
    return Math.min(1, inner / LOGICAL_W);
  }

  function fitToFrame() {
    if (interactionsBlocked()) return;
    fitScale = measureFitScale();
    scale = fitScale;
    resetViewPosition();
    applyTransform();
  }

  function syncSuspended() {
    const modal = modalOpen();
    const inline = inlineExpanded();
    document.documentElement.classList.toggle("content-frame-suspended", inline);
    document.documentElement.classList.toggle("content-frame-modal-open", modal);
    frame.classList.toggle("content-frame--frozen", modal);

    if (inline) {
      modalViewSnapshot = null;
      stage.style.transform = "";
      stage.style.width = "";
      stage.style.willChange = "auto";
      pointers.clear();
      pinchStart = null;
      dragPan = null;
      touchPan = null;
    } else if (modal) {
      if (!modalViewSnapshot) {
        modalViewSnapshot = { scale, tx, ty };
      }
      stage.style.width = `${LOGICAL_W}px`;
      stage.style.willChange = "transform";
      applyTransform();
      pointers.clear();
      pinchStart = null;
      dragPan = null;
      touchPan = null;
    } else {
      stage.style.width = `${LOGICAL_W}px`;
      stage.style.willChange = "transform";
      fitScale = measureFitScale();
      if (modalViewSnapshot) {
        scale = Math.min(MAX_SCALE, Math.max(fitScale, modalViewSnapshot.scale));
        tx = modalViewSnapshot.tx;
        ty = modalViewSnapshot.ty;
        modalViewSnapshot = null;
        applyTransform();
      } else {
        scale = fitScale;
        resetViewPosition();
        applyTransform();
      }
    }
  }

  function zoomAt(factor, cx, cy) {
    if (interactionsBlocked()) return;
    const prev = scale;
    const next = Math.min(MAX_SCALE, Math.max(fitScale, prev * factor));
    if (next === prev) return;

    const rect = frame.getBoundingClientRect();
    const px = cx - rect.left;
    const py = cy - rect.top;
    const contentX = (px - tx) / prev;
    const contentY = (py - ty) / prev;
    scale = next;
    tx = px - contentX * scale;
    ty = py - contentY * scale;
    applyTransform();
  }

  function wheelPixels(e) {
    let dx = e.deltaX;
    let dy = e.deltaY;
    if (e.deltaMode === WheelEvent.DOM_DELTA_LINE) {
      dx *= 16;
      dy *= 16;
    } else if (e.deltaMode === WheelEvent.DOM_DELTA_PAGE) {
      dx *= frame.clientWidth;
      dy *= frame.clientHeight;
    }
    /* Shift + vertical wheel → horizontal pan (common on Linux / mice). */
    if (e.shiftKey && dx === 0 && dy !== 0) {
      dx = dy;
      dy = 0;
    }
    return { dx, dy };
  }

  function onWheel(e) {
    if (interactionsBlocked()) return;

    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const factor = e.deltaY < 0 ? 1.08 : 1 / 1.08;
      zoomAt(factor, e.clientX, e.clientY);
      return;
    }

    if (!finePointer) return;

    e.preventDefault();
    const { dx, dy } = wheelPixels(e);
    tx -= dx;
    ty -= dy;
    applyTransform();
  }

  function onPointerDown(e) {
    if (shouldIgnorePointer(e.target) || interactionsBlocked()) return;

    if (e.pointerType === "mouse" && e.button === 1) {
      e.preventDefault();
      dragPan = { x: e.clientX, y: e.clientY, tx, ty, pointerId: e.pointerId };
      frame.setPointerCapture(e.pointerId);
      frame.classList.add("is-panning");
      return;
    }

    if (e.pointerType !== "touch") return;

    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });

    if (pointers.size === 2) {
      touchPan = null;
      frame.setPointerCapture(e.pointerId);
      const pts = [...pointers.values()];
      const rect = frame.getBoundingClientRect();
      pinchStart = {
        distance: Math.hypot(pts[1].x - pts[0].x, pts[1].y - pts[0].y),
        scale,
        tx,
        ty,
        midX: (pts[0].x + pts[1].x) / 2 - rect.left,
        midY: (pts[0].y + pts[1].y) / 2 - rect.top,
      };
      return;
    }

    if (pointers.size === 1 && panHasSlack()) {
      touchPan = { x: e.clientX, y: e.clientY, tx, ty, pointerId: e.pointerId };
      frame.setPointerCapture(e.pointerId);
    }
  }

  function onPointerMove(e) {
    if (interactionsBlocked()) return;

    if (dragPan && e.pointerId === dragPan.pointerId) {
      tx = dragPan.tx + (e.clientX - dragPan.x);
      ty = dragPan.ty + (e.clientY - dragPan.y);
      applyTransform();
      return;
    }

    if (touchPan && e.pointerId === touchPan.pointerId && pointers.size === 1) {
      e.preventDefault();
      tx = touchPan.tx + (e.clientX - touchPan.x);
      ty = touchPan.ty + (e.clientY - touchPan.y);
      applyTransform();
      frame.classList.add("is-panning");
      return;
    }

    if (!pointers.has(e.pointerId) || e.pointerType !== "touch") return;

    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });

    if (pointers.size === 2 && pinchStart) {
      const pts = [...pointers.values()];
      const dist = Math.hypot(pts[1].x - pts[0].x, pts[1].y - pts[0].y);
      if (!pinchStart.distance) return;
      const rect = frame.getBoundingClientRect();
      const midX = (pts[0].x + pts[1].x) / 2 - rect.left;
      const midY = (pts[0].y + pts[1].y) / 2 - rect.top;
      const next = Math.min(
        MAX_SCALE,
        Math.max(fitScale, (pinchStart.scale * dist) / pinchStart.distance)
      );
      const contentX = (pinchStart.midX - pinchStart.tx) / pinchStart.scale;
      const contentY = (pinchStart.midY - pinchStart.ty) / pinchStart.scale;
      scale = next;
      tx = midX - contentX * scale;
      ty = midY - contentY * scale;
      applyTransform();
    }
  }

  function endPointer(e) {
    if (dragPan && e.pointerId === dragPan.pointerId) {
      dragPan = null;
      frame.classList.remove("is-panning");
    }

    if (touchPan && e.pointerId === touchPan.pointerId) {
      touchPan = null;
      frame.classList.remove("is-panning");
    }

    pointers.delete(e.pointerId);
    if (pointers.size < 2) pinchStart = null;
  }

  frame.addEventListener("wheel", onWheel, { passive: false, capture: true });
  frame.addEventListener("auxclick", (e) => {
    if (e.button === 1) e.preventDefault();
  });
  frame.addEventListener("pointerdown", onPointerDown);
  frame.addEventListener("pointermove", onPointerMove);
  frame.addEventListener("pointerup", endPointer);
  frame.addEventListener("pointercancel", endPointer);

  const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(() => fitToFrame()) : null;
  if (ro) ro.observe(frame);
  window.addEventListener("resize", fitToFrame);

  const suspendObs = new MutationObserver(syncSuspended);
  suspendObs.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["class"],
  });
  document.querySelectorAll("section.resume-section").forEach((section) => {
    suspendObs.observe(section, { attributes: true, attributeFilter: ["class"] });
  });

  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(() => {
      syncSuspended();
      if (!interactionsBlocked()) fitToFrame();
    });
  }
  syncSuspended();
  if (!interactionsBlocked()) fitToFrame();
})();
