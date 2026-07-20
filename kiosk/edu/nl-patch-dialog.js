/* S-A3 / S-B7 / S-B8 / N-5 · AI 改游戏对话
 * 多轮对话：说需求 → 落地 + 试玩说明 → 没生效可反馈再改。
 * 仅在 B6/B7 由 edu-wizard 调用；B5 代码剧场阶段不出现。
 */
(() => {
  "use strict";

  /** @type {HTMLElement|null} */
  let overlayEl = null;
  /** @type {{ sessionId: string, genre: string, onReplay: (() => void)|null }} */
  let ctx = { sessionId: "", genre: "", onReplay: null };
  /** @type {boolean} */
  let busy = false;
  /** @type {boolean} */
  let patched = false;
  /** @type {Array<{role:'user'|'assistant', content:string}>} */
  let history = [];
  /** @type {string} */
  let lastUserText = "";
  /** @type {object|null} 最近一次富结果；重开后再打开对话框要还原，勿只剩气泡输入页 */
  let lastResult = null;

  const RATING_LABELS = {
    1: "非常不满意",
    2: "比较不满意",
    3: "一般般",
    4: "比较满意",
    5: "非常满意",
  };

  const EXAMPLES_BY_GENRE = {
    platformer: [
      "让主角跳得更高",
      "加二段跳并帮我绘制图标",
      "每吃到5个金币进入无敌并加速，有特效和倒计时",
      "敌人慢一点",
    ],
    shmup: [
      "飞机技能太少了，多加有趣的技能",
      "开启清屏炸弹并画图标",
      "开启激光",
      "敌人慢一点",
    ],
    survivor: ["开启吸经验并画图标", "开启环形爆发", "敌人慢一点", "跑得更快一点"],
    pingpong: ["开启大力扣杀并画图标", "开启旋转球", "球慢一点更好打"],
    fighting: ["开启格挡并画图标", "开启上勾拳", "对手慢一点"],
    parkour: ["加二段跳并画图标", "开启滑铲", "跳得更高一点"],
    racing: ["开启氮气加速并画图标", "开启漂移", "弯道更好转一点"],
  };

  const FEEDBACK_BY_GENRE = {
    platformer: [
      "没生效，再改一次",
      "只有图标没有二段跳",
      "吃金币没有无敌加速",
      "不知道怎么玩",
    ],
    shmup: [
      "没生效，再改一次",
      "炸弹按了没反应",
      "激光没有出来",
      "点按钮飞机会跟着跑",
      "不知道怎么玩",
    ],
    survivor: ["没生效，再改一次", "吸经验没感觉", "爆发技能没用", "不知道怎么玩"],
    pingpong: ["没生效，再改一次", "扣杀打不出来", "旋转球没变化", "不知道怎么玩"],
    fighting: ["没生效，再改一次", "格挡没用", "上勾拳打不出", "不知道怎么玩"],
    parkour: ["没生效，再改一次", "二段跳没用", "滑铲没反应", "不知道怎么玩"],
    racing: ["没生效，再改一次", "氮气没加速", "漂移没感觉", "不知道怎么玩"],
  };

  function examplesForGenre() {
    return EXAMPLES_BY_GENRE[ctx.genre] || EXAMPLES_BY_GENRE.platformer;
  }

  function feedbackForGenre() {
    return FEEDBACK_BY_GENRE[ctx.genre] || [
      "没生效，再改一次",
      "技能没有感觉",
      "不知道怎么玩",
    ];
  }

  /** @param {string} text */
  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /** 去掉条目自带的「1. / 1、」以免套 <ol> 后变成「1. 1.」 */
  function stripLeadingListNumber(text) {
    return String(text || "")
      .trim()
      .replace(/^\d+[\.．、\)）]\s*/, "")
      .replace(/^[(（]\d+[)）]\s*/, "");
  }

  function ensureOverlay() {
    if (overlayEl) return overlayEl;
    overlayEl = document.createElement("div");
    overlayEl.id = "edu-nlpatch-overlay";
    overlayEl.className = "edu-nlpatch-overlay";
    overlayEl.hidden = true;
    overlayEl.innerHTML = `
      <div class="edu-nlpatch-backdrop" data-nlp-dismiss aria-hidden="true"></div>
      <div class="edu-nlpatch-dialog" role="dialog" aria-modal="true" aria-labelledby="edu-nlpatch-title">
        <div class="edu-nlpatch-ambient" aria-hidden="true">
          <div class="edu-nlpatch-ambient-gradient"></div>
          <div class="edu-nlpatch-ambient-nebula"></div>
        </div>
        <button type="button" class="edu-nlpatch-close" data-nlp-dismiss aria-label="关闭">×</button>
        <div id="edu-nlpatch-body" class="edu-nlpatch-body"></div>
      </div>`;
    document.body.appendChild(overlayEl);
    overlayEl.querySelectorAll("[data-nlp-dismiss]").forEach((node) => {
      node.addEventListener("click", () => close());
    });
    return overlayEl;
  }

  function setBody(html) {
    const body = document.getElementById("edu-nlpatch-body");
    if (body) body.innerHTML = html;
  }

  function historyHtml() {
    if (!history.length) return "";
    const turns = history
      .slice(-8)
      .map((t) => {
        const cls =
          t.role === "user" ? "edu-nlpatch-bubble edu-nlpatch-bubble--user" : "edu-nlpatch-bubble edu-nlpatch-bubble--bot";
        const who = t.role === "user" ? "你" : "AI";
        return `<div class="${cls}"><span class="edu-nlpatch-bubble-who">${who}</span>${escapeHtml(t.content)}</div>`;
      })
      .join("");
    return `<div class="edu-nlpatch-chat">${turns}</div>`;
  }

  function bindComposer(placeholder) {
    const body = document.getElementById("edu-nlpatch-body");
    if (body) window.EduTouchKeyboard?.bind(body);
    const input = /** @type {HTMLTextAreaElement|null} */ (document.getElementById("edu-nlpatch-input"));
    if (input && placeholder) input.placeholder = placeholder;
    document.querySelectorAll(".edu-nlpatch-chip").forEach((node) => {
      node.addEventListener("click", () => {
        if (input) {
          input.value = node.getAttribute("data-example") || "";
          input.focus({ preventScroll: true });
          window.EduTouchKeyboard?.show?.();
        }
      });
    });
    document.getElementById("edu-nlpatch-submit")?.addEventListener("click", (ev) => {
      ev.preventDefault();
      // 先收起 TabTip（后端勿对「陈旧 open」再 toggle，否则会误弹手写板）
      window.EduTouchKeyboard?.dismissForNavigation?.();
      const text = input?.value || "";
      // 下一帧再提交，让 blur/hide 请求先发出
      window.setTimeout(() => {
        void submit(text, "");
      }, 0);
    });
  }

  function renderInput() {
    const chips = examplesForGenre()
      .map(
        (t) => `<button type="button" class="edu-nlpatch-chip" data-example="${escapeHtml(t)}">${escapeHtml(t)}</button>`
      )
      .join("");
    setBody(`
      <h3 id="edu-nlpatch-title" class="edu-nlpatch-title">🤖 用对话改你的游戏</h3>
      <p class="edu-nlpatch-sub">直接跟 AI 对话改本局游戏；连不上大模型时才用本地规则兜底</p>
      ${historyHtml()}
      <textarea id="edu-nlpatch-input" class="edu-nlpatch-input edu-touch-input text-input" rows="3"
        maxlength="500" placeholder="像跟 AI 聊天一样，直接说你想改什么"
        inputmode="text" lang="zh-CN" enterkeyhint="done" autocomplete="off"></textarea>
      <div class="edu-nlpatch-chips">${chips}</div>
      <div class="edu-nlpatch-actions">
        <button type="button" id="edu-nlpatch-submit" class="btn btn-primary edu-nlpatch-go">发送给 AI</button>
      </div>
    `);
    bindComposer();
  }

  function renderLoading() {
    window.EduLlmCreateWait?.stop?.();
    const wait = window.EduLlmCreateWait?.render
      ? window.EduLlmCreateWait.render()
      : `<p class="edu-nlpatch-loading-text">AI 正在创作代码…</p>`;
    setBody(`
      <h3 class="edu-nlpatch-title">排队中 / 智能体施工中…</h3>
      <p class="edu-nlpatch-sub">人多时会先排队；轮到后开始改本局游戏副本</p>
      ${historyHtml()}
      <div class="edu-nlpatch-wait" id="edu-nlpatch-wait">${wait}</div>
    `);
    const host = document.getElementById("edu-nlpatch-wait");
    if (host && window.EduLlmCreateWait?.start) {
      window.EduLlmCreateWait.start(host);
    }
    startProgressPoll();
  }

  /** @type {number|null} */
  let progressPollId = null;

  function stopProgressPoll() {
    if (progressPollId != null) {
      window.clearInterval(progressPollId);
      progressPollId = null;
    }
  }

  function startProgressPoll() {
    stopProgressPoll();
    const sid = ctx.sessionId;
    // 禁止用 apiWithSession：进度 404 时会误建新会话，导致主请求像「一直加载」
    if (!sid || !window.EduSession?.api) return;
    progressPollId = window.setInterval(async () => {
      try {
        const prog = await window.EduSession.api(`/sessions/${sid}/agent-progress`, {
          method: "GET",
        });
        if (prog && prog.stage && window.EduLlmCreateWait?.setStage) {
          window.EduLlmCreateWait.setStage(String(prog.stage), String(prog.detail || ""));
        }
      } catch (_e) {
        /* 轮询失败静默，绝不重建会话 */
      }
    }, 1200);
  }

  /**
   * 对齐 HF-13 Agent 返回字段：有 Key → provider=agent；门禁靠 gate_passed/partial。
   * @param {{ok:boolean,provider:string,summary:string,message:string,changes:Array<{path:string,before:unknown,after:unknown}>,sandbox_files?:string[],attempted_paths?:string[],how_to_play?:string[],applied_capabilities?:string[],needs_relaunch?:boolean,verify_gaps?:string[],repaired?:boolean,learned_skills?:string[],llm_error?:string,gate_passed?:boolean,partial?:boolean,rolled_back?:boolean,agent_rounds?:number,understanding?:string,goals?:string[],express?:boolean,turn_id?:string}} result
   */
  function renderResult(result) {
    stopProgressPoll();
    window.EduLlmCreateWait?.stop?.();
    const isAgent = result.provider === "agent";
    const isLlm = result.provider === "llm";
    const isPartial = Boolean(result.partial) || result.gate_passed === false;
    const badge = isAgent
      ? isPartial
        ? `<span class="edu-nlpatch-badge edu-nlpatch-badge--stub">智能体施工中 · 尚未验收</span>`
        : `<span class="edu-nlpatch-badge edu-nlpatch-badge--agent">智能体已改本局副本</span>`
      : isLlm
      ? `<span class="edu-nlpatch-badge edu-nlpatch-badge--llm">AI 大模型已改</span>`
      : `<span class="edu-nlpatch-badge edu-nlpatch-badge--stub">本地降级 · 可重试</span>`;
    const repairedBadge = result.repaired
      ? `<span class="edu-nlpatch-badge edu-nlpatch-badge--llm">已自动补齐缺口</span>`
      : "";
    const learned = Array.isArray(result.learned_skills) ? result.learned_skills : [];
    const learnedBadge = learned.length
      ? `<span class="edu-nlpatch-badge edu-nlpatch-badge--llm">复用经验 ${learned.length}</span>`
      : "";
    const roundsN = Number(result.agent_rounds);
    const roundsBadge =
      isAgent && Number.isFinite(roundsN) && roundsN >= 1
        ? `<span class="edu-nlpatch-badge edu-nlpatch-badge--llm">${roundsN} 轮</span>`
        : "";
    const rolledBadge = result.rolled_back
      ? `<span class="edu-nlpatch-badge edu-nlpatch-badge--stub">已撤回未验收改动</span>`
      : "";
    const gateBadge = result.gate_passed
      ? `<span class="edu-nlpatch-badge edu-nlpatch-badge--agent">门禁已通过</span>`
      : isPartial
      ? `<span class="edu-nlpatch-badge edu-nlpatch-badge--stub">完成一部分 / 尚未验收</span>`
      : "";

    const howList = Array.isArray(result.how_to_play) ? result.how_to_play : [];
    const howHtml = howList.length
      ? `<div class="edu-nlpatch-howto"><p class="edu-nlpatch-howto-title">试玩这样验证：</p><ol>${howList
          .map((h) => `<li>${escapeHtml(stripLeadingListNumber(String(h)))}</li>`)
          .join("")}</ol></div>`
      : "";

    const caps = Array.isArray(result.applied_capabilities) ? result.applied_capabilities : [];
    const capsHtml = caps.length
      ? `<p class="edu-nlpatch-sandbox">已落地：<code>${caps.map((c) => escapeHtml(String(c))).join("</code> · <code>")}</code></p>`
      : "";

    const gaps = Array.isArray(result.verify_gaps) ? result.verify_gaps : [];
    const gapsHtml = gaps.length
      ? `<p class="edu-nlpatch-summary" style="color:#b45309">还有缺口：${escapeHtml(gaps.join("；"))}。可点下方「没生效」继续改。</p>`
      : "";

    const sandboxFiles = Array.isArray(result.sandbox_files) ? result.sandbox_files : [];
    const sandboxHtml =
      !isPartial && sandboxFiles.length
        ? `<p class="edu-nlpatch-sandbox">沙箱文件：<code>${sandboxFiles
            .map((p) => escapeHtml(String(p)))
            .join("</code> · <code>")}</code></p>`
        : "";

    const changeRows = (result.changes || [])
      .map(
        (c) => `<li class="edu-nlpatch-change">
          <span class="edu-nlpatch-change-path">${escapeHtml(String(c.path))}</span>
          <span class="edu-nlpatch-change-val">${escapeHtml(String(c.before))} → <b>${escapeHtml(String(c.after))}</b></span>
        </li>`
      )
      .join("");
    const changesHtml = result.ok && changeRows ? `<ul class="edu-nlpatch-changes">${changeRows}</ul>` : "";

    const feedbackChips = feedbackForGenre()
      .map(
        (t) => `<button type="button" class="edu-nlpatch-chip edu-nlpatch-chip--feedback" data-feedback="${escapeHtml(t)}">${escapeHtml(t)}</button>`
      )
      .join("");

    const goals = Array.isArray(result.goals) ? result.goals : [];
    const goalsHtml = goals.length
      ? `<div class="edu-nlpatch-howto"><p class="edu-nlpatch-howto-title">本轮拆解：</p><ol>${goals
          .map((g) => `<li>${escapeHtml(String(g))}</li>`)
          .join("")}</ol></div>`
      : "";
    const understanding = String(result.understanding || "").trim();
    const understandingHtml = understanding
      ? `<p class="edu-nlpatch-sandbox">理解：${escapeHtml(understanding)}</p>`
      : "";

    const titleText = !result.ok
      ? "这次没改成"
      : isPartial
      ? "完成一部分，尚未验收"
      : "收到，我们继续聊";

    const turnId = String(result.turn_id || "").trim();
    const showDiffBtn = Boolean(result.has_diff) || !!turnId;
    const diffCount = Number(result.diff_file_count) || 0;
    const diffBtnHtml = showDiffBtn
      ? `<div class="edu-nlpatch-diff-entry">
          <button type="button" id="edu-nlpatch-open-diff" class="btn btn-secondary edu-nlpatch-diff-btn">
            查看本轮代码改动${diffCount > 0 ? `（${diffCount} 个文件）` : ""}
          </button>
        </div>`
      : "";
    const ratingHtml = turnId
      ? `<div class="edu-nlpatch-rating" id="edu-nlpatch-rating" data-turn-id="${escapeHtml(turnId)}">
          <p class="edu-nlpatch-rating-title">这次改得怎么样？（可跳过）</p>
          <div class="edu-nlpatch-stars" role="group" aria-label="星级评价">
            ${[1, 2, 3, 4, 5]
              .map(
                (n) =>
                  `<button type="button" class="edu-nlpatch-star" data-score="${n}" aria-label="${n}星">${"★".repeat(n)}${"☆".repeat(5 - n)}</button>`
              )
              .join("")}
          </div>
          <p class="edu-nlpatch-rating-label" id="edu-nlpatch-rating-label">点选 1～5 星</p>
          <textarea id="edu-nlpatch-rating-comment" class="edu-nlpatch-rating-comment edu-touch-input text-input"
            rows="2" maxlength="200" placeholder="可选：再写一句想法（最多 200 字）"
            inputmode="text" lang="zh-CN"></textarea>
          <div class="edu-nlpatch-rating-actions">
            <button type="button" id="edu-nlpatch-rating-submit" class="btn btn-primary" disabled>提交评价</button>
            <button type="button" id="edu-nlpatch-rating-skip" class="btn btn-secondary">暂时跳过</button>
          </div>
          <p class="edu-nlpatch-rating-thanks" id="edu-nlpatch-rating-thanks" hidden>已记录，谢谢</p>
        </div>`
      : "";

    setBody(`
      <h3 class="edu-nlpatch-title">${titleText}</h3>
      <div class="edu-nlpatch-provider">${badge}${gateBadge}${roundsBadge}${rolledBadge}${repairedBadge}${learnedBadge}</div>
      ${historyHtml()}
      ${understandingHtml}
      ${goalsHtml}
      <p class="edu-nlpatch-summary">${escapeHtml(result.message || result.summary || "")}</p>
      ${howHtml}
      ${capsHtml}
      ${gapsHtml}
      ${
        result.ok
          ? `<p class="edu-nlpatch-summary" style="color:#0369a1;font-weight:700">请先读完说明，再点「▶ 现在重开游戏」加载新规则；若感觉没生效，回来点「没生效」即可。</p>`
          : ""
      }
      ${sandboxHtml}
      ${changesHtml}
      ${diffBtnHtml}
      <div id="edu-nlpatch-diff-panel" class="edu-nlpatch-diff-panel" hidden></div>
      ${ratingHtml}
      <textarea id="edu-nlpatch-input" class="edu-nlpatch-input edu-touch-input text-input" rows="2"
        maxlength="500" placeholder="继续说，或反馈问题（例如打不开、没生效）"
        inputmode="text" lang="zh-CN" enterkeyhint="done" autocomplete="off"></textarea>
      <div class="edu-nlpatch-chips">${feedbackChips}</div>
      <div class="edu-nlpatch-actions edu-nlpatch-actions--result">
        <button type="button" id="edu-nlpatch-submit" class="btn btn-primary">继续发给 AI</button>
        <button type="button" id="edu-nlpatch-replay" class="btn btn-secondary">▶ 现在重开游戏</button>
        <button type="button" id="edu-nlpatch-done" class="btn btn-secondary">先关闭说明</button>
      </div>
    `);

    if (turnId) bindRatingUI(turnId);
    if (showDiffBtn && turnId) {
      document.getElementById("edu-nlpatch-open-diff")?.addEventListener("click", () => {
        void openDiffPanel(turnId);
      });
    }

    document.querySelectorAll("[data-feedback]").forEach((node) => {
      node.addEventListener("click", () => {
        const fb = node.getAttribute("data-feedback") || "";
        window.EduTouchKeyboard?.dismissForNavigation?.();
        window.setTimeout(() => {
          void submit(lastUserText || "按刚才的要求再改", fb);
        }, 0);
      });
    });
    bindComposer("继续说，或反馈问题（例如打不开、没生效）");
    document.getElementById("edu-nlpatch-replay")?.addEventListener("click", () => {
      window.EduTouchKeyboard?.dismissForNavigation?.();
      close();
      if (typeof ctx.onReplay === "function") ctx.onReplay();
    });
    document.getElementById("edu-nlpatch-done")?.addEventListener("click", () => {
      window.EduTouchKeyboard?.dismissForNavigation?.();
      close();
    });
  }

  /**
   * @param {string} text
   */
  function renderUnifiedDiffHtml(text) {
    const lines = String(text || "").split("\n");
    return lines
      .map((line) => {
        let cls = "edu-diff-line";
        if (line.startsWith("+++") || line.startsWith("---") || line.startsWith("@@")) {
          cls += " edu-diff-line--meta";
        } else if (line.startsWith("+")) {
          cls += " edu-diff-line--add";
        } else if (line.startsWith("-")) {
          cls += " edu-diff-line--del";
        }
        return `<div class="${cls}">${escapeHtml(line || " ")}</div>`;
      })
      .join("");
  }

  /**
   * @param {string} turnId
   */
  async function openDiffPanel(turnId) {
    const panel = document.getElementById("edu-nlpatch-diff-panel");
    if (!panel || !ctx.sessionId) return;
    panel.hidden = false;
    panel.innerHTML = `<p class="edu-nlpatch-summary">正在加载本轮代码改动…</p>`;
    try {
      const data = await window.EduSession.apiWithSession(
        `/sessions/${ctx.sessionId}/turns/${turnId}/diff`
      );
      const files = Array.isArray(data.files) ? data.files : [];
      if (!files.length) {
        panel.innerHTML = `
          <div class="edu-nlpatch-diff-head">
            <strong>本轮代码改动</strong>
            <button type="button" class="btn btn-secondary" id="edu-nlpatch-diff-close">收起</button>
          </div>
          <p class="edu-nlpatch-summary">${escapeHtml(data.overview_note || "本轮无文本文件净变更。")}</p>
          ${
            data.rolled_back
              ? `<p class="edu-nlpatch-summary" style="color:#b45309">本轮改动已回滚，未保留在工作区。</p>`
              : ""
          }
        `;
        document.getElementById("edu-nlpatch-diff-close")?.addEventListener("click", () => {
          panel.hidden = true;
        });
        return;
      }
      let active = 0;
      let mode = "diff"; // diff | after

      const paint = () => {
        const f = files[active] || files[0];
        const tabs = files
          .map(
            (file, i) =>
              `<button type="button" class="edu-diff-tab${i === active ? " is-active" : ""}" data-idx="${i}">${escapeHtml(
                String(file.path)
              )}</button>`
          )
          .join("");
        const body =
          mode === "after"
            ? `<pre class="edu-diff-after">${escapeHtml(String(f.after_text || ""))}</pre>`
            : `<div class="edu-diff-unified">${renderUnifiedDiffHtml(String(f.diff_text || ""))}</div>`;
        panel.innerHTML = `
          <div class="edu-nlpatch-diff-head">
            <strong>本轮代码改动</strong>
            <button type="button" class="btn btn-secondary" id="edu-nlpatch-diff-close">收起</button>
          </div>
          <p class="edu-nlpatch-summary">${escapeHtml(String(data.overview_note || ""))}</p>
          ${
            data.rolled_back
              ? `<p class="edu-nlpatch-summary" style="color:#b45309">本轮改动已回滚；下列为回滚后对照。</p>`
              : ""
          }
          <div class="edu-diff-tabs">${tabs}</div>
          <p class="edu-diff-file-note">${escapeHtml(String(f.note || ""))}</p>
          <div class="edu-diff-mode">
            <button type="button" class="edu-diff-mode-btn${mode === "diff" ? " is-active" : ""}" data-mode="diff">对照 Diff</button>
            <button type="button" class="edu-diff-mode-btn${mode === "after" ? " is-active" : ""}" data-mode="after">改后全文</button>
          </div>
          ${body}
        `;
        document.getElementById("edu-nlpatch-diff-close")?.addEventListener("click", () => {
          panel.hidden = true;
        });
        panel.querySelectorAll(".edu-diff-tab").forEach((btn) => {
          btn.addEventListener("click", () => {
            active = Number(btn.getAttribute("data-idx") || 0);
            paint();
          });
        });
        panel.querySelectorAll(".edu-diff-mode-btn").forEach((btn) => {
          btn.addEventListener("click", () => {
            mode = btn.getAttribute("data-mode") === "after" ? "after" : "diff";
            paint();
          });
        });
      };
      paint();
    } catch (err) {
      panel.innerHTML = `<p class="edu-nlpatch-summary" style="color:#b45309">加载 Diff 失败：${escapeHtml(
        String(err?.message || err)
      )}</p>`;
    }
  }

  /**
   * @param {string} turnId
   */
  function bindRatingUI(turnId) {
    const root = document.getElementById("edu-nlpatch-rating");
    if (!root) return;
    let selected = 0;
    const labelEl = document.getElementById("edu-nlpatch-rating-label");
    const submitBtn = /** @type {HTMLButtonElement|null} */ (
      document.getElementById("edu-nlpatch-rating-submit")
    );
    const thanksEl = document.getElementById("edu-nlpatch-rating-thanks");
    const commentEl = /** @type {HTMLTextAreaElement|null} */ (
      document.getElementById("edu-nlpatch-rating-comment")
    );

    /**
     * @param {number} score
     */
    function paintStars(score) {
      root.querySelectorAll(".edu-nlpatch-star").forEach((btn) => {
        const n = Number(btn.getAttribute("data-score") || 0);
        btn.classList.toggle("is-active", n > 0 && n <= score);
        btn.classList.toggle("is-selected", n === score);
      });
      if (labelEl) {
        labelEl.textContent = score
          ? `${score} 星 · ${RATING_LABELS[score] || ""}`
          : "点选 1～5 星";
      }
      if (submitBtn) submitBtn.disabled = score < 1;
    }

    root.querySelectorAll(".edu-nlpatch-star").forEach((btn) => {
      btn.addEventListener("pointerenter", () => {
        if (root.classList.contains("is-done")) return;
        paintStars(Number(btn.getAttribute("data-score") || 0));
      });
      btn.addEventListener("pointerleave", () => {
        if (root.classList.contains("is-done")) return;
        paintStars(selected);
      });
      btn.addEventListener("click", () => {
        if (root.classList.contains("is-done") && !root.classList.contains("is-editable")) {
          return;
        }
        selected = Number(btn.getAttribute("data-score") || 0);
        paintStars(selected);
      });
    });

    const skipBtn = /** @type {HTMLButtonElement|null} */ (
      document.getElementById("edu-nlpatch-rating-skip")
    );
    skipBtn?.addEventListener("click", () => {
      if (root.classList.contains("is-done")) {
        root.classList.add("is-editable");
        root.classList.remove("is-done");
        if (thanksEl) thanksEl.hidden = true;
        if (submitBtn) {
          submitBtn.disabled = selected < 1;
          submitBtn.textContent = "修改并提交";
        }
        skipBtn.textContent = "暂时跳过";
        return;
      }
      root.hidden = true;
    });

    submitBtn?.addEventListener("click", async () => {
      if (selected < 1 || !ctx.sessionId) return;
      submitBtn.disabled = true;
      try {
        await window.EduSession.apiWithSession(
          `/sessions/${ctx.sessionId}/turns/${turnId}/rating`,
          {
            method: "POST",
            body: JSON.stringify({
              score: selected,
              comment: String(commentEl?.value || "").trim(),
            }),
          }
        );
        root.classList.add("is-done");
        root.classList.remove("is-editable");
        if (thanksEl) {
          thanksEl.hidden = false;
          thanksEl.textContent = "已记录，谢谢";
        }
        if (labelEl) {
          labelEl.textContent = `${selected} 星 · ${RATING_LABELS[selected] || ""} · 已提交`;
        }
        if (skipBtn) skipBtn.textContent = "修改评价";
        submitBtn.textContent = "已提交";
        submitBtn.disabled = true;
      } catch (err) {
        window.EduSession?.log?.(`评价提交失败 · ${err?.message || err}`);
        if (thanksEl) {
          thanksEl.hidden = false;
          thanksEl.textContent = "提交失败，请重试";
        }
        submitBtn.disabled = false;
      }
    });

    window.EduTouchKeyboard?.bind?.(root);
  }

  /**
   * @param {string} text
   * @param {string} feedback
   */
  async function submit(text, feedback) {
    const trimmed = String(text || "").trim();
    const fb = String(feedback || "").trim();
    if (!trimmed && !fb) {
      const input = document.getElementById("edu-nlpatch-input");
      input?.classList.add("edu-nlpatch-input--error");
      return;
    }
    if (busy) return;
    busy = true;

    const userShown = fb || trimmed;
    history.push({ role: "user", content: userShown });
    if (trimmed) lastUserText = trimmed;
    renderLoading();

    const isRuntimeFault =
      /没法.*启动|无法启动|打不开|白屏|黑屏|看不到画|没有画面|点了开始|开始游戏.*(没|不)|进不去|闪退|报错|人物.*消失|不显示|看不见|人没了|角色没了|修复问题/.test(
        userShown
      );
    // 对齐大模型对话：同会话始终带短历史；本轮原文始终作 text（最高优先）
    const historyForApi = history.slice(0, -1).slice(-10);

    // 对齐总纲墙钟 360s：前端略留余量，避免 salvage 返回前被 abort
    const NL_PATCH_TIMEOUT_MS = 420000;
    const ac = typeof AbortController !== "undefined" ? new AbortController() : null;
    const timeoutId = ac
      ? window.setTimeout(() => ac.abort(), NL_PATCH_TIMEOUT_MS)
      : null;

    try {
      const result = await window.EduSession.apiWithSession(
        `/sessions/${ctx.sessionId}/nl-patch`,
        {
          method: "POST",
          body: JSON.stringify({
            text: trimmed || lastUserText,
            history: historyForApi,
            feedback: fb || (isRuntimeFault ? trimmed : ""),
          }),
          signal: ac?.signal,
        }
      );
      patched = patched || !!result.ok;
      const botLine =
        result.message ||
        result.summary ||
        (result.ok ? "已按你的话改好了" : "这次没改成，换个说法试试");
      history.push({ role: "assistant", content: String(botLine).slice(0, 400) });
      lastResult = /** @type {any} */ (result);
      renderResult(lastResult);
      // 不自动重开：游客先读完 AI 说明，再点「现在重开游戏」
    } catch (err) {
      const raw = String(err?.message || err || "");
      const aborted =
        (ac && ac.signal.aborted) ||
        /abort|AbortError|The user aborted/i.test(raw);
      window.EduSession?.log?.(`nl-patch 失败 · ${raw}`);
      let msg = "网络出了点小问题，请稍后再试一次";
      if (aborted) {
        msg = "这轮想得太久了（超过约 6 分钟）。请再发一次，或把需求拆成更短的一句话。";
      } else if (
        /人数已满|排队|正在进行|同一账号|agent_queue_full|session_busy|user_busy/.test(raw)
      ) {
        try {
          const jsonPart = raw.replace(/^\d+:\s*/, "");
          const parsed = JSON.parse(jsonPart);
          msg = String(
            parsed.message ||
              (typeof parsed.detail === "string" ? parsed.detail : parsed.detail?.message) ||
              raw
          );
        } catch (_) {
          if (raw.includes("人数已满") || raw.includes("agent_queue_full")) {
            msg = "当前同时改游戏的人数已满，请稍后再试";
          } else if (
            raw.includes("正在进行") ||
            raw.includes("同一账号") ||
            raw.includes("session_busy") ||
            raw.includes("user_busy")
          ) {
            msg = "已有一轮改游戏正在进行，请稍候再发";
          } else {
            msg = "当前排队人数较多，请稍后再试";
          }
        }
      }
      history.push({ role: "assistant", content: msg });
      lastResult = {
        ok: false,
        provider: "agent",
        summary: "",
        message: msg,
        changes: [],
        how_to_play: [],
        applied_capabilities: [],
      };
      renderResult(lastResult);
    } finally {
      if (timeoutId != null) window.clearTimeout(timeoutId);
      busy = false;
    }
  }

  /**
   * @param {{ sessionId: string, genre: string, onReplay?: () => void }} options
   */
  function open(options) {
    const nextSession = options.sessionId || window.EduSession?.sessionId || "";
    const nextGenre = options.genre || "";
    const sameSession = nextSession && nextSession === ctx.sessionId;
    ctx = {
      sessionId: nextSession,
      genre: nextGenre,
      onReplay: typeof options.onReplay === "function" ? options.onReplay : null,
    };
    patched = false;
    // 同会话重开弹层保留短对话 history（≤8）；换会话则清空
    if (!sameSession) {
      history = [];
      lastUserText = "";
      lastResult = null;
    }
    ensureOverlay();
    // 同会话且已有上次改动说明：还原富结果页（含试玩步骤 / 重开按钮），避免只剩气泡对话框
    if (sameSession && lastResult) {
      renderResult(lastResult);
    } else {
      renderInput();
    }
    if (overlayEl) overlayEl.hidden = false;
  }

  function close() {
    stopProgressPoll();
    window.EduLlmCreateWait?.stop?.();
    window.EduTouchKeyboard?.dismissForNavigation?.();
    if (overlayEl) overlayEl.hidden = true;
  }

  window.EduNlPatchDialog = { open, close };
})();
