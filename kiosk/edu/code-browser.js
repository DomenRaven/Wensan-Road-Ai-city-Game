/* 7.20 W5 · F1 真实工作区代码浏览（证书保存后门闩） */
(() => {
  "use strict";

  /** @type {HTMLElement|null} */
  let overlayEl = null;
  /** @type {string} */
  let sessionId = "";
  /** @type {string} */
  let activePath = "";
  /** @type {Set<string>} */
  const expanded = new Set(["config", "core", "scenes"]);

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function ensureOverlay() {
    if (overlayEl) return overlayEl;
    overlayEl = document.createElement("div");
    overlayEl.id = "eduCodeBrowser";
    overlayEl.className = "edu-code-browser";
    overlayEl.hidden = true;
    overlayEl.innerHTML = `
      <div class="edu-code-browser-bar">
        <div class="edu-code-browser-title">
          <strong>查看游戏代码</strong>
          <span class="edu-code-browser-sub">真实工作区 · 只读</span>
        </div>
        <button type="button" class="btn btn-secondary" id="eduCodeBrowserClose">返回创作/试玩</button>
      </div>
      <div class="edu-code-browser-body">
        <aside class="edu-code-browser-tree" id="eduCodeBrowserTree" aria-label="文件树"></aside>
        <section class="edu-code-browser-main">
          <div class="edu-code-browser-anno" id="eduCodeBrowserAnno">选择左侧文件开始阅读</div>
          <div class="edu-code-browser-path" id="eduCodeBrowserPath"></div>
          <pre class="edu-code-browser-code" id="eduCodeBrowserCode"><code></code></pre>
        </section>
      </div>
    `;
    document.body.appendChild(overlayEl);
    overlayEl.querySelector("#eduCodeBrowserClose")?.addEventListener("click", () => hide());
    return overlayEl;
  }

  /**
   * @param {Array<{name:string,path:string,type:string,previewable?:boolean,children?:any[]}>} nodes
   * @param {number} depth
   */
  function renderTreeNodes(nodes, depth = 0) {
    return (nodes || [])
      .map((node) => {
        if (node.type === "dir") {
          const open = expanded.has(node.path);
          const kids = renderTreeNodes(node.children || [], depth + 1);
          return `
            <div class="edu-cb-dir" style="--depth:${depth}">
              <button type="button" class="edu-cb-dir-btn" data-dir="${escapeHtml(node.path)}">
                <span class="edu-cb-caret">${open ? "▼" : "▶"}</span>
                <span>📁 ${escapeHtml(node.name)}</span>
              </button>
              <div class="edu-cb-children" ${open ? "" : "hidden"}>${kids}</div>
            </div>
          `;
        }
        const previewable = node.previewable !== false;
        return `
          <button type="button" class="edu-cb-file${activePath === node.path ? " is-active" : ""}${
            previewable ? "" : " is-disabled"
          }" data-file="${escapeHtml(node.path)}" data-previewable="${previewable ? "1" : "0"}" style="--depth:${depth}">
            📄 ${escapeHtml(node.name)}
          </button>
        `;
      })
      .join("");
  }

  function bindTree() {
    const tree = document.getElementById("eduCodeBrowserTree");
    if (!tree) return;
    tree.querySelectorAll("[data-dir]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const path = btn.getAttribute("data-dir") || "";
        if (expanded.has(path)) expanded.delete(path);
        else expanded.add(path);
        const wrap = btn.parentElement?.querySelector(".edu-cb-children");
        if (wrap) wrap.hidden = !expanded.has(path);
        const caret = btn.querySelector(".edu-cb-caret");
        if (caret) caret.textContent = expanded.has(path) ? "▼" : "▶";
      });
    });
    tree.querySelectorAll("[data-file]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const path = btn.getAttribute("data-file") || "";
        const ok = btn.getAttribute("data-previewable") === "1";
        if (!ok) {
          const anno = document.getElementById("eduCodeBrowserAnno");
          const code = document.querySelector("#eduCodeBrowserCode code");
          const pathEl = document.getElementById("eduCodeBrowserPath");
          if (anno) anno.textContent = "此文件为资源/二进制，目录中可看到，但不预览正文。";
          if (pathEl) pathEl.textContent = path;
          if (code) code.textContent = "";
          return;
        }
        void openFile(path);
      });
    });
  }

  /**
   * 极简高亮：关键字着色（.gd / .json / .tscn）
   * @param {string} path
   * @param {string} content
   */
  function highlight(path, content) {
    const esc = escapeHtml(content);
    const lower = path.toLowerCase();
    if (lower.endsWith(".json")) {
      return esc
        .replace(/(&quot;[^&]*&quot;)(\s*:)/g, '<span class="cb-key">$1</span>$2')
        .replace(/:\s*(&quot;[^&]*&quot;)/g, ': <span class="cb-str">$1</span>')
        .replace(/:\s*(-?\d+(?:\.\d+)?)/g, ': <span class="cb-num">$1</span>');
    }
    if (lower.endsWith(".gd") || lower.endsWith(".tscn")) {
      return esc
        .replace(
          /\b(func|var|const|class_name|extends|signal|if|elif|else|for|while|return|pass|true|false|null)\b/g,
          '<span class="cb-kw">$1</span>'
        )
        .replace(/(&quot;[^&]*&quot;|&#39;[^&]*&#39;)/g, '<span class="cb-str">$1</span>')
        .replace(/#[^\n]*/g, '<span class="cb-comment">$&</span>');
    }
    return esc;
  }

  /**
   * @param {string} content
   * @param {string} path
   */
  function renderCodeWithLines(content, path) {
    const lines = String(content || "").split("\n");
    const highlighted = highlight(path, content).split("\n");
    return lines
      .map((_, i) => {
        const n = i + 1;
        const html = highlighted[i] ?? "";
        return `<div class="cb-line"><span class="cb-ln">${n}</span><span class="cb-tx">${html || " "}</span></div>`;
      })
      .join("");
  }

  /**
   * @param {string} path
   */
  async function openFile(path) {
    activePath = path;
    const tree = document.getElementById("eduCodeBrowserTree");
    tree?.querySelectorAll(".edu-cb-file").forEach((el) => {
      el.classList.toggle("is-active", el.getAttribute("data-file") === path);
    });
    const anno = document.getElementById("eduCodeBrowserAnno");
    const pathEl = document.getElementById("eduCodeBrowserPath");
    const codeHost = document.getElementById("eduCodeBrowserCode");
    if (pathEl) pathEl.textContent = path;
    if (anno) anno.textContent = "加载中…";
    if (codeHost) codeHost.innerHTML = "<code>加载中…</code>";
    try {
      const data = await window.EduSession.apiWithSession(
        `/sessions/${sessionId}/workspace/file?rel_path=${encodeURIComponent(path)}`
      );
      const note = String(data.annotation || "").trim() || "暂无说明";
      if (anno) {
        anno.textContent = data.truncated ? `${note}（文件较大，已截断显示）` : note;
      }
      if (codeHost) {
        codeHost.innerHTML = `<code class="cb-code">${renderCodeWithLines(
          String(data.content || ""),
          path
        )}</code>`;
      }
    } catch (err) {
      if (anno) anno.textContent = "打开失败，请重试";
      if (codeHost) {
        codeHost.innerHTML = `<code>${escapeHtml(String(err?.message || err))}</code>`;
      }
    }
  }

  async function loadTree() {
    const treeEl = document.getElementById("eduCodeBrowserTree");
    if (!treeEl) return;
    treeEl.innerHTML = `<p class="edu-cb-loading">正在加载真实工作区…</p>`;
    try {
      const data = await window.EduSession.apiWithSession(
        `/sessions/${sessionId}/workspace/tree`
      );
      const tree = Array.isArray(data.tree) ? data.tree : [];
      if (!tree.length) {
        treeEl.innerHTML = `<p class="edu-cb-loading">工作区为空或尚未生成</p>`;
        return;
      }
      treeEl.innerHTML = renderTreeNodes(tree);
      bindTree();
      const prefer =
        tree
          .flatMap(function flatten(n) {
            if (n.type === "file" && n.previewable !== false) return [n.path];
            return (n.children || []).flatMap(flatten);
          })
          .find((p) => p === "config/game_config.json") ||
        tree
          .flatMap(function flatten2(n) {
            if (n.type === "file" && n.previewable !== false) return [n.path];
            return (n.children || []).flatMap(flatten2);
          })[0];
      if (prefer) await openFile(prefer);
    } catch (err) {
      treeEl.innerHTML = `<p class="edu-cb-loading">加载失败：${escapeHtml(
        String(err?.message || err)
      )} <button type="button" class="btn btn-secondary" id="eduCbRetry">重试</button></p>`;
      document.getElementById("eduCbRetry")?.addEventListener("click", () => void loadTree());
    }
  }

  /**
   * @param {{ sessionId?: string }} [opts]
   */
  async function show(opts = {}) {
    sessionId = opts.sessionId || window.EduSession?.sessionId || "";
    if (!sessionId || String(sessionId).startsWith("demo-")) {
      window.alert("会话或工作区未就绪，请先完成制作");
      return;
    }
    const root = ensureOverlay();
    root.hidden = false;
    document.body.classList.add("edu-code-browser-open");
    activePath = "";
    await loadTree();
  }

  function hide() {
    if (!overlayEl) return;
    overlayEl.hidden = true;
    document.body.classList.remove("edu-code-browser-open");
  }

  window.EduCodeBrowser = { show, hide };
})();
