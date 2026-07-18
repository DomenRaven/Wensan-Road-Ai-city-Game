/* AI 改游戏 · 智能体等待动画（D7 多阶段进度）
 * 阶段与后端 PROGRESS_STAGES 对齐；支持 setStage 由轮询推进。
 */
(() => {
  "use strict";

  /** @type {number[]} */
  let timerIds = [];
  /** @type {Array<() => void>} */
  let wakeups = [];
  /** @type {HTMLElement|null} */
  let hostEl = null;
  /** @type {boolean} */
  let running = false;
  /** @type {boolean} */
  let externalStage = false;

  const PHASES = [
    { id: "understand", title: "理解需求", sub: "读懂孩子想改什么" },
    { id: "search_skills", title: "检索长期技能", sub: "查找已验证的同类改法" },
    { id: "read_contract", title: "读取品类契约", sub: "核对可调用 API 与挂钩路径" },
    { id: "write_changes", title: "写入改动", sub: "改本局会话副本 core / config" },
    { id: "validate", title: "校验脚本与声称", sub: "语法 · 契约 API · 声称对齐磁盘" },
    { id: "done", title: "完成说明", sub: "整理试玩步骤 · 准备重开" },
  ];

  const CODE_SNIPPETS = [
    [
      "extends Node",
      "",
      "func apply(bridge) -> void:",
      "\tbridge.rainbow_player_bullets()",
      "\tbridge.grant_temp_shield(8.0)",
      "\tbridge.show_countdown(8.0, \"护盾\")",
    ],
    [
      "# core/ai_sandbox/rainbow_bullets.gd",
      "extends Node",
      "",
      "func apply(bridge) -> void:",
      "\tbridge.tint_player_bullets([",
      "\t\tColor(1, 0.3, 0.4), Color(0.3, 0.9, 0.5)",
      "\t])",
    ],
    [
      "{",
      '  "tuning": {',
      '    "enabled_skills": ["bomb", "laser_beam"]',
      "  }",
      "}",
    ],
  ];

  const FILE_CHIPS = [
    "config/agent_contracts/*.json",
    "core/ai_sandbox/*.gd",
    "config/game_config.json",
  ];

  const STREAM_TOKENS = [
    "contract",
    "bridge",
    "validate",
    "assert",
    "sandbox",
    "gate",
    "core",
    "skill",
    "gdscript",
    "agent",
  ];

  function prefersReducedMotion() {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  /** @param {() => void} fn @param {number} ms */
  function later(fn, ms) {
    const id = window.setTimeout(fn, ms);
    timerIds.push(id);
    return id;
  }

  /** @param {number} ms */
  function sleep(ms) {
    return new Promise((resolve) => {
      if (!running) {
        resolve();
        return;
      }
      const wrap = () => {
        wakeups = wakeups.filter((w) => w !== wrap);
        resolve();
      };
      wakeups.push(wrap);
      later(wrap, ms);
    });
  }

  function clearTimers() {
    timerIds.forEach((id) => window.clearTimeout(id));
    timerIds = [];
    const pending = wakeups.splice(0);
    pending.forEach((w) => w());
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function buildStreamHtml() {
    const cols = prefersReducedMotion() ? 3 : 6;
    let html = "";
    for (let i = 0; i < cols; i += 1) {
      const tokens = Array.from({ length: 10 }, (_, li) => {
        return `<span>${escapeHtml(STREAM_TOKENS[(i + li) % STREAM_TOKENS.length])}</span>`;
      }).join("");
      html += `<div class="llm-wait-stream-col" style="--i:${i};--stream-dur:${5.2 + (i % 4) * 1.1}s;--stream-delay:${-(i * 0.9)}s">
        <div class="llm-wait-stream-chunk">${tokens}</div>
        <div class="llm-wait-stream-chunk" aria-hidden="true">${tokens}</div>
      </div>`;
    }
    return html;
  }

  function buildChipsHtml() {
    return FILE_CHIPS.map(
      (path, i) =>
        `<span class="llm-wait-chip" data-chip="${i}" style="--i:${i}" hidden>
          <span class="llm-wait-chip-dot"></span>
          <code>${escapeHtml(path)}</code>
        </span>`
    ).join("");
  }

  function buildStepsHtml() {
    return PHASES.map(
      (p, i) =>
        `<li class="llm-wait-step${i === 0 ? " llm-wait-step--active" : ""}" data-stage="${escapeHtml(p.id)}">
          <span class="llm-wait-step-idx">${i + 1}</span>
          <span class="llm-wait-step-label">${escapeHtml(p.title)}</span>
        </li>`
    ).join("");
  }

  /**
   * @returns {string}
   */
  function render() {
    const phase0 = PHASES[0];
    return `
      <div class="llm-wait" role="status" aria-live="polite">
        <div class="llm-wait-bg" aria-hidden="true">
          <div class="llm-wait-grid"></div>
          <div class="llm-wait-glow"></div>
          <div class="llm-wait-stream">${buildStreamHtml()}</div>
        </div>
        <ol class="llm-wait-steps" id="llmWaitSteps">${buildStepsHtml()}</ol>
        <div class="llm-wait-stage">
          <div class="llm-wait-panel">
            <div class="llm-wait-panel-bar">
              <span class="llm-wait-dot d1"></span>
              <span class="llm-wait-dot d2"></span>
              <span class="llm-wait-dot d3"></span>
              <span class="llm-wait-panel-path">会话副本 · 智能体闭环</span>
            </div>
            <pre class="llm-wait-code" id="llmWaitCode" aria-hidden="true"></pre>
            <div class="llm-wait-caret" aria-hidden="true"></div>
            <div class="llm-wait-scan" aria-hidden="true"></div>
          </div>
          <div class="llm-wait-chips" id="llmWaitChips">${buildChipsHtml()}</div>
        </div>
        <h3 class="llm-wait-title" id="llmWaitTitle">
          ${escapeHtml(phase0.title)}
          <span class="llm-wait-dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span>
        </h3>
        <p class="llm-wait-sub" id="llmWaitSub">${escapeHtml(phase0.sub)}</p>
        <div class="llm-wait-progress" aria-hidden="true">
          <div class="llm-wait-progress-track">
            <div class="llm-wait-progress-fill" id="llmWaitProgressFill"></div>
            <div class="llm-wait-progress-shine"></div>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * @param {string} stageId
   * @param {string} [detail]
   */
  function setStage(stageId, detail) {
    if (!hostEl) return;
    externalStage = true;
    const idx = Math.max(
      0,
      PHASES.findIndex((p) => p.id === stageId)
    );
    const p = PHASES[idx] || PHASES[0];
    const titleEl = hostEl.querySelector("#llmWaitTitle");
    const subEl = hostEl.querySelector("#llmWaitSub");
    const fill = hostEl.querySelector("#llmWaitProgressFill");
    const steps = hostEl.querySelectorAll(".llm-wait-step");
    if (titleEl) {
      titleEl.innerHTML = `${escapeHtml(p.title)}<span class="llm-wait-dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span>`;
    }
    if (subEl) subEl.textContent = detail || p.sub;
    if (fill instanceof HTMLElement) {
      fill.style.width = `${Math.round(((idx + 1) / PHASES.length) * 100)}%`;
    }
    steps.forEach((el, i) => {
      el.classList.toggle("llm-wait-step--active", i === idx);
      el.classList.toggle("llm-wait-step--done", i < idx);
    });
  }

  /**
   * @param {HTMLElement} codeEl
   * @param {string[]} lines
   * @param {() => boolean} isAlive
   */
  async function typeLines(codeEl, lines, isAlive) {
    codeEl.textContent = "";
    const reduced = prefersReducedMotion();
    for (let li = 0; li < lines.length && isAlive(); li += 1) {
      const line = lines[li];
      if (reduced) {
        codeEl.textContent += `${line}\n`;
        continue;
      }
      for (let ci = 0; ci < line.length && isAlive(); ci += 1) {
        codeEl.textContent += line[ci];
        await sleep(12 + (ci % 5));
      }
      codeEl.textContent += "\n";
      await sleep(90);
      codeEl.scrollTop = codeEl.scrollHeight;
    }
  }

  /**
   * @param {HTMLElement} root
   */
  function start(root) {
    stop();
    hostEl = root;
    running = true;
    externalStage = false;
    const isAlive = () => running && hostEl === root;

    const titleEl = root.querySelector("#llmWaitTitle");
    const subEl = root.querySelector("#llmWaitSub");
    const codeEl = /** @type {HTMLElement|null} */ (root.querySelector("#llmWaitCode"));
    const chips = root.querySelectorAll(".llm-wait-chip");
    const fill = root.querySelector("#llmWaitProgressFill");

    let phaseIdx = 0;
    const tickPhase = () => {
      if (!isAlive()) return;
      if (externalStage) {
        later(tickPhase, 4000);
        return;
      }
      phaseIdx = (phaseIdx + 1) % PHASES.length;
      const p = PHASES[phaseIdx];
      if (titleEl) {
        titleEl.innerHTML = `${escapeHtml(p.title)}<span class="llm-wait-dots" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span>`;
      }
      if (subEl) subEl.textContent = p.sub;
      if (fill instanceof HTMLElement) {
        fill.style.width = `${Math.round(((phaseIdx + 1) / PHASES.length) * 100)}%`;
      }
      root.querySelectorAll(".llm-wait-step").forEach((el, i) => {
        el.classList.toggle("llm-wait-step--active", i === phaseIdx);
        el.classList.toggle("llm-wait-step--done", i < phaseIdx);
      });
      later(tickPhase, 4500);
    };
    later(tickPhase, 4500);

    chips.forEach((chip, i) => {
      later(() => {
        if (!isAlive()) return;
        chip.hidden = false;
        chip.classList.add("llm-wait-chip--in");
      }, 700 + i * 900);
    });

    void (async () => {
      if (!(codeEl instanceof HTMLElement)) return;
      let snip = 0;
      while (isAlive()) {
        await typeLines(codeEl, CODE_SNIPPETS[snip % CODE_SNIPPETS.length], isAlive);
        snip += 1;
        await sleep(prefersReducedMotion() ? 1200 : 600);
        if (!isAlive()) break;
        codeEl.classList.add("llm-wait-code--fade");
        await sleep(280);
        codeEl.classList.remove("llm-wait-code--fade");
        codeEl.textContent = "";
      }
    })();
  }

  function stop() {
    running = false;
    clearTimers();
    hostEl = null;
    externalStage = false;
  }

  window.EduLlmCreateWait = { render, start, stop, setStage, PHASES };
})();
