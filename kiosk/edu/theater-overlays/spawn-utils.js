/* B5 · overlay 边缘/底部随机发射 · 共用工具 */
(() => {
  "use strict";

  /** @type {("top"|"right"|"bottom"|"left")[]} */
  const EDGES = ["top", "right", "bottom", "left"];

  function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  /**
   * @returns {"top"|"right"|"bottom"|"left"}
   */
  function randomEdge() {
    return EDGES[Math.floor(Math.random() * EDGES.length)];
  }

  /**
   * @param {"top"|"right"|"bottom"|"left"} edge
   * @returns {{x:number,y:number}}
   */
  function edgePoint(edge) {
    const pad = 3;
    const along = pad + Math.random() * (100 - pad * 2);
    if (edge === "top") return { x: along, y: pad };
    if (edge === "bottom") return { x: along, y: 100 - pad };
    if (edge === "left") return { x: pad, y: along };
    return { x: 100 - pad, y: along };
  }

  /**
   * @param {"top"|"right"|"bottom"|"left"} from
   * @returns {"top"|"right"|"bottom"|"left"}
   */
  function oppositeEdge(from) {
    if (from === "top") return "bottom";
    if (from === "bottom") return "top";
    if (from === "left") return "right";
    return "left";
  }

  /**
   * @param {HTMLElement} el
   * @param {HTMLElement} rootEl
   * @param {{to?:string,durationMs?:number,anims?:Set<Animation>}} [opts]
   * @returns {Animation|null}
   */
  function flyFromEdge(el, rootEl, opts = {}) {
    if (!(el instanceof HTMLElement) || !(rootEl instanceof HTMLElement)) return null;

    const from = randomEdge();
    const to = opts.to || oppositeEdge(from);
    const start = edgePoint(from);
    const end = edgePoint(to);
    const midX = (start.x + end.x) / 2 + (Math.random() - 0.5) * 18;
    const midY = (start.y + end.y) / 2 + (Math.random() - 0.5) * 14;
    const dur = opts.durationMs || 1600 + Math.floor(Math.random() * 1200);

    el.classList.add("theater-edge-flyer");
    el.style.left = `${start.x}%`;
    el.style.top = `${start.y}%`;

    if (prefersReducedMotion()) {
      el.style.opacity = "0.55";
      el.style.transform = "translate(-50%, -50%) scale(1)";
      return null;
    }

    const anim = el.animate(
      [
        {
          left: `${start.x}%`,
          top: `${start.y}%`,
          opacity: 0,
          transform: "translate(-50%, -50%) scale(0.5)",
        },
        {
          left: `${start.x + (midX - start.x) * 0.18}%`,
          top: `${start.y + (midY - start.y) * 0.18}%`,
          opacity: 1,
          transform: "translate(-50%, -56%) scale(1.22)",
          offset: 0.14,
        },
        {
          left: `${midX}%`,
          top: `${midY}%`,
          opacity: 1,
          transform: "translate(-50%, -62%) scale(1.08)",
          offset: 0.52,
        },
        {
          left: `${end.x}%`,
          top: `${end.y}%`,
          opacity: 0,
          transform: "translate(-50%, -50%) scale(0.82)",
        },
      ],
      {
        duration: dur,
        easing: "cubic-bezier(0.34, 0.02, 0.22, 1)",
        fill: "forwards",
      }
    );

    anim.onfinish = () => el.remove();
    if (opts.anims instanceof Set) opts.anims.add(anim);
    return anim;
  }

  /**
   * @param {() => void} spawnFn
   * @param {number} minMs
   * @param {number} maxMs
   * @returns {() => void}
   */
  function scheduleSpawner(spawnFn, minMs, maxMs) {
    /** @type {number|null} */
    let timerId = null;
    /** @type {boolean} */
    let stopped = false;

    function tick() {
      if (stopped) return;
      spawnFn();
      const delay = minMs + Math.floor(Math.random() * Math.max(1, maxMs - minMs));
      timerId = window.setTimeout(tick, delay);
    }

    tick();

    return () => {
      stopped = true;
      if (timerId) {
        window.clearTimeout(timerId);
        timerId = null;
      }
    };
  }

  window.TheaterSpawnUtil = {
    prefersReducedMotion,
    randomEdge,
    edgePoint,
    oppositeEdge,
    flyFromEdge,
    scheduleSpawner,
  };
})();
