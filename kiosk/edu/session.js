/* B 链教育版 · session bootstrap / release / sendBeacon */
(() => {
  "use strict";

  const EduSession = {
    /** @type {string} */
    apiBase: "http://127.0.0.1:8000",
    /** @type {string} */
    storageKey: "gameforge_kiosk_session_id",
    /** @type {string} */
    sessionId: "",
    /** @type {boolean} */
    ready: false,
    /** @type {Record<string, unknown>} */
    spec: {},

    /**
     * @param {string} path
     * @param {RequestInit} [options]
     */
    async api(path, options = {}) {
      const res = await fetch(`${this.apiBase}${path}`, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options,
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`${res.status}: ${text}`);
      }
      if (res.status === 204) return {};
      return res.json();
    },

    /** @param {string} msg */
    log(msg) {
      const el = document.getElementById("log");
      if (el) {
        el.textContent += msg + "\n";
        el.scrollTop = el.scrollHeight;
      }
    },

    /** @param {string} sid */
    rememberSessionId(sid) {
      if (sid) sessionStorage.setItem(this.storageKey, sid);
      else sessionStorage.removeItem(this.storageKey);
    },

    /** @param {string} sid */
    releaseBeacon(sid) {
      if (!sid) return;
      try {
        navigator.sendBeacon(`${this.apiBase}/sessions/${sid}/release`, "");
      } catch (_) {
        /* ignore */
      }
    },

    /** @param {string} [sid] */
    async releaseAsync(sid) {
      const id = sid || this.sessionId;
      if (!id) return;
      await this.api(`/sessions/${id}/release`, { method: "POST" }).catch(() => {});
      if (id === this.sessionId) {
        this.sessionId = "";
        this.rememberSessionId("");
      }
    },

    async cleanupStaleSession() {
      const prev = sessionStorage.getItem(this.storageKey);
      if (!prev) return;
      this.log("检测到上次未释放会话 · 清理 workspace 副本…");
      await this.releaseAsync(prev);
      sessionStorage.removeItem(this.storageKey);
    },

    /**
     * @param {Record<string, unknown>} spec
     */
    applyThemeFromSpec(spec) {
      const colors = /** @type {Record<string, string>} */ (spec.colors || {});
      const theater = /** @type {Record<string, string>} */ (spec.theater || {});
      const root = document.documentElement;
      const map = {
        "--bg": colors.background,
        "--surface": colors.surface,
        "--code-bg": colors.code_bg || theater.background,
        "--panel-border": colors.panel_border,
        "--text": colors.text,
        "--muted": colors.muted,
        "--accent": colors.accent,
        "--accent-light": colors.accent_light,
        "--highlight": colors.highlight,
        "--keyword": colors.keyword || theater.keyword_color,
        "--string": colors.string || theater.string_color,
        "--success": colors.success,
        "--danger": colors.danger,
        "--theater-bg": theater.background || colors.code_bg,
      };
      for (const [key, val] of Object.entries(map)) {
        if (val) root.style.setProperty(key, String(val));
      }
    },

    configure(spec) {
      this.spec = spec;
      if (spec.api_base) this.apiBase = String(spec.api_base);
      if (spec.session_storage_key) this.storageKey = String(spec.session_storage_key);
      this.applyThemeFromSpec(spec);
    },

    async loadSpec() {
      const base = "../../config/kiosk_edu_spec.json";
      try {
        const res = await fetch(base);
        if (res.ok) {
          this.spec = await res.json();
          this.configure(this.spec);
        }
      } catch (_) {
        this.log("TODO: 无法加载 kiosk_edu_spec.json · 使用内置默认值");
      }
    },

    async verifyBootstrap() {
      const report = await this.api("/bootstrap");
      if (!report.ready) {
        const errs = (report.template_validation?.errors || [])
          .map((/** @type {{slug:string,error:string}} */ e) => `${e.slug}: ${e.error}`)
          .join("; ");
        throw new Error(
          `展厅初始化未通过 · ${errs || report.messages?.join("; ") || "模板校验失败"}`
        );
      }
      const removed = report.orphan_workspaces_removed || [];
      if (removed.length > 0) {
        this.log(`已清理 ${removed.length} 个孤立 workspace`);
      }
      return report;
    },

    async createSession() {
      const data = await this.api("/sessions", { method: "POST", body: "{}" });
      this.sessionId = data.session_id || data.id || "";
      this.rememberSessionId(this.sessionId);
      return this.sessionId;
    },

    async bootstrap() {
      await this.loadSpec();
      await this.cleanupStaleSession();
      try {
        await this.verifyBootstrap();
        await this.createSession();
        this.ready = true;
        this.log(`✓ B0 就绪 · session=${this.sessionId.slice(0, 8)}… · API ${this.apiBase}`);
      } catch (err) {
        this.ready = false;
        this.log(`✗ B0 失败: ${err.message}`);
        this.log("TODO: 启动 backend 后刷新 · 运行 .\\05-工具脚本\\run_backend.ps1 · GET /bootstrap");
        this.log("⚠ 演示模式：可逐步切换 UI · API 调用将 fallback");
        this.sessionId = "demo-" + Date.now().toString(36);
        this.rememberSessionId(this.sessionId);
        throw err;
      }
    },

    bindLifecycle() {
      window.addEventListener("pagehide", () => {
        if (this.sessionId) this.releaseBeacon(this.sessionId);
      });
      window.addEventListener("beforeunload", () => {
        if (this.sessionId) this.releaseBeacon(this.sessionId);
      });
    },
  };

  EduSession.bindLifecycle();
  window.EduSession = EduSession;
})();
