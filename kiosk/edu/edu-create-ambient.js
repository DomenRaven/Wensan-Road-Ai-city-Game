/* 创作全流程 · 全屏分散漂浮 AI/游戏主题动画 */
(() => {
  "use strict";

  /** @type {Array<{text:string,kind:string,x:number,y:number,faint?:boolean}>} */
  const SCATTER_ITEMS = [
    { text: "{ AI }", kind: "code", x: 4, y: 18 },
    { text: "func()", kind: "code", x: 20, y: 34 },
    { text: "if ▶", kind: "code", x: 26, y: 74 },
    { text: "创意", kind: "label", x: 6, y: 44 },
    { text: "0xFF", kind: "code", x: 18, y: 12 },
    { text: "★", kind: "spark", x: 30, y: 52 },
    { text: "game", kind: "code", x: 14, y: 86 },
    { text: "✨", kind: "spark", x: 76, y: 30 },
    { text: "代码", kind: "label", x: 72, y: 66 },
    { text: "{}", kind: "code", x: 84, y: 40 },
    { text: "▶", kind: "spark", x: 68, y: 80 },
    { text: "🌟", kind: "spark", x: 96, y: 70 },
    { text: "run()", kind: "code", x: 80, y: 10 },
    { text: "◇", kind: "spark", x: 42, y: 14, faint: true },
    { text: "λ", kind: "code", x: 58, y: 90, faint: true },
    { text: "✦", kind: "spark", x: 48, y: 76, faint: true },
    { text: "01", kind: "code", x: 36, y: 24, faint: true },
  ];

  /**
   * @param {HTMLElement} container
   * @param {Array<{text:string,kind:string,x:number,y:number,faint?:boolean}>} items
   */
  function fillScatter(container, items) {
    items.forEach((item, i) => {
      const node = document.createElement("span");
      node.className = `edu-float edu-float--${item.kind}${item.faint ? " edu-float--faint" : ""}`;
      node.textContent = item.text;
      node.style.left = `${item.x}%`;
      node.style.top = `${item.y}%`;
      node.style.setProperty("--float-delay", `${(i * 0.47) % 5}s`);
      node.style.setProperty("--float-dur", `${6.5 + (i % 5) * 1.2}s`);
      node.style.setProperty("--float-amp", `${8 + (i % 4) * 4}px`);
      container.appendChild(node);
    });
  }

  function mount() {
    if (document.getElementById("eduCreateAmbient")) return;

    const veil = document.createElement("div");
    veil.id = "eduAmbientVeil";
    veil.className = "edu-ambient-veil";
    veil.setAttribute("aria-hidden", "true");

    const root = document.createElement("div");
    root.id = "eduCreateAmbient";
    root.className = "edu-create-ambient";
    root.setAttribute("aria-hidden", "true");

    const scatter = document.createElement("div");
    scatter.className = "edu-create-ambient__scatter";
    fillScatter(scatter, SCATTER_ITEMS);

    root.appendChild(scatter);
    document.body.append(veil, root);
  }

  /**
   * @param {"off"|"step"|"dual"} mode
   */
  function setMode(mode) {
    document.body.classList.toggle("edu-ambient-active", mode === "step" || mode === "dual");
    document.body.classList.toggle("edu-ambient-step", mode === "step");
    document.body.classList.toggle("edu-ambient-dual", mode === "dual");
  }

  /** @param {boolean} active @deprecated use setMode */
  function setActive(active) {
    setMode(active ? "step" : "off");
  }

  window.EduCreateAmbient = { mount, setMode, setActive };
  document.addEventListener("DOMContentLoaded", () => mount());
})();
