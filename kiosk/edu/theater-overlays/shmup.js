/* B5 · shmup overlay · 边缘随机发射小飞机 */
(() => {
  "use strict";

  /** @type {HTMLElement|null} */
  let rootEl = null;
  /** @type {(() => void)|null} */
  let stopScheduler = null;
  /** @type {Set<Animation>} */
  const activeAnims = new Set();

  function launchShip() {
    if (!rootEl) return;
    const accent = window.EduGenreTheme?.themeFor("shmup")?.accent || "#1d4ed8";
    const ship = document.createElement("div");
    ship.className = "theater-shmup-flyer";
    ship.style.setProperty("--theater-accent", accent);
    ship.innerHTML = `
      <span class="theater-shmup-flame"></span>
      <span class="theater-shmup-flame theater-shmup-flame--2"></span>
      <span class="theater-shmup-icon">🚀</span>`;
    rootEl.appendChild(ship);
    window.TheaterSpawnUtil?.flyFromEdge(ship, rootEl, {
      anims: activeAnims,
      durationMs: 1700 + Math.floor(Math.random() * 1100),
    });
    if (!window.TheaterSpawnUtil || window.TheaterSpawnUtil.prefersReducedMotion()) {
      window.setTimeout(() => ship.remove(), 2000);
    }
  }

  const TheaterShmup = {
    /** @param {HTMLElement} stageEl */
    start(stageEl) {
      TheaterShmup.stop();
      rootEl = document.createElement("div");
      rootEl.className = "theater-overlay theater-overlay-shmup";
      rootEl.setAttribute("aria-hidden", "true");
      stageEl.appendChild(rootEl);

      if (window.TheaterSpawnUtil?.prefersReducedMotion()) {
        rootEl.classList.add("theater-overlay--static");
        const deco = document.createElement("span");
        deco.className = "theater-static-deco";
        deco.textContent = "🚀";
        rootEl.appendChild(deco);
        return;
      }

      launchShip();
      stopScheduler =
        window.TheaterSpawnUtil?.scheduleSpawner(() => {
          launchShip();
          if (Math.random() > 0.6) window.setTimeout(launchShip, 280);
        }, 1400, 2800) || null;
    },

    stop() {
      stopScheduler?.();
      stopScheduler = null;
      activeAnims.forEach((anim) => anim.cancel());
      activeAnims.clear();
      rootEl?.remove();
      rootEl = null;
    },
  };

  window.TheaterShmup = TheaterShmup;
})();
