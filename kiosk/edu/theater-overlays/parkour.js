/* B5 · parkour overlay · 边缘随机发射跑者（无底部条纹） */
(() => {
  "use strict";

  /** @type {HTMLElement|null} */
  let rootEl = null;
  /** @type {(() => void)|null} */
  let stopScheduler = null;
  /** @type {Set<Animation>} */
  const activeAnims = new Set();

  function spawnRunner() {
    if (!rootEl) return;
    const runner = document.createElement("span");
    runner.className = "theater-parkour-flyer";
    runner.textContent = Math.random() > 0.5 ? "🏃" : "💨";
    rootEl.appendChild(runner);
    window.TheaterSpawnUtil?.flyFromEdge(runner, rootEl, {
      anims: activeAnims,
      durationMs: 1300 + Math.floor(Math.random() * 800),
    });
    if (!window.TheaterSpawnUtil || window.TheaterSpawnUtil.prefersReducedMotion()) {
      window.setTimeout(() => runner.remove(), 1600);
    }
  }

  const TheaterParkour = {
    /** @param {HTMLElement} stageEl */
    start(stageEl) {
      TheaterParkour.stop();
      rootEl = document.createElement("div");
      rootEl.className = "theater-overlay theater-overlay-parkour";
      rootEl.setAttribute("aria-hidden", "true");
      const accent = window.EduGenreTheme?.themeFor("parkour")?.accent || "#7c3aed";
      rootEl.style.setProperty("--theater-accent", accent);
      stageEl.appendChild(rootEl);

      if (window.TheaterSpawnUtil?.prefersReducedMotion()) {
        rootEl.classList.add("theater-overlay--static");
        const deco = document.createElement("span");
        deco.className = "theater-static-deco";
        deco.textContent = "🏃";
        rootEl.appendChild(deco);
        return;
      }

      spawnRunner();
      stopScheduler = window.TheaterSpawnUtil?.scheduleSpawner(spawnRunner, 1300, 2600) || null;
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

  window.TheaterParkour = TheaterParkour;
})();
