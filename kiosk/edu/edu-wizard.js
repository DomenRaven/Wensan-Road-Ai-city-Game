/* B 链教育版 · B0–B7 状态机 */
(() => {
  "use strict";

  /** @typedef {"B0"|"B1"|"B2"|"B3"|"B4"|"B5"|"B6"|"B7"} EduStep */

  const STEPS = /** @type {EduStep[]} */ (["B0", "B1", "B2", "B3", "B4", "B5", "B6", "B7"]);

  const STEP_META = {
    B0: { title: "准备中", subtitle: "正在连接创作工坊…", phase: "create" },
    B1: { title: "今天想玩什么？", subtitle: "用一句话告诉我你想玩的游戏", phase: "create" },
    B2: { title: "给游戏起个名字", subtitle: "起个好听的名字吧", phase: "create" },
    B3: { title: "工作区就绪", subtitle: "左边是代码工作区，右边是游戏预览", phase: "create" },
    B4: { title: "创作配方", subtitle: "回答几个问题，定制你的游戏", phase: "create" },
    B5: { title: "AI 正在制作", subtitle: "看！代码正在一行行写出来", phase: "build" },
    B6: { title: "制作完成", subtitle: "这就是 AI 根据你的选择生成的游戏！", phase: "play" },
    B7: { title: "试玩", subtitle: "玩游戏时，左边会亮起对应代码", phase: "play" },
  };

  /** @type {number} */
  let stepIndex = 0;
  /** @type {Record<string, unknown>} */
  let spec = {};
  /** @type {string} */
  let genre = "";
  /** @type {string} */
  let genreLabel = "";
  /** @type {string} */
  let displayName = "";
  /** @type {string} */
  let intentRaw = "";
  /** @type {string} */
  let replyText = "";
  /** @type {Record<string, string | string[]>} */
  let creativeAnswers = {};
  /** @type {Record<string, unknown>} */
  let codeMap = {};
  /** @type {string} */
  let workspacePath = "";
  /** @type {string} */
  let workspaceConfigContent = "";
  /** @type {Map<string, string>} */
  const workspaceFileCache = new Map();
  /** @type {Map<string, string>} */
  const previewFileCache = new Map();
  /** @type {boolean} */
  let fileTreeClickBound = false;
  /** @type {object|null} */
  let creativeTemplate = null;
  /** @type {string[]} */
  let nameSuggestions = [];
  /** @type {boolean} */
  let uiReady = false;
  /** @type {{ok:boolean,already_running?:boolean,pid?:number|null,project_path?:string,godot_path?:string,message?:string,waiting?:boolean}|null} */
  let launchState = null;
  /** @type {number|null} */
  let launchStatusPollTimer = null;
  /** @type {{codeWorkspace:HTMLElement|null}} */
  let paneRefs = { codeWorkspace: null };

  const el = (id) => document.getElementById(id);
  const welcomePanel = el("welcomePanel");
  const stepPanel = el("stepPanel");
  const dualPaneRoot = el("dualPaneRoot");
  const stepTitleEl = el("stepTitle");
  const stepSubtitleEl = el("stepSubtitle");
  const stepFormEl = el("stepForm");
  const workNameEl = el("workName");
  const btnPrev = el("btnPrev");
  const btnNext = el("btnNext");
  const btnReset = el("btnReset");

  /** @returns {EduStep} */
  function currentStep() {
    return STEPS[stepIndex] || "B0";
  }

  function updateWorkName() {
    if (displayName) {
      workNameEl.textContent = `《${displayName}》`;
      workNameEl.classList.remove("empty");
    } else if (stepIndex > 0) {
      workNameEl.textContent = genreLabel ? `【${genreLabel}】创作中` : "创作中…";
      workNameEl.classList.remove("empty");
    } else {
      workNameEl.textContent = "欢迎来到创作工坊";
      workNameEl.classList.add("empty");
    }
  }

  function setUiEnabled(enabled) {
    uiReady = enabled;
    document.body.classList.toggle("kiosk-blocked", !enabled);
    if (btnPrev) btnPrev.disabled = !enabled || stepIndex <= 1;
    if (btnNext) btnNext.disabled = !enabled;
  }

  function showPanel(mode) {
    welcomePanel.hidden = mode !== "welcome";
    stepPanel.hidden = mode !== "step";
    dualPaneRoot.hidden = mode !== "dual";
  }

  function updatePhaseBar() {
    const meta = STEP_META[currentStep()];
    window.EduDualPane?.setPhase(meta.phase);
  }

  async function renderStep() {
    const step = currentStep();
    const meta = STEP_META[step];
    updateWorkName();
    updatePhaseBar();

    if (step === "B0") {
      showPanel("welcome");
      return;
    }

    if (["B1", "B2"].includes(step)) {
      showPanel("step");
      stepTitleEl.textContent = meta.title;
      stepSubtitleEl.textContent = meta.subtitle;
      btnPrev.disabled = step === "B1" || !uiReady;

      if (step === "B1") {
        window.EduB1Intent.render(stepFormEl, spec, { intentRaw, genre, replyText });
        btnNext.textContent = "下一步";
      } else if (step === "B2") {
        nameSuggestions = await window.EduB2Name.getSuggestions(genre, spec);
        window.EduB2Name.render(stepFormEl, spec, { genre, displayName, genreLabel }, nameSuggestions);
        btnNext.textContent = "下一步";
      }
      return;
    }

    showPanel("dual");

    if (step === "B3") {
      mountDualPaneIfNeeded();
      window.EduDualPane.setDisplayName(displayName);
      window.EduDualPane.showGenrePreview(genre, genreLabel);
      paneRefs.codeWorkspace = window.EduDualPane.restoreCodeLayout();
      window.EduCodeViewer.mount(paneRefs.codeWorkspace);
      window.EduCodeViewer.showPlaceholder("你的游戏代码会出现在这里");
      window.EduDualPane.setToolbar(true, `
        <button type="button" id="btnDualPrev" class="btn btn-secondary">上一步</button>
        <button type="button" id="btnDualNext" class="btn btn-primary">开始填写配方</button>
      `);
      bindDualToolbar();
      return;
    }

    if (step === "B4") {
      mountDualPaneIfNeeded();
      const formWrap = document.createElement("div");
      try {
        creativeTemplate = await window.EduB4Creative.loadTemplate(genre);
        await window.EduB4Creative.render(formWrap, creativeTemplate, creativeAnswers, genre);
      } catch (err) {
        creativeTemplate = null;
        window.EduB4Creative.renderError(formWrap, err.message);
      }
      window.EduDualPane.showLeftOverlay(formWrap);
      window.EduDualPane.showGenrePreview(genre, genreLabel);
      window.EduDualPane.setToolbar(true, `
        <button type="button" id="btnDualPrev" class="btn btn-secondary">上一步</button>
        <button type="button" id="btnDualNext" class="btn btn-primary">开始制作</button>
      `);
      bindDualToolbar();
      return;
    }

    if (step === "B5") {
      await runBuildPipeline();
      return;
    }

    if (step === "B6") {
      await renderB6Ready();
      return;
    }

    if (step === "B7") {
      await renderB7Play();
    }
  }

  function mountDualPaneIfNeeded() {
    if (!paneRefs.codeWorkspace) {
      const refs = window.EduDualPane.mount(dualPaneRoot, displayName);
      paneRefs = { codeWorkspace: refs.codeWorkspace };
      bindFileTreeClicks();
    } else {
      window.EduDualPane.setDisplayName(displayName);
    }
  }

  function bindFileTreeClicks() {
    if (!window.EduFileTree || fileTreeClickBound) return;
    fileTreeClickBound = true;
    window.EduFileTree.setClickHandler(async (path) => {
      window.EduDualPane.setActiveFile(path);
      try {
        if (workspacePath && (path.startsWith("config/") || path.startsWith("core/"))) {
          await fetchWorkspaceFile(path);
          return;
        }
        await fetchPreviewFile(path);
      } catch (err) {
        window.EduSession.log(`打不开 ${path} · ${err?.message || err}`);
      }
    });
  }

  async function ensureFileTreePopulated() {
    if (!window.EduFileTree || !genre) return;
    const files = window.EduFileTree.getManifestFiles();
    if (files.length) {
      window.EduFileTree.showAll(files, { instant: true });
      return;
    }
    await window.EduFileTree.loadManifest(genre, spec);
    window.EduFileTree.showAll(window.EduFileTree.getManifestFiles(), { instant: true });
  }

  function bindDualToolbar() {
    document.getElementById("btnDualPrev")?.addEventListener("click", () => goPrev());
    document.getElementById("btnDualNext")?.addEventListener("click", () => goNext());
  }

  function setBuildWaitPanel(phase, progressPct = 10) {
    if (window.EduBuildWait) {
      window.EduDualPane.setRightContent(window.EduBuildWait.render(phase, progressPct));
    } else {
      window.EduDualPane.setRightContent(`
        <div class="theater-progress">
          <p>AI 正在分析你的选择…</p>
          <div class="progress-bar"><div class="progress-fill" id="buildProgress" style="width:${progressPct}%"></div></div>
        </div>
      `);
    }
  }

  async function runBuildPipeline() {
    mountDualPaneIfNeeded();
    window.EduDualPane.setPhase("build");
    paneRefs.codeWorkspace = window.EduDualPane.restoreCodeLayout();
    setBuildWaitPanel("analyze", 8);
    window.EduDualPane.setToolbar(false);

    const sessionId = window.EduSession.sessionId;
    let analyzeOk = false;

    try {
      const analyze = await window.EduSession.api(`/sessions/${sessionId}/analyze-requirements`, {
        method: "POST",
        body: "{}",
      });
      analyzeOk = true;
      if (analyze.code_map_preview) {
        codeMap = { ...codeMap, ...analyze.code_map_preview };
      }
      setBuildWaitPanel("analyze", 16);
    } catch (_) {
      window.EduSession.log("TODO: POST analyze-requirements 未就绪 · 使用默认 preset");
    }

    await window.EduCodeTheater.load(genre, spec);

    paneRefs.codeWorkspace = window.EduDualPane.restoreCodeLayout();

    await new Promise((resolve) => {
      window.EduCodeTheater.start(paneRefs.codeWorkspace, genre, spec, (state, detail) => {
        const progress = typeof detail?.progress === "number" ? detail.progress : null;

        if (state === "theater_scrolling") {
          setBuildWaitPanel("theater", progress ?? 18);
        }
        if (state === "theater_tick" && progress !== null) {
          window.EduBuildWait?.updateProgress(null, progress);
        }
        if (state === "applying") {
          setBuildWaitPanel("apply", progress ?? 72);

          (async () => {
            let genOk = false;
            try {
              const gen = await window.EduSession.api(`/sessions/${sessionId}/generate/v2`, {
                method: "POST",
                body: JSON.stringify({
                  meta: { genre, display_name: displayName },
                  creative_answers: creativeAnswers,
                }),
              });
              genOk = gen.ok !== false;
              workspacePath = gen.workspace_path || "";
              if (gen.code_map) codeMap = gen.code_map;
              if (workspacePath) {
                try {
                  const cfg = await fetchWorkspaceConfig();
                  workspaceConfigContent = cfg.content || "";
                } catch (err) {
                  workspaceConfigContent = "";
                  window.EduSession.log(`加载 game_config 失败 · ${err.message}`);
                }
              }
            } catch (_) {
              window.EduSession.log("TODO: POST generate/v2 未就绪 · 跳过 workspace 生成");
            }

            window.EduSession.log(analyzeOk && genOk ? "✓ 制作完成" : "⚠ 降级模式 · 可试玩经典版");
            window.EduBuildWait?.updateProgress(null, 100);
            window.EduCodeTheater.updateProgress(null, 100);
            window.setTimeout(() => {
              stepIndex = STEPS.indexOf("B6");
              renderStep();
              resolve();
            }, 800);
          })();
        }
      });
    });
  }

  function isDevFallbackAllowed() {
    const host = window.location.hostname;
    return host === "127.0.0.1" || host === "localhost";
  }

  function getCodeMapHighlightLines() {
    const lines = Object.values(getMergedCodeMap())
      .map((entry) => entry.line || entry.line_hint)
      .filter((line) => typeof line === "number" && line > 0);
    return lines.length ? [/** @type {number} */ (lines[0])] : [];
  }

  /**
   * @param {string} [slug]
   * @returns {Record<string, {file:string,line?:number,line_hint?:number,caption?:string,action_id?:string}>}
   */
  function getGenreHighlightFallback(slug) {
    const maps = {
      shmup: {
        kill_enemy: {
          file: "core/enemy_ship.gd",
          line: 131,
          caption: "打爆敌机就执行这里，加分！",
          action_id: "kill_enemy",
        },
        pickup: {
          file: "core/player_ship.gd",
          line: 149,
          caption: "捡到道具就调用这里变强！",
          action_id: "pickup",
        },
        hit: {
          file: "core/player_ship.gd",
          line: 172,
          caption: "被敌人或子弹打中会掉血！",
          action_id: "hit",
        },
      },
      survivor: {
        kill_enemy: {
          file: "core/horde_enemy.gd",
          line: 80,
          caption: "消灭敌人就在这里处理！",
          action_id: "kill_enemy",
        },
        pickup: {
          file: "core/xp_gem.gd",
          line: 40,
          caption: "捡到经验宝石会升级！",
          action_id: "pickup_xp",
        },
      },
      racing: {
        steer: {
          file: "core/car_topdown.gd",
          line: 126,
          caption: "按左右键，车子就会转向！",
          action_id: "steer",
        },
        hit_npc: {
          file: "core/car_topdown.gd",
          line: 149,
          caption: "撞上别的车会减速，就是这里！",
          action_id: "hit_npc",
        },
        hit_trap: {
          file: "core/car_topdown.gd",
          line: 151,
          caption: "碰到路障会打滑，看这段代码！",
          action_id: "hit_trap",
        },
        lap_complete: {
          file: "core/track_runner.gd",
          line: 142,
          caption: "跑够一圈就会记一次圈数！",
          action_id: "lap_complete",
        },
      },
      parkour: {
        jump: {
          file: "core/player_runner.gd",
          line: 133,
          caption: "按空格起跳，就是这里！",
          action_id: "jump",
        },
        slide: {
          file: "core/player_runner.gd",
          line: 141,
          caption: "按下技能键，身体压低滑过去！",
          action_id: "slide",
        },
        collect_coin: {
          file: "core/auto_runner.gd",
          line: 172,
          caption: "吃到金币，分数就在这里加！",
          action_id: "collect_coin",
        },
        pickup_powerup: {
          file: "core/auto_runner.gd",
          line: 175,
          caption: "捡到护盾或双倍金币道具，看这里！",
          action_id: "pickup_powerup",
        },
      },
      platformer: {
        jump: {
          file: "core/player_platformer.gd",
          line: 160,
          caption: "按跳跃键起跳，就是这里！",
          action_id: "jump",
        },
        stomp_enemy: {
          file: "core/player_platformer.gd",
          line: 264,
          caption: "从上方踩到敌人就能消灭它！",
          action_id: "stomp_enemy",
        },
        collect_coin: {
          file: "core/collectible.gd",
          line: 31,
          caption: "碰到金币会执行这里，加分！",
          action_id: "collect_coin",
        },
      },
      fighting: {
        light_punch: {
          file: "core/fighter.gd",
          line: 290,
          caption: "按 J 出轻拳，快攻就靠它！",
          action_id: "light_punch",
        },
        heavy_punch: {
          file: "core/fighter.gd",
          line: 294,
          caption: "按 K 出重拳，威力更大！",
          action_id: "heavy_punch",
        },
        block: {
          file: "core/fighter.gd",
          line: 283,
          caption: "按住 L 格挡，能挡住不少伤害！",
          action_id: "block",
        },
        special: {
          file: "core/fighter.gd",
          line: 298,
          caption: "能量满了按 U 放大招，超帅！",
          action_id: "special",
        },
      },
    };
    return maps[slug] || {
      jump: { file: "config/game_config.json", line: 12, caption: "跳跃力度：你选得越高，跳得越猛！", action_id: "jump" },
      stomp_enemy: { file: "config/game_config.json", line: 16, caption: "从上方踩到敌人就能消灭它！", action_id: "stomp_enemy" },
      collect_coin: { file: "config/game_config.json", line: 19, caption: "每枚金币加分就在这里设定！", action_id: "collect_coin" },
    };
  }

  function getMergedCodeMap() {
    const fallback = getGenreHighlightFallback(genre);
    return { ...fallback, ...codeMap };
  }

  async function fetchWorkspaceConfig() {
    if (workspaceConfigContent) {
      return {
        ok: true,
        genre,
        content: workspaceConfigContent,
        path: "config/game_config.json",
      };
    }
    const sessionId = window.EduSession.sessionId;
    const data = await window.EduSession.api(`/sessions/${sessionId}/workspace/game-config`);
    workspaceConfigContent = String(data.content || "");
    if (data.genre) genre = String(data.genre);
    return data;
  }

  /**
   * @param {string} relPath e.g. config/game_config.json · core/ball.gd
   */
  async function fetchWorkspaceFile(relPath) {
    const normalized = String(relPath || "").replace(/\\/g, "/").replace(/^\/+/, "");
    if (!normalized) {
      throw new Error("文件路径为空");
    }
    if (!workspacePath) {
      throw new Error("无 workspace");
    }
    window.EduCodeViewer.mount(paneRefs.codeWorkspace || document.getElementById("codeWorkspace"));
    if (workspaceFileCache.has(normalized)) {
      const cached = workspaceFileCache.get(normalized);
      window.EduCodeViewer.setContent(cached, []);
      window.EduCodeViewer.setActiveFile(normalized);
      return { ok: true, path: normalized, content: cached };
    }
    const sessionId = window.EduSession.sessionId;
    const data = await window.EduSession.api(
      `/sessions/${sessionId}/workspace/file?rel_path=${encodeURIComponent(normalized)}`
    );
    const content = String(data.content || "");
    workspaceFileCache.set(normalized, content);
    window.EduCodeViewer.setContent(content, []);
    window.EduCodeViewer.setActiveFile(normalized);
    return data;
  }

  /**
   * @param {string} relPath
   */
  async function fetchPreviewFile(relPath) {
    const normalized = String(relPath || "").replace(/\\/g, "/").replace(/^\/+/, "");
    if (!normalized) {
      throw new Error("文件路径为空");
    }
    if (!genre) {
      throw new Error("未知品类");
    }
    window.EduCodeViewer.mount(paneRefs.codeWorkspace || document.getElementById("codeWorkspace"));
    const cacheKey = `${genre}:${normalized}`;
    if (previewFileCache.has(cacheKey)) {
      const cached = previewFileCache.get(cacheKey);
      window.EduCodeViewer.setContent(cached, []);
      window.EduCodeViewer.setActiveFile(normalized);
      return { ok: true, path: normalized, content: cached };
    }
    const data = await window.EduSession.api(
      `/edu/preview/${encodeURIComponent(genre)}/file?rel_path=${encodeURIComponent(normalized)}`
    );
    const content = String(data.content || "");
    previewFileCache.set(cacheKey, content);
    window.EduCodeViewer.setContent(content, []);
    window.EduCodeViewer.setActiveFile(normalized);
    return data;
  }

  async function applyCodeViewerContent(highlightLines) {
    window.EduCodeViewer.mount(paneRefs.codeWorkspace);
    if (workspacePath) {
      try {
        const data = await fetchWorkspaceConfig();
        window.EduCodeViewer.setContent(data.content, highlightLines);
        window.EduCodeViewer.setActiveFile("config/game_config.json");
        return;
      } catch (err) {
        window.EduCodeViewer.showPlaceholder("游戏配置加载失败，请重试");
        window.EduSession.log(`加载 game_config 失败 · ${err.message}`);
        return;
      }
    }
    window.EduCodeViewer.showPlaceholder("请先完成制作");
    if (isDevFallbackAllowed()) {
      console.warn("EduWizard: 无 workspace · 使用 fallback config 片段（仅开发演示）");
      window.EduCodeViewer.setContent(getFallbackConfigSnippet(), highlightLines);
    }
  }

  /**
   * @param {Error|{message?:string}} err
   * @returns {string}
   */
  function parseLaunchError(err) {
    const raw = String(err?.message || "游戏暂时无法启动");
    const match = raw.match(/^\d+:\s*(.+)$/s);
    if (!match) return raw;
    try {
      const body = JSON.parse(match[1]);
      if (typeof body.detail === "string") return body.detail;
    } catch (_) {
      /* use raw fragment */
    }
    return match[1].slice(0, 120);
  }

  /**
   * @param {{ok:boolean,already_running?:boolean,pid?:number|null,project_path?:string,message?:string,waiting?:boolean}|null} data
   * @returns {string}
   */
  function renderLaunchStatusPanel(data) {
    if (!data) {
      return `
        <div class="launch-status-card">
          <p class="launch-status warn" id="launchStatus">请先点击「开始试玩」启动游戏</p>
        </div>
      `;
    }
    if (data.waiting) {
      return `
        <div class="launch-status-card">
          <p class="launch-status" id="launchStatus">正在启动游戏…</p>
        </div>
      `;
    }
    if (data.ok) {
      const mainMsg = data.already_running
        ? "游戏已在运行 · 请到旁边游戏窗口继续试玩"
        : "Godot 已启动 · 请到游戏窗口试玩";
      const pid = data.pid != null ? String(data.pid) : "—";
      const path = data.project_path || "—";
      return `
        <div class="launch-status-card">
          <p class="launch-status ok" id="launchStatus">${mainMsg}</p>
          <details class="launch-details">
            <summary>技术信息（默认折叠）</summary>
            <p class="launch-meta">进程 PID：${pid}</p>
            <p class="launch-meta">项目路径：${path}</p>
          </details>
          <p class="godot-run-status" id="godotRunStatus" aria-live="polite"></p>
        </div>
      `;
    }
    const errMsg = data.message || "游戏暂时无法启动，请讲解员协助";
    return `
      <div class="launch-status-card">
        <p class="launch-status err" id="launchStatus">${errMsg}</p>
        <p class="hint">可点「加载经典版」重试，或先进入演示模式看左侧高亮</p>
      </div>
    `;
  }

  function stopLaunchStatusPolling() {
    if (launchStatusPollTimer) {
      window.clearInterval(launchStatusPollTimer);
      launchStatusPollTimer = null;
    }
  }

  /**
   * @param {string} sessionId
   */
  function startLaunchStatusPolling(sessionId) {
    stopLaunchStatusPolling();
    launchStatusPollTimer = window.setInterval(async () => {
      const el = document.getElementById("godotRunStatus");
      if (!el) return;
      try {
        const status = await window.EduSession.api(`/sessions/${sessionId}/play/status`);
        if (status.running === true) {
          el.textContent = "● 游戏运行中";
          el.className = "godot-run-status running";
        } else if (status.running === false) {
          el.textContent = "○ 游戏窗口已关闭";
          el.className = "godot-run-status stopped";
        }
      } catch (_) {
        /* 可选 UI · 静默 */
      }
    }, 3000);
  }

  function getFallbackConfigSnippet() {
    return `{
  "meta": {
    "genre": "${genre}",
    "display_name": "${displayName}"
  },
  "tuning": {
    "player": {
      "move_speed": 200,
      "jump_velocity": -400
    },
    "enemy": {
      "patrol_speed": 50
    },
    "scoring": {
      "coin": 10
    }
  },
  "theme": {
    "title": "${displayName}"
  }
}`;
  }

  async function renderB6Ready() {
    mountDualPaneIfNeeded();
    window.EduDualPane.setPhase("play");
    paneRefs.codeWorkspace = window.EduDualPane.restoreCodeLayout();
    bindFileTreeClicks();
    await ensureFileTreePopulated();
    await applyCodeViewerContent(getCodeMapHighlightLines());

    if (Object.keys(codeMap).length) {
      window.EduCodeHighlight.configure(spec);
      window.EduCodeHighlight.setCodeMap(getMergedCodeMap());
    } else {
      window.EduCodeHighlight.setCodeMap(getGenreHighlightFallback(genre));
    }

    window.EduDualPane.setRightContent(`
      <p class="preview-placeholder" style="margin-bottom:20px">这就是 AI 根据你的选择生成的游戏！</p>
      <button type="button" id="btnLaunch" class="btn btn-success">开始试玩</button>
      <div id="launchStatusWrap">${renderLaunchStatusPanel(launchState)}</div>
      <p class="hint" style="margin-top:16px">讲解员演示：点击下方按钮模拟「跳跃」高亮</p>
      <button type="button" id="btnSimJump" class="btn btn-ghost" aria-label="讲解员演示用：模拟跳跃">模拟跳跃 → 高亮代码</button>
      <button type="button" id="btnSimStomp" class="btn btn-ghost" aria-label="讲解员演示用：模拟踩怪">模拟踩怪 → 高亮代码</button>
    `);

    document.getElementById("btnLaunch")?.addEventListener("click", launchGame);
    document.getElementById("btnSimJump")?.addEventListener("click", () => {
      window.EduCodeHighlight.simulateAction("jump");
    });
    document.getElementById("btnSimStomp")?.addEventListener("click", () => {
      window.EduCodeHighlight.simulateAction("stomp_enemy");
    });

    window.EduDualPane.setToolbar(true, `
      <button type="button" id="btnDualPrev" class="btn btn-secondary" disabled>上一步</button>
      <button type="button" id="btnDualNext" class="btn btn-primary">进入试玩</button>
    `);
    bindDualToolbar();
  }

  async function launchGame() {
    launchState = { ok: false, waiting: true };
    const wrap = document.getElementById("launchStatusWrap");
    if (wrap) wrap.innerHTML = renderLaunchStatusPanel(launchState);

    try {
      const data = await window.EduSession.api(
        `/sessions/${window.EduSession.sessionId}/play/launch`,
        { method: "POST", body: "{}" }
      );
      if (!data.ok) {
        launchState = { ok: false, message: data.message || "游戏启动失败，请重试" };
        window.EduSession.log(`play/launch 未成功 · ${launchState.message}`);
        if (wrap) wrap.innerHTML = renderLaunchStatusPanel(launchState);
        return;
      }
      launchState = {
        ok: true,
        already_running: !!data.already_running,
        pid: data.pid ?? null,
        project_path: data.project_path || "",
        godot_path: data.godot_path || "",
        message: data.message || "",
      };
      window.EduSession.log(
        launchState.already_running ? "✓ 游戏已在运行" : "✓ Godot 已启动"
      );
      stepIndex = STEPS.indexOf("B7");
      await renderStep();
    } catch (err) {
      const msg = parseLaunchError(err);
      launchState = { ok: false, message: msg };
      window.EduSession.log(`play/launch 失败 · ${msg}`);
      if (wrap) wrap.innerHTML = renderLaunchStatusPanel(launchState);
    }
  }

  function renderB7DemoActionsHtml() {
    if (genre === "shmup") {
      return `
        <button type="button" id="btnSimKill" class="btn btn-primary" aria-label="讲解员演示用：模拟击毁敌机">打敌机</button>
        <button type="button" id="btnSimPickup" class="btn btn-secondary" aria-label="讲解员演示用：模拟吃道具">吃道具</button>
        <button type="button" id="btnSimHit" class="btn btn-secondary" aria-label="讲解员演示用：模拟受伤">受伤</button>
      `;
    }
    if (genre === "racing") {
      return `
        <button type="button" id="btnSimNpc" class="btn btn-primary" aria-label="讲解员演示用：模拟撞车">撞车</button>
        <button type="button" id="btnSimTrap" class="btn btn-secondary" aria-label="讲解员演示用：模拟撞路障">撞路障</button>
        <button type="button" id="btnSimLap" class="btn btn-secondary" aria-label="讲解员演示用：模拟完圈">完圈</button>
      `;
    }
    if (genre === "parkour") {
      return `
        <button type="button" id="btnSimJump" class="btn btn-primary" aria-label="讲解员演示用：模拟跳跃">跳跃</button>
        <button type="button" id="btnSimSlide" class="btn btn-secondary" aria-label="讲解员演示用：模拟滑铲">滑铲</button>
        <button type="button" id="btnSimCoin" class="btn btn-secondary" aria-label="讲解员演示用：模拟捡金币">捡金币</button>
        <button type="button" id="btnSimPickup" class="btn btn-secondary" aria-label="讲解员演示用：模拟吃道具">吃道具</button>
      `;
    }
    if (genre === "fighting") {
      return `
        <button type="button" id="btnSimLight" class="btn btn-primary" aria-label="讲解员演示用：模拟轻拳">轻拳</button>
        <button type="button" id="btnSimHeavy" class="btn btn-secondary" aria-label="讲解员演示用：模拟重拳">重拳</button>
        <button type="button" id="btnSimBlock" class="btn btn-secondary" aria-label="讲解员演示用：模拟格挡">格挡</button>
        <button type="button" id="btnSimUlt" class="btn btn-secondary" aria-label="讲解员演示用：模拟大招">大招</button>
      `;
    }
    return `
      <button type="button" id="btnSimJump" class="btn btn-primary" aria-label="讲解员演示用：模拟跳跃">跳！</button>
      <button type="button" id="btnSimStomp" class="btn btn-secondary" aria-label="讲解员演示用：模拟踩怪">踩怪</button>
      <button type="button" id="btnSimCoin" class="btn btn-secondary" aria-label="讲解员演示用：模拟捡金币">捡金币</button>
    `;
  }

  function bindB7DemoActions() {
    if (genre === "shmup") {
      document.getElementById("btnSimKill")?.addEventListener("click", () => {
        window.EduCodeHighlight.simulateAction("kill_enemy");
      });
      document.getElementById("btnSimPickup")?.addEventListener("click", () => {
        window.EduCodeHighlight.simulateAction("pickup");
      });
      document.getElementById("btnSimHit")?.addEventListener("click", () => {
        window.EduCodeHighlight.simulateAction("hit");
      });
      return;
    }
    if (genre === "racing") {
      document.getElementById("btnSimNpc")?.addEventListener("click", () => {
        window.EduCodeHighlight.simulateAction("hit_npc");
      });
      document.getElementById("btnSimTrap")?.addEventListener("click", () => {
        window.EduCodeHighlight.simulateAction("hit_trap");
      });
      document.getElementById("btnSimLap")?.addEventListener("click", () => {
        window.EduCodeHighlight.simulateAction("lap_complete");
      });
      return;
    }
    if (genre === "parkour") {
      document.getElementById("btnSimJump")?.addEventListener("click", () => {
        window.EduCodeHighlight.simulateAction("jump");
      });
      document.getElementById("btnSimSlide")?.addEventListener("click", () => {
        window.EduCodeHighlight.simulateAction("slide");
      });
      document.getElementById("btnSimCoin")?.addEventListener("click", () => {
        window.EduCodeHighlight.simulateAction("collect_coin");
      });
      document.getElementById("btnSimPickup")?.addEventListener("click", () => {
        window.EduCodeHighlight.simulateAction("pickup_powerup");
      });
      return;
    }
    if (genre === "fighting") {
      document.getElementById("btnSimLight")?.addEventListener("click", () => {
        window.EduCodeHighlight.simulateAction("light_punch");
      });
      document.getElementById("btnSimHeavy")?.addEventListener("click", () => {
        window.EduCodeHighlight.simulateAction("heavy_punch");
      });
      document.getElementById("btnSimBlock")?.addEventListener("click", () => {
        window.EduCodeHighlight.simulateAction("block");
      });
      document.getElementById("btnSimUlt")?.addEventListener("click", () => {
        window.EduCodeHighlight.simulateAction("special");
      });
      return;
    }
    document.getElementById("btnSimJump")?.addEventListener("click", () => {
      window.EduCodeHighlight.simulateAction("jump");
    });
    document.getElementById("btnSimStomp")?.addEventListener("click", () => {
      window.EduCodeHighlight.simulateAction("stomp_enemy");
    });
    document.getElementById("btnSimCoin")?.addEventListener("click", () => {
      window.EduCodeHighlight.simulateAction("collect_coin");
    });
  }

  async function renderB7Play() {
    mountDualPaneIfNeeded();
    window.EduDualPane.setPhase("play");
    paneRefs.codeWorkspace = window.EduDualPane.restoreCodeLayout();
    bindFileTreeClicks();
    await ensureFileTreePopulated();
    await applyCodeViewerContent([]);

    window.EduCodeHighlight.configure(spec);
    window.EduCodeHighlight.setCodeMap(getMergedCodeMap());

    const launched = !!(launchState && launchState.ok);
    window.EduCodeHighlight.stopPolling();
    stopLaunchStatusPolling();
    if (launched) {
      window.EduCodeHighlight.startPolling(window.EduSession.sessionId);
      startLaunchStatusPolling(window.EduSession.sessionId);
    } else if (workspacePath) {
      window.EduCodeHighlight.startPolling(window.EduSession.sessionId);
    }

    window.EduDualPane.setRightContent(`
      <div class="godot-frame-wrap">
        ${renderLaunchStatusPanel(launched ? launchState : null)}
        <div class="play-window-hint">
          <p class="play-window-title">🎮 游戏在外置窗口中运行</p>
          <p class="hint">请看讲解员指向的大屏旁 Godot 游戏窗口（不在此网页内）</p>
        </div>
      </div>
      <p class="hint demo-hint">以下按钮仅供讲解员演示 · 真机试玩请操作 Godot 窗口</p>
      <div class="demo-actions" style="margin-top:12px;display:flex;gap:10px;flex-wrap:wrap;justify-content:center">
        ${renderB7DemoActionsHtml()}
      </div>
    `);

    bindB7DemoActions();

    window.EduDualPane.setToolbar(true, `
      <button type="button" id="btnLoadClassic" class="btn btn-ghost">加载经典版</button>
      <button type="button" id="btnFinish" class="btn btn-secondary">完成创作</button>
    `);
    document.getElementById("btnLoadClassic")?.addEventListener("click", async () => {
      try {
        const data = await window.EduSession.api(
          `/sessions/${window.EduSession.sessionId}/play/launch`,
          { method: "POST", body: "{}" }
        );
        if (data.ok) {
          launchState = {
            ok: true,
            already_running: !!data.already_running,
            pid: data.pid ?? null,
            project_path: data.project_path || "",
            message: data.message || "",
          };
          window.EduSession.log("已加载经典版 · Godot 已启动");
          await renderB7Play();
        } else {
          window.EduSession.log(`经典版加载失败 · ${data.message || "未知错误"}`);
        }
      } catch (err) {
        window.EduSession.log(`经典版 fallback 失败 · ${parseLaunchError(err)}`);
      }
    });
    document.getElementById("btnFinish")?.addEventListener("click", () => resetWizard());
  }

  async function goNext() {
    const step = currentStep();

    if (step === "B1") {
      intentRaw = window.EduB1Intent.getInput(stepFormEl);
      if (!intentRaw) return;
      btnNext.disabled = true;
      const match = await window.EduB1Intent.matchGenre(intentRaw, window.EduSession.sessionId);
      genre = match.matched_genre || "platformer";
      replyText = match.reply_text || "";
      const names = spec.genre_display_names || {};
      genreLabel = names[genre] || genre;
      stepIndex += 1;
      btnNext.disabled = false;
      await renderStep();
      return;
    }

    if (step === "B2") {
      displayName = window.EduB2Name.getInput(stepFormEl);
      if (!window.EduB2Name.isValid(displayName)) return;
      try {
        await window.EduSession.api(`/sessions/${window.EduSession.sessionId}/wizard/S0`, {
          method: "POST",
          body: JSON.stringify({ data: { display_name: displayName } }),
        });
      } catch (err) {
        window.EduSession.log(`保存游戏名称失败 · ${err.message}`);
      }
      stepIndex += 1;
      await renderStep();
      return;
    }

    if (step === "B3") {
      stepIndex = STEPS.indexOf("B4");
      await renderStep();
      return;
    }

    if (step === "B4") {
      if (!creativeTemplate) {
        window.EduSession.log("创作模板未加载 · 无法继续制作");
        return;
      }
      creativeAnswers = { ...window.EduB4Creative.answers };
      if (!window.EduB4Creative.validate(creativeTemplate)) return;
      const dualNext = document.getElementById("btnDualNext");
      if (dualNext) dualNext.disabled = true;
      try {
        await window.EduB4Creative.submitAnswers(window.EduSession.sessionId, creativeAnswers);
      } catch (err) {
        window.EduSession.log(`提交创作答案失败 · 请重试 · ${err.message}`);
        if (dualNext) dualNext.disabled = false;
        return;
      }
      stepIndex = STEPS.indexOf("B5");
      await renderStep();
      return;
    }

    if (step === "B6") {
      stepIndex = STEPS.indexOf("B7");
      await renderStep();
    }
  }

  async function goPrev() {
    if (stepIndex <= 1) return;
    if (currentStep() === "B5") return;
    window.EduCodeTheater.stop();
    window.EduCodeHighlight.stopPolling();
    stopLaunchStatusPolling();
    stepIndex -= 1;
    if (currentStep() === "B3") paneRefs.codeWorkspace = null;
    await renderStep();
  }

  async function resetWizard() {
    window.EduCodeTheater.stop();
    window.EduCodeHighlight.stopPolling();
    stopLaunchStatusPolling();
    launchState = null;
    await window.EduSession.releaseAsync();
    genre = "";
    genreLabel = "";
    displayName = "";
    intentRaw = "";
    replyText = "";
    creativeAnswers = {};
    codeMap = {};
    workspacePath = "";
    workspaceConfigContent = "";
    workspaceFileCache.clear();
    creativeTemplate = null;
    paneRefs = { codeWorkspace: null };
    stepIndex = 1;
    try {
      await window.EduSession.createSession();
      setUiEnabled(true);
    } catch (_) {
      setUiEnabled(false);
    }
    await renderStep();
  }

  async function init() {
    showPanel("welcome");
    const statusEl = el("bootstrapStatus");

    btnNext.addEventListener("click", () => goNext());
    btnPrev.addEventListener("click", () => goPrev());
    btnReset.addEventListener("click", () => resetWizard());

    try {
      await window.EduSession.bootstrap();
      spec = window.EduSession.spec;
      window.EduCodeHighlight.configure(spec);
      if (statusEl) statusEl.textContent = "准备就绪！";
      setUiEnabled(true);
      stepIndex = 1;
      await renderStep();
    } catch (err) {
      spec = window.EduSession.spec || {};
      window.EduCodeHighlight.configure(spec);
      if (statusEl) statusEl.textContent = "演示模式（后端未连接）";
      setUiEnabled(true);
      stepIndex = 1;
      await renderStep();
    }
  }

  window.EduWizard = { spec, init, currentStep, resetWizard, fetchWorkspaceFile, fetchPreviewFile };
  document.addEventListener("DOMContentLoaded", () => init());
})();
