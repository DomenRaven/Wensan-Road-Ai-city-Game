/* 7.20 W5 / UH · 真实工作区代码浏览（可叠本轮 Diff 高亮） */
(() => {
  "use strict";

  /** @type {HTMLElement|null} */
  let overlayEl = null;
  /** @type {string} */
  let sessionId = "";
  /** @type {string} */
  let turnId = "";
  /** @type {string} */
  let activePath = "";
  /** @type {Set<string>} */
  const expanded = new Set(["config", "core", "scenes"]);
  /**
   * path → { path, change_type, diff_text, after_text, note }
   * @type {Map<string, Record<string, string>>}
   */
  let turnDiffByPath = new Map();

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
          <strong id="eduCodeBrowserTitle">查看游戏代码</strong>
          <span class="edu-code-browser-sub" id="eduCodeBrowserSub">真实工作区 · 只读</span>
        </div>
        <button type="button" class="btn btn-secondary" id="eduCodeBrowserClose">返回创作/试玩</button>
      </div>
      <div class="edu-code-browser-body">
        <aside class="edu-code-browser-tree" id="eduCodeBrowserTree" aria-label="文件树"></aside>
        <section class="edu-code-browser-main">
          <div class="edu-code-browser-anno" id="eduCodeBrowserAnno">选择左侧文件开始阅读</div>
          <div class="edu-code-browser-path" id="eduCodeBrowserPath"></div>
          <pre class="edu-code-browser-code" id="eduCodeBrowserCode" tabindex="0"><code></code></pre>
        </section>
      </div>
    `;
    document.body.appendChild(overlayEl);
    overlayEl.querySelector("#eduCodeBrowserClose")?.addEventListener("click", () => hide());
    return overlayEl;
  }

  function setChrome() {
    const title = document.getElementById("eduCodeBrowserTitle");
    const sub = document.getElementById("eduCodeBrowserSub");
    if (turnId && turnDiffByPath.size) {
      if (title) title.textContent = "改后全文 · 真实工作区";
      if (sub) {
        sub.textContent = `本轮改动高亮 · ${turnDiffByPath.size} 个文件 · 绿=新增 红斜体=删除`;
      }
    } else {
      if (title) title.textContent = "查看游戏代码";
      if (sub) sub.textContent = "真实工作区 · 只读";
    }
  }

  /**
   * 由 unified diff 标注 after 全文行：add / touch（hunk 内未改上下文）/ 在对应位置插入 del。
   * hunk 内 context 也标 touch，避免「+」夹「 」造成斑马线空档。
   * @param {string} afterText
   * @param {string} diffText
   * @returns {Array<{kind:'ctx'|'add'|'del'|'touch', text:string, lineNo:number|null}>}
   */
  function buildAnnotatedRows(afterText, diffText) {
    const afterLines = String(afterText || "").split("\n");
    /** @type {Set<number>} */
    const addAt = new Set();
    /** @type {Set<number>} */
    const touchAt = new Set();
    /** @type {Map<number, string[]>} */
    const delBefore = new Map();
    let afterIdx = 0;
    const raw = String(diffText || "").split("\n");
    for (const line of raw) {
      if (line.startsWith("@@")) {
        const m = line.match(/\+(\d+)/);
        if (m) afterIdx = Math.max(0, Number(m[1]) - 1);
        continue;
      }
      if (line.startsWith("+++") || line.startsWith("---")) continue;
      if (line.startsWith("+")) {
        addAt.add(afterIdx);
        afterIdx += 1;
      } else if (line.startsWith("-")) {
        const arr = delBefore.get(afterIdx) || [];
        arr.push(line.slice(1));
        delBefore.set(afterIdx, arr);
      } else if (line.startsWith("\\")) {
        continue;
      } else if (line.startsWith(" ") || line === "") {
        // hunk 内 context（unified 前导空格）；标 touch 避免 +/ctx 斑马空档
        touchAt.add(afterIdx);
        afterIdx += 1;
      }
      // 其它头信息 / 截断提示：忽略，不推进 afterIdx
    }

    /** @type {Array<{kind:'ctx'|'add'|'del'|'touch', text:string, lineNo:number|null}>} */
    const rows = [];
    for (let i = 0; i < afterLines.length; i += 1) {
      const dels = delBefore.get(i);
      if (dels) {
        for (const d of dels) rows.push({ kind: "del", text: d, lineNo: null });
      }
      let kind = "ctx";
      if (addAt.has(i)) kind = "add";
      else if (touchAt.has(i)) kind = "touch";
      rows.push({
        kind,
        text: afterLines[i],
        lineNo: i + 1,
      });
    }
    const trailing = delBefore.get(afterLines.length);
    if (trailing) {
      for (const d of trailing) rows.push({ kind: "del", text: d, lineNo: null });
    }
    if (!rows.length && !afterLines.length) {
      const onlyDel = [];
      for (const [, arr] of delBefore) onlyDel.push(...arr);
      for (const d of onlyDel) rows.push({ kind: "del", text: d, lineNo: null });
    }
    return rows;
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
        const changed = turnDiffByPath.has(node.path);
        return `
          <button type="button" class="edu-cb-file${activePath === node.path ? " is-active" : ""}${
            previewable ? "" : " is-disabled"
          }${changed ? " is-changed" : ""}" data-file="${escapeHtml(node.path)}" data-previewable="${
            previewable ? "1" : "0"
          }" style="--depth:${depth}">
            <span class="edu-cb-file-mark" aria-hidden="true"></span>
            <span class="edu-cb-file-name">📄 ${escapeHtml(node.name)}</span>
            ${changed ? '<span class="edu-cb-changed-badge">改</span>' : ""}
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
   * @param {string} [diffText]
   */
  function renderCodeWithLines(content, path, diffText) {
    if (diffText) {
      const rows = buildAnnotatedRows(content, diffText);
      return rows
        .map((row) => {
          const cls =
            row.kind === "add"
              ? "cb-line cb-line--add"
              : row.kind === "touch"
              ? "cb-line cb-line--touch"
              : row.kind === "del"
              ? "cb-line cb-line--del"
              : "cb-line";
          const ln = row.lineNo != null ? String(row.lineNo) : "−";
          const html = highlight(path, row.text);
          return `<div class="${cls}"><span class="cb-ln">${ln}</span><span class="cb-tx">${
            html || " "
          }</span></div>`;
        })
        .join("");
    }
    const lines = String(content || "").split("\n");
    const highlighted = highlight(path, content).split("\n");
    return lines
      .map((_, i) => {
        const n = i + 1;
        const html = highlighted[i] ?? "";
        return `<div class="cb-line"><span class="cb-ln">${n}</span><span class="cb-tx">${
          html || " "
        }</span></div>`;
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

    const diffMeta = turnDiffByPath.get(path);
    try {
      let content = "";
      let note = "暂无说明";
      let truncated = false;
      if (diffMeta && String(diffMeta.change_type) === "deleted") {
        content = "";
        note = String(diffMeta.note || "本轮删除了该文件");
      } else {
        const data = await window.EduSession.apiWithSession(
          `/sessions/${sessionId}/workspace/file?rel_path=${encodeURIComponent(path)}`
        );
        content = String(data.content || "");
        note = String(data.annotation || "").trim() || "暂无说明";
        truncated = !!data.truncated;
      }
      if (diffMeta) {
        note = `${String(diffMeta.note || note)} · 绿底=新增，红斜体=删除`;
      }
      if (anno) {
        anno.textContent = truncated ? `${note}（文件较大，已截断显示）` : note;
      }
      if (codeHost) {
        const diffText = diffMeta ? String(diffMeta.diff_text || "") : "";
        // 新增文件：整文件按 after，diff 可能从空文件起
        const body =
          diffMeta && !content && String(diffMeta.after_text || "")
            ? String(diffMeta.after_text)
            : content;
        codeHost.innerHTML = `<code class="cb-code">${renderCodeWithLines(
          body,
          path,
          diffText || undefined
        )}</code>`;
        codeHost.scrollTop = 0;
      }
    } catch (err) {
      if (anno) anno.textContent = "打开失败，请重试";
      if (codeHost) {
        codeHost.innerHTML = `<code>${escapeHtml(String(err?.message || err))}</code>`;
      }
    }
  }

  /**
   * @param {Array<{name:string,path:string,type:string,previewable?:boolean,children?:any[]}>} tree
   * @returns {string[]}
   */
  function flattenFiles(tree) {
    /** @type {string[]} */
    const out = [];
    const walk = (nodes) => {
      for (const n of nodes || []) {
        if (n.type === "file" && n.previewable !== false) out.push(n.path);
        if (n.children) walk(n.children);
      }
    };
    walk(tree);
    return out;
  }

  async function loadTurnDiff() {
    turnDiffByPath = new Map();
    if (!turnId || !sessionId) return;
    try {
      const data = await window.EduSession.apiWithSession(
        `/sessions/${sessionId}/turns/${turnId}/diff`
      );
      for (const f of Array.isArray(data.files) ? data.files : []) {
        if (f?.path) turnDiffByPath.set(String(f.path), /** @type {*} */ (f));
      }
    } catch (err) {
      window.EduSession?.log?.(
        `加载本轮 Diff 失败 · ${/** @type {Error} */ (err).message || err}`
      );
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
      const files = flattenFiles(tree);
      const changedFirst = [...turnDiffByPath.keys()].find((p) => files.includes(p));
      const prefer =
        changedFirst ||
        files.find((p) => p === "config/game_config.json") ||
        files[0];
      if (prefer) await openFile(prefer);
    } catch (err) {
      treeEl.innerHTML = `<p class="edu-cb-loading">加载失败：${escapeHtml(
        String(err?.message || err)
      )} <button type="button" class="btn btn-secondary" id="eduCbRetry">重试</button></p>`;
      const anno = document.getElementById("eduCodeBrowserAnno");
      const pathEl = document.getElementById("eduCodeBrowserPath");
      const codeHost = document.getElementById("eduCodeBrowserCode");
      if (anno) {
        anno.textContent =
          "工作区未就绪或会话已更换。请返回后重新走一遍「制作」，再查看代码。";
      }
      if (pathEl) pathEl.textContent = "";
      if (codeHost) codeHost.innerHTML = "<code></code>";
      document.getElementById("eduCbRetry")?.addEventListener("click", () => void loadTree());
    }
  }

  /**
   * @param {{ sessionId?: string, turnId?: string }} [opts]
   */
  async function show(opts = {}) {
    sessionId = opts.sessionId || window.EduSession?.sessionId || "";
    turnId = String(opts.turnId || "").trim();
    if (!sessionId || String(sessionId).startsWith("demo-")) {
      window.alert("会话或工作区未就绪，请先完成制作");
      return;
    }
    const root = ensureOverlay();
    root.hidden = false;
    document.body.classList.add("edu-code-browser-open");
    activePath = "";
    await loadTurnDiff();
    setChrome();
    await loadTree();
    // 打开后把焦点放到代码区，滚轮更易命中
    document.getElementById("eduCodeBrowserCode")?.focus?.({ preventScroll: true });
  }

  function hide() {
    if (!overlayEl) return;
    overlayEl.hidden = true;
    document.body.classList.remove("edu-code-browser-open");
    turnId = "";
    turnDiffByPath = new Map();
  }

  window.EduCodeBrowser = { show, hide };
})();
