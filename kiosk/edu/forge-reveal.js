/* P4-C-3 · B2→B3 揭幕过渡 · 暗屏 + 炫酷卡片 + 烟花 */

(() => {
  "use strict";

  const OVERLAY_ID = "forgeRevealOverlay";
  const SKIP_TIMEOUT_MS = 5000;
  const SPARKLE_CHARS = ["✨", "⭐", "💫", "🌟", "✦"];

  /** @type {boolean} */
  let playing = false;

  /**
   * @param {number} ms
   * @returns {Promise<void>}
   */
  function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * @param {number} ms
   * @param {(t: number) => void} fn
   * @returns {Promise<void>}
   */
  function animate(ms, fn) {
    return new Promise((resolve) => {
      const start = performance.now();
      /** @param {number} now */
      const tick = (now) => {
        const t = Math.min(1, (now - start) / ms);
        fn(t);
        if (t < 1) requestAnimationFrame(tick);
        else resolve();
      };
      requestAnimationFrame(tick);
    });
  }

  /**
   * @param {boolean} blocked
   */
  function setBlocked(blocked) {
    document.body.classList.toggle("forge-reveal-active", blocked);
    if (window.EduWizard?.setUiEnabled) {
      window.EduWizard.setUiEnabled(!blocked);
    } else {
      document.body.classList.toggle("kiosk-blocked", blocked);
    }
    ["btnNext", "btnPrev", "btnDualNext"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.disabled = blocked;
    });
  }

  /**
   * @param {string} template
   * @param {string} creator
   * @param {string} game
   * @returns {string}
   */
  function fillTemplate(template, creator, game) {
    return template
      .replace(/\{creator\}/g, creator)
      .replace(/\{game\}/g, game);
  }

  /**
   * @param {HTMLElement} container
   */
  function mountBackgroundStars(container) {
    container.innerHTML = "";
    for (let i = 0; i < 24; i += 1) {
      const star = document.createElement("span");
      star.className = "forge-reveal-star";
      star.style.left = `${Math.random() * 100}%`;
      star.style.top = `${Math.random() * 100}%`;
      star.style.animationDelay = `${Math.random() * 2}s`;
      star.style.width = `${2 + Math.random() * 4}px`;
      star.style.height = star.style.width;
      container.appendChild(star);
    }
  }

  /**
   * @param {HTMLElement} container
   */
  function mountCardSparkles(container) {
    container.innerHTML = "";
    const positions = [
      [8, 12], [92, 18], [6, 78], [94, 82], [50, 4], [18, 50], [82, 48],
    ];
    positions.forEach(([left, top], i) => {
      const spark = document.createElement("span");
      spark.className = "forge-reveal-sparkle";
      spark.textContent = SPARKLE_CHARS[i % SPARKLE_CHARS.length];
      spark.style.left = `${left}%`;
      spark.style.top = `${top}%`;
      spark.style.animationDelay = `${i * 0.25}s`;
      container.appendChild(spark);
    });
  }

  /**
   * @param {CanvasRenderingContext2D} ctx
   * @param {number} x
   * @param {number} y
   * @param {number} r
   * @param {string} color
   * @param {number} alpha
   */
  function drawStar(ctx, x, y, r, color, alpha) {
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.fillStyle = color;
    ctx.beginPath();
    for (let i = 0; i < 5; i += 1) {
      const angle = (Math.PI * 2 * i) / 5 - Math.PI / 2;
      const outerX = x + Math.cos(angle) * r;
      const outerY = y + Math.sin(angle) * r;
      if (i === 0) ctx.moveTo(outerX, outerY);
      else ctx.lineTo(outerX, outerY);
      const innerAngle = angle + Math.PI / 5;
      ctx.lineTo(x + Math.cos(innerAngle) * r * 0.45, y + Math.sin(innerAngle) * r * 0.45);
    }
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  /**
   * @typedef {{x:number,y:number,px:number,py:number,vx:number,vy:number,life:number,color:string,size:number,kind:'dot'|'star'|'trail'}} Particle
   */

  /**
   * @param {HTMLCanvasElement} canvas
   * @param {number} count
   * @param {string} accent
   * @returns {() => void}
   */
  function startFireworks(canvas, count, accent) {
    const ctx = canvas.getContext("2d");
    if (!ctx) return () => {};

    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);

    /** @type {Particle[]} */
    const particles = [];
    const palette = [accent, "#fbbf24", "#f472b6", "#60a5fa", "#ffffff", "#a855f7", "#34d399"];
    let rafId = 0;
    let nextBurst = performance.now() + 150;
    let burstIndex = 0;
    const burstPoints = [
      [0.5, 0.36], [0.28, 0.28], [0.72, 0.32], [0.4, 0.48], [0.62, 0.44],
    ];

    /** @param {number} cx @param {number} cy @param {number} n */
    function burst(cx, cy, n) {
      for (let i = 0; i < n; i += 1) {
        const angle = (Math.PI * 2 * i) / n + Math.random() * 0.5;
        const speed = 2.8 + Math.random() * 5.5;
        const kind = i % 4 === 0 ? "star" : "dot";
        particles.push({
          x: cx,
          y: cy,
          px: cx,
          py: cy,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          life: 1,
          color: palette[Math.floor(Math.random() * palette.length)],
          size: kind === "star" ? 5 + Math.random() * 4 : 2 + Math.random() * 3,
          kind,
        });
      }
      for (let j = 0; j < 8; j += 1) {
        const angle = Math.random() * Math.PI * 2;
        const speed = 1 + Math.random() * 2;
        particles.push({
          x: cx,
          y: cy,
          px: cx,
          py: cy,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          life: 0.6 + Math.random() * 0.4,
          color: "#ffffff",
          size: 1.5,
          kind: "trail",
        });
      }
    }

    /** @param {number} now */
    const loop = (now) => {
      ctx.clearRect(0, 0, w, h);

      if (now >= nextBurst && burstIndex < burstPoints.length) {
        const [bx, by] = burstPoints[burstIndex];
        burst(w * bx, h * by, count + burstIndex * 2);
        burstIndex += 1;
        nextBurst = now + 380 + Math.random() * 200;
      }

      for (let i = particles.length - 1; i >= 0; i -= 1) {
        const p = particles[i];
        p.px = p.x;
        p.py = p.y;
        p.x += p.vx;
        p.y += p.vy;
        p.vy += p.kind === "trail" ? 0.04 : 0.07;
        p.vx *= 0.985;
        p.life -= p.kind === "trail" ? 0.025 : 0.014;
        if (p.life <= 0) {
          particles.splice(i, 1);
          continue;
        }

        if (p.kind !== "trail") {
          ctx.strokeStyle = p.color;
          ctx.globalAlpha = p.life * 0.35;
          ctx.lineWidth = p.size * 0.6;
          ctx.beginPath();
          ctx.moveTo(p.px, p.py);
          ctx.lineTo(p.x, p.y);
          ctx.stroke();
        }

        if (p.kind === "star") {
          drawStar(ctx, p.x, p.y, p.size, p.color, p.life);
        } else {
          ctx.globalAlpha = p.life;
          ctx.fillStyle = p.color;
          ctx.beginPath();
          ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
          ctx.fill();
          if (p.life > 0.5) {
            ctx.globalAlpha = p.life * 0.3;
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size * 2.5, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }
      ctx.globalAlpha = 1;

      if (particles.length > 0 || burstIndex < burstPoints.length) {
        rafId = requestAnimationFrame(loop);
      }
    };
    rafId = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(rafId);
  }

  /**
   * @param {string} genre
   * @param {Record<string, Record<string, string>>} themes
   * @returns {string}
   */
  function decorEmoji(genre, themes) {
    const decor = themes[genre]?.decor || "";
    if (decor) return decor.slice(0, 2);
    return "🎮";
  }

  /**
   * @param {{creatorName:string,displayName:string,genre:string,genreLabel?:string}} opts
   * @returns {Promise<void>}
   */
  async function play(opts) {
    if (playing) return;
    playing = true;

    const spec = window.EduSession?.spec || {};
    const revealCfg = /** @type {{card_template?:string,firework_count?:number,skip_on_reduced_motion?:boolean}} */ (
      spec.forge_reveal || {}
    );
    const themes = /** @type {Record<string, {accent?:string,decor?:string}>} */ (spec.genre_themes || {});
    const theme = themes[opts.genre] || {};
    const accent = theme.accent || "#2563eb";
    const emoji = decorEmoji(opts.genre, themes);
    const template = revealCfg.card_template || "开始制作{creator}的{game}游戏！";
    const fireworkCount = Math.min(28, Math.max(8, revealCfg.firework_count || 16));
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches
      && revealCfg.skip_on_reduced_motion !== false;

    const cardText = fillTemplate(template, opts.creatorName, opts.displayName);

    /** @type {HTMLElement|null} */
    let overlay = document.getElementById(OVERLAY_ID);
    if (!overlay) {
      overlay = document.createElement("div");
      overlay.id = OVERLAY_ID;
      overlay.className = "forge-reveal-overlay";
      overlay.setAttribute("role", "dialog");
      overlay.setAttribute("aria-modal", "true");
      overlay.innerHTML = `
        <div class="forge-reveal-stars" aria-hidden="true"></div>
        <canvas class="forge-reveal-canvas" aria-hidden="true"></canvas>
        <div class="forge-reveal-card" style="--forge-accent:${accent}">
          <div class="forge-reveal-card-inner">
            <div class="forge-reveal-glow" aria-hidden="true"></div>
            <div class="forge-reveal-sparkles" aria-hidden="true"></div>
            <span class="forge-reveal-emoji"></span>
            <p class="forge-reveal-text"></p>
            <div class="forge-reveal-shine" aria-hidden="true"></div>
          </div>
        </div>`;
      document.body.appendChild(overlay);
    }

    const card = /** @type {HTMLElement} */ (overlay.querySelector(".forge-reveal-card"));
    const textEl = /** @type {HTMLElement} */ (overlay.querySelector(".forge-reveal-text"));
    const emojiEl = /** @type {HTMLElement} */ (overlay.querySelector(".forge-reveal-emoji"));
    const canvas = /** @type {HTMLCanvasElement} */ (overlay.querySelector(".forge-reveal-canvas"));
    const starsEl = /** @type {HTMLElement} */ (overlay.querySelector(".forge-reveal-stars"));
    const sparklesEl = /** @type {HTMLElement} */ (overlay.querySelector(".forge-reveal-sparkles"));

    card.style.setProperty("--forge-accent", accent);
    textEl.textContent = cardText;
    emojiEl.textContent = emoji;
    mountBackgroundStars(starsEl);
    mountCardSparkles(sparklesEl);

    overlay.style.opacity = "0";
    card.style.opacity = "0";
    card.style.transform = "scale(0.85) rotate(-2deg)";
    overlay.hidden = false;

    setBlocked(true);

    /** @type {(() => void)|null} */
    let stopFireworks = null;

    const runSequence = async () => {
      if (reducedMotion) {
        await animate(300, (t) => {
          overlay.style.opacity = String(0.85 * t);
        });
        card.style.opacity = "1";
        card.style.transform = "scale(1) rotate(0deg)";
        await delay(800);
        await animate(300, (t) => {
          overlay.style.opacity = String(0.85 * (1 - t));
          card.style.opacity = String(1 - t);
        });
      } else {
        await animate(400, (t) => {
          overlay.style.opacity = String(0.85 * t);
        });
        await animate(500, (t) => {
          const ease = 1 - Math.pow(1 - t, 3);
          card.style.opacity = String(ease);
          card.style.transform = `scale(${0.85 + 0.15 * ease}) rotate(${-2 + 2 * ease}deg)`;
        });
        stopFireworks = startFireworks(canvas, fireworkCount, accent);
        await delay(1400);
        await animate(400, (t) => {
          card.style.opacity = String(1 - t);
          card.style.transform = `scale(${1 + 0.05 * t}) rotate(0deg)`;
        });
        if (stopFireworks) stopFireworks();
        await animate(600, (t) => {
          overlay.style.opacity = String(0.85 * (1 - t));
        });
      }
    };

    try {
      await Promise.race([
        runSequence(),
        delay(SKIP_TIMEOUT_MS),
      ]);
    } finally {
      if (stopFireworks) stopFireworks();
      overlay.hidden = true;
      overlay.style.opacity = "";
      card.style.opacity = "";
      card.style.transform = "";
      setBlocked(false);
      playing = false;
    }
  }

  window.EduForgeReveal = { play };
})();
