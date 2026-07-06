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
      if (!sid || sid.startsWith("demo-")) return;
      try {
        navigator.sendBeacon(`${this.apiBase}/sessions/${sid}/release`, "");
      } catch (_) {
        /* ignore */
      }
    },

    /** @param {string} [sid] */
    async releaseAsync(sid) {
      const id = sid || this.sessionId;
      if (!id || id.startsWith("demo-")) return;
      await this.api(`/sessions/${id}/release`, { method: "POST" }).catch(() => {});
      if (id === this.sessionId) {
        this.sessionId = "";
        this.rememberSessionId("");
      }
    },

    async cleanupStaleSession() {
      const prev = sessionStorage.getItem(this.storageKey);
      if (!prev) return;
      if (prev.startsWith("demo-")) {
        sessionStorage.removeItem(this.storageKey);
        return;
      }
      this.log("检测到上次未释放会话 · 清理 workspace 副本…");
      await this.releaseAsync(prev);
      sessionStorage.removeItem(this.storageKey);
    },

    /**
     * 会话池满（429）时释放最旧的一条非当前会话，腾出名额
     * @returns {Promise<boolean>}
     */
    async recoverSessionPool() {
      try {
        const list = await this.api("/sessions");
        const sessions = /** @type {Array<{session_id:string,created_at?:number}>} */ (
          list.sessions || []
        );
        if (!sessions.length) return false;
        const sorted = [...sessions].sort(
          (a, b) => (a.created_at || 0) - (b.created_at || 0)
        );
        for (const row of sorted) {
          const sid = row.session_id;
          if (!sid || sid === this.sessionId) continue;
          this.log(`会话池已满 · 释放最旧会话 ${sid.slice(0, 8)}…`);
          await this.releaseAsync(sid);
          return true;
        }
      } catch (err) {
        this.log(`会话池恢复失败 · ${/** @type {Error} */ (err).message || err}`);
      }
      return false;
    },

    /**
     * @param {number} [retries]
     * @returns {Promise<Record<string, unknown>>}
     */
    async createSessionWithRecovery(retries = 2) {
      for (let attempt = 0; attempt <= retries; attempt += 1) {
        try {
          return await this.api("/sessions", { method: "POST", body: "{}" });
        } catch (err) {
          const msg = String(/** @type {Error} */ (err).message || err);
          if (!msg.includes("429") || attempt >= retries) throw err;
          const recovered = await this.recoverSessionPool();
          if (!recovered) throw err;
        }
      }
      throw new Error("创建会话失败");
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
      if (spec.api_base) this.apiBase = this.resolveApiBase(String(spec.api_base));
      if (spec.session_storage_key) this.storageKey = String(spec.session_storage_key);
      this.applyThemeFromSpec(spec);
    },

    /**
     * 展馆 LAN：页面用 IP 打开时，API 自动跟同源主机（避免手机/副屏连 127.0.0.1 失败）
     * @param {string} configured
     * @returns {string}
     */
    resolveApiBase(configured) {
      const raw = String(configured || "http://127.0.0.1:8000").replace(/\/$/, "");
      try {
        const parsed = new URL(raw);
        const pageHost = window.location.hostname;
        if (
          pageHost &&
          pageHost !== "localhost" &&
          pageHost !== "127.0.0.1" &&
          pageHost !== parsed.hostname
        ) {
          const port = parsed.port || "8000";
          return `${parsed.protocol}//${pageHost}:${port}`;
        }
        return raw;
      } catch {
        return raw;
      }
    },

    /** @returns {boolean} */
    isDemoSession() {
      return !this.sessionId || this.sessionId.startsWith("demo-");
    },

    /**
     * 写操作前确保后端存在有效 session（404 / demo 时自动重建）
     * @returns {Promise<string>}
     */
    async ensureSession() {
      if (!this.isDemoSession()) {
        try {
          const res = await fetch(`${this.apiBase}/sessions/${this.sessionId}`, {
            headers: { Accept: "application/json" },
          });
          if (res.ok) return this.sessionId;
          if (res.status !== 404) {
            const text = await res.text();
            throw new Error(`${res.status}: ${text}`);
          }
          this.log("会话已失效 · 正在重新建立…");
        } catch (err) {
          if (err instanceof TypeError) {
            throw new Error("无法连接后端 API · 请确认服务已启动");
          }
          if (!String(/** @type {Error} */ (err).message).includes("404")) throw err;
        }
      } else if (this.sessionId?.startsWith("demo-")) {
        this.log("演示模式 · 正在连接后端并建立会话…");
      }

      const data = await this.createSessionWithRecovery();
      this.sessionId = data.session_id || data.id || "";
      if (!this.sessionId) throw new Error("创建会话失败");
      this.rememberSessionId(this.sessionId);
      this.ready = true;
      this.log(`✓ 会话就绪 · ${this.sessionId.slice(0, 8)}…`);
      return this.sessionId;
    },

    /**
     * @param {Record<string, unknown>} report
     */
    applyCertificateDeploy(report) {
      const deploy = /** @type {Record<string, unknown>|undefined} */ (report?.certificate);
      if (!deploy) return;

      const cert = {
        .../** @type {Record<string, unknown>} */ (this.spec.certificate || {}),
      };
      const publicBase = String(deploy.public_download_base || "").trim();
      if (publicBase) {
        cert.public_download_base = publicBase;
        cert.qr_download_host = publicBase;
      }
      const ttl = deploy.download_ttl_sec;
      if (ttl != null) cert.download_ttl_sec = Number(ttl);

      this.spec = { ...this.spec, certificate: cert };
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
      this.applyCertificateDeploy(report);
      return report;
    },

    async createSession() {
      const data = await this.createSessionWithRecovery();
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
