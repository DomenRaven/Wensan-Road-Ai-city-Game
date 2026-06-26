/* B5 · 制作等待动画 · 右栏 HTML 渲染 */
(() => {
  "use strict";

  /** @type {Record<string, {title:string,subtitle:string,emoji:string}>} */
  const PHASES = {
    analyze: {
      title: "AI 正在分析你的选择",
      subtitle: "读取配方 · 匹配代码锚点 · 计算数值",
      emoji: "🧠",
    },
    theater: {
      title: "正在编织游戏代码",
      subtitle: "一行行写入配置 · 高亮关键参数",
      emoji: "✨",
    },
    apply: {
      title: "正在生成你的游戏",
      subtitle: "打包 workspace · 注入小技能",
      emoji: "🚀",
    },
  };

  const FLOAT_TOKENS = [
    "{ }",
    "tuning",
    "speed",
    "jump",
    "★",
    "if",
    "func",
    "coin",
  ];

  const EduBuildWait = {
    /**
     * @param {"analyze"|"theater"|"apply"} [phase]
     * @param {number} [progressPct]
     */
    render(phase = "analyze", progressPct = 10) {
      const meta = PHASES[phase] || PHASES.analyze;
      const pct = Math.min(100, Math.max(0, progressPct));
      const particles = Array.from({ length: 10 }, (_, i) => {
        return `<span class="build-wait-particle" style="--i:${i}"></span>`;
      }).join("");
      const tokens = FLOAT_TOKENS.map((token, i) => {
        return `<span class="build-wait-token" style="--i:${i}">${token}</span>`;
      }).join("");

      return `
        <div class="build-wait" data-phase="${phase}">
          <div class="build-wait-bg" aria-hidden="true">
            <div class="build-wait-grid"></div>
            <div class="build-wait-aurora"></div>
            ${particles}
          </div>
          <div class="build-wait-core" aria-hidden="true">
            <div class="build-wait-ring ring-outer"></div>
            <div class="build-wait-ring ring-inner"></div>
            <div class="build-wait-orbit">
              <span class="build-wait-orbit-dot od1"></span>
              <span class="build-wait-orbit-dot od2"></span>
              <span class="build-wait-orbit-dot od3"></span>
            </div>
            <div class="build-wait-icon">${meta.emoji}</div>
          </div>
          <div class="build-wait-tokens" aria-hidden="true">${tokens}</div>
          <h3 class="build-wait-title">
            ${meta.title}
            <span class="build-wait-dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span>
          </h3>
          <p class="build-wait-sub">${meta.subtitle}</p>
          <div class="build-wait-progress">
            <div class="build-wait-progress-track">
              <div class="build-wait-progress-fill" id="buildProgress" style="width:${pct}%"></div>
              <div class="build-wait-progress-shine"></div>
            </div>
            <span class="build-wait-pct" id="buildProgressPct">${Math.round(pct)}%</span>
          </div>
          <div class="build-wait-scanline" aria-hidden="true"></div>
        </div>
      `;
    },

    /**
     * @param {HTMLElement|null} [root]
     * @param {number} pct
     */
    updateProgress(root, pct) {
      const scope = root || document;
      const fill =
        scope.querySelector?.(".build-wait-progress-fill") ||
        document.getElementById("buildProgress");
      const pctEl = scope.querySelector?.(".build-wait-pct") || document.getElementById("buildProgressPct");
      const v = Math.min(100, Math.max(0, pct));
      if (fill) fill.style.width = `${v}%`;
      if (pctEl) pctEl.textContent = `${Math.round(v)}%`;
    },
  };

  window.EduBuildWait = EduBuildWait;
})();
