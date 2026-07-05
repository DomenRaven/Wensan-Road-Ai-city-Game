/* B4 · 卡片轮播问卷 · P4-C-4 */

(() => {
  "use strict";

  const FLY_OUT_MS = 280;
  const PICK_PAUSE_MS = 520;
  const PICK_PAUSE_REDUCED_MS = 140;

  /** @type {number} */
  let currentIndex = 0;
  /** @type {boolean} */
  let pickLocked = false;
  /** @type {boolean} */
  let cardTransitioning = false;
  /** @type {Set<number>} */
  let confirmedIndices = new Set();
  /** @type {HTMLElement|null} */
  let rootEl = null;
  /** @type {{questions:Array<{id:string,widget?:string,prompt:string,optional?:boolean,options?:Array<{id:string,label:string}>,skill_ids?:string[]}>}|null} */
  let activeTemplate = null;
  /** @type {string} */
  let activeGenre = "";
  /** @type {Record<string, Array<{id:string,label:string}>>|null} */
  let activeCatalog = null;

  /**
   * @param {string} accent
   * @returns {string}
   */
  function accentStyle(accent) {
    return `--b4-accent:${accent};--b4-accent-light:${accent}22`;
  }

  /** @type {Record<string, Record<string, string>>} */
  const B4_QUESTION_EMOJI = {
    platformer: { q_move: "🏃", q_jump: "⬆️", q_enemy: "👾", q_lives: "❤️", q_coin: "🪙" },
    shmup: { q_speed: "🚀", q_fire_rate: "🔥", q_spawn: "✈️", q_hp: "🛡️", q_enemy_bullet: "💥" },
    survivor: { q_speed: "⚡", q_spawn: "👾", q_duration: "⏳", q_hp: "💖", q_weapon: "⚔️" },
    pingpong: { q_ball: "🏓", q_win: "🏆", q_ai: "🤖", q_paddle: "🎯", q_angle: "📐" },
    fighting: { q_speed: "💨", q_light: "👊", q_ai: "🤖", q_heavy: "💪" },
    parkour: { q_run: "🏃", q_jump: "⬆️", q_obstacle: "🚧", q_gravity: "⬇️", q_coin_gap: "🪙" },
    racing: { q_speed: "🏎️", q_turn: "🔄", q_lap: "🏁", q_time: "⏱️", q_traffic: "🚗" },
  };

  /**
   * @param {string} genre
   * @param {string} questionId
   * @returns {string}
   */
  function getQuestionEmoji(genre, questionId) {
    return B4_QUESTION_EMOJI[genre]?.[questionId] || getGenreEmoji(genre);
  }

  /** @type {Record<string, Record<string, (accent:string)=>string>>} */
  const B4_WIDGET_REGISTRY = {
    platformer: {
      q_move: (accent) => `
        <div class="b4-widget b4-widget-speed-strip" style="${accentStyle(accent)}">
          <div class="b4-speed-track"><span class="b4-speed-pointer"></span></div>
        </div>`,
      q_jump: (accent) => `
        <div class="b4-widget b4-widget-jump-arc" style="${accentStyle(accent)}">
          <svg width="72" height="32" viewBox="0 0 120 48" aria-hidden="true"><path class="b4-jump-path" d="M8,40 Q60,4 112,40"/></svg>
        </div>`,
      q_enemy: (accent) => `
        <div class="b4-widget b4-widget-enemy-march" style="${accentStyle(accent)}">
          <span>👾</span><span>👾</span><span class="dim">👾</span>
        </div>`,
      q_lives: (accent) => `
        <div class="b4-widget b4-widget-heart-row" style="${accentStyle(accent)}">
          <span class="b4-heart on">❤</span><span class="b4-heart on">❤</span><span class="b4-heart on">❤</span>
        </div>`,
      q_coin: (accent) => `
        <div class="b4-widget b4-widget-coin-spin" style="${accentStyle(accent)}"><span class="b4-coin">🪙</span></div>`,
    },
    shmup: {
      q_speed: (accent) => `
        <div class="b4-widget b4-widget-thrust" style="${accentStyle(accent)}">
          <span class="b4-thrust-flame"></span><span class="b4-ship-icon">🚀</span>
        </div>`,
      q_fire_rate: (accent) => `
        <div class="b4-widget b4-widget-bullet-row" style="${accentStyle(accent)}">
          <span></span><span></span><span></span>
        </div>`,
      q_spawn: (accent) => `
        <div class="b4-widget b4-widget-star-drift" style="${accentStyle(accent)}">
          <span>✦</span><span>✦</span><span>✦</span>
        </div>`,
      q_hp: (accent) => `
        <div class="b4-widget b4-widget-shield-bar" style="${accentStyle(accent)}">
          <div class="b4-shield-fill"></div>
        </div>`,
      q_enemy_bullet: (accent) => `
        <div class="b4-widget b4-widget-bullet-rain" style="${accentStyle(accent)}">
          <span></span><span></span><span></span>
        </div>`,
    },
    survivor: {
      q_speed: (accent) => `
        <div class="b4-widget b4-widget-orbit-run" style="${accentStyle(accent)}">
          <span class="b4-orbit-core">⚔️</span>
        </div>`,
      q_spawn: (accent) => `
        <div class="b4-widget b4-widget-mob-wave" style="${accentStyle(accent)}">
          <span>👾</span><span>👾</span><span>👾</span>
        </div>`,
      q_duration: (accent) => `
        <div class="b4-widget b4-widget-hourglass" style="${accentStyle(accent)}">
          <span class="b4-sand-top"></span><span class="b4-sand-bottom"></span>
        </div>`,
      q_hp: (accent) => `
        <div class="b4-widget b4-widget-hp-hearts" style="${accentStyle(accent)}">
          <span>❤</span><span>❤</span><span>❤</span><span class="dim">♡</span>
        </div>`,
      q_weapon: (accent) => `
        <div class="b4-widget b4-widget-weapon-icon" style="${accentStyle(accent)}">
          <span class="b4-weapon-swap">⚔️</span>
        </div>`,
    },
    pingpong: {
      q_ball: (accent) => `
        <div class="b4-widget b4-widget-ball-bounce" style="${accentStyle(accent)}">
          <span class="b4-bounce-ball">🏓</span>
        </div>`,
      q_win: (accent) => `
        <div class="b4-widget b4-widget-score-tick" style="${accentStyle(accent)}">
          <span>11</span><span class="b4-score-sep">:</span><span>9</span>
        </div>`,
      q_ai: (accent) => `
        <div class="b4-widget b4-widget-ai-pulse" style="${accentStyle(accent)}">
          <span>🤖</span>
        </div>`,
      q_paddle: (accent) => `
        <div class="b4-widget b4-widget-paddle" style="${accentStyle(accent)}">
          <span class="b4-paddle-bar"></span><span class="b4-paddle-ball">🏓</span>
        </div>`,
      q_angle: (accent) => `
        <div class="b4-widget b4-widget-angle-arc" style="${accentStyle(accent)}">
          <svg width="48" height="28" viewBox="0 0 48 28" aria-hidden="true"><path d="M4,24 L44,24 M24,24 L40,8" class="b4-angle-line"/></svg>
        </div>`,
    },
    fighting: {
      q_speed: (accent) => `
        <div class="b4-widget b4-widget-dash-lines" style="${accentStyle(accent)}">
          <span></span><span></span><span></span>
        </div>`,
      q_light: (accent) => `
        <div class="b4-widget b4-widget-punch-flash" style="${accentStyle(accent)}"><span>👊</span></div>`,
      q_ai: (accent) => `
        <div class="b4-widget b4-widget-dual-hp" style="${accentStyle(accent)}">
          <div class="b4-hp-bar you"><span></span></div>
          <div class="b4-hp-bar foe"><span></span></div>
        </div>`,
      q_heavy: (accent) => `
        <div class="b4-widget b4-widget-heavy-impact" style="${accentStyle(accent)}">
          <span>💥</span>
        </div>`,
    },
    parkour: {
      q_run: (accent) => `
        <div class="b4-widget b4-widget-lane-scroll" style="${accentStyle(accent)}">
          <div class="b4-lane-lines"></div>
        </div>`,
      q_jump: (accent) => `
        <div class="b4-widget b4-widget-jump-arc" style="${accentStyle(accent)}">
          <svg width="72" height="32" viewBox="0 0 120 48" aria-hidden="true"><path class="b4-jump-path" d="M8,40 Q60,4 112,40"/></svg>
        </div>`,
      q_obstacle: (accent) => `
        <div class="b4-widget b4-widget-obstacle-row" style="${accentStyle(accent)}">
          <span>🚧</span><span>▮</span><span>🚧</span>
        </div>`,
      q_gravity: (accent) => `
        <div class="b4-widget b4-widget-fall-arrow" style="${accentStyle(accent)}">
          <span class="b4-arrow">⬇</span><span class="b4-arrow delay">⬇</span>
        </div>`,
      q_coin_gap: (accent) => `
        <div class="b4-widget b4-widget-coin-trail" style="${accentStyle(accent)}">
          <span>🪙</span><span>🪙</span><span>🪙</span>
        </div>`,
    },
    racing: {
      q_speed: (accent) => `
        <div class="b4-widget b4-widget-speed-gauge" style="${accentStyle(accent)}">
          <span class="b4-gauge-needle"></span>
        </div>`,
      q_turn: (accent) => `
        <div class="b4-widget b4-widget-steer" style="${accentStyle(accent)}">
          <span class="b4-steer-wheel"></span>
        </div>`,
      q_lap: (accent) => `
        <div class="b4-widget b4-widget-lap-flag" style="${accentStyle(accent)}">
          <span>🏁</span><span class="b4-lap-num">3</span>
        </div>`,
      q_time: (accent) => `
        <div class="b4-widget b4-widget-timer-ring" style="${accentStyle(accent)}">
          <svg width="40" height="40" viewBox="0 0 48 48" aria-hidden="true"><circle cx="24" cy="24" r="18" class="b4-timer-ring"/></svg>
          <span class="b4-timer-dot"></span>
        </div>`,
      q_traffic: (accent) => `
        <div class="b4-widget b4-widget-traffic" style="${accentStyle(accent)}">
          <span class="b4-car-dot"></span><span class="b4-car-dot delay"></span><span class="b4-car-dot delay2"></span>
        </div>`,
    },
  };

  /**
   * @returns {boolean}
   */
  function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  /**
   * @param {string} genre
   * @returns {string}
   */
  function getGenreEmoji(genre) {
    const theme = window.EduGenreTheme?.themeFor?.(genre);
    if (theme?.decor) {
      return [...String(theme.decor)][0] || String(theme.decor);
    }
    return window.EduB1Intent?.emoji?.(genre) || "🎮";
  }

  /**
   * @returns {string}
   */
  function sparkleMarkup() {
    const items = [
      { left: "6%", top: "10%", delay: "0s" },
      { left: "88%", top: "14%", delay: "0.4s" },
      { left: "12%", top: "78%", delay: "0.8s" },
      { left: "82%", top: "72%", delay: "1.1s" },
    ];
    return items
      .map(
        (s) =>
          `<span class="b4-card-sparkle" style="left:${s.left};top:${s.top};animation-delay:${s.delay}">✦</span>`
      )
      .join("");
  }

  /**
   * @param {string} genre
   * @returns {string}
   */
  function getAccent(genre) {
    const theme = window.EduGenreTheme?.themeFor?.(genre);
    return theme?.accent || "#2563eb";
  }

  /**
   * @param {string} genre
   * @param {string} questionId
   * @returns {string}
   */
  function renderWidgetHtml(genre, questionId) {
    const accent = getAccent(genre);
    const genreMap = B4_WIDGET_REGISTRY[genre];
    if (!genreMap) return "";
    const fn = genreMap[questionId];
    return fn ? fn(accent) : "";
  }

  /**
   * @returns {number}
   */
  function totalQuestions() {
    return activeTemplate?.questions?.length || 0;
  }

  /**
   * @returns {boolean}
   */
  function isBusy() {
    return pickLocked || cardTransitioning;
  }

  function updateToolbarLock() {
    const busy = isBusy();
    const dualPrev = document.getElementById("btnDualPrev");
    const dualNext = document.getElementById("btnDualNext");
    if (dualPrev) dualPrev.disabled = busy;
    if (dualNext && !dualNext.hidden) dualNext.disabled = busy;
  }

  function setPickLock(locked) {
    pickLocked = locked;
    updateToolbarLock();
  }

  function setCardTransitionLock(locked) {
    cardTransitioning = locked;
    updateToolbarLock();
  }

  function updateProgress() {
    if (!rootEl) return;
    const total = totalQuestions();
    const idx = currentIndex + 1;
    const fill = rootEl.querySelector(".b4-progress-fill");
    const label = rootEl.querySelector(".b4-progress-label");
    const pct = total > 0 ? (confirmedIndices.size / total) * 100 : 0;
    const displayPct = total > 0 ? (idx / total) * 100 : 0;
    if (fill) fill.style.width = `${displayPct}%`;
    if (label) label.textContent = `${idx} / ${total}`;
    const fillConfirmed = rootEl.querySelector(".b4-progress-fill-confirmed");
    if (fillConfirmed) fillConfirmed.style.width = `${pct}%`;
  }

  /**
   * @returns {boolean}
   */
  function isReadyToSubmit() {
    const total = totalQuestions();
    return total > 0
      && confirmedIndices.size >= total
      && currentIndex >= total - 1;
  }

  function syncSubmitButtonVisibility() {
    const btn = document.getElementById("btnDualNext");
    if (!btn) return;
    const show = isReadyToSubmit();
    btn.hidden = !show;
    btn.style.display = show ? "" : "none";
    btn.toggleAttribute("hidden", !show);
    if (show) {
      btn.classList.add("b4-submit-btn--reveal");
      btn.disabled = isBusy();
    } else {
      btn.classList.remove("b4-submit-btn--reveal");
      btn.disabled = false;
    }
  }

  /**
   * @param {number} ms
   * @returns {Promise<void>}
   */
  function pauseMs(ms) {
    return new Promise((resolve) => {
      window.setTimeout(resolve, ms);
    });
  }

  /**
   * @param {MouseEvent|TouchEvent|PointerEvent} ev
   * @returns {{x:number,y:number}|null}
   */
  function pointerFromEvent(ev) {
    if ("changedTouches" in ev && ev.changedTouches.length > 0) {
      const t = ev.changedTouches[0];
      return { x: t.clientX, y: t.clientY };
    }
    if ("clientX" in ev && Number.isFinite(ev.clientX) && Number.isFinite(ev.clientY)) {
      return { x: ev.clientX, y: ev.clientY };
    }
    return null;
  }

  /**
   * @param {HTMLElement} container
   * @param {{x:number,y:number}} point
   * @returns {{x:number,y:number}}
   */
  function pointRelativeTo(container, point) {
    const rect = container.getBoundingClientRect();
    return {
      x: point.x - rect.left,
      y: point.y - rect.top,
    };
  }

  /**
   * @param {HTMLElement} inner
   * @param {HTMLElement} anchorEl
   * @param {{x:number,y:number}|null} pointer
   * @returns {{x:number,y:number}}
   */
  function resolveBurstPoint(inner, anchorEl, pointer) {
    if (pointer) {
      const rel = pointRelativeTo(inner, pointer);
      const pad = 6;
      return {
        x: Math.max(pad, Math.min(inner.clientWidth - pad, rel.x)),
        y: Math.max(pad, Math.min(inner.clientHeight - pad, rel.y)),
      };
    }
    const anchorRect = anchorEl.getBoundingClientRect();
    const innerRect = inner.getBoundingClientRect();
    return {
      x: anchorRect.left + anchorRect.width / 2 - innerRect.left,
      y: anchorRect.top + anchorRect.height / 2 - innerRect.top,
    };
  }

  /**
   * @param {HTMLElement} shell
   * @param {HTMLElement} anchorEl
   * @param {{x:number,y:number}|null} [pointer]
   */
  function playPickFeedback(shell, anchorEl, pointer = null) {
    const inner = shell.querySelector(".b4-card-inner");
    if (!inner) return;

    shell.classList.add("b4-card--celebrate");
    anchorEl.classList.add("b4-option--pop");

    if (prefersReducedMotion()) {
      window.setTimeout(() => {
        shell.classList.remove("b4-card--celebrate");
        anchorEl.classList.remove("b4-option--pop");
      }, PICK_PAUSE_REDUCED_MS);
      return;
    }

    const origin = resolveBurstPoint(inner, anchorEl, pointer);

    const burst = document.createElement("div");
    burst.className = "b4-pick-burst";
    burst.setAttribute("aria-hidden", "true");
    burst.style.left = `${origin.x}px`;
    burst.style.top = `${origin.y}px`;

    const symbols = ["✦", "⭐", "✨", "★", "✦", "⭐", "✨", "★"];
    symbols.forEach((sym, i) => {
      const star = document.createElement("span");
      star.className = "b4-pick-star";
      star.textContent = sym;
      star.style.setProperty("--b4-burst-i", String(i));
      burst.appendChild(star);
    });

    const flash = document.createElement("div");
    flash.className = "b4-pick-flash";
    burst.appendChild(flash);

    inner.appendChild(burst);

    window.setTimeout(() => {
      burst.remove();
      shell.classList.remove("b4-card--celebrate");
      anchorEl.classList.remove("b4-option--pop");
    }, 720);
  }

  /**
   * @param {HTMLElement} shell
   * @param {number} qIndex
   * @returns {Promise<void>}
   */
  async function afterQuestionAnswered(shell, qIndex) {
    confirmedIndices.add(qIndex);
    updateProgress();
    syncSubmitButtonVisibility();

    const pauseDur = prefersReducedMotion() ? PICK_PAUSE_REDUCED_MS : PICK_PAUSE_MS;
    await pauseMs(pauseDur);

    if (qIndex >= totalQuestions() - 1) {
      setPickLock(false);
      return;
    }
    await advanceForward(shell);
  }

  /**
   * @param {boolean} [animateIn]
   * @param {"forward"|"back"} [direction]
   */
  function renderCurrentCard(animateIn = false, direction = "forward") {
    if (!rootEl || !activeTemplate) return;
    const stage = rootEl.querySelector(".b4-card-stage");
    if (!stage) return;

    const q = activeTemplate.questions[currentIndex];
    if (!q) return;

    const creative = window.EduB4Creative;
    const blockHtml = creative.renderQuestionBlock(q, activeCatalog || {}, activeGenre, creative.answers);
    const widgetHtml = renderWidgetHtml(activeGenre, q.id);
    const genreMap = B4_WIDGET_REGISTRY[activeGenre];
    const hasSpecificWidget = !!(genreMap && genreMap[q.id]);
    const widgetType = q.widget || "single_choice";
    const isSkill = widgetType === "skill_pick";
    const isLast = currentIndex >= totalQuestions() - 1;

    const accent = getAccent(activeGenre);
    const emoji = getQuestionEmoji(activeGenre, q.id);

    const shell = document.createElement("div");
    shell.className = "b4-card-shell b4-card--active";
    shell.style.setProperty("--b4-accent", accent);
    if (animateIn && !prefersReducedMotion()) {
      shell.classList.add(direction === "back" ? "b4-card--enter-back" : "b4-card--enter");
    }

    shell.innerHTML = `
      <div class="b4-card">
        <div class="b4-card-inner">
          <div class="b4-card-glow" aria-hidden="true"></div>
          <div class="b4-card-sparkles" aria-hidden="true">${sparkleMarkup()}</div>
          <span class="b4-card-emoji">${emoji}</span>
          ${hasSpecificWidget && widgetHtml ? `<div class="b4-card-widget-wrap">${widgetHtml}</div>` : ""}
          <div class="b4-card-body">${blockHtml}</div>
          ${isSkill ? `<button type="button" class="btn btn-primary b4-card-next-btn">${isLast ? "完成配方" : "下一题"}</button>` : ""}
        </div>
      </div>
    `;

    stage.innerHTML = "";
    stage.appendChild(shell);
    bindCardEvents(shell, q);
    updateProgress();
    syncSubmitButtonVisibility();

    if (animateIn && !prefersReducedMotion()) {
      requestAnimationFrame(() => {
        shell.classList.remove("b4-card--enter", "b4-card--enter-back");
      });
    }
  }

  /**
   * @param {HTMLElement} shell
   * @param {{id:string,widget?:string,optional?:boolean}} q
   */
  function bindCardEvents(shell, q) {
    const creative = window.EduB4Creative;
    const widget = q.widget || "single_choice";
    const qid = q.id;

    if (widget === "single_choice") {
      shell.querySelectorAll(".option-card").forEach((optionCard) => {
        optionCard.addEventListener("click", (ev) => {
          if (isBusy()) return;
          setPickLock(true);
          shell.querySelectorAll(".option-card").forEach((c) => c.classList.remove("selected"));
          optionCard.classList.add("selected");
          const radio = /** @type {HTMLInputElement|null} */ (optionCard.querySelector("input"));
          if (radio) {
            radio.checked = true;
            creative.answers[qid] = radio.value;
          }
          playPickFeedback(shell, optionCard, pointerFromEvent(ev));
          void (async () => {
            try {
              await afterQuestionAnswered(shell, currentIndex);
            } finally {
              setPickLock(false);
              updateToolbarLock();
            }
          })();
        });
      });
      return;
    }

    shell.querySelectorAll(".skill-chip").forEach((chip) => {
      chip.addEventListener("click", () => {
        if (isBusy()) return;
        const skillId = chip.getAttribute("data-skill") || "";
        const current = Array.isArray(creative.answers[qid]) ? [...creative.answers[qid]] : [];
        const idx = current.indexOf(skillId);
        if (idx >= 0) {
          current.splice(idx, 1);
          chip.classList.remove("selected");
        } else if (current.length < 2) {
          current.push(skillId);
          chip.classList.add("selected");
        }
        creative.answers[qid] = current;
      });
    });

    shell.querySelector(".b4-card-next-btn")?.addEventListener("click", (ev) => {
      if (isBusy()) return;
      setPickLock(true);
      const btn = shell.querySelector(".b4-card-next-btn");
      if (btn) playPickFeedback(shell, btn, pointerFromEvent(ev));
      void (async () => {
        try {
          await afterQuestionAnswered(shell, currentIndex);
        } finally {
          setPickLock(false);
          updateToolbarLock();
        }
      })();
    });
  }

  /**
   * @param {HTMLElement} shell
   * @returns {Promise<void>}
   */
  async function advanceForward(shell) {
    if (currentIndex >= totalQuestions() - 1) return;
    await animateTransition(shell, "forward", () => {
      currentIndex += 1;
      renderCurrentCard(true, "forward");
    });
  }

  /**
   * @param {HTMLElement} shell
   * @param {"forward"|"back"} direction
   * @param {() => void} onMid
   * @returns {Promise<void>}
   */
  async function animateTransition(shell, direction, onMid) {
    if (cardTransitioning) return;
    setCardTransitionLock(true);

    if (prefersReducedMotion()) {
      onMid();
      setCardTransitionLock(false);
      syncSubmitButtonVisibility();
      return;
    }

    shell.classList.remove("b4-card--active");
    shell.classList.add(direction === "forward" ? "b4-card--exit" : "b4-card--exit-back");

    await new Promise((resolve) => {
      window.setTimeout(resolve, FLY_OUT_MS);
    });

    onMid();
    setCardTransitionLock(false);
    syncSubmitButtonVisibility();
  }

  const EduB4CardFlow = {
    /**
     * @param {HTMLElement} container
     * @param {{questions:Array<{id:string,widget?:string,prompt:string,optional?:boolean,options?:Array<{id:string,label:string}>,skill_ids?:string[]}>}} template
     * @param {Record<string, string | string[]>} _answers
     * @param {string} genre
     * @param {{catalog?:Record<string, Array<{id:string,label:string}>>}} [_hooks]
     */
    mount(container, template, _answers, genre, _hooks = {}) {
      activeTemplate = template;
      activeGenre = genre;
      activeCatalog = _hooks.catalog || null;
      currentIndex = 0;
      pickLocked = false;
      cardTransitioning = false;
      confirmedIndices = new Set();

      const accent = getAccent(genre);
      container.innerHTML = `
        <div class="creative-form-panel b4-card-flow-root" style="--b4-accent:${accent}">
          <div class="b4-scene-bg" aria-hidden="true">
            <span class="b4-scene-orb b4-scene-orb--a"></span>
            <span class="b4-scene-orb b4-scene-orb--b"></span>
            <span class="b4-scene-orb b4-scene-orb--c"></span>
            <span class="b4-scene-float">✨</span>
            <span class="b4-scene-float delay-1">⭐</span>
            <span class="b4-scene-float delay-2">✦</span>
            <span class="b4-scene-float delay-3">🌟</span>
            <span class="b4-scene-float delay-4">★</span>
          </div>
          <h3 class="b4-flow-title">填写你的创作配方</h3>
          <div class="b4-card-flow">
            <div class="b4-progress-header">
              <div class="b4-progress" aria-hidden="true">
                <div class="b4-progress-fill-confirmed"></div>
                <div class="b4-progress-fill"></div>
              </div>
              <span class="b4-progress-label">1 / ${template.questions.length}</span>
            </div>
            <div class="b4-card-stage"></div>
          </div>
        </div>
      `;

      rootEl = container.querySelector(".b4-card-flow");
      renderCurrentCard(false);
      syncSubmitButtonVisibility();
    },

    syncSubmitButton() {
      syncSubmitButtonVisibility();
    },

    /**
     * @returns {boolean}
     */
    isReadyToSubmit() {
      return isReadyToSubmit();
    },

    /**
     * @returns {boolean}
     */
    canGoPrev() {
      return currentIndex > 0 && !isBusy();
    },

    /**
     * @returns {Promise<void>}
     */
    async prev() {
      if (!this.canGoPrev() || !rootEl) return;
      const shell = rootEl.querySelector(".b4-card-shell");
      if (!shell) return;

      await animateTransition(shell, "back", () => {
        currentIndex -= 1;
        renderCurrentCard(true, "back");
        syncSubmitButtonVisibility();
      });
    },

    /**
     * @returns {number}
     */
    getCurrentIndex() {
      return currentIndex;
    },

    destroy() {
      rootEl = null;
      activeTemplate = null;
      activeCatalog = null;
      currentIndex = 0;
      pickLocked = false;
      cardTransitioning = false;
      confirmedIndices = new Set();
    },
  };

  window.EduB4CardFlow = EduB4CardFlow;
})();
