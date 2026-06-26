/* GameForge K12 · Kiosk wizard v1.0 — 线 A 产品 UI + L0 快速通道 */
(() => {
  "use strict";

  const eduMode = new URLSearchParams(location.search).get("mode");
  if (eduMode && eduMode.toLowerCase() === "edu") {
    location.replace("edu/" + location.hash);
    return;
  }

  const API = "http://127.0.0.1:8000";
  const CONFIG_BASE = "../config";
  const ASSETS_BASE = "../assets";
  const SESSION_STORAGE_KEY = "gameforge_kiosk_session_id";
  const DEFAULT_NAME = "经典试玩";
  const INTENT_STEPS = ["S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7"];
  const SHORTCUT_FLOW = ["S0", "S1", "S9"];
  const SHORTCUT_LABELS = ["起名", "选游戏", "试玩"];
  const SUGGESTED_NAMES = ["星星大冒险", "小明的游戏", "超级闯关", "快乐星球", "太空探险"];
  const FEEL_LABELS = {
    easy: "轻松 — 慢一点、更友好",
    balanced: "平衡 — 默认手感",
    challenge: "挑战 — 更快、更难",
  };
  const STYLE_LABELS = {
    default: "默认明亮",
    cute: "可爱 Q 版",
    cool: "酷感科幻",
  };
  const GENRE_EMOJI = {
    shooter: "🎯",
    fighting: "🥊",
    survivor: "⚔️",
    tower_defense: "🏰",
    parkour: "🏃",
    platformer: "🌟",
    life_sim: "🌾",
    sports_race: "🏅",
    pingpong: "🏓",
    racing: "🏎️",
    shmup: "🚀",
  };
  const DEFAULT_VARIANTS = {
    fighting: { id: "duel", label: "双人对战" },
    survivor: { id: "horde", label: "越变越强" },
    parkour: { id: "endless", label: "无尽跑酷" },
    sports_race: { id: "sprint", label: "计时冲刺" },
    pingpong: { id: "versus", label: "双人对打" },
    shmup: { id: "vertical", label: "纵版射击" },
  };

  /** @type {"shortcut"|"full"} */
  let flowMode = "shortcut";
  /** @type {string[]} */
  let flowSteps = [...SHORTCUT_FLOW];
  /** @type {number} */
  let stepIndex = 0;
  /** @type {string} */
  let sessionId = "";
  /** @type {Array<{slug:string, display_name:string}>} */
  let genres = [];
  /** @type {Record<string, Array<{id:string, label:string, subtitle?:string, redirect_hint?:string}>>} */
  let skillsCatalog = {};
  /** @type {Record<string, string>} */
  let audioPaths = {};
  /** @type {Array<{id:string, label:string, subtitle?:string, redirect_hint?:string}>} */
  let playVariants = [];
  /** @type {string} */
  let selectedGenre = "";
  /** @type {string} */
  let displayName = "";
  /** @type {boolean} */
  let s0Skipped = false;
  /** @type {boolean} */
  let generateDone = false;
  /** @type {boolean} */
  let generateFailed = false;
  /** @type {string} */
  let workspacePath = "";
  /** @type {Record<string, unknown>} */
  let kioskSpec = {};
  /** @type {boolean} */
  let s8Running = false;
  /** @type {boolean} */
  let bootstrapReady = false;

  const el = (id) => document.getElementById(id);
  const logEl = el("log");
  const formEl = el("stepForm");
  const previewEl = el("preview");
  const progressDotsEl = el("progressDots");
  const progressLabelEl = el("progressLabel");
  const stepTitleEl = el("stepTitle");
  const stepSubtitleEl = el("stepSubtitle");
  const workNameEl = el("workName");
  const btnPrev = el("btnPrev");
  const btnNext = el("btnNext");
  const btnSkip = el("btnSkip");
  const btnReset = el("btnReset");
  const btnFullWizard = el("btnFullWizard");

  /** @param {string} msg */
  const log = (msg) => {
    logEl.textContent += msg + "\n";
    logEl.scrollTop = logEl.scrollHeight;
  };

  /** @param {boolean} enabled */
  function setUiEnabled(enabled) {
    bootstrapReady = enabled;
    btnPrev.disabled = !enabled || stepIndex <= 0;
    btnNext.disabled = !enabled;
    btnSkip.disabled = !enabled;
    btnReset.disabled = false;
    btnFullWizard.disabled = !enabled;
    document.body.classList.toggle("kiosk-blocked", !enabled);
  }

  /** @param {string} sid */
  function rememberSessionId(sid) {
    if (sid) sessionStorage.setItem(SESSION_STORAGE_KEY, sid);
    else sessionStorage.removeItem(SESSION_STORAGE_KEY);
  }

  /** @param {string} sid */
  function releaseSessionBeacon(sid) {
    if (!sid) return;
    try {
      navigator.sendBeacon(`${API}/sessions/${sid}/release`, "");
    } catch (_) {
      /* ignore */
    }
  }

  /** @param {string} [sid] */
  async function releaseSessionAsync(sid) {
    const id = sid || sessionId;
    if (!id) return;
    await api(`/sessions/${id}/release`, { method: "POST" }).catch(() => {});
    if (id === sessionId) {
      sessionId = "";
      rememberSessionId("");
    }
  }

  async function cleanupStaleStoredSession() {
    const prev = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (!prev) return;
    log(`检测到上次未释放会话 · 清理 workspace 副本…`);
    await releaseSessionAsync(prev);
    sessionStorage.removeItem(SESSION_STORAGE_KEY);
  }

  async function verifyServerBootstrap() {
    const report = await api("/bootstrap");
    if (!report.ready) {
      const errs = (report.template_validation?.errors || [])
        .map((e) => `${e.slug}: ${e.error}`)
        .join("; ");
      throw new Error(
        `展厅初始化未通过 · ${errs || report.messages?.join("; ") || "模板校验失败"}`
      );
    }
    const removed = report.orphan_workspaces_removed || [];
    if (removed.length > 0) {
      log(`已清理 ${removed.length} 个孤立 workspace（意外退出残留）`);
    }
    log("✓ B 链隔离就绪 · 修改仅写入 workspace 副本 · templates 只读");
    return report;
  }

  /** @param {string} key */
  const playSfx = (key) => {
    const rel = audioPaths[key] || audioPaths.ui_click;
    if (!rel) return;
    const audio = new Audio(`${ASSETS_BASE}/${rel.replace(/^assets\//, "")}`);
    audio.volume = 0.45;
    audio.play().catch(() => {});
  };

  /**
   * @param {string} path
   * @param {RequestInit} [options]
   */
  async function api(path, options = {}) {
    const res = await fetch(`${API}${path}`, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(`${res.status}: ${text}`);
    }
    return res.json();
  }

  async function loadBootstrap() {
    await verifyServerBootstrap();
    const [specRes, genresRes, skillsRes, audioRes] = await Promise.all([
      fetch(`${CONFIG_BASE}/kiosk_ui_spec.json`).then((r) => r.json()).catch(() => ({})),
      api("/genres"),
      fetch(`${CONFIG_BASE}/optional_skills.json`).then((r) => r.json()),
      fetch(`${ASSETS_BASE}/audio_paths.json`).then((r) => r.json()).catch(() => ({})),
    ]);
    kioskSpec = specRes || {};
    const allGenres = genresRes.genres || genresRes;
    const featured = kioskSpec.featured_genres;
    if (featured && Array.isArray(featured.slugs) && featured.slugs.length > 0) {
      const overrides = featured.display_name_overrides || {};
      genres = featured.slugs
        .map((slug) => {
          const g = allGenres.find((x) => x.slug === slug);
          if (!g) return null;
          const label = overrides[slug] || g.display_name || slug;
          return { ...g, display_name: label };
        })
        .filter(Boolean);
    } else {
      genres = allGenres;
    }
    skillsCatalog = skillsRes.catalog || {};
    audioPaths = {
      ui_click: audioRes.kiosk?.click || audioRes.mapping?.ui_click || "",
      ui_button: audioRes.kiosk?.success || audioRes.mapping?.ui_button || "",
      ui_select: audioRes.kiosk?.step || audioRes.mapping?.ui_select || "",
    };
    log(`就绪 · 线 A 快速通道 · 展厅 ${genres.length} 款精选 · 后端 ${API}`);
    setUiEnabled(true);
  }

  /** @returns {string} */
  function currentStepId() {
    return flowSteps[stepIndex] || "";
  }

  function updateWorkNameHeader() {
    const name = displayName || (s0Skipped ? "" : "");
    if (name) {
      workNameEl.textContent = "《" + name + "》";
      workNameEl.classList.remove("empty");
    } else {
      workNameEl.textContent = "给你的游戏起个名字吧";
      workNameEl.classList.add("empty");
    }
  }

  function renderProgressDots() {
    progressDotsEl.innerHTML = "";
    if (flowMode === "shortcut") {
      flowSteps.forEach((stepId, i) => {
        const dot = document.createElement("span");
        dot.className = "progress-dot";
        dot.title = SHORTCUT_LABELS[i] || stepId;
        if (i < stepIndex) dot.classList.add("done");
        else if (i === stepIndex) dot.classList.add("active");
        progressDotsEl.appendChild(dot);
      });
      progressLabelEl.textContent = `步骤 ${stepIndex + 1}/${flowSteps.length} · ${SHORTCUT_LABELS[stepIndex] || ""}`;
      return;
    }
    INTENT_STEPS.forEach((stepId, i) => {
      const dot = document.createElement("span");
      dot.className = "progress-dot";
      dot.title = stepId;
      const current = currentStepId();
      const intentIdx = INTENT_STEPS.indexOf(current);
      if (INTENT_STEPS.includes(current)) {
        if (i < intentIdx) dot.classList.add("done");
        else if (i === intentIdx) dot.classList.add("active");
      }
      progressDotsEl.appendChild(dot);
    });
    const current = currentStepId();
    if (INTENT_STEPS.includes(current)) {
      progressLabelEl.textContent = `进度 ${INTENT_STEPS.indexOf(current) + 1}/8`;
    } else if (current === "R") {
      progressLabelEl.textContent = "★ 配方确认";
    } else if (current === "S8") {
      progressLabelEl.textContent = "AI 制作";
    } else if (current === "S9") {
      progressLabelEl.textContent = "试玩";
    } else {
      progressLabelEl.textContent = current;
    }
  }

  function updateChrome() {
    const stepId = currentStepId();
    renderProgressDots();
    updateWorkNameHeader();

    btnPrev.disabled = !bootstrapReady || stepIndex <= 0;
    btnSkip.hidden = !(flowMode === "shortcut" && stepId === "S0");

    if (stepId === "S9") {
      btnNext.textContent = "完成体验";
      btnNext.className = "btn btn-secondary";
    } else if (stepId === "R") {
      btnNext.textContent = "确认配方";
      btnNext.className = "btn btn-primary";
    } else if (stepId === "S8") {
      btnNext.textContent = s8Running ? "制作中…" : "下一步";
      btnNext.className = "btn btn-primary";
    } else {
      btnNext.textContent = "下一步";
      btnNext.className = "btn btn-primary";
    }
    btnNext.disabled =
      !bootstrapReady ||
      (stepId === "S1" && !selectedGenre) ||
      (stepId === "S8" && (s8Running || (!generateDone && !generateFailed)));
  }

  /** @param {string} slug */
  function previewImageUrl(slug) {
    return `${ASSETS_BASE}/previews/${slug}.png`;
  }

  /** @param {string} slug */
  function updateGenrePreview(slug) {
    if (!slug) {
      previewEl.innerHTML = `<p class="preview-placeholder">选择游戏类型后，这里会显示预览图</p>`;
      return;
    }
    const g = genres.find((x) => x.slug === slug);
    const label = g?.display_name || slug;
    const emoji = GENRE_EMOJI[slug] || "🎮";
    previewEl.innerHTML = `
      <img class="preview-img" src="${previewImageUrl(slug)}" alt="${label}"
           onerror="this.style.display='none'; this.nextElementSibling.style.display='block'"/>
      <span class="emoji-fallback" style="display:none;font-size:4rem">${emoji}</span>
      <p><strong>${label}</strong></p>
      <p class="hint">精选验收版 · 完整创作请走完整向导</p>`;
  }

  async function ensureSession() {
    if (sessionId) return;
    const data = await api("/sessions", { method: "POST" });
    sessionId = data.session_id || data.id;
    rememberSessionId(sessionId);
    log("Session: " + sessionId + " · 独立 workspace 槽位");
  }

  function renderS0() {
    stepTitleEl.textContent = "给你的游戏起个名字";
    stepSubtitleEl.textContent = flowMode === "shortcut"
      ? "可选步骤 · 也可以直接跳过，先选游戏类型"
      : "2–20 字，将在作品卡与试玩标题中显示";
    const chips = SUGGESTED_NAMES.map(
      (n) => `<button type="button" class="chip" data-name="${n}">${n}</button>`
    ).join("");
    formEl.innerHTML = `
      <div class="hint-banner">先体验经典版 · 完整创作请走完整向导</div>
      <input type="text" id="f_name" class="text-input" maxlength="20"
             placeholder="例如：星星大冒险" value="${displayName === DEFAULT_NAME ? "" : displayName}" />
      <div class="chip-row" id="nameChips">${chips}</div>
      <p class="hint">点击上方推荐名字，或自己输入（2–20 字）</p>`;
    const input = el("f_name");
    formEl.querySelectorAll(".chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        playSfx("ui_click");
        input.value = chip.dataset.name || "";
        formEl.querySelectorAll(".chip").forEach((c) => c.classList.remove("selected"));
        chip.classList.add("selected");
      });
    });
    input.addEventListener("input", () => {
      formEl.querySelectorAll(".chip").forEach((c) => c.classList.remove("selected"));
    });
  }

  function renderS1() {
    stepTitleEl.textContent = "选择游戏类型";
    const featured = kioskSpec.featured_genres;
    stepSubtitleEl.textContent =
      (featured && featured.subtitle) ||
      `点选一张卡片 · 共 ${genres.length} 种经典游戏`;
    const cards = genres
      .map((g) => {
        const slug = g.slug;
        const label = g.display_name || slug;
        const emoji = GENRE_EMOJI[slug] || "🎮";
        const selected = selectedGenre === slug ? " selected" : "";
        return `
          <button type="button" class="genre-card${selected}" data-slug="${slug}" aria-pressed="${selectedGenre === slug}">
            <img src="${previewImageUrl(slug)}" alt=""
                 onerror="this.style.display='none'; this.parentElement.querySelector('.emoji-fallback').style.display='block'"/>
            <span class="emoji-fallback" style="display:none">${emoji}</span>
            <span class="genre-label">${label}</span>
          </button>`;
      })
      .join("");
    formEl.innerHTML = `<div class="genre-grid" role="listbox" aria-label="游戏类型">${cards}</div>`;
    formEl.querySelectorAll(".genre-card").forEach((card) => {
      card.addEventListener("click", () => {
        playSfx("ui_click");
        selectedGenre = card.dataset.slug || "";
        formEl.querySelectorAll(".genre-card").forEach((c) => {
          c.classList.toggle("selected", c.dataset.slug === selectedGenre);
          c.setAttribute("aria-pressed", String(c.dataset.slug === selectedGenre));
        });
        updateGenrePreview(selectedGenre);
        updateChrome();
      });
    });
    if (selectedGenre) updateGenrePreview(selectedGenre);
  }

  async function renderS2() {
    stepTitleEl.textContent = "你想怎么玩？";
    stepSubtitleEl.textContent = "选择一种玩法子模式";
    formEl.innerHTML = `<p class="hint">加载玩法子模式…</p>`;
    const genre = selectedGenre || genres[0]?.slug || "platformer";
    const res = await api(`/genres/${genre}/play-variants`);
    playVariants = res.variants || [];
    if (!playVariants.length && DEFAULT_VARIANTS[genre]) {
      playVariants = [{ ...DEFAULT_VARIANTS[genre], subtitle: "默认模式" }];
    }
    const cards = playVariants
      .map(
        (v, i) => `
        <label class="option-card${i === 0 ? " selected" : ""}">
          <input type="radio" name="variant" value="${v.id}" ${i === 0 ? "checked" : ""}/>
          <span>
            <strong>${v.label}</strong>
            <small>${v.subtitle || ""}</small>
            ${v.redirect_hint ? `<em>${v.redirect_hint}</em>` : ""}
          </span>
        </label>`
      )
      .join("");
    formEl.innerHTML = `<div class="option-cards">${cards || "<p>暂无子模式</p>"}</div>`;
    bindOptionCardSelection("variant");
  }

  function renderS3() {
    stepTitleEl.textContent = "选择风格";
    stepSubtitleEl.textContent = "决定游戏的视觉氛围";
    formEl.innerHTML = `
      <div class="option-cards">
        <label class="option-card selected"><input type="radio" name="style" value="default" checked/>
          <span><strong>${STYLE_LABELS.default}</strong></span></label>
        <label class="option-card"><input type="radio" name="style" value="cute"/>
          <span><strong>${STYLE_LABELS.cute}</strong></span></label>
        <label class="option-card"><input type="radio" name="style" value="cool"/>
          <span><strong>${STYLE_LABELS.cool}</strong></span></label>
      </div>
      <label class="hint" style="display:block;margin-top:16px">氛围关键词（可选，逗号分隔）
        <input type="text" id="f_mood" class="text-input" placeholder="快乐, 冒险, 太空" />
      </label>`;
    bindOptionCardSelection("style");
  }

  function renderS4() {
    stepTitleEl.textContent = "创建人物";
    stepSubtitleEl.textContent = "给你的主角起个名字";
    formEl.innerHTML = `
      <label>角色昵称
        <input type="text" id="f_char_name" class="text-input" placeholder="小蓝" maxlength="12"/>
      </label>
      <label style="display:block;margin-top:12px">代表色
        <input type="color" id="f_char_color" value="#38bdf8" style="width:100%;min-height:48px;border:0;background:transparent"/>
      </label>`;
  }

  function renderS5() {
    stepTitleEl.textContent = "创建道具";
    stepSubtitleEl.textContent = "选择想出现在游戏里的道具（可多选）";
    formEl.innerHTML = `
      <div class="option-cards">
        <label class="option-card selected"><input type="checkbox" name="prop" value="star" checked/>
          <span><strong>⭐ 星星</strong></span></label>
        <label class="option-card"><input type="checkbox" name="prop" value="coin"/>
          <span><strong>🪙 金币</strong></span></label>
        <label class="option-card"><input type="checkbox" name="prop" value="heart"/>
          <span><strong>❤️ 爱心</strong></span></label>
        <label class="option-card"><input type="checkbox" name="prop" value="gem"/>
          <span><strong>💎 宝石</strong></span></label>
      </div>`;
  }

  function renderS6() {
    stepTitleEl.textContent = "动作手感";
    stepSubtitleEl.textContent = "选择适合你的难度";
    formEl.innerHTML = `
      <div class="option-cards">
        <label class="option-card"><input type="radio" name="feel" value="easy"/>
          <span><strong>${FEEL_LABELS.easy}</strong></span></label>
        <label class="option-card selected"><input type="radio" name="feel" value="balanced" checked/>
          <span><strong>${FEEL_LABELS.balanced}</strong></span></label>
        <label class="option-card"><input type="radio" name="feel" value="challenge"/>
          <span><strong>${FEEL_LABELS.challenge}</strong></span></label>
      </div>`;
    bindOptionCardSelection("feel");
  }

  function renderS7() {
    stepTitleEl.textContent = "小技能";
    stepSubtitleEl.textContent = "最多选 2 个技能";
    const genre = selectedGenre || "platformer";
    const list = skillsCatalog[genre] || [];
    const items = list
      .map(
        (s) =>
          `<label class="option-card"><input type="checkbox" name="skill" value="${s.id}"/>
            <span><strong>${s.label}</strong><small>${s.desc}</small></span></label>`
      )
      .join("");
    formEl.innerHTML = items || `<p class="hint">该品类暂无预制技能</p>`;
  }

  /** @param {string} name */
  function bindOptionCardSelection(name) {
    formEl.querySelectorAll(`input[name="${name}"]`).forEach((input) => {
      input.addEventListener("change", () => {
        if (input.type === "radio") {
          formEl.querySelectorAll(".option-card").forEach((c) => c.classList.remove("selected"));
          input.closest(".option-card")?.classList.add("selected");
        } else {
          input.closest(".option-card")?.classList.toggle("selected", input.checked);
        }
      });
    });
  }

  async function renderR() {
    stepTitleEl.textContent = "你的创作配方";
    stepSubtitleEl.textContent = "确认无误后进入 AI 制作";
    formEl.innerHTML = `<p class="hint">加载配方…</p>`;
    const recap = await api(`/sessions/${sessionId}/recap`);
    const feel = recap.payload?.tuning?.feel_id || "balanced";
    const skills = (recap.payload?.tuning?.enabled_skills || []).join("、") || "无";
    const props = (recap.payload?.theme?.props || []).join("、") || "默认";
    const g = genres.find((x) => x.slug === recap.genre);
    formEl.innerHTML = `
      <ul class="recap-list">
        <li><span class="label">作品名</span><span class="value">${recap.display_name || "未命名"}</span></li>
        <li><span class="label">游戏类型</span><span class="value">${g?.display_name || recap.genre || "—"}</span></li>
        <li><span class="label">玩法</span><span class="value">${recap.play_variant_id || "默认"}</span></li>
        <li><span class="label">手感</span><span class="value">${FEEL_LABELS[feel] || feel}</span></li>
        <li><span class="label">道具</span><span class="value">${props}</span></li>
        <li><span class="label">技能</span><span class="value">${skills}</span></li>
      </ul>`;
    previewEl.innerHTML = `
      <div class="work-card-preview">
        <h3>${recap.display_name || "未命名"}</h3>
        <p>${g?.display_name || recap.genre || ""}</p>
        <img class="preview-img" src="${previewImageUrl(recap.genre)}" alt=""
             onerror="this.remove()"/>
      </div>`;
  }

  /** @param {string} msg */
  function setS8Status(msg) {
    const statusEl = el("s8Status");
    if (statusEl) statusEl.textContent = msg;
  }

  function renderS8Loading() {
    stepTitleEl.textContent = "AI 正在制作";
    stepSubtitleEl.textContent = "把你的配方写入专属 workspace…";
    formEl.innerHTML = `
      <div class="s8-generating">
        <div class="s8-spinner" aria-hidden="true"></div>
        <p id="s8Status" class="s8-status">准备中…</p>
        <ul class="s8-steps">
          <li id="s8StepRecap">① 确认配方</li>
          <li id="s8StepCopy">② 复制模板</li>
          <li id="s8StepConfig">③ 写入 game_config</li>
          <li id="s8StepDone">④ 完成</li>
        </ul>
      </div>`;
    previewEl.innerHTML = `
      <div class="work-card-preview">
        <h3>${displayName || "你的游戏"}</h3>
        <p>正在生成专属版本…</p>
      </div>`;
  }

  function renderS8Failure(errMsg) {
    generateFailed = true;
    s8Running = false;
    stepTitleEl.textContent = "制作未完成";
    stepSubtitleEl.textContent = "专属版本生成失败，可加载经典版继续体验";
    formEl.innerHTML = `
      <div class="s8-failure">
        <div class="icon">⚠️</div>
        <p class="launch-status err">${errMsg}</p>
        <p class="hint">正在加载经典版 · 使用 templates 预设，不影响试玩</p>
        <button type="button" id="btnLoadClassic" class="btn btn-primary" style="margin-top:16px">
          加载经典版
        </button>
        <button type="button" id="btnRetryGenerate" class="btn btn-secondary" style="margin-top:8px">
          重试制作
        </button>
      </div>`;
    el("btnLoadClassic").onclick = () => {
      playSfx("ui_click");
      launchClassicFallback();
    };
    el("btnRetryGenerate").onclick = () => {
      playSfx("ui_click");
      generateFailed = false;
      runGeneratePipeline();
    };
    updateChrome();
  }

  /** @param {string} stepId */
  function markS8Step(stepId) {
    const ids = ["s8StepRecap", "s8StepCopy", "s8StepConfig", "s8StepDone"];
    ids.forEach((id) => el(id)?.classList.remove("active", "done"));
    const order = ["s8StepRecap", "s8StepCopy", "s8StepConfig", "s8StepDone"];
    const targetIdx = order.indexOf(stepId);
    order.forEach((id, i) => {
      const node = el(id);
      if (!node) return;
      if (i < targetIdx) node.classList.add("done");
      else if (i === targetIdx) node.classList.add("active");
    });
  }

  async function runGeneratePipeline() {
    if (s8Running) return;
    s8Running = true;
    generateFailed = false;
    generateDone = false;
    renderS8Loading();
    updateChrome();

    try {
      await ensureSession();
      setS8Status("正在确认配方…");
      markS8Step("s8StepRecap");

      const session = await api(`/sessions/${sessionId}`);
      if (!session.payload?.recap_confirmed) {
        await api(`/sessions/${sessionId}/recap`, { method: "POST" });
        log("✓ 配方已确认");
      }

      setS8Status("正在复制模板到 workspace…");
      markS8Step("s8StepCopy");

      setS8Status("正在合并 tuning 与技能配置…");
      markS8Step("s8StepConfig");

      const gen = await api(`/sessions/${sessionId}/generate`, { method: "POST" });
      workspacePath = gen.workspace_path || "";
      generateDone = true;
      s8Running = false;

      setS8Status("制作完成！");
      markS8Step("s8StepDone");
      log(`✓ 生成完成 · ${workspacePath}`);
      playSfx("ui_select");

      previewEl.innerHTML = `
        <div class="work-card-preview">
          <h3>${displayName || session.display_name || "你的游戏"}</h3>
          <p style="color:var(--success)">✓ 专属版本已就绪</p>
          <p class="hint">${workspacePath}</p>
        </div>`;

      stepIndex = flowSteps.indexOf("S9");
      if (stepIndex < 0) stepIndex = flowSteps.length - 1;
      await renderStepForm();
    } catch (err) {
      log("✗ 生成失败: " + err.message);
      renderS8Failure(err.message || "生成失败");
    }
  }

  async function launchClassicFallback() {
    try {
      setS8Status?.("正在加载经典版…");
      const statusEl = el("launchStatus");
      const res = await api(`/sessions/${sessionId}/play/launch`, { method: "POST" });
      log(`✓ 经典版已启动 · ${res.project_path}`);
      generateDone = false;
      workspacePath = "";
      stepIndex = flowSteps.indexOf("S9");
      await renderStepForm();
      if (statusEl) {
        statusEl.textContent = `正在加载经典版 · ${res.project_path}`;
        statusEl.className = "hint launch-status ok";
      }
      playSfx("ui_select");
    } catch (err) {
      log("✗ 经典版启动失败: " + err.message);
      renderS8Failure(err.message || "经典版加载失败");
    }
  }

  async function renderS8() {
    if (flowMode !== "full") {
      renderS8Failure("请使用完整创作向导进入 S8");
      return;
    }
    try {
      const session = await api(`/sessions/${sessionId}`);
      if (session.payload?.generate_completed && session.payload?.workspace_path) {
        generateDone = true;
        workspacePath = session.payload.workspace_path;
        displayName = session.display_name || displayName;
        stepIndex = flowSteps.indexOf("S9");
        await renderStepForm();
        return;
      }
    } catch (_) {
      /* continue to generate */
    }
    await runGeneratePipeline();
  }

  async function renderS9() {
    stepTitleEl.textContent = "开始试玩";
    stepSubtitleEl.textContent = "点击大按钮，在本机打开 Godot 游戏窗口";
    let genre = selectedGenre || "platformer";
    let name = displayName || DEFAULT_NAME;
    let useWorkspace = false;
    try {
      const session = await api(`/sessions/${sessionId}`);
      genre = session.genre || genre;
      name = session.display_name || name;
      displayName = name;
      if (flowMode === "full" && session.payload?.generate_completed) {
        useWorkspace = true;
        workspacePath = session.payload.workspace_path || workspacePath;
        generateDone = true;
      }
    } catch (_) {
      /* use local state */
    }
    const g = genres.find((x) => x.slug === genre);
    const banner = useWorkspace
      ? `你的专属版本 · workspace 已就绪`
      : `正在加载经典版 · templates/${genre}/`;
    const pathHint = useWorkspace && workspacePath
      ? `<p class="hint">${workspacePath}</p>`
      : "";
    formEl.innerHTML = `
      <div class="hint-banner">${banner}</div>
      <div class="work-card-preview">
        <h3>🎮 ${name}</h3>
        <p>${g?.display_name || genre}</p>
        ${pathHint}
      </div>
      <button type="button" id="btnLaunchPlay" class="btn btn-success">▶ 启动试玩</button>
      <p id="launchStatus" class="hint launch-status">点击后弹出独立游戏窗口 · 关闭 Godot 即可结束</p>`;
    updateWorkNameHeader();
    if (useWorkspace) {
      previewEl.innerHTML = `
        <div class="work-card-preview">
          <h3>《${name}》</h3>
          <p>${g?.display_name || genre}</p>
          <p class="hint">${workspacePath || `workspace/${sessionId}/`}</p>
        </div>`;
    } else {
      updateGenrePreview(genre);
    }
    el("btnLaunchPlay").onclick = () => launchGodotPlay(genre);
  }

  /**
   * @param {string} genre
   * @param {boolean} [force]
   */
  async function launchGodotPlay(genre, force = false) {
    try {
      playSfx("ui_button");
      const statusEl = el("launchStatus");
      if (statusEl) {
        statusEl.textContent = "正在启动…";
        statusEl.className = "hint launch-status";
      }

      let res = await api(
        `/sessions/${sessionId}/play/launch${force ? "?force=true" : ""}`,
        { method: "POST" }
      );

      if (res.already_running) {
        const st = await api(`/sessions/${sessionId}/play/status`);
        if (!st.running) {
          res = await api(`/sessions/${sessionId}/play/launch?force=true`, { method: "POST" });
        }
      }

      log(`✓ 试玩已启动 pid=${res.pid}`);
      const pathLabel = res.project_path.includes("workspace")
        ? "专属 workspace"
        : "经典版 templates";
      if (statusEl) {
        statusEl.textContent = `${res.message} · ${pathLabel} · PID ${res.pid}`;
        statusEl.className = "hint launch-status ok";
      }
      previewEl.innerHTML = `
        <img class="preview-img" src="${previewImageUrl(genre)}" alt=""
             onerror="this.style.display='none'"/>
        <p style="color:var(--success)">✓ ${res.message}</p>
        <p class="hint">${pathLabel}: ${res.project_path}</p>
        <button type="button" id="btnRelaunch" class="btn btn-secondary" style="margin-top:12px">
          重新打开游戏
        </button>`;
      el("btnRelaunch").onclick = () => launchGodotPlay(genre, true);
      playSfx("ui_select");
    } catch (err) {
      log("✗ 试玩启动失败: " + err.message);
      const statusEl = el("launchStatus");
      if (statusEl) {
        statusEl.textContent = err.message;
        statusEl.className = "hint launch-status err";
      }
    }
  }

  async function renderStepForm() {
    const stepId = currentStepId();
    if (!stepId) return;
    if (stepId === "S0") renderS0();
    else if (stepId === "S1") renderS1();
    else if (stepId === "S2") await renderS2();
    else if (stepId === "S3") renderS3();
    else if (stepId === "S4") renderS4();
    else if (stepId === "S5") renderS5();
    else if (stepId === "S6") renderS6();
    else if (stepId === "S7") renderS7();
    else if (stepId === "R") await renderR();
    else if (stepId === "S8") await renderS8();
    else if (stepId === "S9") await renderS9();
    updateChrome();
  }

  /**
   * @param {string} stepId
   * @returns {Record<string, unknown>}
   */
  function collectStepData(stepId) {
    if (stepId === "S0") {
      const name = el("f_name")?.value.trim() || "";
      if (name.length < 2) throw new Error("游戏名至少 2 个字，或点「跳过」");
      displayName = name;
      return { display_name: name };
    }
    if (stepId === "S1") {
      if (!selectedGenre) throw new Error("请选择游戏类型");
      return { genre: selectedGenre };
    }
    if (stepId === "S2") {
      const picked = formEl.querySelector('input[name="variant"]:checked');
      if (!picked) throw new Error("请选择玩法子模式");
      return { play_variant_id: picked.value };
    }
    if (stepId === "S3") {
      const style = formEl.querySelector('input[name="style"]:checked')?.value || "default";
      const moodRaw = el("f_mood")?.value || "";
      const mood = moodRaw.split(/[,，]/).map((s) => s.trim()).filter(Boolean);
      return { style_pack: style, mood_keywords: mood };
    }
    if (stepId === "S4") {
      return {
        character: {
          name: el("f_char_name")?.value.trim() || "小英雄",
          color: el("f_char_color")?.value || "#38bdf8",
        },
      };
    }
    if (stepId === "S5") {
      const props = [...formEl.querySelectorAll('input[name="prop"]:checked')].map((n) => n.value);
      return { props };
    }
    if (stepId === "S6") {
      const feel = formEl.querySelector('input[name="feel"]:checked')?.value || "balanced";
      return { feel_id: feel };
    }
    if (stepId === "S7") {
      const skills = [...formEl.querySelectorAll('input[name="skill"]:checked')].map((n) => n.value);
      if (skills.length > 2) throw new Error("最多选择 2 个技能");
      return { enabled_skills: skills };
    }
    if (stepId === "R") return {};
    return {};
  }

  /**
   * @param {string} stepId
   * @param {Record<string, unknown>} data
   */
  async function submitStep(stepId, data) {
    return api(`/sessions/${sessionId}/wizard/${stepId}`, {
      method: "POST",
      body: JSON.stringify({ data }),
    });
  }

  function switchToFullFlow() {
    flowMode = "full";
    flowSteps = [...INTENT_STEPS, "R", "S8", "S9"];
    stepIndex = sessionId ? Math.min(stepIndex, flowSteps.length - 1) : 0;
    log("已切换完整创作向导");
    renderStepForm();
  }

  function switchToShortcutFlow() {
    flowMode = "shortcut";
    flowSteps = [...SHORTCUT_FLOW];
    stepIndex = selectedGenre ? flowSteps.indexOf("S9") : flowSteps.indexOf("S0");
    if (stepIndex < 0) stepIndex = 0;
    renderStepForm();
  }

  btnNext.onclick = async () => {
    try {
      playSfx("ui_click");
      const stepId = currentStepId();
      if (!stepId) return;

      if (stepId === "S9") {
        log("试玩阶段完成 · 感谢体验！");
        playSfx("ui_select");
        return;
      }

      if (stepId === "S8") {
        if (generateDone) {
          stepIndex = flowSteps.indexOf("S9");
          await renderStepForm();
        } else if (generateFailed) {
          await launchClassicFallback();
        }
        return;
      }

      if (stepId === "S0" || stepId === "S1") await ensureSession();

      const data = collectStepData(stepId);
      await submitStep(stepId, data);
      log(`✓ ${stepId} 已保存`);

      if (stepId === "S1" && flowMode === "shortcut") {
        stepIndex = flowSteps.indexOf("S9");
      } else if (stepIndex < flowSteps.length - 1) {
        stepIndex += 1;
      }

      await renderStepForm();
      playSfx("ui_select");
    } catch (err) {
      log("✗ " + err.message);
    }
  };

  btnSkip.onclick = async () => {
    try {
      playSfx("ui_click");
      s0Skipped = true;
      displayName = "";
      stepIndex = flowSteps.indexOf("S1");
      if (stepIndex < 0) stepIndex = 1;
      await renderStepForm();
      log("已跳过起名 · 直接进入选游戏");
    } catch (err) {
      log("✗ " + err.message);
    }
  };

  btnPrev.onclick = async () => {
    if (stepIndex > 0) {
      stepIndex -= 1;
      playSfx("ui_click");
      await renderStepForm();
    }
  };

  btnReset.onclick = async () => {
    if (sessionId) {
      await releaseSessionAsync(sessionId);
    }
    stepIndex = 0;
    selectedGenre = "";
    displayName = "";
    s0Skipped = false;
    generateDone = false;
    generateFailed = false;
    workspacePath = "";
    s8Running = false;
    flowMode = "shortcut";
    flowSteps = [...SHORTCUT_FLOW];
    logEl.textContent = "";
    previewEl.innerHTML = `<p class="preview-placeholder">选择游戏类型后，这里会显示预览图</p>`;
    try {
      await ensureSession();
      setUiEnabled(true);
    } catch (_) {
      setUiEnabled(false);
    }
    await renderStepForm();
    log("已重新开始 · 已释放旧会话并分配新 workspace 槽位");
  };

  btnFullWizard.onclick = () => {
    playSfx("ui_click");
    if (flowMode === "full") {
      switchToShortcutFlow();
      btnFullWizard.textContent = "完整创作向导（S0–S9 个性化）";
    } else {
      switchToFullFlow();
      btnFullWizard.textContent = "返回快速试玩通道";
    }
  };

  window.addEventListener("pagehide", () => {
    if (sessionId) releaseSessionBeacon(sessionId);
  });
  window.addEventListener("beforeunload", () => {
    if (sessionId) releaseSessionBeacon(sessionId);
  });

  async function initApp() {
    setUiEnabled(false);
    stepTitleEl.textContent = "正在初始化展厅…";
    stepSubtitleEl.textContent = "校验模板与 workspace 隔离";
    try {
      await cleanupStaleStoredSession();
      await loadBootstrap();
      await renderStepForm();
    } catch (e) {
      stepTitleEl.textContent = "系统未就绪";
      stepSubtitleEl.textContent = "请确认 backend 已启动且 7 款模板完整";
      formEl.innerHTML = `<p class="hint" style="color:var(--danger)">${e.message}</p>`;
      log("✗ 初始化失败: " + e.message);
      setUiEnabled(false);
    }
  }

  initApp();
})();
