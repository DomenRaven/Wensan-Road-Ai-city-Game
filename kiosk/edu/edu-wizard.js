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
    B6: { title: "制作完成", subtitle: "点右边大按钮开始试玩", phase: "play" },
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
  let creatorName = "";
  /** @type {"creator"|"gameName"} */
  let b2SubStep = "creator";
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
  /** @type {boolean} */
  let launchInFlight = false;
  /** @type {boolean} */
  let prevGodotRunning = false;
  /** @type {boolean} */
  let leaderboardHandledThisRun = false;
  /** @type {boolean} */
  let sawGodotRunning = false;
  /** @type {number} */
  let launchPollStartedAt = 0;
  /** @type {{codeWorkspace:HTMLElement|null}} */
  let paneRefs = { codeWorkspace: null };
  /** @type {Date|null} */
  let certificateCreatedAt = null;

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
    if (creatorName && displayName) {
      workNameEl.textContent = `${creatorName}《${displayName}》`;
      workNameEl.classList.remove("empty");
    } else if (displayName) {
      workNameEl.textContent = `《${displayName}》`;
      workNameEl.classList.remove("empty");
    } else if (creatorName) {
      workNameEl.textContent = creatorName;
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

  /** @param {HTMLElement|null|undefined} node */
  function bindNavDismiss(node) {
    if (!node || node.dataset.eduKbDismiss) return;
    node.dataset.eduKbDismiss = "1";
    node.addEventListener(
      "pointerdown",
      () => window.EduTouchKeyboard?.dismissForNavigation?.(),
      true
    );
  }

  function showPanel(mode) {
    welcomePanel.hidden = mode !== "welcome";
    stepPanel.hidden = mode !== "step";
    dualPaneRoot.hidden = mode !== "dual";
    const ambientMode = mode === "step" ? "step" : mode === "dual" ? "dual" : "off";
    window.EduCreateAmbient?.setMode(ambientMode);
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
    updateLeaderboardButton();

    if (step === "B0") {
      showPanel("welcome");
      return;
    }

    if (["B1", "B2"].includes(step)) {
      showPanel("step");
      document.body.classList.toggle("edu-step-b1", step === "B1");
      document.body.classList.toggle("edu-step-b2", step === "B2");
      stepTitleEl.textContent = meta.title;
      stepSubtitleEl.textContent = meta.subtitle;
      btnPrev.disabled = step === "B1" || !uiReady;

      if (step === "B1") {
        window.EduB1Intent.render(stepFormEl, spec, { intentRaw, genre, replyText });
        btnNext.textContent = "下一步";
      } else if (step === "B2") {
        window.EduB1Intent.destroy?.();
        if (b2SubStep === "creator") {
          stepTitleEl.textContent = "你的名字是？";
          stepSubtitleEl.textContent = "讲解员和证书上会这样叫你";
          stepSubtitleEl.hidden = false;
          btnPrev.disabled = !uiReady;
          window.EduB2Creator.render(stepFormEl, spec, { creatorName });
        } else {
          stepTitleEl.textContent = creatorName ? `你好，${creatorName}！` : "你好！";
          stepSubtitleEl.textContent = "";
          stepSubtitleEl.hidden = true;
          btnPrev.disabled = !uiReady;
          nameSuggestions = await window.EduB2Name.getSuggestions(genre, spec);
          window.EduB2Name.render(
            stepFormEl,
            spec,
            { genre, displayName, genreLabel, creatorName },
            nameSuggestions
          );
        }
        btnNext.textContent = "下一步";
      }
      return;
    }

    document.body.classList.remove("edu-step-b1", "edu-step-b2");
    document.body.classList.toggle("edu-step-dual-create", step === "B3" || step === "B4");
    document.body.classList.toggle("edu-step-b4", step === "B4");

    showPanel("dual");

    if (step === "B3") {
      mountDualPaneIfNeeded();
      window.EduDualPane.setDisplayName(displayName);
      window.EduDualPane.showGenrePreview(genre, genreLabel);
      paneRefs.codeWorkspace = window.EduDualPane.restoreCodeLayout();
      window.EduCodeViewer.mount(paneRefs.codeWorkspace);
      window.EduCodeViewer.setViewportPinned(true);
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
        <button type="button" id="btnDualNext" class="btn btn-primary b4-submit-btn" hidden>开始制作</button>
      `);
      bindDualToolbar();
      window.EduB4CardFlow?.syncSubmitButton?.();
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
    bindNavDismiss(document.getElementById("btnDualPrev"));
    bindNavDismiss(document.getElementById("btnDualNext"));
    document.getElementById("btnDualPrev")?.addEventListener("click", () => goPrev());
    document.getElementById("btnDualNext")?.addEventListener("click", () => goNext());
    document.getElementById("btnViewLeaderboard")?.addEventListener("click", () => {
      void openLeaderboardPanel();
    });
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

  /**
   * B5 制作前确保会话仍在；若中途被 A 链误杀，重建并重放关键状态。
   * @returns {Promise<string>}
   */
  async function ensureBuildSession() {
    const sid = await window.EduSession.ensureSession();
    try {
      if (intentRaw || genre) {
        await window.EduSession.api("/intent/match-genre", {
          method: "POST",
          body: JSON.stringify({
            text: intentRaw || genreLabel || genre,
            session_id: sid,
          }),
        });
      }
      if (creatorName) {
        await window.EduSession.api(`/sessions/${sid}`, {
          method: "PATCH",
          body: JSON.stringify({ creator_name: creatorName }),
        });
      }
      if (displayName) {
        await window.EduSession.api(`/sessions/${sid}/wizard/S0`, {
          method: "POST",
          body: JSON.stringify({ data: { display_name: displayName } }),
        }).catch(() => {});
      }
      if (Object.keys(creativeAnswers).length) {
        await window.EduSession.api(`/sessions/${sid}/creative/answers`, {
          method: "POST",
          body: JSON.stringify({ answers: creativeAnswers }),
        });
        await window.EduSession.api(`/sessions/${sid}/analyze-requirements`, {
          method: "POST",
          body: "{}",
        });
      }
    } catch (err) {
      window.EduSession.log(`同步会话状态失败 · ${err?.message || err}`);
    }
    return sid;
  }

  async function runBuildPipeline() {
    mountDualPaneIfNeeded();
    window.EduDualPane.setPhase("build");
    paneRefs.codeWorkspace = window.EduDualPane.restoreCodeLayout();
    setBuildWaitPanel("analyze", 8);
    window.EduDualPane.setToolbar(false);
    window.EduSession.protectRelease = true;

    let sessionId = window.EduSession.sessionId;
    let analyzeOk = false;

    try {
      sessionId = await ensureBuildSession();
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
              sessionId = await ensureBuildSession();
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
            } catch (err) {
              const msg = String(err?.message || err);
              window.EduSession.log(`制作失败 · ${msg}`);
              // 会话丢失时再重建一次
              if (msg.includes("404") || msg.includes("Session not found")) {
                try {
                  sessionId = await ensureBuildSession();
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
                } catch (err2) {
                  window.EduSession.log(`重试制作仍失败 · ${err2?.message || err2}`);
                }
              }
            }

            window.EduSession.protectRelease = false;
            window.EduSession.log(
              analyzeOk && genOk && workspacePath
                ? "✓ 制作完成"
                : "⚠ 制作未完成 · 可点讲解演示看代码，或重新开始"
            );
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
          line: 46,
          caption: "子弹打中怪物，血量归零就会被击败！",
          action_id: "kill_enemy",
        },
        pickup_xp: {
          file: "core/survivor_arena.gd",
          line: 142,
          caption: "吸收经验宝石就在这里，攒够就能升级！",
          action_id: "pickup_xp",
        },
        level_up: {
          file: "core/survivor_arena.gd",
          line: 152,
          caption: "升级啦！选一个增益技能吧！",
          action_id: "level_up",
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

  /** B7 gameplay action_id keys that must prefer core/*.gd over config tuning rows */
  const B7_GAMEPLAY_ACTION_IDS = new Set([
    "pickup",
    "kill_enemy",
    "hit",
    "jump",
    "slide",
    "collect_coin",
    "pickup_powerup",
    "pickup_xp",
    "level_up",
    "light_punch",
    "heavy_punch",
    "block",
    "special",
    "steer",
    "hit_npc",
    "hit_trap",
    "lap_complete",
    "stomp_enemy",
  ]);

  /**
   * @param {string} key
   * @param {{file?:string,action_id?:string}|undefined} existing
   * @param {{file?:string,action_id?:string}} incoming
   */
  function shouldKeepExistingCodeMapEntry(key, existing, incoming) {
    if (!B7_GAMEPLAY_ACTION_IDS.has(key) || !existing) return false;
    const inFile = String(incoming.file || "");
    const exFile = String(existing.file || "");
    if (!inFile.startsWith("config/") || !exFile.startsWith("core/")) return false;
    return !incoming.action_id;
  }

  function getMergedCodeMap() {
    const fallback = getGenreHighlightFallback(genre);
    const merged = { ...fallback };
    Object.entries(codeMap || {}).forEach(([key, entry]) => {
      if (!shouldKeepExistingCodeMapEntry(key, merged[key], entry)) {
        merged[key] = entry;
      }
      const actionId = entry.action_id;
      if (typeof actionId === "string" && actionId.length > 0) {
        if (!shouldKeepExistingCodeMapEntry(actionId, merged[actionId], entry)) {
          merged[actionId] = entry;
        }
      }
    });
    return merged;
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
   * @returns {string}
   */
  function getLaunchViewportBody() {
    const payload = window.EduOrientation?.getViewportPayload?.();
    return JSON.stringify(payload || {});
  }

  /**
   * @param {{ok:boolean,already_running?:boolean,pid?:number|null,project_path?:string,message?:string,waiting?:boolean,window_placed?:boolean,placement_rect?:object,orientation?:string}|null} data
   * @returns {string}
   */
  function renderLaunchStatusPanel(data) {
    if (!data) return "";
    if (data.waiting) {
      return `
        <div class="launch-status-inline launch-status-inline--waiting">
          <span class="launch-inline-spinner" aria-hidden="true"></span>
          <span id="launchStatus">正在启动游戏窗口…</span>
        </div>
      `;
    }
    if (data.ok) {
      const mainMsg = data.already_running
        ? "游戏已在运行 · 请到旁边窗口继续"
        : "Godot 已启动 · 请到游戏窗口试玩";
      const pid = data.pid != null ? String(data.pid) : "—";
      const path = data.project_path || "—";
      const orient = data.orientation || window.EduOrientation?.getMode?.() || "landscape";
      let placementHint = "";
      if (data.window_placed === true) {
        placementHint = `<p class="launch-placement-hint launch-placement-hint--ok">游戏窗口已自动贴到${orient === "portrait" ? "屏幕下方" : "屏幕右侧"}</p>`;
      } else if (data.window_placed === false) {
        placementHint = `<p class="launch-placement-hint launch-placement-hint--manual">请在屏幕${orient === "portrait" ? "下方" : "右侧"}找到游戏窗口</p>`;
      }
      return `
        <div class="launch-status-inline launch-status-inline--ok">
          <span class="launch-inline-icon" aria-hidden="true">✓</span>
          <span class="launch-status ok" id="launchStatus">${mainMsg}</span>
          ${placementHint}
          <details class="launch-details launch-details--compact">
            <summary>技术信息</summary>
            <p class="launch-meta">进程 PID：${pid}</p>
            <p class="launch-meta">项目路径：${path}</p>
          </details>
          <p class="godot-run-status" id="godotRunStatus" aria-live="polite"></p>
        </div>
      `;
    }
    const errMsg = data.message || "游戏暂时无法启动，请讲解员协助";
    return `
      <div class="launch-status-inline launch-status-inline--err">
        <span class="launch-inline-icon" aria-hidden="true">!</span>
        <p class="launch-status err" id="launchStatus">${errMsg}</p>
        <p class="hint">可点「重新试玩」再试一次，或先看左侧代码高亮演示</p>
      </div>
    `;
  }

  /** @typedef {{ actionId: string, label: string, icon: string, ariaLabel: string }} GenreDemoAction */

  /** @type {Record<string, GenreDemoAction[]>} */
  const GENRE_DEMO_ACTIONS = {
    platformer: [
      { actionId: "jump", label: "跳！", icon: "⬆️", ariaLabel: "讲解员演示用：模拟跳跃" },
      { actionId: "stomp_enemy", label: "踩怪", icon: "👾", ariaLabel: "讲解员演示用：模拟踩怪" },
      { actionId: "collect_coin", label: "捡金币", icon: "🪙", ariaLabel: "讲解员演示用：模拟捡金币" },
    ],
    pingpong: [
      { actionId: "rally", label: "击球", icon: "🏓", ariaLabel: "讲解员演示用：模拟击球" },
      { actionId: "score", label: "得分", icon: "⭐", ariaLabel: "讲解员演示用：模拟得分" },
    ],
    shmup: [
      { actionId: "kill_enemy", label: "打敌机", icon: "✈️", ariaLabel: "讲解员演示用：模拟击毁敌机" },
      { actionId: "pickup", label: "吃道具", icon: "🎁", ariaLabel: "讲解员演示用：模拟吃道具" },
    ],
    survivor: [
      { actionId: "kill_enemy", label: "消灭", icon: "👾", ariaLabel: "讲解员演示用：模拟消灭敌人" },
      { actionId: "pickup_xp", label: "吸经验", icon: "✨", ariaLabel: "讲解员演示用：模拟吸收经验" },
      { actionId: "level_up", label: "升级", icon: "⬆️", ariaLabel: "讲解员演示用：模拟升级" },
    ],
    fighting: [
      { actionId: "light_punch", label: "轻拳", icon: "👊", ariaLabel: "讲解员演示用：模拟轻拳" },
      { actionId: "heavy_punch", label: "重拳", icon: "💪", ariaLabel: "讲解员演示用：模拟重拳" },
      { actionId: "block", label: "格挡", icon: "🛡️", ariaLabel: "讲解员演示用：模拟格挡" },
      { actionId: "special", label: "大招", icon: "⚡", ariaLabel: "讲解员演示用：模拟大招" },
    ],
    parkour: [
      { actionId: "jump", label: "跳跃", icon: "⬆️", ariaLabel: "讲解员演示用：模拟跳跃" },
      { actionId: "slide", label: "滑铲", icon: "⤵️", ariaLabel: "讲解员演示用：模拟滑铲" },
      { actionId: "collect_coin", label: "捡金币", icon: "🪙", ariaLabel: "讲解员演示用：模拟捡金币" },
      { actionId: "pickup_powerup", label: "吃道具", icon: "🎁", ariaLabel: "讲解员演示用：模拟吃道具" },
    ],
    racing: [
      { actionId: "hit_npc", label: "撞车", icon: "🚗", ariaLabel: "讲解员演示用：模拟撞车" },
      { actionId: "hit_trap", label: "撞路障", icon: "🚧", ariaLabel: "讲解员演示用：模拟撞路障" },
      { actionId: "lap_complete", label: "完圈", icon: "🏁", ariaLabel: "讲解员演示用：模拟完圈" },
    ],
  };

  /**
   * @param {string} genreSlug
   * @param {{ launched?: boolean }} [opts]
   * @returns {GenreDemoAction[]}
   */
  function getGenreDemoActions(genreSlug, opts = {}) {
    const launched = !!opts.launched;
    const actions = GENRE_DEMO_ACTIONS[genreSlug] || GENRE_DEMO_ACTIONS.platformer;
    if (genreSlug === "shmup" && launched) {
      return actions.filter((a) => a.actionId !== "hit");
    }
    return actions;
  }

  /**
   * @param {string} genreSlug
   * @param {{ compact?: boolean, launched?: boolean }} [opts]
   * @returns {string}
   */
  function renderGenreDemoActionsHtml(genreSlug, opts = {}) {
    const compact = !!opts.compact;
    const actions = getGenreDemoActions(genreSlug, opts);
    return actions.map((action) => {
      const iconHtml = compact
        ? ""
        : `<span class="btn-demo-action__icon" aria-hidden="true">${action.icon}</span>`;
      return `
        <button type="button" class="btn-demo-action" data-demo-action="${action.actionId}" aria-label="${action.ariaLabel}">
          ${iconHtml}
          <span>${action.label}</span>
        </button>
      `;
    }).join("");
  }

  /**
   * S-A3 / S-B6 · AI 改代码入口按钮（放在讲解演示下方并放大，触控友好 ≥ 56px）。
   * @returns {string}
   */
  function renderAiPatchButtonHtml() {
    return `
      <button type="button" id="btnAiPatch" class="btn-ai-patch" aria-label="用 AI 改游戏参数">
        <span class="btn-ai-patch__icon" aria-hidden="true">🤖</span>
        <span class="btn-ai-patch__body">
          <span class="btn-ai-patch__title">用 AI 改游戏</span>
          <span class="btn-ai-patch__sub">说一句话，让 AI 帮你调整游戏</span>
        </span>
      </button>
    `;
  }

  function bindAiPatchButton() {
    const root = document.getElementById("paneRightInner");
    const btn = root?.querySelector("#btnAiPatch");
    btn?.addEventListener("click", () => openAiPatchDialog());
  }

  /** 打开 AI 改代码对话框（S-A3/N-5）。完成后可「用新参数试玩」→ force relaunch。 */
  function openAiPatchDialog() {
    if (!window.EduNlPatchDialog) {
      window.EduSession.log("AI 改代码组件未就绪");
      return;
    }
    window.EduNlPatchDialog.open({
      sessionId: window.EduSession.sessionId,
      genre,
      onReplay: () => {
        void launchCurrentGame({ force: true, reason: "ai-patch" });
      },
    });
  }

  /**
   * @param {string} genreSlug
   * @param {{ launched?: boolean }} [opts]
   */
  function bindGenreDemoActions(genreSlug, opts = {}) {
    const actions = getGenreDemoActions(genreSlug, opts);
    const root = document.getElementById("paneRightInner");
    if (!root) return;
    actions.forEach((action) => {
      const btn = root.querySelector(`[data-demo-action="${action.actionId}"]`);
      btn?.addEventListener("click", () => {
        window.EduCodeHighlight.simulateAction(action.actionId);
      });
    });
  }

  /**
   * @param {"full"|"auto_flash"} [mode]
   */
  function showCertificateOverlay(mode = "full") {
    if (!window.EduCertificate) return;
    if (!certificateCreatedAt) {
      certificateCreatedAt = new Date();
    }
    window.EduCertificate.show({
      displayName,
      creatorName,
      genreLabel: creativeTemplate?.display_name || genreLabel || genre,
      genre,
      genreEmoji: window.EduB1Intent?.emoji(genre),
      sessionId: window.EduSession?.sessionId || "",
      questions: creativeTemplate?.questions || [],
      answers: creativeAnswers,
      createdAt: certificateCreatedAt,
      mode,
    });
  }

  /**
   * @param {string} [genreEmoji]
   * @returns {string}
   */
  function renderPlayReadyPanel(genreEmoji) {
    const icon = genreEmoji || "🎮";
    return `
      <div class="pane-right-stack">
        <div class="play-ready-hero">
          <div class="play-ready-badge" aria-hidden="true">✨ 制作完成</div>
          <div class="play-ready-icon-wrap">
            <span class="play-ready-icon-ring"></span>
            <span class="play-ready-icon">${icon}</span>
          </div>
          <h3 class="play-ready-title">你的游戏做好啦！</h3>
          <p class="play-ready-sub">点下面的大按钮，在旁边的 Godot 窗口里试玩</p>
          <button type="button" id="btnLaunch" class="btn-play-launch">
            <span class="btn-play-launch__shine" aria-hidden="true"></span>
            <span class="btn-play-launch__icon" aria-hidden="true">▶</span>
            <span class="btn-play-launch__text">开始试玩</span>
          </button>
          <div id="launchStatusWrap" class="play-ready-status">${renderLaunchStatusPanel(launchState)}</div>
        </div>
        <div class="demo-panel-card">
          <p class="demo-panel-label">🎤 讲解员演示区</p>
          <p class="demo-panel-hint">点击下方按钮，左边代码会亮起对应行</p>
          <div class="demo-panel-actions demo-panel-actions--wrap">
            ${renderGenreDemoActionsHtml(genre, { compact: false, launched: false })}
          </div>
          ${renderAiPatchButtonHtml()}
        </div>
      </div>
    `;
  }

  function stopLaunchStatusPolling() {
    if (launchStatusPollTimer) {
      window.clearInterval(launchStatusPollTimer);
      launchStatusPollTimer = null;
    }
    prevGodotRunning = false;
    sawGodotRunning = false;
  }

  function updateLeaderboardButton() {
    const btn = document.getElementById("btnLeaderboard");
    if (!btn) return;
    const enabled = window.EduSession?.spec?.leaderboard?.daily_enabled !== false;
    const show = enabled && genre && window.EduLeaderboard?.LEADERBOARD_GENRES?.has(genre);
    btn.hidden = !show;
  }

  async function openLeaderboardPanel() {
    if (!window.EduLeaderboard?.openDaily) return;
    await window.EduLeaderboard.openDaily(genre || "platformer");
  }

  /**
   * @param {string} sessionId
   */
  async function handleLeaderboardAfterRunClose(sessionId) {
    if (!window.EduLeaderboard?.LEADERBOARD_GENRES?.has(genre)) return;
    if (leaderboardHandledThisRun) return;
    leaderboardHandledThisRun = true;
    sawGodotRunning = false;

    await new Promise((resolve) => window.setTimeout(resolve, 450));

    const result = await window.EduLeaderboard.submitAfterRun({
      sessionId,
      genre,
      creatorName,
      displayName,
    });
    window.EduLeaderboard.open({
      genre,
      entries: result.entries || [],
      highlightSessionId: result.skippedSubmit ? null : sessionId,
      highlightCreatedAt: result.skippedSubmit ? null : result.entry?.created_at || null,
      degraded: !!result.degraded,
      fallbackEntry: result.entry,
    });
  }

  /**
   * @param {string} sessionId
   */
  async function pollLaunchStatus(sessionId) {
    const statusEl = document.getElementById("godotRunStatus");
    try {
      const status = await window.EduSession.api(`/sessions/${sessionId}/play/status`);
      if (status.running === true) {
        sawGodotRunning = true;
        prevGodotRunning = true;
        if (statusEl) {
          statusEl.textContent = "● 游戏运行中";
          statusEl.className = "godot-run-status running";
        }
        return;
      }

      if (statusEl) {
        statusEl.textContent = "○ 游戏窗口已关闭";
        statusEl.className = "godot-run-status stopped";
      }
      // N-4 · 关窗后把「运行中」死态改为「已关闭」，引导重新试玩
      if (sawGodotRunning) {
        const hint = document.getElementById("playWindowHint");
        const title = document.getElementById("playWindowTitle");
        const hintText = document.getElementById("playWindowHintText");
        if (hint) hint.classList.add("play-window-hint--closed");
        if (title) title.textContent = "游戏已关闭";
        if (hintText) hintText.textContent = "点「重新试玩」再玩一次，或看看今日榜单";
      }

      const elapsed = Date.now() - launchPollStartedAt;
      const closedAfterRun =
        genre === "pingpong"
          ? sawGodotRunning
          : sawGodotRunning || (!!launchState?.ok && elapsed >= 1200);
      const shouldHandle =
        closedAfterRun &&
        window.EduLeaderboard?.LEADERBOARD_GENRES?.has(genre) &&
        !leaderboardHandledThisRun;
      if (shouldHandle) {
        await handleLeaderboardAfterRunClose(sessionId);
      }
      prevGodotRunning = false;
    } catch (_) {
      /* 可选 UI · 静默 */
    }
  }

  /**
   * @param {string} sessionId
   */
  function startLaunchStatusPolling(sessionId) {
    stopLaunchStatusPolling();
    leaderboardHandledThisRun = false;
    launchPollStartedAt = Date.now();
    sawGodotRunning = !!(launchState && launchState.ok && launchState.already_running);
    void pollLaunchStatus(sessionId);
    launchStatusPollTimer = window.setInterval(() => {
      void pollLaunchStatus(sessionId);
    }, 1500);
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
    window.EduCodeViewer?.setViewportPinned(false);
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

    window.EduDualPane.setRightContent(
      renderPlayReadyPanel(window.EduB1Intent?.emoji(genre))
    );

    document.getElementById("btnLaunch")?.addEventListener("click", () =>
      launchCurrentGame({ force: false, reason: "start" })
    );
    bindGenreDemoActions(genre, { launched: false });
    bindAiPatchButton();

    window.EduDualPane.setToolbar(true, `
      <button type="button" id="btnDualPrev" class="btn btn-secondary" disabled>上一步</button>
      <button type="button" id="btnViewLeaderboard" class="btn btn-secondary">今日榜单</button>
      <button type="button" id="btnDualNext" class="btn btn-primary">进入试玩</button>
    `);
    bindDualToolbar();
    // S-B1 · 进入 B6 自动闪现证书约 3 秒后消失（闪现态无保存钮，不阻断开始试玩）
    showCertificateOverlay("auto_flash");
  }

  /**
   * S-B3 · 统一启动通路：开始试玩 / 重新试玩 / AI 用新参数试玩共用。
   * force=true 时后端会结束旧 Godot 并重启，读到最新 game_config.json（N-5）。
   * @param {{ force?: boolean, reason?: string }} [opts]
   */
  async function launchCurrentGame(opts = {}) {
    if (launchInFlight) return;
    const force = !!opts.force;
    launchInFlight = true;

    const launchBtns = ["btnLaunch", "btnReplay"]
      .map((id) => /** @type {HTMLButtonElement|null} */ (document.getElementById(id)))
      .filter(Boolean);
    launchBtns.forEach((b) => {
      if (b) b.disabled = true;
    });

    launchState = { ok: false, waiting: true };
    const wrap = document.getElementById("launchStatusWrap");
    if (wrap) wrap.innerHTML = renderLaunchStatusPanel(launchState);

    try {
      let sessionId = await ensureBuildSession();
      // 若制作阶段未写出 workspace，启动前补一次 generate
      if (!workspacePath) {
        try {
          const gen = await window.EduSession.api(`/sessions/${sessionId}/generate/v2`, {
            method: "POST",
            body: JSON.stringify({
              meta: { genre, display_name: displayName },
              creative_answers: creativeAnswers,
            }),
          });
          workspacePath = gen.workspace_path || "";
          if (gen.code_map) codeMap = gen.code_map;
        } catch (err) {
          window.EduSession.log(`补做 generate 失败 · ${err?.message || err}`);
        }
      }

      const path = `/sessions/${sessionId}/play/launch${force ? "?force=true" : ""}`;
      const data = await window.EduSession.api(path, {
        method: "POST",
        body: getLaunchViewportBody(),
      });
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
        window_placed: data.window_placed,
        placement_rect: data.placement_rect || null,
        orientation: window.EduOrientation?.getMode?.() || "landscape",
      };
      leaderboardHandledThisRun = false;
      launchPollStartedAt = Date.now();
      sawGodotRunning = !!data.already_running;
      window.EduSession.log(
        force ? "✓ 已用新参数重新启动" : launchState.already_running ? "✓ 游戏已在运行" : "✓ Godot 已启动"
      );
      stepIndex = STEPS.indexOf("B7");
      await renderStep();
    } catch (err) {
      const msg = parseLaunchError(err);
      launchState = { ok: false, message: msg };
      window.EduSession.log(`play/launch 失败 · ${msg}`);
      if (wrap) wrap.innerHTML = renderLaunchStatusPanel(launchState);
    } finally {
      launchInFlight = false;
      launchBtns.forEach((b) => {
        if (b) b.disabled = false;
      });
    }
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

    window.EduDualPane.setRightContent(`
      <div class="pane-right-stack">
        <div class="godot-frame-wrap play-active-wrap">
          ${launched ? renderLaunchStatusPanel(launchState) : ""}
          <div class="play-window-hint play-window-hint--active" id="playWindowHint">
            <span class="play-window-icon" aria-hidden="true">🎮</span>
            <p class="play-window-title" id="playWindowTitle">游戏已全屏铺满显示器</p>
            <p class="hint" id="playWindowHintText">请在游戏窗口试玩；玩完关闭窗口即可看今日榜</p>
          </div>
        </div>
        <div class="demo-panel-card demo-panel-card--compact">
          <p class="demo-panel-label">🎤 讲解员演示</p>
          <div class="demo-panel-actions demo-panel-actions--wrap">
            ${renderGenreDemoActionsHtml(genre, { compact: true, launched })}
          </div>
          ${renderAiPatchButtonHtml()}
        </div>
      </div>
    `);

    if (launched) {
      window.EduCodeHighlight.startPolling(window.EduSession.sessionId);
      startLaunchStatusPolling(window.EduSession.sessionId);
    } else if (workspacePath) {
      window.EduCodeHighlight.startPolling(window.EduSession.sessionId);
    }

    bindGenreDemoActions(genre, { launched });
    bindAiPatchButton();

    window.EduDualPane.setToolbar(true, `
      <button type="button" id="btnReplay" class="btn btn-primary">▶ 重新试玩</button>
      <button type="button" id="btnViewLeaderboard" class="btn btn-secondary">今日榜单</button>
      <button type="button" id="btnViewCertificate" class="btn btn-secondary">查看证书</button>
      <button type="button" id="btnFinish" class="btn btn-secondary">完成创作</button>
    `);
    document.getElementById("btnReplay")?.addEventListener("click", () =>
      launchCurrentGame({ force: true, reason: "replay" })
    );
    document.getElementById("btnViewCertificate")?.addEventListener("click", () => {
      showCertificateOverlay("full");
    });
    document.getElementById("btnViewLeaderboard")?.addEventListener("click", () => {
      void openLeaderboardPanel();
    });
    document.getElementById("btnFinish")?.addEventListener("click", () => resetWizard());
  }

  async function goNext() {
    const step = currentStep();

    if (step === "B1") {
      intentRaw = window.EduB1Intent.getInput(stepFormEl);
      if (!intentRaw) return;
      btnNext.disabled = true;
      try {
        const match = await window.EduB1Intent.matchGenre(intentRaw, window.EduSession.sessionId);
        genre = match.matched_genre || "platformer";
        replyText = match.reply_text || "";
        const names = spec.genre_display_names || {};
        genreLabel = names[genre] || genre;
        stepIndex += 1;
        await renderStep();
      } catch (err) {
        window.EduSession.log(`B1 匹配失败 · ${err.message || err}`);
      } finally {
        btnNext.disabled = false;
      }
      return;
    }

    if (step === "B2") {
      if (b2SubStep === "creator") {
        if (window.EduB2Creator.isComposing?.(stepFormEl)) {
          window.EduB2Creator.showValidationError(stepFormEl, "请选字确认后再点下一步");
          return;
        }
        window.EduB2Creator.commitComposition?.(stepFormEl);
        creatorName = window.EduB2Creator.getInput(stepFormEl);
        if (!window.EduB2Creator.isValid(creatorName)) {
          const raw = stepFormEl.querySelector("#creatorInput")?.value || "";
          const msg = /[a-zA-Z]{2,}/.test(String(raw))
            ? "请从拼音里选中文，再点下一步"
            : "请先填写你的名字（1–8 个字）";
          window.EduB2Creator.showValidationError(stepFormEl, msg);
          return;
        }
        window.EduB2Creator.clearValidationError(stepFormEl);
        try {
          await window.EduSession.apiWithSession(`/sessions/${window.EduSession.sessionId}`, {
            method: "PATCH",
            body: JSON.stringify({ creator_name: creatorName }),
          });
        } catch (err) {
          window.EduSession.log(`保存名字失败 · ${err.message}`);
          const msg = String(err.message || "").includes("无法连接")
            ? "无法连接创作工坊，请检查网络或联系老师"
            : "保存失败，请重试";
          window.EduB2Creator.showValidationError(stepFormEl, msg);
          return;
        }
        b2SubStep = "gameName";
        await renderStep();
        return;
      }

      displayName = window.EduB2Name.getInput(stepFormEl);
      if (!window.EduB2Name.isValid(displayName)) {
        window.EduB2Name.showValidationError(stepFormEl);
        return;
      }
      window.EduB2Name.clearValidationError(stepFormEl);
      try {
        await window.EduSession.apiWithSession(`/sessions/${window.EduSession.sessionId}/wizard/S0`, {
          method: "POST",
          body: JSON.stringify({ data: { display_name: displayName } }),
        });
      } catch (err) {
        window.EduSession.log(`保存游戏名称失败 · ${err.message}`);
      }
      window.EduTouchKeyboard?.dismissForNavigation?.();
      if (window.EduForgeReveal?.play) {
        await window.EduForgeReveal.play({
          creatorName,
          displayName,
          genre,
          genreLabel,
        });
      }
      b2SubStep = "creator";
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
    if (currentStep() === "B2" && b2SubStep === "gameName") {
      b2SubStep = "creator";
      await renderStep();
      return;
    }
    if (currentStep() === "B4" && window.EduB4CardFlow?.canGoPrev?.()) {
      await window.EduB4CardFlow.prev();
      return;
    }
    window.EduCodeTheater.stop();
    window.EduCodeHighlight.stopPolling();
    stopLaunchStatusPolling();
    stepIndex -= 1;
    if (currentStep() === "B2") {
      b2SubStep = creatorName ? "gameName" : "creator";
    }
    if (currentStep() === "B3") paneRefs.codeWorkspace = null;
    await renderStep();
  }

  async function resetWizard() {
    window.EduSession.protectRelease = false;
    window.EduCertificate?.hide();
    window.EduCodeViewer?.setViewportPinned(false);
    window.EduGenreTheme?.clear?.();
    certificateCreatedAt = null;
    window.EduCodeTheater.stop();
    window.EduCodeHighlight.stopPolling();
    stopLaunchStatusPolling();
    launchState = null;
    sawGodotRunning = false;
    leaderboardHandledThisRun = false;
    await window.EduSession.releaseAsync();
    genre = "";
    genreLabel = "";
    displayName = "";
    creatorName = "";
    b2SubStep = "creator";
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

  async function hydrateSessionMeta() {
    const sessionId = window.EduSession.sessionId;
    if (!sessionId || sessionId.startsWith("demo-")) return;
    try {
      const record = await window.EduSession.api(`/sessions/${sessionId}`);
      if (record.creator_name) creatorName = String(record.creator_name);
      if (record.display_name) displayName = String(record.display_name);
    } catch (_) {
      /* 演示模式或无 GET · 静默 */
    }
  }

  async function init() {
    showPanel("welcome");
    const statusEl = el("bootstrapStatus");

    bindNavDismiss(btnNext);
    bindNavDismiss(btnPrev);
    btnNext.addEventListener("click", () => goNext());
    btnPrev.addEventListener("click", () => goPrev());
    btnReset.addEventListener("click", () => resetWizard());
    document.getElementById("btnLeaderboard")?.addEventListener("click", () => {
      void openLeaderboardPanel();
    });

    try {
      await window.EduSession.bootstrap();
      spec = window.EduSession.spec;
      await hydrateSessionMeta();
      window.EduOrientation?.configure(/** @type {{orientation_breakpoint_px?: number}} */ (spec.layout));
      window.EduOrientation?.mount();
      window.EduTouchKeyboard?.init();
      window.EduCodeHighlight.configure(spec);
      if (statusEl) statusEl.textContent = "准备就绪！";
      setUiEnabled(true);
      stepIndex = 1;
      await renderStep();
    } catch (err) {
      spec = window.EduSession.spec || {};
      window.EduOrientation?.configure(/** @type {{orientation_breakpoint_px?: number}} */ (spec.layout));
      window.EduOrientation?.mount();
      window.EduTouchKeyboard?.init();
      window.EduCodeHighlight.configure(spec);
      if (statusEl) statusEl.textContent = "演示模式（后端未连接）";
      setUiEnabled(true);
      stepIndex = 1;
      await renderStep();
    }
  }

  window.EduWizard = {
    get spec() {
      return spec;
    },
    init,
    currentStep,
    resetWizard,
    fetchWorkspaceFile,
    fetchPreviewFile,
    hasWorkspace: () => !!workspacePath,
    setUiEnabled,
  };
  document.addEventListener("DOMContentLoaded", () => init());
})();
