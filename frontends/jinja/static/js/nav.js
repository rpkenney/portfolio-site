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
  const navMax =
    typeof CFG.siteNavMaxWidthPx === "number" ? CFG.siteNavMaxWidthPx : 1149;
  const navMq = window.matchMedia(`(max-width: ${navMax}px)`);

  (function wireMobileNav() {
    const nav = document.querySelector("[data-site-nav]");
    const btn = nav?.querySelector("[data-site-nav-toggle]");
    const list = nav?.querySelector("#site-nav-list");
    if (!nav || !btn || !list) return;

    function sync() {
      const open = nav.classList.contains("site-nav--open");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      list.hidden = navMq.matches ? !open : false;
    }

    function setOpen(next) {
      nav.classList.toggle("site-nav--open", !!next);
      sync();
    }

    btn.addEventListener("click", () => setOpen(!nav.classList.contains("site-nav--open")));
    list.addEventListener("click", (e) => {
      const a = e.target && e.target.closest ? e.target.closest("a") : null;
      if (!a) return;
      if (navMq.matches) setOpen(false);
    });

    if (typeof navMq.addEventListener === "function") navMq.addEventListener("change", () => setOpen(false));
    else if (typeof navMq.addListener === "function") navMq.addListener(() => setOpen(false));

    sync();
  })();
})();
