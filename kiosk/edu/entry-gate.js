/* 7.20 W1 · 初始页：游客 ∥ 登录/注册 */
(() => {
  "use strict";

  /** @typedef {{id:string,username:string,nickname:string,role:string,class_label?:string}} EduUser */

  const EduEntryGate = {
    /** @type {HTMLElement|null} */
    root: null,
    /** @type {(mode:"guest"|"login")=>void|Promise<void>} */
    onReady: null,

    /**
     * @param {HTMLElement} host
     * @param {(mode:"guest"|"login")=>void|Promise<void>} onReady
     */
    mount(host, onReady) {
      this.root = host;
      this.onReady = onReady;
      host.hidden = false;
      this.renderChoice();
    },

    hide() {
      if (this.root) {
        this.root.hidden = true;
        this.root.innerHTML = "";
      }
    },

    renderChoice() {
      if (!this.root) return;
      this.root.innerHTML = `
        <div class="entry-gate-card">
          <h1>AI 游戏创作工坊</h1>
          <p class="entry-gate-lead">先选一种方式进入。游客可直接体验；登录后作品与学情会记在你的账号下。</p>
          <div class="entry-gate-actions">
            <button type="button" class="btn btn-primary entry-gate-btn" data-act="guest">游客模式</button>
            <button type="button" class="btn btn-secondary entry-gate-btn" data-act="login">登录 / 注册</button>
          </div>
          <p class="entry-gate-hint">学情仅用于教学改进，不会公开你的账号密码。</p>
        </div>
      `;
      this.root.querySelector('[data-act="guest"]')?.addEventListener("click", () => {
        void this.chooseGuest();
      });
      this.root.querySelector('[data-act="login"]')?.addEventListener("click", () => {
        this.renderAuth("login");
      });
    },

    /**
     * @param {"login"|"register"} mode
     */
    renderAuth(mode) {
      if (!this.root) return;
      const isReg = mode === "register";
      this.root.innerHTML = `
        <div class="entry-gate-card entry-gate-card--auth">
          <h1>${isReg ? "注册账号" : "登录账号"}</h1>
          <p class="entry-gate-lead">${
            isReg
              ? "填写即创建账号，无需邀请码。昵称会用于作品署名。"
              : "使用用户名与密码登录。"
          }</p>
          <form class="entry-gate-form" id="entryAuthForm">
            <label>用户名
              <input name="username" class="text-input edu-touch-input" autocomplete="username"
                placeholder="3～32 位，字母/数字/下划线" required />
            </label>
            ${
              isReg
                ? `<label>昵称
              <input name="nickname" class="text-input edu-touch-input" autocomplete="nickname"
                maxlength="8" placeholder="1～8 个字" required />
            </label>
            <label>班级（可选）
              <input name="class_label" class="text-input edu-touch-input" placeholder="如 高一(3)班" />
            </label>`
                : ""
            }
            <label>密码
              <input name="password" type="password" class="text-input edu-touch-input"
                autocomplete="${isReg ? "new-password" : "current-password"}"
                placeholder="至少 6 位" required />
            </label>
            <p class="entry-gate-error" id="entryAuthError" hidden></p>
            <div class="entry-gate-actions">
              <button type="submit" class="btn btn-primary">${isReg ? "注册并进入" : "登录并进入"}</button>
              <button type="button" class="btn btn-secondary" data-act="back">返回</button>
            </div>
            <p class="entry-gate-switch">
              ${
                isReg
                  ? `已有账号？<button type="button" class="entry-link" data-act="to-login">去登录</button>`
                  : `还没有账号？<button type="button" class="entry-link" data-act="to-register">去注册</button>`
              }
            </p>
            ${
              isReg
                ? `<p class="entry-gate-hint">注册即表示了解：对话与评价将用于教学改进，不写入玩法模板源码。</p>`
                : ""
            }
          </form>
        </div>
      `;
      this.root.querySelector('[data-act="back"]')?.addEventListener("click", () => {
        this.renderChoice();
      });
      this.root.querySelector('[data-act="to-login"]')?.addEventListener("click", () => {
        this.renderAuth("login");
      });
      this.root.querySelector('[data-act="to-register"]')?.addEventListener("click", () => {
        this.renderAuth("register");
      });
      const form = /** @type {HTMLFormElement|null} */ (this.root.querySelector("#entryAuthForm"));
      form?.addEventListener("submit", (ev) => {
        ev.preventDefault();
        void this.submitAuth(mode, form);
      });
      window.EduTouchKeyboard?.bind?.(this.root);
    },

    async chooseGuest() {
      window.EduSession.clearAuth();
      window.EduSession.authMode = "guest";
      if (this.onReady) await this.onReady("guest");
      this.hide();
    },

    /**
     * @param {"login"|"register"} mode
     * @param {HTMLFormElement} form
     */
    async submitAuth(mode, form) {
      const errEl = /** @type {HTMLElement|null} */ (this.root?.querySelector("#entryAuthError"));
      const fd = new FormData(form);
      const username = String(fd.get("username") || "").trim();
      const password = String(fd.get("password") || "");
      const nickname = String(fd.get("nickname") || "").trim();
      const classLabel = String(fd.get("class_label") || "").trim();
      if (errEl) {
        errEl.hidden = true;
        errEl.textContent = "";
      }
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn) /** @type {HTMLButtonElement} */ (submitBtn).disabled = true;
      try {
        if (mode === "register") {
          await window.EduSession.register({
            username,
            password,
            nickname,
            class_label: classLabel,
          });
        } else {
          await window.EduSession.login({ username, password });
        }
        window.EduSession.authMode = "login";
        if (this.onReady) await this.onReady("login");
        this.hide();
      } catch (err) {
        const msg = String(/** @type {Error} */ (err).message || err);
        if (errEl) {
          errEl.hidden = false;
          errEl.textContent = msg.replace(/^\d+:\s*/, "").replace(/^"|"$/g, "") || "操作失败，请重试";
        }
      } finally {
        if (submitBtn) /** @type {HTMLButtonElement} */ (submitBtn).disabled = false;
      }
    },
  };

  window.EduEntryGate = EduEntryGate;
})();
