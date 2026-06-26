/* 全流程深邃星空背景 · 缓慢闪烁 + 漂移星点 */
(() => {
  "use strict";

  const STAR_COUNT = 96;

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
      star.className = "edu-star";
      const size = 1 + Math.random() * 2.8;
      const driftX = (Math.random() - 0.5) * 48;
      const driftY = (Math.random() - 0.5) * 36;
      star.style.left = `${Math.random() * 100}%`;
      star.style.top = `${Math.random() * 100}%`;
      star.style.setProperty("--star-size", `${size}px`);
      star.style.setProperty("--twinkle-dur", `${2.2 + Math.random() * 3.8}s`);
      star.style.setProperty("--twinkle-delay", `${Math.random() * 6}s`);
      star.style.setProperty("--star-opacity", `${0.25 + Math.random() * 0.75}`);
      star.style.setProperty("--drift-x", `${driftX.toFixed(1)}px`);
      star.style.setProperty("--drift-y", `${driftY.toFixed(1)}px`);
      star.style.setProperty("--drift-dur", `${38 + Math.random() * 42}s`);
      star.style.setProperty("--drift-delay", `${Math.random() * 12}s`);
      if (Math.random() > 0.82) {
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
