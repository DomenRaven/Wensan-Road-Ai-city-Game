/* B1 · 全屏肥皂泡泡 · UI-C07 · 拖拽 · 碰撞 · K12 */

(() => {
  "use strict";

  /** @type {number|null} */
  let rafId = null;
  /** @type {(() => void)|null} */
  let cleanup = null;

  const CHIP_COLOR_MAP = Object.freeze({
    "马里奥闯关": "#4ade80",
    "我想打飞机": "#60a5fa",
    "割草打怪": "#e879f9",
    "乒乓球": "#34d399",
    "格斗双人": "#f87171",
    "跑酷": "#a78bfa",
    "赛车": "#fb923c",
  });

  const FALLBACK_COLORS = [
    "#4ade80", "#60a5fa", "#e879f9", "#34d399", "#f87171", "#a78bfa", "#fb923c",
  ];

  const BOUNCE = 0.9;
  /** 横屏直径约 152–160px · 竖屏略小仍 ≥128px 儿童触控 */
  const BASE_RADIUS_LANDSCAPE = 76;
  const BASE_RADIUS_PORTRAIT = 80;
  const DRAG_THRESHOLD = 10;

  /** @returns {number} */
  function baseRadius() {
    return document.body.getAttribute("data-orientation") === "portrait"
      ? BASE_RADIUS_PORTRAIT
      : BASE_RADIUS_LANDSCAPE;
  }

  /**
   * @param {string} text
   * @param {number} index
   * @returns {string}
   */
  function colorForChip(text, index) {
    return CHIP_COLOR_MAP[text] || FALLBACK_COLORS[index % FALLBACK_COLORS.length];
  }

  /**
   * @param {string} hex
   * @returns {string}
   */
  function hexToRgb(hex) {
    const raw = hex.replace("#", "");
    const num = parseInt(raw, 16);
    return `${(num >> 16) & 255}, ${(num >> 8) & 255}, ${num & 255}`;
  }

  /** @returns {boolean} */
  function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  /**
   * 全视口（仅避开顶栏）· 工具栏在上层，不裁切泡泡活动区
   * @returns {{ x: number, y: number, width: number, height: number }}
   */
  function getPlayBounds() {
    const header = document.getElementById("eduHeader");
    const top = header ? header.getBoundingClientRect().bottom + 4 : 76;
    let bottom = window.innerHeight - 12;

    const portraitB1 = document.body.classList.contains("edu-step-b1")
      && document.body.getAttribute("data-orientation") === "portrait";
    if (portraitB1) {
      bottom = window.innerHeight - 96;
    }

    const height = Math.max(240, bottom - top);
    return { x: 0, y: top, width: window.innerWidth, height };
  }

  /**
   * @param {string} text
   * @returns {{ slug: string, emoji: string }}
   */
  function bubbleIconMeta(text) {
    const b1 = window.EduB1Intent;
    const slug = b1?.chipGenre?.(text) || "platformer";
    return {
      slug,
      emoji: b1?.emoji?.(slug) || "🎮",
    };
  }

  /**
   * 与证书 `.edu-certificate-medal` 同系 · HTML emoji 奖章（不用本地 PNG）
   * @param {string} emoji
   * @returns {HTMLSpanElement}
   */
  function createBubbleMedal(emoji) {
    const medal = document.createElement("span");
    medal.className = "intent-bubble-medal";
    medal.setAttribute("aria-hidden", "true");

    const glow = document.createElement("span");
    glow.className = "intent-bubble-medal-glow";

    const ring = document.createElement("span");
    ring.className = "intent-bubble-medal-ring";

    const glyph = document.createElement("span");
    glyph.className = "intent-bubble-emoji";
    glyph.textContent = emoji;

    medal.append(glow, ring, glyph);
    return medal;
  }

  /**
   * @param {string} text
   * @param {number} index
   * @param {number} r
   * @returns {HTMLButtonElement}
   */
  function createBubbleButton(text, index, r) {
    const color = colorForChip(text, index);
    const icon = bubbleIconMeta(text);
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "intent-bubble-float";
    btn.style.setProperty("--bubble-color", color);
    btn.style.setProperty("--bubble-rgb", hexToRgb(color));
    btn.style.width = `${r * 2}px`;
    btn.style.height = `${r * 2}px`;

    const aura = document.createElement("span");
    aura.className = "intent-bubble-aura";
    aura.setAttribute("aria-hidden", "true");

    const shine = document.createElement("span");
    shine.className = "intent-bubble-shine";
    shine.setAttribute("aria-hidden", "true");

    const arc = document.createElement("span");
    arc.className = "intent-bubble-arc";
    arc.setAttribute("aria-hidden", "true");

    const content = document.createElement("span");
    content.className = "intent-bubble-content";

    const label = document.createElement("span");
    label.className = "intent-bubble-label";
    label.textContent = text;

    content.appendChild(createBubbleMedal(icon.emoji));
    content.appendChild(label);

    btn.appendChild(aura);
    btn.appendChild(shine);
    btn.appendChild(arc);
    btn.appendChild(content);
    return btn;
  }

  /**
   * @param {HTMLElement} host
   * @param {string[]} chips
   * @param {(text: string) => void} onSelect
   */
  function mountStatic(host, chips, onSelect) {
    host.className = "intent-bubble-field intent-bubble-field--static";
    host.innerHTML = "";

    const grid = document.createElement("div");
    grid.className = "intent-bubble-static-grid";
    grid.setAttribute("role", "group");
    grid.setAttribute("aria-label", "快捷示例泡泡");

    chips.forEach((text, index) => {
      const btn = createBubbleButton(text, index, baseRadius());
      btn.addEventListener("click", () => {
        grid.querySelectorAll(".is-selected").forEach((el) => el.classList.remove("is-selected"));
        btn.classList.add("is-selected");
        onSelect(text);
      });
      grid.appendChild(btn);
    });

    host.appendChild(grid);
    cleanup = () => {
      host.remove();
    };
  }

  /**
   * @typedef {{
   *   text: string,
   *   color: string,
   *   x: number,
   *   y: number,
   *   vx: number,
   *   vy: number,
   *   r: number,
   *   el: HTMLButtonElement,
   * }} Bubble
   */

  /**
   * @param {Bubble[]} bubbles
   * @param {{ x: number, y: number, width: number, height: number }} bounds
   */
  function placeBubbles(bubbles, bounds) {
    const pad = 18;
    const zones = 3;
    const zoneH = bounds.height / zones;

    bubbles.forEach((bubble, index) => {
      const zone = index % zones;
      const yLo = bounds.y + zone * zoneH + bubble.r + pad;
      const yHi = bounds.y + (zone + 1) * zoneH - bubble.r - pad;
      let placed = false;

      for (let attempt = 0; attempt < 120; attempt += 1) {
        bubble.x = bounds.x + bubble.r + pad
          + Math.random() * Math.max(1, bounds.width - bubble.r * 2 - pad * 2);
        bubble.y = yLo + Math.random() * Math.max(1, yHi - yLo);
        let overlap = false;
        for (let j = 0; j < index; j += 1) {
          const other = bubbles[j];
          if (Math.hypot(bubble.x - other.x, bubble.y - other.y) < bubble.r + other.r + 8) {
            overlap = true;
            break;
          }
        }
        if (!overlap) {
          placed = true;
          break;
        }
      }

      if (!placed) {
        bubble.x = bounds.x + bubble.r + pad + (index % 4) * (bubble.r * 2 + 20);
        bubble.y = yLo + (Math.floor(index / 4) % 2) * (bubble.r * 1.2);
      }

      const speed = 14 + Math.random() * 16;
      const angle = Math.random() * Math.PI * 2;
      bubble.vx = Math.cos(angle) * speed;
      bubble.vy = Math.sin(angle) * speed;
    });
  }

  /**
   * @param {Bubble} bubble
   * @param {{ x: number, y: number, width: number, height: number }} bounds
   */
  function bounceWall(bubble, bounds) {
    const minX = bounds.x + bubble.r;
    const maxX = bounds.x + bounds.width - bubble.r;
    const minY = bounds.y + bubble.r;
    const maxY = bounds.y + bounds.height - bubble.r;

    if (bubble.x < minX) {
      bubble.x = minX;
      bubble.vx = Math.abs(bubble.vx) * BOUNCE;
    }
    if (bubble.x > maxX) {
      bubble.x = maxX;
      bubble.vx = -Math.abs(bubble.vx) * BOUNCE;
    }
    if (bubble.y < minY) {
      bubble.y = minY;
      bubble.vy = Math.abs(bubble.vy) * BOUNCE;
    }
    if (bubble.y > maxY) {
      bubble.y = maxY;
      bubble.vy = -Math.abs(bubble.vy) * BOUNCE;
    }
  }

  /**
   * @param {Bubble} a
   * @param {Bubble} b
   */
  function resolveCollision(a, b) {
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const dist = Math.hypot(dx, dy);
    const minDist = a.r + b.r;
    if (dist >= minDist || dist === 0) return;

    const nx = dx / dist;
    const ny = dy / dist;
    const overlap = minDist - dist;
    const half = overlap / 2;
    a.x -= nx * half;
    a.y -= ny * half;
    b.x += nx * half;
    b.y += ny * half;

    const dvx = a.vx - b.vx;
    const dvy = a.vy - b.vy;
    const dvNormal = dvx * nx + dvy * ny;
    if (dvNormal > 0) return;

    a.vx -= dvNormal * nx;
    a.vy -= dvNormal * ny;
    b.vx += dvNormal * nx;
    b.vy += dvNormal * ny;
  }

  /**
   * @param {Bubble} bubble
   */
  function syncBubbleDom(bubble) {
    bubble.el.style.transform = `translate3d(${bubble.x - bubble.r}px, ${bubble.y - bubble.r}px, 0)`;
  }

  /**
   * @param {HTMLElement} host
   * @param {string[]} chips
   * @param {(text: string) => void} onSelect
   */
  function mountAnimated(host, chips, onSelect) {
    host.className = "intent-bubble-field";
    host.innerHTML = "";
    host.setAttribute("aria-hidden", "false");

    /** @type {Bubble[]} */
    const bubbles = chips.map((text, index) => {
      const r = baseRadius() + (index % 2) * 4;
      const el = createBubbleButton(text, index, r);
      host.appendChild(el);
      return {
        text,
        color: colorForChip(text, index),
        x: 0,
        y: 0,
        vx: 0,
        vy: 0,
        r,
        el,
      };
    });

    /** @type {{ x: number, y: number, width: number, height: number }} */
    let bounds = getPlayBounds();
    let lastTs = 0;
    let hasPlaced = false;

    /** @type {Bubble|null} */
    let dragBubble = null;
    /** @type {Bubble|null} */
    let selectedBubble = null;
    let dragPointerId = -1;
    let dragMoved = false;
    let dragLastX = 0;
    let dragLastY = 0;
    let dragPrevX = 0;
    let dragPrevY = 0;

    /**
     * @param {Bubble|null} bubble
     */
    function setSelected(bubble) {
      if (selectedBubble && selectedBubble !== bubble) {
        selectedBubble.el.classList.remove("is-selected");
      }
      selectedBubble = bubble;
      if (bubble) bubble.el.classList.add("is-selected");
    }

    /** @returns {void} */
    function measureAndPlace() {
      bounds = getPlayBounds();
      if (!hasPlaced) {
        placeBubbles(bubbles, bounds);
        hasPlaced = true;
      } else {
        bubbles.forEach((bubble) => bounceWall(bubble, bounds));
      }
      bubbles.forEach(syncBubbleDom);
    }

    /**
     * @param {number} ts
     * @returns {void}
     */
    function tick(ts) {
      rafId = requestAnimationFrame(tick);

      if (!host.isConnected) {
        EduBubblePicker.destroy();
        return;
      }
      if (document.hidden) return;

      bounds = getPlayBounds();

      const dt = lastTs ? Math.min(0.05, (ts - lastTs) / 1000) : 0.016;
      lastTs = ts;

      if (!dragBubble) {
        bubbles.forEach((bubble) => {
          bubble.x += bubble.vx * dt;
          bubble.y += bubble.vy * dt;
          bounceWall(bubble, bounds);
        });

        for (let i = 0; i < bubbles.length; i += 1) {
          for (let j = i + 1; j < bubbles.length; j += 1) {
            resolveCollision(bubbles[i], bubbles[j]);
          }
        }
      }

      bubbles.forEach(syncBubbleDom);
    }

    /**
     * @param {Bubble} bubble
     * @param {PointerEvent} event
     */
    function startDrag(bubble, event) {
      if (event.button !== 0) return;
      dragBubble = bubble;
      dragPointerId = event.pointerId;
      dragMoved = false;
      dragLastX = event.clientX;
      dragLastY = event.clientY;
      dragPrevX = event.clientX;
      dragPrevY = event.clientY;
      bubble.vx = 0;
      bubble.vy = 0;
      bubble.el.classList.add("is-dragging");
      setSelected(bubble);
      document.addEventListener("pointermove", onPointerMove);
      document.addEventListener("pointerup", onPointerUp);
      document.addEventListener("pointercancel", onPointerUp);
      event.preventDefault();
    }

    /** @param {PointerEvent} event */
    function onPointerMove(event) {
      if (!dragBubble || event.pointerId !== dragPointerId) return;

      bounds = getPlayBounds();
      const dx = event.clientX - dragLastX;
      const dy = event.clientY - dragLastY;
      if (!dragMoved && Math.hypot(dx, dy) > DRAG_THRESHOLD) dragMoved = true;

      dragBubble.x = event.clientX;
      dragBubble.y = event.clientY;
      bounceWall(dragBubble, bounds);
      syncBubbleDom(dragBubble);

      dragPrevX = dragLastX;
      dragPrevY = dragLastY;
      dragLastX = event.clientX;
      dragLastY = event.clientY;
    }

    /** @param {PointerEvent} event */
    function onPointerUp(event) {
      if (!dragBubble || event.pointerId !== dragPointerId) return;

      const bubble = dragBubble;
      bubble.el.classList.remove("is-dragging");
      document.removeEventListener("pointermove", onPointerMove);
      document.removeEventListener("pointerup", onPointerUp);
      document.removeEventListener("pointercancel", onPointerUp);

      if (dragMoved) {
        bubble.vx = (event.clientX - dragPrevX) * 12;
        bubble.vy = (event.clientY - dragPrevY) * 12;
      } else {
        onSelect(bubble.text);
      }

      dragBubble = null;
      dragPointerId = -1;
    }

    /** @returns {void} */
    function onVisibilityChange() {
      if (!document.hidden) lastTs = 0;
    }

    bubbles.forEach((bubble) => {
      bubble.el.addEventListener("pointerdown", (event) => startDrag(bubble, event));
    });

    window.addEventListener("resize", measureAndPlace);
    document.addEventListener("visibilitychange", onVisibilityChange);

    requestAnimationFrame(() => {
      requestAnimationFrame(measureAndPlace);
    });
    rafId = requestAnimationFrame(tick);

    cleanup = () => {
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
      document.removeEventListener("pointermove", onPointerMove);
      document.removeEventListener("pointerup", onPointerUp);
      document.removeEventListener("pointercancel", onPointerUp);
      window.removeEventListener("resize", measureAndPlace);
      document.removeEventListener("visibilitychange", onVisibilityChange);
      host.remove();
    };
  }

  const EduBubblePicker = {
    createMedal: createBubbleMedal,

    /**
     * @param {HTMLElement|null} container
     * @param {{ chips: string[], onSelect: (text: string) => void, fullscreen?: boolean }} opts
     */
    mount(container, opts) {
      EduBubblePicker.destroy();
      const chips = Array.isArray(opts?.chips) ? opts.chips.map((v) => String(v)) : [];
      const onSelect = typeof opts?.onSelect === "function" ? opts.onSelect : () => {};
      const fullscreen = opts?.fullscreen !== false;

      if (chips.length === 0) return;

      /** @type {HTMLElement} */
      let host = container;
      if (fullscreen || !host) {
        host = document.createElement("div");
        host.id = "intentBubbleField";
        document.body.appendChild(host);
      }

      if (prefersReducedMotion()) {
        mountStatic(host, chips, onSelect);
      } else {
        mountAnimated(host, chips, onSelect);
      }
    },

    /** @returns {void} */
    destroy() {
      if (cleanup) {
        cleanup();
        cleanup = null;
      }
      if (rafId !== null) {
        cancelAnimationFrame(rafId);
        rafId = null;
      }
      document.getElementById("intentBubbleField")?.remove();
    },
  };

  window.EduBubblePicker = EduBubblePicker;
})();
