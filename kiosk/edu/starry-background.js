/* 全流程深邃星空背景 · 缓慢闪烁 + 漂移星点 */
(() => {
  "use strict";

  const STAR_COUNT = 110;
  const GOLD_RATIO = 0.38;

  /**
   * @param {number} i
   * @returns {"gold"|"orange"|"blue"}
   */
  function starTone(i) {
    const r = (i * 0.618) % 1;
    if (r < GOLD_RATIO * 0.55) return "gold";
    if (r < GOLD_RATIO) return "orange";
    return "blue";
  }

  function mount() {
    if (document.getElementById("eduStarrySky")) return;

    const layer = document.createElement("div");
    layer.id = "eduStarrySky";
    layer.className = "edu-starry-sky";
    layer.setAttribute("aria-hidden", "true");

    const gradient = document.createElement("div");
    gradient.className = "edu-starry-gradient";
    layer.appendChild(gradient);

    const nebula = document.createElement("div");
    nebula.className = "edu-starry-nebula";
    layer.appendChild(nebula);

    for (let i = 0; i < STAR_COUNT; i += 1) {
      const star = document.createElement("span");
      const tone = starTone(i);
      star.className = `edu-star edu-star--${tone}`;
      const size = 1 + Math.random() * 3.2;
      const driftX = (Math.random() - 0.5) * 48;
      const driftY = (Math.random() - 0.5) * 36;
      star.style.left = `${Math.random() * 100}%`;
      star.style.top = `${Math.random() * 100}%`;
      star.style.setProperty("--star-size", `${size}px`);
      star.style.setProperty("--twinkle-dur", `${2.2 + Math.random() * 3.8}s`);
      star.style.setProperty("--twinkle-delay", `${Math.random() * 6}s`);
      const baseOpacity = tone === "gold" ? 0.35 + Math.random() * 0.45 : 0.15 + Math.random() * 0.35;
      star.style.setProperty("--star-opacity", `${baseOpacity}`);
      star.style.setProperty("--drift-x", `${driftX.toFixed(1)}px`);
      star.style.setProperty("--drift-y", `${driftY.toFixed(1)}px`);
      star.style.setProperty("--drift-dur", `${38 + Math.random() * 42}s`);
      star.style.setProperty("--drift-delay", `${Math.random() * 12}s`);
      if (Math.random() > 0.88) {
        star.classList.add("edu-star--bright");
      }
      layer.appendChild(star);
    }

    document.body.prepend(layer);
    document.body.classList.add("edu-has-starry-bg");
  }

  window.EduStarryBackground = { mount };
  document.addEventListener("DOMContentLoaded", () => mount());
})();
