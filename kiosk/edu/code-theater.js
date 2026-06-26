/* B5 · 多文件代码剧场 · 自上而下浮现 + 真实模板节选打字 */
(() => {
  "use strict";

  /** @type {number|null} */
  let timerId = null;
  /** @type {boolean} */
  let running = false;

  /**
   * @param {string} relPath
   * @returns {number}
   */
  function maxLinesForPath(relPath) {
    if (relPath === "project.godot") return 18;
    if (relPath.endsWith(".tscn")) return 28;
    if (relPath.endsWith(".json")) return 55;
    if (relPath.endsWith(".gd")) return 42;
    return 36;
  }

  /**
   * @param {string} content
   * @param {string} relPath
   * @returns {string[]}
   */
  function excerptLines(content, relPath) {
    const all = String(content || "").replace(/\r\n/g, "\n").split("\n");
    const cap = maxLinesForPath(relPath);
    if (all.length <= cap) return all;
    const head = all.slice(0, cap);
    head.push("…  （展示节选，完整文件在试玩阶段可点开查看）");
    return head;
  }

  /**
   * @param {number} ms
   */
  function sleep(ms) {
    return new Promise((resolve) => {
      timerId = window.setTimeout(resolve, ms);
    });
  }

  const EduCodeTheater = {
    /** @type {number} */
    totalMs: 45000,

    /**
     * @param {string} slug
     * @param {Record<string, unknown>} spec
     */
    async load(slug, spec) {
      const theater = spec.theater || {};
      this.totalMs = Number(theater.theater_total_ms) || 45000;
      if (window.EduFileTree) {
        await window.EduFileTree.loadManifest(slug, spec);
      }
    },

    /**
     * @param {HTMLElement} codeContainer
     * @param {string} genre
     * @param {Record<string, unknown>} spec
     * @param {(state:string, detail?:{progress?:number,file?:string})=>void} onStateChange
     */
    async start(codeContainer, genre, spec, onStateChange) {
      this.stop();
      running = true;

      const apiBase = String(spec.api_base || window.EduSession?.apiBase || "http://127.0.0.1:8000").replace(
        /\/$/,
        ""
      );
      const files = window.EduFileTree?.getManifestFiles() || [
        "project.godot",
        "config/game_config.json",
        "core/game_manager.gd",
      ];
      const theaterBudgetMs = Math.floor(this.totalMs * 0.58);
      const msPerFile = Math.max(2800, Math.floor(theaterBudgetMs / Math.max(1, files.length)));

      const theater = /** @type {Record<string, unknown>} */ (spec.theater || {});
      const colors = /** @type {Record<string, unknown>} */ (spec.colors || {});
      const theaterBg = String(theater.background || colors.code_bg || "");
      if (theaterBg) {
        codeContainer.style.setProperty("--theater-bg", theaterBg);
        const scroll = codeContainer.querySelector(".code-scroll");
        if (scroll instanceof HTMLElement) scroll.style.background = theaterBg;
      }

      if (window.EduCodeViewer) window.EduCodeViewer.mount(codeContainer);
      window.EduFileTree?.clear();
      const treeHost = document.getElementById("fileTree");
      if (treeHost && window.EduFileTree) window.EduFileTree.mount(treeHost);

      onStateChange("theater_scrolling", { progress: 12 });

      for (let fi = 0; fi < files.length && running; fi += 1) {
        const relPath = files[fi];
        window.EduFileTree?.revealFile(relPath);
        window.EduFileTree?.setActive(relPath);
        window.EduDualPane?.setActiveFile(relPath);
        if (window.EduCodeViewer) {
          window.EduCodeViewer.setActiveFile(relPath);
          window.EduCodeViewer.setTheaterLines([]);
        }

        let content = "";
        try {
          const res = await fetch(
            `${apiBase}/edu/preview/${encodeURIComponent(genre)}/file?rel_path=${encodeURIComponent(relPath)}`
          );
          if (res.ok) {
            const data = await res.json();
            content = String(data.content || "");
          }
        } catch (_) {
          /* fallback below */
        }

        if (!content) {
          try {
            const fallbackUrl = `../../templates/${genre}/${relPath}`;
            const res = await fetch(fallbackUrl);
            if (res.ok) content = await res.text();
          } catch (_) {
            content = `// 预览加载中…\n// ${relPath}`;
          }
        }

        const lines = excerptLines(content, relPath);
        const lineDelay = Math.max(28, Math.min(72, Math.floor(msPerFile / Math.max(1, lines.length))));
        const displayed = [];

        for (let li = 0; li < lines.length && running; li += 1) {
          displayed.push({ delay_ms: lineDelay, text: lines[li], highlight: false });
          if (window.EduCodeViewer) window.EduCodeViewer.setTheaterLines(displayed);
          const basePct = 12 + Math.floor((fi / files.length) * 52);
          const filePct = Math.floor(((li + 1) / lines.length) * (52 / files.length));
          onStateChange("theater_tick", { progress: basePct + filePct, file: relPath });
          await sleep(lineDelay);
        }
      }

      if (running) {
        window.EduFileTree?.showAll(files, { instant: true });
        onStateChange("applying", { progress: 72 });
      }
    },

    stop() {
      running = false;
      if (timerId) {
        window.clearTimeout(timerId);
        timerId = null;
      }
    },

    /**
     * @param {HTMLElement|null} progressEl
     * @param {number} pct
     */
    updateProgress(progressEl, pct) {
      if (window.EduBuildWait) {
        window.EduBuildWait.updateProgress(progressEl, pct);
        return;
      }
      const fill = progressEl?.querySelector(".progress-fill");
      if (fill) fill.style.width = `${Math.min(100, pct)}%`;
    },
  };

  window.EduCodeTheater = EduCodeTheater;
})();
