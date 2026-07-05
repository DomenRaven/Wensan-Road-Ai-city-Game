/* B5 · 剧场 overlay registry · P4-C-5 */
(() => {
  "use strict";

  /** @type {{start:(stageEl:HTMLElement)=>void, stop:()=>void}|null} */
  let activeModule = null;

  /** @type {Record<string, {start:(stageEl:HTMLElement)=>void, stop:()=>void}|undefined>} */
  const REGISTRY = {
    platformer: window.TheaterPlatformer,
    shmup: window.TheaterShmup,
    survivor: window.TheaterSurvivor,
    pingpong: window.TheaterPingpong,
    fighting: window.TheaterFighting,
    parkour: window.TheaterParkour,
    racing: window.TheaterRacing,
  };

  const EduTheaterOverlays = {
    /**
     * @param {string} slug
     * @param {HTMLElement} stageEl
     */
    start(slug, stageEl) {
      EduTheaterOverlays.stop();
      if (!(stageEl instanceof HTMLElement)) return;
      const mod = REGISTRY[String(slug || "")];
      if (!mod || typeof mod.start !== "function") return;
      const theme = window.EduGenreTheme?.themeFor(slug);
      if (theme?.accent) {
        stageEl.style.setProperty("--theater-accent", theme.accent);
      }
      stageEl.dataset.theaterGenre = String(slug || "");
      window.TheaterDataStream?.start(stageEl);
      activeModule = mod;
      mod.start(stageEl);
    },

    stop() {
      window.TheaterDataStream?.stop();
      if (activeModule && typeof activeModule.stop === "function") {
        activeModule.stop();
      }
      activeModule = null;
    },
  };

  window.EduTheaterOverlays = EduTheaterOverlays;
})();
