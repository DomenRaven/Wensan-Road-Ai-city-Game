/* B3+ 双栏布局 · 左伪 IDE · 右 Godot 预览 */

(() => {

  "use strict";



  /** @type {HTMLElement|null} */

  let rootEl = null;

  /** @type {HTMLElement|null} */

  let leftBodyEl = null;

  /** @type {HTMLElement|null} */

  let rightInnerEl = null;

  /** @type {string} */

  let workspaceTitle = "工作区";



  const EduDualPane = {

    /**

     * @param {HTMLElement} container

     * @param {string} displayName

     */

    mount(container, displayName) {

      workspaceTitle = displayName ? `${displayName} 工作区` : "工作区";

      rootEl = container;

      container.innerHTML = `

        <div class="pane-left">

          <div class="pane-left-header" id="paneLeftTitle">${workspaceTitle}</div>

          <div class="pane-left-body" id="paneLeftBody">

            <div class="file-tree" id="fileTree" aria-label="项目文件"></div>

            <div class="code-workspace" id="codeWorkspace"></div>

          </div>

          <div class="dual-toolbar" id="dualToolbar" hidden></div>

        </div>

        <div class="pane-right">

          <div class="pane-right-inner" id="paneRightInner">

            <p class="preview-placeholder">即将开始制作你的游戏…</p>

          </div>

        </div>

      `;

      leftBodyEl = container.querySelector("#paneLeftBody");

      rightInnerEl = container.querySelector("#paneRightInner");

      const fileTree = container.querySelector("#fileTree");

      if (fileTree && window.EduFileTree) {

        window.EduFileTree.mount(/** @type {HTMLElement} */ (fileTree));

      }

      return {

        codeWorkspace: container.querySelector("#codeWorkspace"),

        fileTree,

        rightInner: rightInnerEl,

        toolbar: container.querySelector("#dualToolbar"),

        leftTitle: container.querySelector("#paneLeftTitle"),

      };

    },



    /** @param {string} name */

    setDisplayName(name) {

      workspaceTitle = name ? `${name} 工作区` : "工作区";

      const title = rootEl?.querySelector("#paneLeftTitle");

      if (title) title.textContent = workspaceTitle;

    },



    /**

     * @param {"create"|"build"|"play"} phase

     */

    setPhase(phase) {

      document.body.dataset.eduPhase = phase;

      const paneRight = rootEl?.querySelector(".pane-right");

      if (paneRight) {

        paneRight.classList.toggle("godot-zone", phase === "play");

      }

      document.querySelectorAll(".phase-segment").forEach((el) => {

        const seg = /** @type {HTMLElement} */ (el);

        const p = seg.dataset.phase;

        seg.classList.remove("active", "done");

        const order = ["create", "build", "play"];

        const ci = order.indexOf(phase);

        const pi = order.indexOf(p || "");

        if (pi < ci) seg.classList.add("done");

        else if (pi === ci) seg.classList.add("active");

      });

    },



    /**

     * @param {string} html

     */

    setRightContent(html) {

      if (rightInnerEl) rightInnerEl.innerHTML = html;

    },



    /**

     * @param {string} src

     * @param {string} [alt]

     */

    showPreviewImage(src, alt) {

      this.setRightContent(`

        <img class="preview-img" src="${src}" alt="${alt || "预览"}" onerror="this.style.display='none'" />

        <p class="preview-placeholder">这就是你的游戏类型预览</p>

      `);

    },



    /**

     * @param {string} genre

     * @param {string} [label]

     */

    showGenrePreview(genre, label) {

      if (rightInnerEl && window.EduGenrePreview?.render) {

        window.EduGenrePreview.render(rightInnerEl, genre, label);

        return;

      }

      const src = window.EduB1Intent?.previewUrl?.(genre) || "";

      this.showPreviewImage(src, label);

    },



    /**

     * @param {HTMLElement} el

     */

    showLeftOverlay(el) {

      if (!leftBodyEl) return;

      leftBodyEl.classList.add("overlay-mode");

      el.classList.add("left-overlay-host");

      leftBodyEl.innerHTML = "";

      leftBodyEl.appendChild(el);

    },



    /** 恢复左栏文件树 + 代码区 */

    restoreCodeLayout() {

      if (!rootEl || !leftBodyEl) return null;

      leftBodyEl.classList.remove("overlay-mode");

      leftBodyEl.innerHTML = `

        <div class="file-tree" id="fileTree" aria-label="项目文件"></div>

        <div class="code-workspace" id="codeWorkspace"></div>

      `;

      const fileTree = rootEl.querySelector("#fileTree");

      if (fileTree && window.EduFileTree) {

        window.EduFileTree.mount(/** @type {HTMLElement} */ (fileTree));

      }

      return rootEl.querySelector("#codeWorkspace");

    },



    /**

     * @param {string} file

     */

    setActiveFile(file) {

      window.EduFileTree?.setActive(file);

      rootEl?.querySelectorAll(".file-tree-item[data-file]").forEach((el) => {

        el.classList.toggle("active", el.getAttribute("data-file") === file);

      });

    },



    /**

     * @param {boolean} visible

     * @param {string} [html]

     */

    setToolbar(visible, html) {

      const tb = rootEl?.querySelector("#dualToolbar");

      if (!tb) return;

      tb.hidden = !visible;

      if (html) tb.innerHTML = html;

    },

  };



  window.EduDualPane = EduDualPane;

})();

