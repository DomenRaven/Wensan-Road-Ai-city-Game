/* P4-C-7 · 日榜排行榜 · 赛博霓虹弹层 */
(() => {
  "use strict";

  const ALL_GENRES = [
    "platformer",
    "shmup",
    "survivor",
    "pingpong",
    "fighting",
    "parkour",
    "racing",
  ];

  const GENRE_LABELS = {
    platformer: "横版闯关",
    shmup: "街机飞机",
    survivor: "生存升级",
    pingpong: "乒乓球",
    fighting: "格斗对战",
    parkour: "跑酷",
    racing: "欢乐赛车",
  };

  const GENRE_EMOJI = {
    platformer: "🪙",
    shmup: "🚀",
    survivor: "⚔️",
    pingpong: "🏓",
    fighting: "🥊",
    parkour: "🏃",
    racing: "🏎️",
  };

  const RANK_MEDAL = ["🥇", "🥈", "🥉"];

  const SESSION_CACHE_KEY = "edu_leaderboard_session_fallback";

  /** @type {HTMLElement|null} */
  let overlayEl = null;
  /** @type {number|null} */
  let fxTimer = null;

  /** @param {string} text */
  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function configFromSpec() {
    const lb = window.EduSession?.spec?.leaderboard || {};
    const genres = Array.isArray(lb.genres)
      ? lb.genres.filter((g) => ALL_GENRES.includes(g))
      : ALL_GENRES;
    return {
      dailyEnabled: lb.daily_enabled !== false,
      timezone: lb.timezone || "Asia/Shanghai",
      topLimit: Number(lb.top_limit) || 10,
      genres,
    };
  }

  function getLeaderboardGenres() {
    return new Set(configFromSpec().genres);
  }

  /**
   * @param {number} ms
   * @returns {string}
   */
  function formatDuration(ms) {
    const totalSec = Math.max(0, Math.floor(ms / 1000));
    const min = Math.floor(totalSec / 60);
    const sec = totalSec % 60;
    if (min > 0) {
      return `${min}分${String(sec).padStart(2, "0")}秒`;
    }
    return `${sec}秒`;
  }

  /**
   * @param {string} name
   * @returns {number}
   */
  function hashHue(name) {
    let h = 0;
    const text = String(name || "小创作者");
    for (let i = 0; i < text.length; i += 1) {
      h = (h * 31 + text.charCodeAt(i)) >>> 0;
    }
    return h % 360;
  }

  /**
   * @param {string} creatorName
   * @param {number} rank
   * @returns {string}
   */
  function renderAvatar(creatorName, rank) {
    const name = String(creatorName || "小创作者");
    const letter = escapeHtml(name.slice(0, 1) || "创");
    const hue = hashHue(name);
    const hue2 = (hue + 40) % 360;
    const medal = rank >= 1 && rank <= 3 ? RANK_MEDAL[rank - 1] : "";
    return `
      <div class="edu-lb-avatar" style="--av-hue:${hue}; background: linear-gradient(145deg, hsl(${hue} 85% 58%), hsl(${hue2} 80% 42%)); box-shadow: 0 0 16px hsla(${hue}, 85%, 55%, 0.55), inset 0 0 12px rgba(255,255,255,0.25);" aria-hidden="true">
        <span class="edu-lb-avatar-ring"></span>
        <span class="edu-lb-avatar-core">${letter}</span>
        ${medal ? `<span class="edu-lb-avatar-medal">${medal}</span>` : ""}
      </div>`;
  }

  /**
   * @param {string} genre
   * @param {Record<string, unknown>} entry
   * @returns {{ primary: string, secondary: string, tertiary?: string }}
   */
  function formatMetricParts(genre, entry) {
    const score = Number(entry.score) || 0;
    const elapsed = Number(entry.elapsed_ms) || 0;
    const survival = Number(entry.survival_ms) || 0;
    const levelReached = Number(entry.level_reached) || 0;

    switch (genre) {
      case "platformer": {
        if (levelReached > 0) {
          return {
            primary: `第 ${levelReached} 关`,
            secondary: `${score} 分`,
            tertiary: elapsed > 0 ? formatDuration(elapsed) : "",
          };
        }
        return {
          primary: `${score} 分`,
          secondary: elapsed > 0 ? formatDuration(elapsed) : "",
          tertiary: "",
        };
      }
      case "survivor":
        return {
          primary: formatDuration(survival),
          secondary: score > 0 ? `等级 ${score}` : "",
          tertiary: "",
        };
      case "parkour":
        return {
          primary: `${score} 米`,
          secondary: survival > 0 ? formatDuration(survival) : "",
          tertiary: "",
        };
      case "racing":
        return {
          primary: `${score} 圈`,
          secondary: elapsed > 0 ? formatDuration(elapsed) : "",
          tertiary: "",
        };
      case "pingpong":
        return {
          primary: `${score} 分`,
          secondary: score > 0 ? "获胜" : "惜败",
          tertiary: elapsed > 0 ? formatDuration(elapsed) : "",
        };
      case "fighting":
        if (score >= 2) {
          return { primary: "胜利", secondary: "KO!", tertiary: "" };
        }
        if (score === 1) {
          return { primary: "平局", secondary: "", tertiary: "" };
        }
        return { primary: "惜败", secondary: "", tertiary: "" };
      case "shmup":
        if (elapsed > 0 || survival > 0) {
          return {
            primary: `${score} 分`,
            secondary: formatDuration(survival || elapsed),
          };
        }
        return { primary: `${score} 分`, secondary: "" };
      default:
        if (elapsed > 0) {
          return { primary: `${score} 分`, secondary: formatDuration(elapsed) };
        }
        return { primary: `${score} 分`, secondary: "" };
    }
  }

  /**
   * @param {string} genre
   * @param {Record<string, unknown>} entry
   * @returns {string}
   */
  function formatMetric(genre, entry) {
    const parts = formatMetricParts(genre, entry);
    const chunks = [parts.primary, parts.secondary, parts.tertiary].filter(Boolean);
    return chunks.join(" · ");
  }

  /**
   * @param {string} genre
   * @returns {string}
   */
  function defaultMetricForGenre(genre) {
    const map = {
      survivor: "survival_ms",
      parkour: "distance_m",
      racing: "lap_count",
      fighting: "win",
      pingpong: "score",
      shmup: "score",
      platformer: "level_reached",
    };
    return map[genre] || "score";
  }

  /**
   * @param {string} [timezone]
   * @returns {string}
   */
  function formatTodayTitle(timezone) {
    try {
      const parts = new Intl.DateTimeFormat("zh-CN", {
        timeZone: timezone || "Asia/Shanghai",
        year: "numeric",
        month: "numeric",
        day: "numeric",
      }).formatToParts(new Date());
      const y = parts.find((p) => p.type === "year")?.value || "";
      const m = parts.find((p) => p.type === "month")?.value || "";
      const d = parts.find((p) => p.type === "day")?.value || "";
      return `${y}年${m}月${d}日`;
    } catch (_) {
      const now = new Date();
      return `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日`;
    }
  }

  function stopFx() {
    if (fxTimer) {
      window.cancelAnimationFrame(fxTimer);
      fxTimer = null;
    }
  }

  function startFx() {
    stopFx();
    const host = document.getElementById("edu-lb-particles");
    if (!host) return;
    const dots = host.querySelectorAll(".edu-lb-particle");
    if (!dots.length) return;

    const halos = document.querySelectorAll(".edu-lb-glow, .edu-lb-halo");
    let t0 = performance.now();
    const tick = (now) => {
      const t = (now - t0) / 1000;
      dots.forEach((dot, i) => {
        const el = /** @type {HTMLElement} */ (dot);
        const speed = 0.55 + (i % 5) * 0.12;
        const amp = 22 + (i % 4) * 10;
        const y = Math.sin(t * speed + i * 0.7) * amp;
        const x = Math.cos(t * speed * 0.65 + i * 0.55) * amp * 0.75;
        const scale = 0.85 + 0.35 * (0.5 + 0.5 * Math.sin(t * 1.4 + i));
        el.style.transform = `translate(${x}px, ${y}px) scale(${scale})`;
        el.style.opacity = String(0.55 + 0.45 * (0.5 + 0.5 * Math.sin(t * 1.8 + i * 0.9)));
      });
      halos.forEach((node, i) => {
        const el = /** @type {HTMLElement} */ (node);
        const breathe = 1 + Math.sin(t * 0.9 + i * 1.2) * 0.08;
        const drift = Math.sin(t * 0.5 + i) * 12;
        const centered = el.classList.contains("edu-lb-glow--accent");
        const base = centered ? "translateX(-50%) " : "";
        el.style.transform = `${base}scale(${breathe}) translateY(${drift}px)`;
        el.style.opacity = String(0.72 + 0.28 * (0.5 + 0.5 * Math.sin(t * 1.1 + i)));
      });
      fxTimer = window.requestAnimationFrame(tick);
    };
    fxTimer = window.requestAnimationFrame(tick);
  }

  function spawnSparkles() {
    const host = document.getElementById("edu-lb-sparkles");
    if (!host || host.childElementCount > 0) return;
    const frag = document.createDocumentFragment();
    for (let i = 0; i < 14; i += 1) {
      const s = document.createElement("span");
      s.className = "edu-lb-sparkle";
      s.style.setProperty("--sp-left", `${(i * 13 + 4) % 94}%`);
      s.style.setProperty("--sp-delay", `${(i * 0.21).toFixed(2)}s`);
      frag.appendChild(s);
    }
    host.appendChild(frag);
  }

  function spawnParticles() {
    const host = document.getElementById("edu-lb-particles");
    if (!host || host.childElementCount > 0) return;
    const frag = document.createDocumentFragment();
    for (let i = 0; i < 32; i += 1) {
      const p = document.createElement("span");
      p.className = "edu-lb-particle";
      if (i % 3 === 0) p.classList.add("edu-lb-particle--lg");
      if (i % 5 === 0) p.classList.add("edu-lb-particle--spark");
      if (i % 7 === 0) p.classList.add("edu-lb-particle--magenta");
      p.style.left = `${(i * 17 + 8) % 96}%`;
      p.style.top = `${(i * 23 + 5) % 88}%`;
      p.style.animationDelay = `${(i * 0.17).toFixed(2)}s`;
      frag.appendChild(p);
    }
    host.appendChild(frag);
  }

  function ensureOverlay() {
    if (overlayEl) return overlayEl;
    overlayEl = document.createElement("div");
    overlayEl.id = "edu-leaderboard-overlay";
    overlayEl.className = "edu-leaderboard-overlay";
    overlayEl.hidden = true;
    overlayEl.innerHTML = `
      <div class="edu-lb-backdrop" data-lb-dismiss aria-hidden="true"></div>
      <div class="edu-lb-dialog" role="dialog" aria-modal="true" aria-labelledby="edu-leaderboard-title">
        <div id="edu-leaderboard-card" class="edu-lb-card">
          <div class="edu-lb-bg" aria-hidden="true"></div>
          <div class="edu-lb-glow edu-lb-glow--cyan" aria-hidden="true"></div>
          <div class="edu-lb-glow edu-lb-glow--magenta" aria-hidden="true"></div>
          <div class="edu-lb-glow edu-lb-glow--accent" aria-hidden="true"></div>
          <div class="edu-lb-halo" aria-hidden="true"></div>
          <div class="edu-lb-neon-grid" aria-hidden="true"></div>
          <div class="edu-lb-scanlines" aria-hidden="true"></div>
          <div id="edu-lb-particles" class="edu-lb-particles" aria-hidden="true"></div>
          <div id="edu-lb-sparkles" class="edu-lb-sparkles" aria-hidden="true"></div>
          <div class="edu-lb-frame" aria-hidden="true"></div>
          <div class="edu-lb-inner">
            <header class="edu-lb-header">
              <p class="edu-lb-kicker"><span class="edu-lb-kicker-icon">🏆</span> 今日榜单</p>
              <h2 id="edu-leaderboard-title" class="edu-lb-title"></h2>
              <p id="edu-lb-genre-badge" class="edu-lb-genre-badge"></p>
              <div id="edu-leaderboard-tabs" class="edu-lb-tabs" hidden></div>
            </header>
            <div id="edu-leaderboard-body" class="edu-lb-body"></div>
            <p id="edu-leaderboard-note" class="edu-lb-note" hidden></p>
          </div>
        </div>
        <button type="button" id="btnLeaderboardContinue" class="btn edu-lb-continue">继续</button>
      </div>`;
    document.body.appendChild(overlayEl);
    overlayEl.querySelector("[data-lb-dismiss]")?.addEventListener("click", () => {
      close();
    });
    overlayEl.querySelector("#btnLeaderboardContinue")?.addEventListener("click", () => {
      close();
    });
    spawnParticles();
    spawnSparkles();
    return overlayEl;
  }

  /**
   * @param {string} genre
   */
  function applyGenreAccent(genre) {
    const card = document.getElementById("edu-leaderboard-card");
    const badge = document.getElementById("edu-lb-genre-badge");
    if (!card) return;
    const theme = window.EduGenreTheme?.themeFor?.(genre || "");
    const accent = theme?.accent || "#00f5ff";
    const accentLight = theme?.accent_light || "rgba(0, 245, 255, 0.18)";
    card.style.setProperty("--lb-accent", accent);
    card.style.setProperty("--lb-accent-light", accentLight);
    if (badge) {
      badge.textContent = `${GENRE_EMOJI[genre] || "🎮"} ${GENRE_LABELS[genre] || genre}`;
    }
  }

  /**
   * @param {Array<Record<string, unknown>>} entries
   * @param {string} genre
   * @param {string|null} highlightSessionId
   * @param {string|null} highlightCreatedAt
   * @returns {string}
   */
  function renderRows(entries, genre, highlightSessionId, highlightCreatedAt) {
    if (!entries.length) {
      return `<p class="edu-lb-empty">今天还没有记录，再来一局冲榜吧！</p>`;
    }
    const rows = entries
      .map((entry) => {
        const rank = Number(entry.rank) || 0;
        const creator = escapeHtml(String(entry.creator_name || "小创作者"));
        const gameName = escapeHtml(String(entry.display_name || "未命名游戏"));
        const sessionId = String(entry.session_id || "");
        const createdAt = String(entry.created_at || "");
        const highlight =
          (highlightSessionId && sessionId && sessionId === highlightSessionId) ||
          (highlightCreatedAt && createdAt && createdAt === highlightCreatedAt);
        const rankClass = rank <= 3 ? ` edu-lb-row--top${rank}` : "";
        const rankLabel = rank <= 3 ? RANK_MEDAL[rank - 1] : String(rank);
        const metricParts = formatMetricParts(genre, entry);
        const statSecondary = metricParts.secondary
          ? `<span class="edu-lb-stat-secondary">${escapeHtml(metricParts.secondary)}</span>`
          : "";
        const statTertiary = metricParts.tertiary
          ? `<span class="edu-lb-stat-tertiary">${escapeHtml(metricParts.tertiary)}</span>`
          : "";
        return `
          <article class="edu-lb-row${rankClass}${highlight ? " is-highlight" : ""}" data-rank="${rank}">
            <span class="edu-lb-rank">${rankLabel}</span>
            ${renderAvatar(String(entry.creator_name || "小创作者"), rank)}
            <div class="edu-lb-meta">
              <span class="edu-lb-name">${creator}</span>
              <span class="edu-lb-game">《${gameName}》</span>
            </div>
            <div class="edu-lb-stats">
              <span class="edu-lb-stat-primary">${escapeHtml(metricParts.primary)}</span>
              ${statSecondary}
              ${statTertiary}
            </div>
          </article>`;
      })
      .join("");
    return `<div class="edu-lb-table">${rows}</div>`;
  }

  /**
   * @param {string[]} tabGenres
   * @param {string} activeGenre
   * @param {(genre: string) => void} onSelect
   */
  function renderTabs(tabGenres, activeGenre, onSelect) {
    const tabsEl = document.getElementById("edu-leaderboard-tabs");
    if (!tabsEl) return;
    if (!tabGenres || tabGenres.length <= 1) {
      tabsEl.hidden = true;
      tabsEl.innerHTML = "";
      return;
    }
    tabsEl.hidden = false;
    tabsEl.innerHTML = tabGenres
      .map((slug) => {
        const active = slug === activeGenre ? " is-active" : "";
        const emoji = GENRE_EMOJI[slug] || "🎮";
        return `<button type="button" class="edu-lb-tab${active}" data-genre="${slug}">${emoji} ${escapeHtml(GENRE_LABELS[slug] || slug)}</button>`;
      })
      .join("");
    tabsEl.querySelectorAll("[data-genre]").forEach((node) => {
      node.addEventListener("click", () => {
        const slug = node.getAttribute("data-genre");
        if (slug) onSelect(slug);
      });
    });
  }

  /**
   * @param {object} opts
   */
  function open(opts) {
    const cfg = configFromSpec();
    if (!cfg.dailyEnabled) return;

    const genre = opts.genre || "";
    if (!getLeaderboardGenres().has(genre)) return;

    const overlay = ensureOverlay();
    const titleEl = overlay.querySelector("#edu-leaderboard-title");
    const bodyEl = overlay.querySelector("#edu-leaderboard-body");
    const noteEl = overlay.querySelector("#edu-leaderboard-note");
    if (!titleEl || !bodyEl || !noteEl) return;

    const tabGenres = Array.isArray(opts.tabGenres)
      ? opts.tabGenres.filter((g) => getLeaderboardGenres().has(g))
      : cfg.genres;

    applyGenreAccent(genre);
    const dateLabel = formatTodayTitle(cfg.timezone);
    titleEl.textContent = dateLabel;

    renderTabs(tabGenres, genre, (nextGenre) => {
      void openDaily(nextGenre, { keepTabs: true });
    });

    bodyEl.innerHTML = renderRows(
      opts.entries || [],
      genre,
      opts.highlightSessionId || null,
      opts.highlightCreatedAt || null
    );

    if (opts.degraded) {
      noteEl.hidden = false;
      noteEl.textContent = "今日榜单暂不可用，已记录本次成绩。";
    } else {
      noteEl.hidden = true;
      noteEl.textContent = "";
    }

    overlay.hidden = false;
    const accent = window.EduGenreTheme?.themeFor?.(genre || "")?.accent || "#00f5ff";
    const cont = document.getElementById("btnLeaderboardContinue");
    if (cont) {
      cont.style.setProperty("--lb-accent", accent);
    }
    startFx();
    cont?.focus();
  }

  function close() {
    stopFx();
    if (overlayEl) overlayEl.hidden = true;
  }

  /**
   * @param {string} sessionId
   * @returns {Promise<Record<string, unknown>|null>}
   */
  async function fetchRunCompletePayload(sessionId) {
    try {
      const data = await window.EduSession.api(
        `/sessions/${sessionId}/play/actions?since=0`
      );
      const actions = Array.isArray(data.actions) ? data.actions : [];
      for (let i = actions.length - 1; i >= 0; i -= 1) {
        const row = actions[i];
        if (row && row.action_id === "run_complete") {
          return row;
        }
      }
    } catch (_) {
      /* 静默 */
    }
    return null;
  }

  /**
   * @param {object} opts
   */
  async function submitAfterRun(opts) {
    const cfg = configFromSpec();
    if (!cfg.dailyEnabled || !getLeaderboardGenres().has(opts.genre)) {
      return { ok: false, degraded: true, entry: null, entries: [] };
    }

    const payload = opts.runPayload || (await fetchRunCompletePayload(opts.sessionId)) || {};

    if (opts.genre === "pingpong" && !payload.session_end) {
      try {
        const daily = await window.EduSession.api(
          `/leaderboard/${opts.genre}/daily?date=today&limit=${cfg.topLimit}`
        );
        return {
          ok: true,
          degraded: false,
          entry: null,
          entries: daily.entries || [],
          skippedSubmit: true,
        };
      } catch (err) {
        window.EduSession?.log?.(`读取日榜失败 · ${err?.message || err}`);
        return { ok: false, degraded: true, entry: null, entries: [], skippedSubmit: true };
      }
    }

    const body = {
      session_id: opts.sessionId,
      creator_name: opts.creatorName || "",
      display_name: opts.displayName || "",
      score: Number(payload.score) || 0,
      elapsed_ms: Number(payload.elapsed_ms) || 0,
      survival_ms: Number(payload.survival_ms) || 0,
      level_reached: Number(payload.level_reached) || 0,
      metric: String(payload.metric || "") || defaultMetricForGenre(opts.genre),
    };

    try {
      const submit = await window.EduSession.api(`/leaderboard/${opts.genre}/entries`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      const daily = await window.EduSession.api(
        `/leaderboard/${opts.genre}/daily?date=today&limit=${cfg.topLimit}`
      );
      return {
        ok: true,
        degraded: false,
        entry: submit.entry || null,
        entries: daily.entries || [],
      };
    } catch (err) {
      window.EduSession?.log?.(`日榜提交失败 · ${err?.message || err}`);
      try {
        sessionStorage.setItem(
          SESSION_CACHE_KEY,
          JSON.stringify({ ...body, genre: opts.genre, cached_at: Date.now() })
        );
      } catch (_) {
        /* ignore */
      }
      return {
        ok: false,
        degraded: true,
        entry: { ...body, creator_name: body.creator_name || "小创作者", rank: 1 },
        entries: [{ ...body, creator_name: body.creator_name || "小创作者", rank: 1 }],
      };
    }
  }

  /**
   * @param {string} [preferredGenre]
   * @param {{keepTabs?: boolean}} [options]
   */
  async function openDaily(preferredGenre, options = {}) {
    const cfg = configFromSpec();
    if (!cfg.dailyEnabled) return;

    const tabGenres = cfg.genres;
    const genre =
      preferredGenre && getLeaderboardGenres().has(preferredGenre)
        ? preferredGenre
        : tabGenres[0] || "platformer";

    try {
      const daily = await window.EduSession.api(
        `/leaderboard/${genre}/daily?date=today&limit=${cfg.topLimit}`
      );
      open({
        genre,
        entries: daily.entries || [],
        tabGenres: options.keepTabs === false ? [] : tabGenres,
      });
    } catch (err) {
      window.EduSession?.log?.(`读取日榜失败 · ${err?.message || err}`);
      open({
        genre,
        entries: [],
        degraded: true,
        tabGenres: options.keepTabs === false ? [] : tabGenres,
      });
    }
  }

  window.EduLeaderboard = {
    get LEADERBOARD_GENRES() {
      return getLeaderboardGenres();
    },
    ALL_GENRES,
    submitAfterRun,
    open,
    openDaily,
    close,
    formatMetric,
  };
})();
