/* B3+ 伪工作区文件树 · 自上而下浮现 · 可点击预览 */
(() => {
  "use strict";

  /** @typedef {{ type: "folder", name: string, key: string } | { type: "file", path: string, name: string, folderKey: string }} TreeRow */

  /** @type {HTMLElement|null} */
  let containerEl = null;
  /** @type {string[]} */
  let manifestFiles = [];
  /** @type {Set<string>} */
  const revealedPaths = new Set();
  /** @type {Set<string>} */
  const revealedFolders = new Set();
  /** @type {(path: string) => void | Promise<void>|null} */
  let clickHandler = null;

  /**
   * @param {string} relPath
   * @returns {string}
   */
  function folderKeyForPath(relPath) {
    if (relPath === "project.godot") return "__root__";
    const slash = relPath.indexOf("/");
    return slash > 0 ? relPath.slice(0, slash) : "__root__";
  }

  /**
   * @param {string} relPath
   * @returns {string}
   */
  function fileLabel(relPath) {
    const parts = relPath.split("/");
    return parts[parts.length - 1] || relPath;
  }

  /**
   * @param {string} folderKey
   * @returns {string}
   */
  function folderLabel(folderKey) {
    if (folderKey === "__root__") return "";
    return folderKey;
  }

  /**
   * @param {string} folderKey
   * @param {boolean} [instant]
   */
  function ensureFolder(folderKey, instant = false) {
    if (!containerEl || folderKey === "__root__" || revealedFolders.has(folderKey)) return;
    revealedFolders.add(folderKey);
    const row = document.createElement("div");
    row.className = "file-tree-folder";
    row.dataset.folder = folderKey;
    if (!instant) row.classList.add("file-tree-item--revealing");
    row.textContent = `📁 ${folderLabel(folderKey)}`;
    containerEl.appendChild(row);
    if (!instant) {
      requestAnimationFrame(() => {
        row.classList.add("file-tree-item--visible");
        row.classList.remove("file-tree-item--revealing");
      });
    } else {
      row.classList.add("file-tree-item--visible");
    }
  }

  const EduFileTree = {
    /**
     * @param {HTMLElement} container
     */
    mount(container) {
      containerEl = container;
      containerEl.classList.add("edu-file-tree-root");
      containerEl.innerHTML = "";
      revealedPaths.clear();
      revealedFolders.clear();
    },

    clear() {
      if (containerEl) containerEl.innerHTML = "";
      revealedPaths.clear();
      revealedFolders.clear();
      manifestFiles = [];
    },

    /**
     * @param {string} genre
     * @param {Record<string, unknown>} spec
     */
    async loadManifest(genre, spec) {
      const base = String(spec.config_base || "../../config").replace(/\/$/, "");
      const url = `${base}/edu_workspace_trees.json`;
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        const genreBlock = data.genres?.[genre];
        manifestFiles = Array.isArray(genreBlock?.files) ? genreBlock.files.slice() : [];
        return manifestFiles;
      } catch (err) {
        window.EduSession?.log(`文件树清单加载失败 · ${url} · ${err.message}`);
        manifestFiles = ["project.godot", "config/game_config.json", "core/game_manager.gd"];
        return manifestFiles;
      }
    },

    /** @returns {string[]} */
    getManifestFiles() {
      return manifestFiles.slice();
    },

    /**
     * @param {string} relPath
     * @param {{ instant?: boolean }} [opts]
     */
    revealFile(relPath, opts = {}) {
      if (!containerEl || revealedPaths.has(relPath)) return;
      const instant = Boolean(opts.instant);
      const folderKey = folderKeyForPath(relPath);
      if (folderKey !== "__root__") ensureFolder(folderKey, instant);
      revealedPaths.add(relPath);

      const row = document.createElement("div");
      row.className = "file-tree-item file-tree-file";
      row.dataset.file = relPath;
      if (folderKey !== "__root__") row.dataset.inFolder = folderKey;
      if (!instant) row.classList.add("file-tree-item--revealing");
      row.textContent = `📄 ${fileLabel(relPath)}`;
      row.title = relPath;
      row.addEventListener("click", () => {
        if (clickHandler) clickHandler(relPath);
      });
      containerEl.appendChild(row);
      if (!instant) {
        requestAnimationFrame(() => {
          row.classList.add("file-tree-item--visible");
          row.classList.remove("file-tree-item--revealing");
        });
      } else {
        row.classList.add("file-tree-item--visible");
      }
    },

    /**
     * @param {string[]} files
     * @param {{ instant?: boolean }} [opts]
     */
    showAll(files, opts = {}) {
      files.forEach((path) => this.revealFile(path, opts));
    },

    /**
     * @param {string} path
     */
    setActive(path) {
      containerEl?.querySelectorAll(".file-tree-file[data-file]").forEach((el) => {
        el.classList.toggle("active", el.getAttribute("data-file") === path);
      });
    },

    /**
     * @param {(path: string) => void | Promise<void>} fn
     */
    setClickHandler(fn) {
      clickHandler = fn;
    },
  };

  window.EduFileTree = EduFileTree;
})();
