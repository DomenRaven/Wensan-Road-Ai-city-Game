/* B5 · racing overlay · 仪表指针随节奏摆动 */
(() => {
  "use strict";

  /** @type {HTMLElement|null} */
  let rootEl = null;

  function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  /**
   * @param {HTMLElement} stageEl
   * @returns {HTMLElement}
   */
  function ensureRoot(stageEl) {
    const existing = stageEl.querySelector(".theater-overlay-racing");
    if (existing instanceof HTMLElement) return existing;
    const el = document.createElement("div");
    el.className = "theater-overlay theater-overlay-racing";
    el.setAttribute("aria-hidden", "true");
    stageEl.appendChild(el);
    return el;
  }

  const TheaterRacing = {
    /** @param {HTMLElement} stageEl */
    start(stageEl) {
      TheaterRacing.stop();
      rootEl = ensureRoot(stageEl);
      const accent = window.EduGenreTheme?.themeFor("racing")?.accent || "#ea580c";
      rootEl.style.setProperty("--theater-accent", accent);
      const gauge = document.createElement("div");
      gauge.className = "theater-racing-gauge";
      gauge.innerHTML = `
        <svg width="56" height="36" viewBox="0 0 56 36" aria-hidden="true">
          <path class="theater-racing-arc" d="M6,32 A22,22 0 0 1 50,32"/>
          <line class="theater-racing-needle" x1="28" y1="32" x2="28" y2="14"/>
        </svg>`;
      if (prefersReducedMotion()) {
        gauge.classList.add("theater-racing-gauge--static");
      }
      rootEl.appendChild(gauge);
    },

    stop() {
      rootEl?.remove();
      rootEl = null;
    },
  };

  window.TheaterRacing = TheaterRacing;
})();
