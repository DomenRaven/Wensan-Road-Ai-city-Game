/* 只读代码区 · 行号 · 文件切换 */
(() => {
  "use strict";

  /** @type {HTMLElement|null} */
  let containerEl = null;
  /** @type {HTMLElement|null} */
  let gutterEl = null;
  /** @type {HTMLElement|null} */
  let contentEl = null;
  /** @type {string} */
  let currentFile = "config/game_config.json";

  const EduCodeViewer = {
    /**
     * @param {HTMLElement} container
     */
    mount(container) {
      containerEl = container;
      container.innerHTML = `
        <div class="code-scroll" id="codeScroll">
          <div class="code-gutter" id="codeGutter"></div>
          <pre class="code-content" id="codeContent" aria-readonly="true"></pre>
        </div>
      `;
      gutterEl = container.querySelector("#codeGutter");
      contentEl = container.querySelector("#codeContent");
      return { gutter: gutterEl, content: contentEl };
    },

    /** @param {string} text */
    showPlaceholder(text) {
      this.setContent(text || "你的游戏代码会出现在这里", []);
    },

    /**
     * @param {string} text
     * @param {number[]} [highlightLines]
     */
    setContent(text, highlightLines) {
      if (!contentEl || !gutterEl) return;
      const lines = text.split("\n");
      const hlSet = new Set(highlightLines || []);
      gutterEl.innerHTML = lines.map((_, i) => `<span>${i + 1}</span>`).join("\n");
      contentEl.innerHTML = lines
        .map((line, i) => {
          const cls = hlSet.has(i + 1) ? "line code-line-highlight" : "line";
          const escaped = line
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
          return `<span class="${cls}" data-line="${i + 1}">${escaped || " "}</span>`;
        })
        .join("\n");
    },

    /**
     * @param {Array<{text:string, highlight?:boolean, anchor_id?:string}>} lines
     */
    setTheaterLines(lines) {
      if (!contentEl || !gutterEl) return;
      gutterEl.innerHTML = lines.map((_, i) => `<span>${i + 1}</span>`).join("\n");
      contentEl.innerHTML = lines
        .map((item, i) => {
          let cls = "line";
          if (item.highlight) cls += " hl-theater";
          if (item.anchor_id) cls += ` anchor-${item.anchor_id}`;
          const escaped = item.text
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
          return `<span class="${cls}" data-line="${i + 1}" data-anchor="${item.anchor_id || ""}">${escaped || " "}</span>`;
        })
        .join("\n");
      const last = contentEl.querySelector(".line:last-child");
      if (last) last.scrollIntoView({ block: "nearest", behavior: "smooth" });
    },

    /**
     * @param {number} lineNum
     * @param {number} [durationMs]
     * @returns {boolean}
     */
    highlightLine(lineNum, durationMs) {
      if (!contentEl) return false;
      contentEl.querySelectorAll(".code-line-highlight").forEach((el) => {
        el.classList.remove("code-line-highlight");
      });
      const line = contentEl.querySelector(`[data-line="${lineNum}"]`);
      if (!line) return false;
      line.classList.add("code-line-highlight");
      line.scrollIntoView({ block: "center", behavior: "smooth" });
      if (durationMs && durationMs > 0) {
        window.setTimeout(() => line.classList.remove("code-line-highlight"), durationMs);
      }
      return true;
    },

    /** @param {string} file */
    setActiveFile(file) {
      currentFile = file;
      if (window.EduDualPane) window.EduDualPane.setActiveFile(file);
    },

    getCurrentFile() {
      return currentFile;
    },

    /**
     * @param {Record<string, string>} files
     * @param {string} activeFile
     */
    showFileTabs(files, activeFile) {
      this.setActiveFile(activeFile);
      this.setContent(files[activeFile] || "", []);
    },
  };

  window.EduCodeViewer = EduCodeViewer;
})();
