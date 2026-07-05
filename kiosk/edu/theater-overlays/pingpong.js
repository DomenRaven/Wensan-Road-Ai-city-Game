/* B5 · pingpong overlay · 边缘随机发射乒乓球 */
(() => {
  "use strict";

  /** @type {HTMLElement|null} */
  let rootEl = null;
  /** @type {(() => void)|null} */
  let stopScheduler = null;
  /** @type {Set<Animation>} */
  const activeAnims = new Set();

  function spawnBall() {
    if (!rootEl) return;
    const accent = window.EduGenreTheme?.themeFor("pingpong")?.accent || "#059669";
    const burst = Math.random() > 0.5 ? 2 : 1;
    for (let i = 0; i < burst; i += 1) {
      const ball = document.createElement("span");
      ball.className = "theater-pingpong-flyer";
      ball.style.setProperty("--theater-accent", accent);
      ball.textContent = "🏓";
      rootEl.appendChild(ball);
      window.TheaterSpawnUtil?.flyFromEdge(ball, rootEl, {
        anims: activeAnims,
        durationMs: 1500 + Math.floor(Math.random() * 900) + i * 120,
      });
      if (!window.TheaterSpawnUtil || window.TheaterSpawnUtil.prefersReducedMotion()) {
        window.setTimeout(() => ball.remove(), 1800);
      }
    }
  }

  const TheaterPingpong = {
    /** @param {HTMLElement} stageEl */
    start(stageEl) {
      TheaterPingpong.stop();
      rootEl = document.createElement("div");
      rootEl.className = "theater-overlay theater-overlay-pingpong";
      rootEl.setAttribute("aria-hidden", "true");
      stageEl.appendChild(rootEl);

      if (window.TheaterSpawnUtil?.prefersReducedMotion()) {
        rootEl.classList.add("theater-overlay--static");
        const deco = document.createElement("span");
        deco.className = "theater-static-deco";
        deco.textContent = "🏓";
        rootEl.appendChild(deco);
        return;
      }

      spawnBall();
      stopScheduler = window.TheaterSpawnUtil?.scheduleSpawner(spawnBall, 1200, 2400) || null;
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

  window.TheaterPingpong = TheaterPingpong;
})();
