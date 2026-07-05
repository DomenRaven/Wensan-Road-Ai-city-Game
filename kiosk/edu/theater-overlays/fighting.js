/* B5 · fighting overlay · 冲击框 flash + 轻微 shake */
(() => {
  "use strict";

  /** @type {HTMLElement|null} */
  let rootEl = null;
  /** @type {number|null} */
  let timerId = null;

  function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  /**
   * @param {HTMLElement} stageEl
   * @returns {HTMLElement}
   */
  function ensureRoot(stageEl) {
    const existing = stageEl.querySelector(".theater-overlay-fighting");
    if (existing instanceof HTMLElement) return existing;
    const el = document.createElement("div");
    el.className = "theater-overlay theater-overlay-fighting";
    el.setAttribute("aria-hidden", "true");
    stageEl.appendChild(el);
    return el;
  }

  function impactFlash() {
    if (!rootEl) return;
    const accent = window.EduGenreTheme?.themeFor("fighting")?.accent || "#dc2626";
    const flash = document.createElement("div");
    flash.className = "theater-fighting-flash";
    flash.style.setProperty("--theater-accent", accent);
    rootEl.appendChild(flash);
    rootEl.classList.add("theater-fighting-shake");
    window.setTimeout(() => {
      flash.remove();
      rootEl?.classList.remove("theater-fighting-shake");
    }, 480);
  }

  function scheduleNext() {
    if (!rootEl) return;
    timerId = window.setTimeout(() => {
      impactFlash();
      scheduleNext();
    }, 4000);
  }

  const TheaterFighting = {
    /** @param {HTMLElement} stageEl */
    start(stageEl) {
      TheaterFighting.stop();
      rootEl = ensureRoot(stageEl);
      if (prefersReducedMotion()) {
        rootEl.classList.add("theater-overlay--static");
        const deco = document.createElement("span");
        deco.className = "theater-static-deco";
        deco.textContent = "🥊";
        rootEl.appendChild(deco);
        return;
      }
      impactFlash();
      scheduleNext();
    },

    stop() {
      if (timerId) {
        window.clearTimeout(timerId);
        timerId = null;
      }
      rootEl?.remove();
      rootEl = null;
    },
  };

  window.TheaterFighting = TheaterFighting;
})();
