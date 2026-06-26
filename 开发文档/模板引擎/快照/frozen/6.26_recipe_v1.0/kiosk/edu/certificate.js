/* B6/B7 · 作品登记证书 · 配方摘要 + 打印 */
(() => {
  "use strict";

  const DEFAULT_TITLE = "AI 小游戏创作工坊 · 作品登记证书";
  const DEFAULT_FOOTER = "GameForge K12 · 文三路 AI 馆";

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

  /** @returns {{title:string,footer:string,btnPrint:string,btnContinue:string}} */
  function copyFromSpec() {
    const cert = /** @type {Record<string,string>|undefined} */ (
      window.EduSession?.spec?.certificate
    );
    return {
      title: cert?.title || DEFAULT_TITLE,
      footer: cert?.footer || DEFAULT_FOOTER,
      btnPrint: cert?.btn_print || "打印证书",
      btnContinue: cert?.btn_continue || "继续试玩",
    };
  }

  /**
   * @param {{
   *   displayName: string,
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
        <div class="edu-certificate-bg" aria-hidden="true"></div>
        <div class="edu-cert-neon-grid" aria-hidden="true"></div>
        <div class="edu-cert-scanlines" aria-hidden="true"></div>
        <div class="edu-cert-glow edu-cert-glow--cyan" aria-hidden="true"></div>
        <div class="edu-cert-glow edu-cert-glow--magenta" aria-hidden="true"></div>
        ${corners}
        <div class="edu-cert-pixels" aria-hidden="true">${pixels}</div>
        <div class="edu-certificate-sparkles" aria-hidden="true">${sparkles}</div>
        <div class="edu-certificate-content">
          <div class="edu-certificate-ribbon">
            <span class="edu-certificate-ribbon-icon" aria-hidden="true">🏆</span>
            <span class="edu-certificate-ribbon-text">LEVEL UP · 小创作者成就证</span>
          </div>
          <header class="edu-certificate-header">
            <p class="edu-certificate-kicker">▶ GAME FORGE K12 ◀</p>
            <h2 class="edu-certificate-title" id="edu-certificate-title">${escapeHtml(copy.title)}</h2>
            <p class="edu-certificate-tagline">专属游戏配方已锁定 · 值得打印留念</p>
          </header>
          <div class="edu-certificate-hero">
            <div class="edu-certificate-medal" aria-hidden="true">
              <span class="edu-certificate-medal-glow"></span>
              <span class="edu-certificate-medal-ring"></span>
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

  /** @returns {HTMLElement} */
  function ensureOverlayRoot() {
    let overlay = document.getElementById("edu-certificate-overlay");
    if (overlay) return overlay;

    overlay = document.createElement("div");
    overlay.id = "edu-certificate-overlay";
    overlay.className = "edu-certificate-overlay";
    overlay.hidden = true;
    overlay.innerHTML = `
      <div class="edu-certificate-backdrop" data-cert-dismiss aria-hidden="true"></div>
      <div class="edu-certificate-dialog" role="dialog" aria-modal="true" aria-labelledby="edu-certificate-title">
        <div id="edu-certificate" class="edu-certificate"></div>
        <div class="edu-certificate-actions">
          <button type="button" id="btnCertPrint" class="btn btn-primary edu-cert-btn">${escapeHtml(copyFromSpec().btnPrint)}</button>
          <button type="button" id="btnCertContinue" class="btn btn-secondary edu-cert-btn">${escapeHtml(copyFromSpec().btnContinue)}</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);

    overlay.querySelector("#btnCertPrint")?.addEventListener("click", () => {
      openPrint();
    });
    overlay.querySelector("#btnCertContinue")?.addEventListener("click", () => {
      hide();
    });
    overlay.querySelector("[data-cert-dismiss]")?.addEventListener("click", () => {
      hide();
    });

    return overlay;
  }

  /**
   * @param {{
   *   displayName: string,
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
    }
    const copy = copyFromSpec();
    const printBtn = overlay.querySelector("#btnCertPrint");
    const continueBtn = overlay.querySelector("#btnCertContinue");
    if (printBtn) printBtn.textContent = copy.btnPrint;
    if (continueBtn) continueBtn.textContent = copy.btnContinue;
    return overlay;
  }

  function openPrint() {
    document.body.classList.add("edu-printing");
    const cleanup = () => {
      document.body.classList.remove("edu-printing");
      window.removeEventListener("afterprint", cleanup);
    };
    window.addEventListener("afterprint", cleanup);
    window.print();
  }

  function hide() {
    const overlay = document.getElementById("edu-certificate-overlay");
    if (overlay) overlay.hidden = true;
    document.body.classList.remove("edu-printing");
  }

  /**
   * @param {{
   *   displayName?: string,
   *   genreLabel?: string,
   *   genre?: string,
   *   genreEmoji?: string,
   *   sessionId?: string,
   *   rows?: Array<{prompt:string,choice:string}>,
   *   createdAt?: Date,
   *   questions?: Array<{id:string,widget?:string,prompt:string,options?:Array<{id:string,label:string,value?:unknown}>}>,
   *   answers?: Record<string, string|string[]>,
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

    const ctx = {
      displayName: input.displayName || "",
      genreLabel: input.genreLabel || "",
      genreEmoji,
      sessionId: input.sessionId || window.EduSession?.sessionId || "",
      rows,
      createdAt: input.createdAt || new Date(),
    };

    mountOverlay(ctx);
    const overlay = document.getElementById("edu-certificate-overlay");
    if (overlay) overlay.hidden = false;
  }

  window.EduCertificate = {
    buildRecipeRows,
    formatCreatedAt,
    buildCertificateHtml,
    mountOverlay,
    openPrint,
    show,
    hide,
  };
})();
