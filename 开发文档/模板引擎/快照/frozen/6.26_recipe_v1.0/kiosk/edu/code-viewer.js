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

  /** @type {boolean} */
  let viewportPinned = false;

  /**
   * 创建/制作阶段：锁定横向 · 顶格起始
   * @param {HTMLElement|null|undefined} scrollEl
   */
  function pinViewportTop(scrollEl) {
    if (!(scrollEl instanceof HTMLElement)) return;
    scrollEl.scrollLeft = 0;
    scrollEl.scrollTop = 0;
  }

  /**
   * 仅纵向滚入视口；横向 scrollLeft 永不自动改变（仅用户手势可横滚）
   * @param {HTMLElement} scrollEl
   * @param {HTMLElement} target
   * @param {"center"|"nearest"} [block]
   */
  function scrollIntoContainer(scrollEl, target, block = "center") {
    const scrollRect = scrollEl.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();
    let nextTop = scrollEl.scrollTop;

    if (block === "center") {
      nextTop += targetRect.top - scrollRect.top - (scrollRect.height - targetRect.height) / 2;
    } else if (targetRect.top < scrollRect.top) {
      nextTop += targetRect.top - scrollRect.top;
    } else if (targetRect.bottom > scrollRect.bottom) {
      nextTop += targetRect.bottom - scrollRect.bottom;
    }

    scrollEl.scrollTo({
      top: Math.max(0, nextTop),
      left: scrollEl.scrollLeft,
      behavior: "smooth",
    });
  }

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
      this.applyViewportPinClass();
      const scrollEl = container.querySelector(".code-scroll");
      if (viewportPinned) pinViewportTop(scrollEl);
      return { gutter: gutterEl, content: contentEl };
    },

    /** @param {boolean} pinned */
    setViewportPinned(pinned) {
      viewportPinned = !!pinned;
      this.applyViewportPinClass();
      const scrollEl = contentEl?.closest(".code-scroll");
      if (scrollEl instanceof HTMLElement) {
        scrollEl.scrollLeft = 0;
        if (viewportPinned) scrollEl.scrollTop = 0;
      }
    },

    isViewportPinned() {
      return viewportPinned;
    },

    applyViewportPinClass() {
      const scrollEl = containerEl?.querySelector(".code-scroll");
      if (scrollEl instanceof HTMLElement) {
        scrollEl.classList.toggle("code-scroll--pinned", viewportPinned);
      }
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
      const scrollEl = contentEl.closest(".code-scroll");
      if (last instanceof HTMLElement && scrollEl instanceof HTMLElement) {
        scrollIntoContainer(scrollEl, last, "nearest");
      }
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
      const scrollEl = contentEl.closest(".code-scroll");
      if (scrollEl instanceof HTMLElement) {
        scrollIntoContainer(scrollEl, line, "center");
      }
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
