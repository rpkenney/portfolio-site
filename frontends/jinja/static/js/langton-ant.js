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
  const CELL_PX = typeof CFG.langtonAntCellPx === "number" ? CFG.langtonAntCellPx : 24;
  const STEP_MS = typeof CFG.langtonAntStepMs === "number" ? CFG.langtonAntStepMs : 120;
  const INITIAL_FILL =
    typeof CFG.langtonAntInitialFill === "number" ? CFG.langtonAntInitialFill : 0.3;
  const PERSIST = CFG.langtonAntPersist !== false;
  const modalMax =
    typeof CFG.resumeModalMaxWidthPx === "number" ? CFG.resumeModalMaxWidthPx : 767;
  const mobileMq = window.matchMedia(`(max-width: ${modalMax}px)`);
  const STORAGE_KEY = "langton-ant-v5";

  const canvas = document.getElementById("site-backdrop");
  if (!canvas) return;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  /** Up, right, down, left */
  const DIR = [
    { dx: 0, dy: -1 },
    { dx: 1, dy: 0 },
    { dx: 0, dy: 1 },
    { dx: -1, dy: 0 },
  ];

  function shouldRun() {
    return (
      !window.matchMedia("(prefers-reduced-motion: reduce)").matches && !mobileMq.matches
    );
  }

  function randomSeed() {
    return (Math.random() * 0xffffffff) >>> 0;
  }

  function mulberry32(seed) {
    let s = seed >>> 0;
    return function () {
      s = (s + 0x6d2b79f5) >>> 0;
      let t = s;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  let cols = 0;
  let rows = 0;
  let grid = null;
  let ant = null;
  let dpr = 1;
  let cellColor = "";
  let timer = null;
  let running = false;
  let resizeTimer = null;

  function cellColorFromCss() {
    const raw = getComputedStyle(document.documentElement).getPropertyValue("--langton-cell").trim();
    return raw || "rgba(30, 74, 140, 0.14)";
  }

  function cellIndex(x, y) {
    return y * cols + x;
  }

  function randomizeGrid(seed) {
    grid = new Uint8Array(cols * rows);
    const rng = mulberry32(seed);
    const fill = Math.min(0.55, Math.max(0.08, INITIAL_FILL));
    for (let y = 0; y < rows; y++) {
      for (let x = 0; x < cols; x++) {
        if (rng() < fill) grid[cellIndex(x, y)] = 1;
      }
    }
  }

  function spawnAnt(seed) {
    const antSeed = typeof seed === "number" ? seed >>> 0 : randomSeed();
    const rng = mulberry32(antSeed);
    return {
      seed: antSeed,
      x: Math.floor(rng() * cols),
      y: Math.floor(rng() * rows),
      dir: Math.floor(rng() * 4),
    };
  }

  function antValid(a) {
    return (
      a &&
      Number.isInteger(a.x) &&
      Number.isInteger(a.y) &&
      Number.isInteger(a.dir) &&
      a.x >= 0 &&
      a.y >= 0 &&
      a.x < cols &&
      a.y < rows &&
      a.dir >= 0 &&
      a.dir <= 3
    );
  }

  function resetSimulation() {
    const seed = randomSeed();
    randomizeGrid(seed);
    ant = spawnAnt(seed ^ 0xa5a5a5a5);
  }

  function gridToBase64(arr) {
    let s = "";
    for (let i = 0; i < arr.length; i++) s += String.fromCharCode(arr[i]);
    return btoa(s);
  }

  function gridFromBase64(b64, len) {
    const s = atob(b64);
    if (s.length !== len) return null;
    const out = new Uint8Array(len);
    for (let i = 0; i < len; i++) out[i] = s.charCodeAt(i);
    return out;
  }

  function saveState() {
    if (!PERSIST || !grid || !ant || !shouldRun()) return;
    try {
      sessionStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          v: 5,
          cellPx: CELL_PX,
          cols,
          rows,
          ant,
          grid: gridToBase64(grid),
        })
      );
    } catch {
      /* quota or private mode */
    }
  }

  function tryRestoreState() {
    if (!PERSIST) return false;
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (!raw) return false;
      const s = JSON.parse(raw);
      if (
        s.v !== 5 ||
        s.cellPx !== CELL_PX ||
        s.cols !== cols ||
        s.rows !== rows ||
        typeof s.grid !== "string" ||
        !s.ant
      ) {
        return false;
      }
      const restored = gridFromBase64(s.grid, cols * rows);
      if (!restored) return false;
      grid = restored;
      ant = antValid(s.ant) ? s.ant : spawnAnt(s.ant?.seed);
      return antValid(ant);
    } catch {
      return false;
    }
  }

  function drawCell(x, y, on) {
    const px = x * CELL_PX;
    const py = y * CELL_PX;
    if (on) {
      ctx.fillStyle = cellColor;
      ctx.fillRect(px, py, CELL_PX, CELL_PX);
    } else {
      ctx.clearRect(px, py, CELL_PX, CELL_PX);
    }
  }

  function redrawAll() {
    if (!grid) return;
    const w = window.innerWidth;
    const h = window.innerHeight;
    ctx.clearRect(0, 0, w, h);
    cellColor = cellColorFromCss();
    for (let y = 0; y < rows; y++) {
      for (let x = 0; x < cols; x++) {
        if (grid[cellIndex(x, y)] === 1) {
          drawCell(x, y, true);
        }
      }
    }
  }

  function clearCanvas() {
    ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
  }

  function resize() {
    if (!shouldRun()) {
      stop();
      clearCanvas();
      return;
    }

    dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = window.innerWidth;
    const h = window.innerHeight;
    canvas.width = Math.floor(w * dpr);
    canvas.height = Math.floor(h * dpr);
    canvas.style.width = `${w}px`;
    canvas.style.height = `${h}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    cols = Math.max(1, Math.ceil(w / CELL_PX));
    rows = Math.max(1, Math.ceil(h / CELL_PX));
    if (!tryRestoreState()) {
      resetSimulation();
    } else if (!antValid(ant)) {
      ant = spawnAnt(ant?.seed);
    }

    cellColor = cellColorFromCss();
    redrawAll();
  }

  function advanceAnt() {
    if (!ant) return;

    const i = cellIndex(ant.x, ant.y);
    const wasBlack = grid[i] === 1;
    grid[i] = wasBlack ? 0 : 1;
    drawCell(ant.x, ant.y, grid[i] === 1);

    ant.dir = wasBlack ? (ant.dir + 3) % 4 : (ant.dir + 1) % 4;
    ant.x = (ant.x + DIR[ant.dir].dx + cols) % cols;
    ant.y = (ant.y + DIR[ant.dir].dy + rows) % rows;
  }

  function tick() {
    if (!running || !shouldRun()) return;
    advanceAnt();
    timer = window.setTimeout(tick, STEP_MS);
  }

  function start() {
    if (!shouldRun()) return;
    if (running) return;
    running = true;
    tick();
  }

  function stop() {
    running = false;
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
  }

  function onResize() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      if (shouldRun()) saveState();
      resize();
      if (shouldRun()) start();
      else stop();
    }, 150);
  }

  function isSameSiteLink(a) {
    if (!(a instanceof HTMLAnchorElement)) return false;
    if (a.target === "_blank" || a.hasAttribute("download")) return false;
    const href = a.getAttribute("href");
    if (!href || href.startsWith("#") || href.startsWith("mailto:") || href.startsWith("tel:")) {
      return false;
    }
    try {
      return new URL(a.href, window.location.href).origin === window.location.origin;
    } catch {
      return !/^([a-z][a-z0-9+.-]*:|\/\/)/i.test(href);
    }
  }

  function wireNavSave() {
    document.addEventListener(
      "click",
      (e) => {
        if (!shouldRun()) return;
        const a = e.target.closest("a[href]");
        if (!a || !isSameSiteLink(a)) return;
        saveState();
      },
      true
    );
  }

  function onMobileChange() {
    if (shouldRun()) {
      resize();
      start();
    } else {
      stop();
      clearCanvas();
    }
  }

  window.addEventListener("pagehide", saveState);
  wireNavSave();
  window.addEventListener("resize", onResize);
  if (typeof mobileMq.addEventListener === "function") {
    mobileMq.addEventListener("change", onMobileChange);
  } else if (typeof mobileMq.addListener === "function") {
    mobileMq.addListener(onMobileChange);
  }

  if (shouldRun()) {
    resize();
    start();
  }
})();
