/* B5 · 工作区流动数据流背景 · 全品类共用 */
(() => {
  "use strict";

  /** @type {HTMLElement|null} */
  let streamEl = null;

  /** @type {string[]} */
  const STREAM_TOKENS = [
    "func",
    "var",
    "if",
    "jump",
    "speed",
    "score",
    "01101",
    "config",
    "game",
    "sync",
    "run",
    "true",
    "tuning",
    "coin",
    "hp",
    "spawn",
    "gdscript",
    "01010",
    "11001",
    "apply",
  ];

  function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  /**
   * @param {number} index
   * @param {number} total
   * @returns {HTMLElement}
   */
  function buildColumn(index, total) {
    const col = document.createElement("div");
    col.className = "theater-stream-col";
    const leftPct = 4 + (index / Math.max(1, total - 1)) * 88;
    col.style.left = `${leftPct}%`;
    col.style.setProperty("--stream-dur", `${5.5 + (index % 5) * 1.4}s`);
    col.style.setProperty("--stream-delay", `${-(index * 1.1)}s`);
    col.style.setProperty("--stream-opacity", `${0.35 + (index % 3) * 0.12}`);

    const chunk = document.createElement("div");
    chunk.className = "theater-stream-chunk";
    for (let li = 0; li < 16; li += 1) {
      const span = document.createElement("span");
      span.textContent = STREAM_TOKENS[(index + li) % STREAM_TOKENS.length];
      chunk.appendChild(span);
    }
    col.appendChild(chunk);
    const clone = /** @type {HTMLElement} */ (chunk.cloneNode(true));
    clone.setAttribute("aria-hidden", "true");
    col.appendChild(clone);
    return col;
  }

  const TheaterDataStream = {
    /** @param {HTMLElement} stageEl */
    start(stageEl) {
      TheaterDataStream.stop();
      if (!(stageEl instanceof HTMLElement)) return;

      const el = document.createElement("div");
      el.className = prefersReducedMotion()
        ? "theater-data-stream theater-data-stream--static"
        : "theater-data-stream";
      el.setAttribute("aria-hidden", "true");

      const cols = prefersReducedMotion() ? 4 : 9;
      for (let i = 0; i < cols; i += 1) {
        el.appendChild(buildColumn(i, cols));
      }

      const pulse = document.createElement("div");
      pulse.className = "theater-stream-pulse";
      el.appendChild(pulse);

      stageEl.insertBefore(el, stageEl.firstChild);
      streamEl = el;
    },

    stop() {
      streamEl?.remove();
      streamEl = null;
    },
  };

  window.TheaterDataStream = TheaterDataStream;
})();
