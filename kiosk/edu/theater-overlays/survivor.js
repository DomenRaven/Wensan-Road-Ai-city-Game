/* B5 · survivor overlay · 随机位置多色经验粒子向中心汇聚 */
(() => {
  "use strict";

  /** @type {HTMLElement|null} */
  let rootEl = null;
  /** @type {(() => void)|null} */
  let stopScheduler = null;
  /** @type {Set<Animation>} */
  const activeAnims = new Set();

  /** @type {string[]} */
  const ORB_COLORS = ["#c026d3", "#e879f9", "#a855f7", "#f472b6", "#818cf8", "#22d3ee", "#fbbf24", "#4ade80", "#fb7185", "#38bdf8"];

  /** @type {string[]} */
  const ORB_GLYPHS = ["", "", "✦", "💎", "⚔️", "⭐"];

  function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  /**
   * @param {() => void} fn
   * @param {number} minMs
   * @param {number} maxMs
   * @returns {() => void}
   */
  function scheduleBurst(fn, minMs, maxMs) {
    if (window.TheaterSpawnUtil?.scheduleSpawner) {
      return window.TheaterSpawnUtil.scheduleSpawner(fn, minMs, maxMs);
    }
    /** @type {number|null} */
    let timerId = null;
    /** @type {boolean} */
    let stopped = false;
    function tick() {
      if (stopped) return;
      fn();
      timerId = window.setTimeout(tick, minMs + Math.floor(Math.random() * Math.max(1, maxMs - minMs)));
    }
    tick();
    return () => {
      stopped = true;
      if (timerId) window.clearTimeout(timerId);
    };
  }

  function spawnParticle() {
    if (!rootEl) return;

    const rect = rootEl.getBoundingClientRect();
    if (rect.width < 8 || rect.height < 8) return;

    const xPct = 4 + Math.random() * 92;
    const yPct = 4 + Math.random() * 92;
    const color = ORB_COLORS[Math.floor(Math.random() * ORB_COLORS.length)];
    const glyph = ORB_GLYPHS[Math.floor(Math.random() * ORB_GLYPHS.length)];
    const size = 0.85 + Math.random() * 0.65;

    const orb = document.createElement("span");
    orb.className = glyph ? "theater-survivor-particle theater-survivor-particle--glyph" : "theater-survivor-particle";
    orb.style.setProperty("--orb-color", color);
    orb.style.setProperty("--orb-size", String(size));
    orb.style.left = `${xPct}%`;
    orb.style.top = `${yPct}%`;
    if (glyph) orb.textContent = glyph;

    rootEl.appendChild(orb);

    if (prefersReducedMotion()) {
      orb.style.opacity = "0.75";
      orb.style.transform = "translate(-50%, -50%) scale(1)";
      window.setTimeout(() => orb.remove(), 1200);
      return;
    }

    const sx = (xPct / 100) * rect.width;
    const sy = (yPct / 100) * rect.height;
    const ex = rect.width * 0.5;
    const ey = rect.height * 0.5;
    const mx = sx + (ex - sx) * (0.38 + Math.random() * 0.22) + (Math.random() - 0.5) * 36;
    const my = sy + (ey - sy) * (0.38 + Math.random() * 0.22) + (Math.random() - 0.5) * 28;
    const dur = 680 + Math.floor(Math.random() * 520);

    const anim = orb.animate(
      [
        {
          transform: "translate(-50%, -50%) scale(0.35)",
          opacity: 0,
        },
        {
          transform: `translate(calc(-50% + ${mx - sx}px), calc(-50% + ${my - sy}px)) scale(${1.25 * size})`,
          opacity: 1,
          offset: 0.18,
        },
        {
          transform: `translate(calc(-50% + ${(ex - sx) * 0.85}px), calc(-50% + ${(ey - sy) * 0.85}px)) scale(${1.05 * size})`,
          opacity: 0.9,
          offset: 0.72,
        },
        {
          transform: `translate(calc(-50% + ${ex - sx}px), calc(-50% + ${ey - sy}px)) scale(0.12)`,
          opacity: 0,
        },
      ],
      { duration: dur, easing: "cubic-bezier(0.33, 0.02, 0.18, 1)", fill: "forwards" }
    );

    anim.onfinish = () => orb.remove();
    activeAnims.add(anim);
  }

  function spawnBurst() {
    const count = 5 + Math.floor(Math.random() * 4);
    for (let i = 0; i < count; i += 1) {
      window.setTimeout(spawnParticle, i * (45 + Math.floor(Math.random() * 55)));
    }
  }

  const TheaterSurvivor = {
    /** @param {HTMLElement} stageEl */
    start(stageEl) {
      TheaterSurvivor.stop();
      rootEl = document.createElement("div");
      rootEl.className = "theater-overlay theater-overlay-survivor";
      rootEl.setAttribute("aria-hidden", "true");
      stageEl.appendChild(rootEl);

      if (prefersReducedMotion()) {
        rootEl.classList.add("theater-overlay--static");
        const deco = document.createElement("span");
        deco.className = "theater-static-deco";
        deco.textContent = "💎";
        rootEl.appendChild(deco);
        return;
      }

      spawnBurst();
      stopScheduler = scheduleBurst(() => {
        spawnBurst();
        if (Math.random() > 0.45) window.setTimeout(spawnBurst, 260);
      }, 700, 1400);
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

  window.TheaterSurvivor = TheaterSurvivor;
})();
