/* B6/B7 · 作品登记证书 · 配方摘要 + PNG 保存 */
(() => {
  "use strict";

  const DEFAULT_SUBTITLE = "AI 小游戏创作工坊 · 作品登记证书";
  const DEFAULT_FOOTER = "GameForge K12 · 文三路 AI 馆";
  const DEFAULT_QR_HINT = "用手机扫描二维码，即可下载证书图片";

  /** @type {string} */
  let lastDisplayName = "证书";
  /** @type {string} */
  let lastSessionId = "";
  /** @type {number} */
  let lastExpiresInSec = 259200;
  /** @type {number|null} */
  let autoFlashTimer = null;
  /** 自动闪现总时长（含淡入淡出） */
  const AUTO_FLASH_MS = 3500;
  /** 淡入 / 淡出各约 0.45s，与 CSS transition 对齐 */
  const FADE_MS = 450;

  /** N-3 · 是否已具备公网扫码下载能力（未配 PUBLIC_API_BASE 则否） */
  function isPublicQrReady() {
    const cert = /** @type {Record<string, unknown>|undefined} */ (
      window.EduSession?.spec?.certificate
    );
    return !!(cert?.ready_for_public_qr || cert?.public_download_base);
  }

  /** 隐藏调试开关（默认关）：?certdebug=1 时允许开发本机另存证书 */
  function isCertDebugEnabled() {
    try {
      return new URLSearchParams(window.location.search).get("certdebug") === "1";
    } catch (_) {
      return false;
    }
  }

  /** @param {string} text */
  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /** @param {string} prompt */
  function trimPromptDash(prompt) {
    return String(prompt || "")
      .replace(/[—–\-]+\s*$/u, "")
      .trim();
  }

  /**
   * @param {Array<{id:string,label:string,value?:unknown}>|undefined} options
   * @param {string|number} raw
   * @returns {string|null}
   */
  function matchOptionLabel(options, raw) {
    if (!options || raw === "" || raw == null) return null;
    const needle = String(raw);
    for (const opt of options) {
      if (opt.id === needle) return opt.label;
      if (opt.value != null && String(opt.value) === needle) return opt.label;
    }
    return null;
  }

  /**
   * @param {Array<{id:string,widget?:string,prompt:string,options?:Array<{id:string,label:string,value?:unknown}>}>} questions
   * @param {Record<string, string|string[]>} answers
   * @returns {Array<{prompt:string,choice:string}>}
   */
  function buildRecipeRows(questions, answers) {
    const rows = [];
    if (!Array.isArray(questions)) return rows;

    for (const question of questions) {
      if (question.widget === "skill_pick" || question.id === "q_skill") continue;

      const qid = question.id;
      const raw = answers[qid];
      if (raw == null || raw === "") continue;

      let choiceLabel = null;
      if (Array.isArray(raw)) {
        if (raw.length === 0) continue;
        choiceLabel = matchOptionLabel(question.options, raw[0]);
      } else {
        choiceLabel = matchOptionLabel(question.options, raw);
      }

      rows.push({
        prompt: trimPromptDash(question.prompt),
        choice: choiceLabel || "已选择",
      });
    }

    if (rows.length < 3) {
      console.warn(
        `[EduCertificate] 配方行不足 3 条（${rows.length}），仍渲染占位`
      );
      while (rows.length < 3) {
        rows.push({ prompt: "—", choice: "—" });
      }
    }

    return rows;
  }

  /**
   * @param {Date} [date]
   * @returns {string}
   */
  function formatCreatedAt(date) {
    const d = date instanceof Date ? date : new Date();
    const y = d.getFullYear();
    const m = d.getMonth() + 1;
    const day = d.getDate();
    const hh = String(d.getHours()).padStart(2, "0");
    const mm = String(d.getMinutes()).padStart(2, "0");
    return `${y}年${m}月${day}日 ${hh}:${mm}`;
  }

  /**
   * @param {string} sessionId
   * @returns {string}
   */
  function sessionFootnote(sessionId) {
    const sid = String(sessionId || "");
    if (sid.length <= 6) return sid;
    return sid.slice(-6);
  }

  /**
   * @param {string} creator
   * @param {string} displayName
   * @returns {string}
   */
  function formatTitle(creator, displayName) {
    const cert = /** @type {Record<string, unknown>|undefined} */ (
      window.EduSession?.spec?.certificate
    );
    const dn = String(displayName || "未命名作品").trim();
    const cr = String(creator || "").trim();

    if (!cr) {
      const fallback = String(cert?.title_fallback || "《{display_name}》诞生啦！");
      return fallback.replace(/\{display_name\}/g, dn);
    }

    let template = String(cert?.title_template || "{creator}的{display_name}！");
    const templates = /** @type {Record<string, string>|undefined} */ (
      cert?.title_templates
    );
    if (templates && typeof templates === "object") {
      template =
        templates.possessive ||
        Object.values(templates)[0] ||
        template;
    }

    return template
      .replace(/\{creator\}/g, cr)
      .replace(/\{display_name\}/g, dn);
  }

  /** @returns {{subtitle:string,footer:string,btnSave:string,btnContinue:string,qrHint:string}} */
  function copyFromSpec() {
    const cert = /** @type {Record<string,string>|undefined} */ (
      window.EduSession?.spec?.certificate
    );
    return {
      subtitle: cert?.subtitle || cert?.title || DEFAULT_SUBTITLE,
      footer: cert?.footer || DEFAULT_FOOTER,
      // N-3 · 主操作改为「扫码下载」，不再引导本机保存
      btnSave: cert?.btn_scan || "📱 扫码下载证书",
      btnContinue: cert?.btn_continue || "继续试玩",
      qrHint: cert?.qr_hint || DEFAULT_QR_HINT,
    };
  }

  /** @param {string} name */
  function sanitizeFilename(name) {
    return String(name || "证书")
      .replace(/[\\/:*?"<>|]/g, "_")
      .trim()
      .slice(0, 40) || "证书";
  }

  /** @returns {Promise<(el: HTMLElement, opts?: object) => Promise<HTMLCanvasElement>>} */
  function loadHtml2Canvas() {
    const existing = /** @type {((el: HTMLElement, opts?: object) => Promise<HTMLCanvasElement>)|undefined} */ (
      window.html2canvas
    );
    if (existing) return Promise.resolve(existing);
    return Promise.reject(new Error("html2canvas not loaded — check vendor/html2canvas.min.js"));
  }

  /** @returns {string} */
  function resolvePublicApiBase() {
    const cert = /** @type {Record<string,string>|undefined} */ (
      window.EduSession?.spec?.certificate
    );
    if (cert?.public_download_base) {
      return String(cert.public_download_base).replace(/\/$/, "");
    }
    if (cert?.qr_download_host) {
      return String(cert.qr_download_host).replace(/\/$/, "");
    }
    const apiBase = window.EduSession?.apiBase || "http://127.0.0.1:8000";
    try {
      const parsed = new URL(apiBase);
      const pageHost = window.location.hostname;
      const host =
        pageHost && pageHost !== "localhost" && pageHost !== "127.0.0.1"
          ? pageHost
          : parsed.hostname;
      const port = parsed.port || "8000";
      return `${parsed.protocol}//${host}:${port}`;
    } catch {
      return apiBase;
    }
  }

  /**
   * @param {string} sessionId
   * @returns {string}
   */
  function buildDownloadUrl(sessionId) {
    const sid = String(sessionId || "").trim();
    return `${resolvePublicApiBase()}/sessions/${sid}/certificate/download`;
  }

  /** @returns {number} */
  function configuredTtlSec() {
    const cert = /** @type {Record<string, unknown>|undefined} */ (
      window.EduSession?.spec?.certificate
    );
    const ttl = Number(cert?.download_ttl_sec);
    return Number.isFinite(ttl) && ttl > 0 ? ttl : 259200;
  }

  /**
   * @param {number} [expiresInSec]
   * @returns {string}
   */
  function formatQrExpiryNote(expiresInSec) {
    const sec = expiresInSec != null && expiresInSec > 0 ? expiresInSec : configuredTtlSec();
    if (sec <= 3600) {
      const mins = Math.max(1, Math.round(sec / 60));
      return `链接约 ${mins} 分钟内有效 · 手机有网即可下载`;
    }
    const hours = Math.max(1, Math.round(sec / 3600));
    return `链接 ${hours} 小时内有效 · 手机有网即可下载`;
  }

  /**
   * @param {Blob} blob
   * @param {string} sessionId
   * @returns {Promise<{url:string, publicReachable:boolean, relayProvider:string|null, expiresInSec:number}>}
   */
  async function uploadCertificatePng(blob, sessionId) {
    const apiBase = window.EduSession?.apiBase || "http://127.0.0.1:8000";
    const res = await fetch(`${apiBase}/sessions/${sessionId}/certificate`, {
      method: "PUT",
      headers: { "Content-Type": "image/png" },
      body: blob,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`${res.status}: ${text}`);
    }
    const data = /** @type {{
      download_url?:string,
      download_path?:string,
      download_token?:string,
      expires_in_sec?:number,
      public_reachable?:boolean,
      relay_provider?:string|null,
    }} */ (await res.json());
    if (data.expires_in_sec != null && data.expires_in_sec > 0) {
      lastExpiresInSec = data.expires_in_sec;
    }
    let url = "";
    if (data.download_url && data.download_url.startsWith("http")) {
      url = data.download_url;
    } else {
      const path =
        data.download_url ||
        data.download_path ||
        (data.download_token ? `/public/certificates/${data.download_token}` : "");
      if (!path) throw new Error("missing download url");
      if (path.startsWith("http")) {
        url = path;
      } else {
        url = `${resolvePublicApiBase()}${path.startsWith("/") ? path : `/${path}`}`;
      }
    }
    const publicReachable =
      data.public_reachable === true ||
      (!!data.relay_provider && !/127\.0\.0\.1|localhost/i.test(url));
    return {
      url,
      publicReachable,
      relayProvider: data.relay_provider || null,
      expiresInSec: lastExpiresInSec,
    };
  }

  function hideQrPanel() {
    const panel = document.getElementById("edu-cert-qr-panel");
    if (panel) panel.hidden = true;
  }

  /**
   * @param {string} downloadUrl
   */
  function showQrPanel(downloadUrl) {
    const panel = document.getElementById("edu-cert-qr-panel");
    const mount = document.getElementById("eduCertQrMount");
    const hint = document.getElementById("eduCertQrHint");
    if (!panel || !mount) return;

    const copy = copyFromSpec();
    if (hint) hint.textContent = copy.qrHint;

    const note = document.getElementById("eduCertQrNote");
    if (note) note.textContent = formatQrExpiryNote(lastExpiresInSec);

    mount.innerHTML = "";
    const QRCodeCtor = /** @type {typeof QRCode|undefined} */ (window.QRCode);
    if (!QRCodeCtor) {
      mount.textContent = downloadUrl;
      panel.hidden = false;
      return;
    }

    /* qrcodejs · 每次重新生成须新建容器 */
    const holder = document.createElement("div");
    holder.className = "edu-cert-qr-code";
    mount.appendChild(holder);
    // eslint-disable-next-line no-new
    new QRCodeCtor(holder, {
      text: downloadUrl,
      width: 220,
      height: 220,
      colorDark: "#0f172a",
      colorLight: "#ffffff",
      correctLevel: QRCodeCtor.CorrectLevel.M,
    });
    panel.hidden = false;
  }

  /**
   * @param {Blob} blob
   * @param {string} filename
   */
  function tryDirectDownload(blob, filename) {
    try {
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      anchor.rel = "noopener";
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.warn("[EduCertificate] direct download skipped", err);
    }
  }

  /**
   * @param {{
   *   displayName: string,
   *   creatorName?: string,
   *   genre?: string,
   *   genreLabel: string,
   *   genreEmoji: string,
   *   sessionId: string,
   *   rows: Array<{prompt:string,choice:string}>,
   *   createdAt: Date|string,
   * }} ctx
   * @returns {string}
   */
  function buildCertificateHtml(ctx) {
    const copy = copyFromSpec();
    const funTitle = formatTitle(ctx.creatorName || "", ctx.displayName || "");
    const created =
      ctx.createdAt instanceof Date
        ? formatCreatedAt(ctx.createdAt)
        : String(ctx.createdAt || formatCreatedAt());
    const foot = sessionFootnote(ctx.sessionId);
    const rowCount = ctx.rows?.length || 0;
    const denseClass = rowCount > 6 ? " edu-certificate--dense" : "";

    const recipeCards = (ctx.rows || [])
      .map(
        (row, index) => `
        <li class="edu-cert-recipe-card" style="--card-i:${index}">
          <span class="edu-cert-recipe-q">${escapeHtml(row.prompt)}</span>
          <span class="edu-cert-recipe-a">${escapeHtml(row.choice)}</span>
        </li>`
      )
      .join("");

    const sparkles = [6, 18, 32, 48, 62, 78, 92]
      .map(
        (left, i) =>
          `<span class="edu-certificate-sparkle" style="--sp-left:${left}%;--sp-delay:${i * 0.35}s"></span>`
      )
      .join("");

    const confetti = ["#00f5ff", "#e879f9", "#facc15", "#4ade80", "#fb7185"]
      .flatMap((color, ci) =>
        [12, 28, 44, 58, 72, 86].map(
          (left, i) =>
            `<span class="edu-cert-confetti" style="--cf-left:${left + (ci % 3) * 2}%;--cf-color:${color};--cf-delay:${(ci * 0.18 + i * 0.12).toFixed(2)}s;--cf-rot:${(ci * 37 + i * 19) % 360}deg"></span>`
        )
      )
      .join("");

    const corners = ["tl", "tr", "bl", "br"]
      .map((pos) => `<span class="edu-cert-corner edu-cert-corner--${pos}" aria-hidden="true"></span>`)
      .join("");

    const pixels = Array.from({ length: 14 }, (_, i) => {
      const top = 8 + ((i * 17) % 82);
      const left = 4 + ((i * 13) % 90);
      return `<span class="edu-cert-pixel" style="--px-top:${top}%;--px-left:${left}%;--px-delay:${i * 0.2}s" aria-hidden="true"></span>`;
    }).join("");

    const orbitIcons = ["✦", "◆", "▲", "✧"]
      .map(
        (icon, i) =>
          `<span class="edu-cert-orbit-icon" style="--orbit-i:${i}" aria-hidden="true">${icon}</span>`
      )
      .join("");

    return `
      <div class="edu-certificate-inner${denseClass}">
        <div class="edu-certificate-frame" aria-hidden="true"></div>
        <div class="edu-certificate-bg" aria-hidden="true"></div>
        <div class="edu-cert-neon-grid" aria-hidden="true"></div>
        <div class="edu-cert-scanlines" aria-hidden="true"></div>
        <div class="edu-cert-glow edu-cert-glow--cyan" aria-hidden="true"></div>
        <div class="edu-cert-glow edu-cert-glow--magenta" aria-hidden="true"></div>
        <div class="edu-cert-glow edu-cert-glow--accent" aria-hidden="true"></div>
        ${corners}
        <div class="edu-cert-pixels" aria-hidden="true">${pixels}</div>
        <div class="edu-certificate-sparkles" aria-hidden="true">${sparkles}</div>
        <div class="edu-cert-confetti-wrap" aria-hidden="true">${confetti}</div>
        <div class="edu-certificate-content">
          <div class="edu-certificate-ribbon">
            <span class="edu-certificate-ribbon-icon" aria-hidden="true">🏆</span>
            <span class="edu-certificate-ribbon-text">LEVEL UP · 小创作者成就证</span>
          </div>
          <header class="edu-certificate-header">
            <p class="edu-certificate-kicker">▶ GAME FORGE K12 ◀</p>
            <h2 class="edu-certificate-title" id="edu-certificate-title">${escapeHtml(funTitle)}</h2>
            <p class="edu-certificate-subtitle">${escapeHtml(copy.subtitle)}</p>
            <p class="edu-certificate-tagline">专属游戏配方已锁定 · 值得保存留念</p>
          </header>
          <div class="edu-certificate-hero">
            <div class="edu-certificate-medal" aria-hidden="true">
              <span class="edu-certificate-medal-halo"></span>
              <span class="edu-certificate-medal-glow"></span>
              <span class="edu-certificate-medal-ring"></span>
              <span class="edu-certificate-medal-core"></span>
              <span class="edu-certificate-emoji">${escapeHtml(ctx.genreEmoji || "🎮")}</span>
              <div class="edu-certificate-orbit">${orbitIcons}</div>
            </div>
            <p class="edu-certificate-work">${escapeHtml(ctx.displayName || "未命名作品")}</p>
            <p class="edu-certificate-genre">
              <span class="edu-certificate-genre-tag">${escapeHtml(ctx.genreLabel || "创意游戏")}</span>
            </p>
          </div>
          <div class="edu-certificate-meta">
            <span class="edu-cert-pill edu-cert-pill--time">🕐 ${escapeHtml(created)}</span>
            ${foot ? `<span class="edu-cert-pill edu-cert-pill--id">🔖 NO.${escapeHtml(foot)}</span>` : ""}
          </div>
          <section class="edu-cert-recipe-section" aria-label="创作配方摘要">
            <h3 class="edu-cert-recipe-heading">
              <span class="edu-cert-recipe-icon" aria-hidden="true">⚡</span>
              创作配方摘要
              <small>你的选择</small>
            </h3>
            <ul class="edu-cert-recipe-grid">${recipeCards}</ul>
          </section>
          <footer class="edu-certificate-footer">
            <div class="edu-certificate-seal" aria-hidden="true">
              <span class="edu-certificate-seal-inner">GF</span>
              <span class="edu-certificate-seal-ring"></span>
            </div>
            <p class="edu-certificate-signoff">${escapeHtml(copy.footer)}</p>
            <p class="edu-certificate-motto">▶ 继续创作，下一张霓虹证书等你来拿！ ◀</p>
          </footer>
        </div>
      </div>`;
  }

  /** @param {HTMLElement} overlay */
  function wireQrPanel(overlay) {
    overlay.querySelector("#btnCertQrClose")?.addEventListener("click", () => {
      hideQrPanel();
    });
  }

  /** @param {HTMLElement} overlay */
  function ensureQrPanel(overlay) {
    if (overlay.querySelector("#edu-cert-qr-panel")) return;
    const copy = copyFromSpec();
    const panel = document.createElement("div");
    panel.id = "edu-cert-qr-panel";
    panel.className = "edu-cert-qr-panel";
    panel.hidden = true;
    panel.innerHTML = `
      <div class="edu-cert-qr-card">
        <p class="edu-cert-qr-title">📱 扫码下载证书</p>
        <div id="eduCertQrMount" class="edu-cert-qr-mount" aria-hidden="true"></div>
        <p id="eduCertQrHint" class="edu-cert-qr-hint">${escapeHtml(copy.qrHint)}</p>
        <p id="eduCertQrNote" class="edu-cert-qr-note">${escapeHtml(formatQrExpiryNote())}</p>
        <button type="button" id="btnCertQrClose" class="btn btn-secondary edu-cert-qr-close">知道了</button>
      </div>`;
    const dialog = overlay.querySelector(".edu-certificate-dialog");
    if (dialog) dialog.appendChild(panel);
    wireQrPanel(overlay);
  }

  /** @returns {HTMLElement} */
  function ensureOverlayRoot() {
    let overlay = document.getElementById("edu-certificate-overlay");
    if (overlay) {
      ensureQrPanel(overlay);
      return overlay;
    }

    const copy = copyFromSpec();
    overlay = document.createElement("div");
    overlay.id = "edu-certificate-overlay";
    overlay.className = "edu-certificate-overlay";
    overlay.hidden = true;
    overlay.innerHTML = `
      <div class="edu-certificate-backdrop" data-cert-dismiss aria-hidden="true"></div>
      <div class="edu-certificate-dialog" role="dialog" aria-modal="true" aria-labelledby="edu-certificate-title">
        <div id="edu-certificate" class="edu-certificate"></div>
        <div class="edu-certificate-actions">
          <button type="button" id="btnCertSave" class="btn btn-primary edu-cert-btn">${escapeHtml(copy.btnSave)}</button>
          <button type="button" id="btnCertContinue" class="btn btn-secondary edu-cert-btn">${escapeHtml(copy.btnContinue)}</button>
        </div>
        <div id="edu-cert-qr-panel" class="edu-cert-qr-panel" hidden>
          <div class="edu-cert-qr-card">
            <p class="edu-cert-qr-title">📱 扫码下载证书</p>
            <div id="eduCertQrMount" class="edu-cert-qr-mount" aria-hidden="true"></div>
            <p id="eduCertQrHint" class="edu-cert-qr-hint">${escapeHtml(copy.qrHint)}</p>
            <p id="eduCertQrNote" class="edu-cert-qr-note">${escapeHtml(formatQrExpiryNote())}</p>
            <button type="button" id="btnCertQrClose" class="btn btn-secondary edu-cert-qr-close">知道了</button>
          </div>
        </div>
      </div>`;
    document.body.appendChild(overlay);

    overlay.querySelector("#btnCertSave")?.addEventListener("click", () => {
      void saveCertificate();
    });
    overlay.querySelector("#btnCertContinue")?.addEventListener("click", () => {
      hide();
    });
    wireQrPanel(overlay);
    overlay.querySelector("[data-cert-dismiss]")?.addEventListener("click", () => {
      hide();
    });

    return overlay;
  }

  /**
   * @param {string} [genre]
   */
  function applyGenreAccent(genre) {
    const card = document.getElementById("edu-certificate");
    if (!card) return;
    const theme = window.EduGenreTheme?.themeFor?.(genre || "");
    const accent = theme?.accent || "#00f5ff";
    const accentLight = theme?.accent_light || "rgba(0, 245, 255, 0.15)";
    card.style.setProperty("--cert-accent", accent);
    card.style.setProperty("--cert-accent-light", accentLight);
  }

  /** N-3 · 展馆扫码下载未开通时的提示（禁止把本机另存当成功主路径） */
  function showQrUnavailableNote(reason) {
    const panel = document.getElementById("edu-cert-qr-panel");
    const mount = document.getElementById("eduCertQrMount");
    const hint = document.getElementById("eduCertQrHint");
    const note = document.getElementById("eduCertQrNote");
    if (!panel || !mount) return;
    mount.innerHTML = `<div class="edu-cert-qr-unavailable" aria-hidden="true">📵</div>`;
    if (hint) {
      hint.textContent = reason || "展馆扫码下载暂未开通";
    }
    if (note) {
      note.textContent =
        "本机调试时手机扫不开 127.0.0.1。请配置 PUBLIC_API_BASE，或确保服务器能访问外网图床中继";
    }
    panel.hidden = false;
  }

  async function saveCertificate() {
    const card = document.getElementById("edu-certificate");
    if (!card) return;

    const copy = copyFromSpec();
    const saveBtn = /** @type {HTMLButtonElement|null} */ (
      document.getElementById("btnCertSave")
    );
    const prevLabel = saveBtn?.textContent || copy.btnSave;
    const sessionId =
      lastSessionId || window.EduSession?.sessionId || "";

    if (!sessionId) {
      window.alert("会话未就绪，请刷新页面后重试");
      return;
    }

    // N-3：未配公网下载地址时不做本机保存，明确提示（隐藏调试开关除外）
    if (!isPublicQrReady() && !isCertDebugEnabled()) {
      showQrUnavailableNote();
      return;
    }

    if (saveBtn) {
      saveBtn.disabled = true;
      saveBtn.textContent = "正在生成…";
    }
    hideQrPanel();

    try {
      const html2canvas = await loadHtml2Canvas();
      const canvas = await html2canvas(card, {
        scale: 2,
        useCORS: true,
        backgroundColor: "#060b1f",
        logging: false,
        allowTaint: true,
        onclone: (doc) => {
          const cloned = doc.getElementById("edu-certificate");
          if (cloned) {
            cloned.style.transform = "none";
            cloned.style.animation = "none";
          }
        },
      });

      const blob = await new Promise((resolve) => {
        canvas.toBlob(resolve, "image/png", 0.92);
      });
      if (!blob) throw new Error("PNG encode failed");

      if (saveBtn) saveBtn.textContent = "正在上传…";
      const uploaded = await uploadCertificatePng(blob, sessionId);

      // 默认仅扫码下载，禁止游客本机另存；仅隐藏调试开关允许本机保存
      if (isCertDebugEnabled()) {
        const filename = `${sanitizeFilename(lastDisplayName)}_证书.png`;
        tryDirectDownload(blob, filename);
      }

      if (!uploaded.publicReachable && !isCertDebugEnabled()) {
        // 本地回落链（127.0.0.1）对手机无意义：明确提示，不弹「生成失败」
        showQrUnavailableNote("图床中继未成功，暂无公网下载链接");
        return;
      }
      showQrPanel(uploaded.url);
    } catch (err) {
      console.error("[EduCertificate] save failed", err);
      const detail = err && err.message ? String(err.message).slice(0, 120) : "";
      window.alert(
        detail
          ? `生成失败：${detail}`
          : "生成失败，请检查网络后重试，或联系老师帮忙"
      );
    } finally {
      if (saveBtn) {
        saveBtn.disabled = false;
        saveBtn.textContent = prevLabel;
      }
    }
  }

  /**
   * @param {{
   *   displayName: string,
   *   creatorName?: string,
   *   genre?: string,
   *   genreLabel: string,
   *   genreEmoji: string,
   *   sessionId: string,
   *   rows: Array<{prompt:string,choice:string}>,
   *   createdAt: Date|string,
   * }} ctx
   */
  function mountOverlay(ctx) {
    const overlay = ensureOverlayRoot();
    const card = document.getElementById("edu-certificate");
    if (card) {
      card.innerHTML = buildCertificateHtml(ctx);
      applyGenreAccent(ctx.genre);
    }
    const copy = copyFromSpec();
    const saveBtn = overlay.querySelector("#btnCertSave");
    const continueBtn = overlay.querySelector("#btnCertContinue");
    if (saveBtn) saveBtn.textContent = copy.btnSave;
    if (continueBtn) continueBtn.textContent = copy.btnContinue;
    return overlay;
  }

  function clearAutoFlash() {
    if (autoFlashTimer) {
      window.clearTimeout(autoFlashTimer);
      autoFlashTimer = null;
    }
  }

  function hide() {
    clearAutoFlash();
    const overlay = document.getElementById("edu-certificate-overlay");
    if (overlay) {
      overlay.hidden = true;
      overlay.classList.remove(
        "edu-certificate-overlay--flash",
        "edu-certificate-overlay--in",
        "edu-certificate-overlay--out"
      );
    }
    hideQrPanel();
    document.body.classList.remove("edu-printing");
  }

  /** 淡出后再隐藏（闪现模式） */
  function fadeOutThenHide() {
    const overlay = document.getElementById("edu-certificate-overlay");
    if (!overlay || overlay.hidden) return;
    overlay.classList.remove("edu-certificate-overlay--in");
    overlay.classList.add("edu-certificate-overlay--out");
    autoFlashTimer = window.setTimeout(() => {
      hide();
    }, FADE_MS);
  }

  /**
   * @param {{
   *   displayName?: string,
   *   creatorName?: string,
   *   genreLabel?: string,
   *   genre?: string,
   *   genreEmoji?: string,
   *   sessionId?: string,
   *   rows?: Array<{prompt:string,choice:string}>,
   *   createdAt?: Date,
   *   questions?: Array<{id:string,widget?:string,prompt:string,options?:Array<{id:string,label:string,value?:unknown}>}>,
   *   answers?: Record<string, string|string[]>,
   *   mode?: "full"|"auto_flash",
   * }} input
   */
  function show(input) {
    const questions = input.questions || [];
    const answers = input.answers || {};
    const rows =
      input.rows && input.rows.length
        ? input.rows
        : buildRecipeRows(questions, answers);
    const genreEmoji =
      input.genreEmoji ||
      (input.genre && window.EduB1Intent?.emoji(input.genre)) ||
      "🎮";

    lastDisplayName = input.displayName || "证书";
    lastSessionId = input.sessionId || window.EduSession?.sessionId || "";

    const ctx = {
      displayName: input.displayName || "",
      creatorName: input.creatorName || "",
      genre: input.genre || "",
      genreLabel: input.genreLabel || "",
      genreEmoji,
      sessionId: input.sessionId || window.EduSession?.sessionId || "",
      rows,
      createdAt: input.createdAt || new Date(),
    };

    mountOverlay(ctx);
    const overlay = document.getElementById("edu-certificate-overlay");
    if (!overlay) return;

    clearAutoFlash();
    hideQrPanel();

    const flash = input.mode === "auto_flash";
    overlay.classList.toggle("edu-certificate-overlay--flash", flash);
    const actions = /** @type {HTMLElement|null} */ (
      overlay.querySelector(".edu-certificate-actions")
    );
    // S-B1 · 闪现态：隐藏操作区，淡入→展示→淡出，总时长约 3.5s（不阻断开始试玩）
    if (actions) {
      actions.hidden = flash;
      actions.style.display = flash ? "none" : "";
    }
    overlay.classList.remove("edu-certificate-overlay--out", "edu-certificate-overlay--in");
    overlay.hidden = false;
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => {
        overlay.classList.add("edu-certificate-overlay--in");
      });
    });
    if (flash) {
      const holdMs = Math.max(0, AUTO_FLASH_MS - FADE_MS);
      autoFlashTimer = window.setTimeout(() => {
        fadeOutThenHide();
      }, holdMs);
    }
  }

  window.EduCertificate = {
    buildRecipeRows,
    formatCreatedAt,
    formatTitle,
    buildCertificateHtml,
    mountOverlay,
    saveCertificate,
    show,
    hide,
  };
})();
