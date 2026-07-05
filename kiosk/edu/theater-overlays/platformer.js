/* B5 · platformer overlay · 下栏随机位置金币向上发射 */
(() => {
  "use strict";

  /** @type {HTMLElement|null} */
  let rootEl = null;
  /** @type {(() => void)|null} */
  let stopScheduler = null;

  function spawnCoin() {
    if (!rootEl) return;
    const accent = window.EduGenreTheme?.themeFor("platformer")?.accent || "#16a34a";
    const burst = Math.random() > 0.45 ? 2 : 1;
    for (let i = 0; i < burst; i += 1) {
      const coin = document.createElement("span");
      coin.className = "theater-coin-pop theater-coin-pop--from-bottom";
      coin.style.setProperty("--theater-accent", accent);
      coin.style.left = `${6 + Math.random() * 86}%`;
      coin.style.setProperty("--coin-delay", `${i * 0.12}s`);
      coin.style.setProperty("--coin-drift", `${(Math.random() - 0.5) * 36}px`);
      coin.textContent = "+10 🪙";
      rootEl.appendChild(coin);
      window.setTimeout(() => coin.remove(), 1400);
    }
  }

  const TheaterPlatformer = {
    /** @param {HTMLElement} stageEl */
    start(stageEl) {
      TheaterPlatformer.stop();
      rootEl = document.createElement("div");
      rootEl.className = "theater-overlay theater-overlay-platformer";
      rootEl.setAttribute("aria-hidden", "true");
      stageEl.appendChild(rootEl);

      if (window.TheaterSpawnUtil?.prefersReducedMotion()) {
        rootEl.classList.add("theater-overlay--static");
        const deco = document.createElement("span");
        deco.className = "theater-static-deco theater-static-deco--bottom";
        deco.textContent = "🪙";
        rootEl.appendChild(deco);
        return;
      }

      spawnCoin();
      stopScheduler = window.TheaterSpawnUtil?.scheduleSpawner(spawnCoin, 1100, 2200) || null;
    },

    stop() {
      stopScheduler?.();
      stopScheduler = null;
      rootEl?.remove();
      rootEl = null;
    },
  };

  window.TheaterPlatformer = TheaterPlatformer;
})();
