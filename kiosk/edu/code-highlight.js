/* B7 · 操作 ↔ 代码高亮 · 轮询 play/actions */
(() => {
  "use strict";

  /** @type {number|null} */
  let pollTimer = null;
  /** @type {number|null} */
  let captionTimer = null;
  /** @type {number} */
  let actionCursor = 0;
  /** @type {Record<string, number>} */
  let lastActionAt = {};
  /** @type {Record<string, {file:string,line:number,caption:string,_priority?:number}>} */
  let codeMap = {};
  /** @type {number} */
  let presentationLockUntil = 0;
  /** @type {number} */
  let presentationLockPriority = 0;
  /** @type {{poll_interval_ms:number,debounce_ms:number,highlight_duration_ms:number,caption_duration_ms:number,suppress_actions?:string[],action_priority?:Record<string,number>,fire_debounce_ms?:number}} */
  let config = {
    poll_interval_ms: 200,
    debounce_ms: 500,
    highlight_duration_ms: 2000,
    caption_duration_ms: 3000,
    suppress_actions: ["fire", "boost", "move"],
    action_priority: {
      steer: 1,
      fire: 1,
      boost: 2,
      move: 1,
      jump: 9,
      slide: 9,
      hit: 7,
      pickup: 9,
      pickup_xp: 10,
      level_up: 10,
      pickup_powerup: 9,
      collect_coin: 9,
      stomp_enemy: 9,
      light_punch: 9,
      heavy_punch: 9,
      block: 9,
      special: 9,
      kill_enemy: 10,
      hit_npc: 9,
      hit_trap: 9,
      lap_complete: 8,
    },
  };

  const DEFAULT_ACTION_PRIORITY = {
    steer: 1,
    fire: 1,
    boost: 2,
    move: 1,
    jump: 9,
    slide: 9,
    hit: 7,
    pickup: 9,
    pickup_xp: 10,
    level_up: 10,
    pickup_powerup: 9,
    collect_coin: 9,
    stomp_enemy: 9,
    light_punch: 9,
    heavy_punch: 9,
    block: 9,
    special: 9,
    kill_enemy: 10,
    hit_npc: 9,
    hit_trap: 9,
    lap_complete: 8,
  };

  /**
   * @param {string} actionId
   * @returns {number}
   */
  function actionPriority(actionId) {
    const fromConfig = config.action_priority?.[actionId];
    if (typeof fromConfig === "number") return fromConfig;
    return DEFAULT_ACTION_PRIORITY[actionId] ?? 5;
  }

  const EduCodeHighlight = {
    /**
     * @param {Record<string, unknown>} spec
     */
    configure(spec) {
      if (spec.code_highlight) {
        config = { ...config, ...spec.code_highlight };
      }
    },

    /**
     * @param {Record<string, {file?:string,line?:number,caption?:string,path?:string,action_id?:string,line_hint?:number}>} map
     */
    setCodeMap(map) {
      codeMap = {};
      Object.entries(map || {}).forEach(([id, entry]) => {
        const normalized = {
          file: entry.file || "config/game_config.json",
          line: entry.line || entry.line_hint || 12,
          caption: entry.caption || "",
        };

        const register = (/** @type {string} */ key) => {
          const keyPriority = actionPriority(key);
          const existing = codeMap[key];
          if (!existing || keyPriority >= (existing._priority ?? 0)) {
            codeMap[key] = { ...normalized, _priority: keyPriority };
          }
        };

        register(id);
        const actionId = entry.action_id || id;
        if (actionId && actionId !== id) {
          register(actionId);
        }
      });
    },

    /**
     * @param {string} actionId
     */
    async handleAction(actionId) {
      if ((config.suppress_actions || []).includes(actionId)) return;

      const now = Date.now();
      if (now >= presentationLockUntil) {
        presentationLockUntil = 0;
        presentationLockPriority = 0;
      }

      const priority = actionPriority(actionId);

      if (priority < presentationLockPriority && now < presentationLockUntil) return;
      if (priority <= 1 && now < presentationLockUntil) return;

      const last = lastActionAt[actionId] || 0;
      const debounceMs =
        actionId === "fire" ? Number(config.fire_debounce_ms) || 12000 : config.debounce_ms;
      if (now - last < debounceMs) return;
      lastActionAt[actionId] = now;

      const anchor = codeMap[actionId];
      if (!anchor) {
        window.EduSession?.log(`TODO: code_map 缺少 action_id=${actionId}`);
        return;
      }

      presentationLockPriority = priority;
      presentationLockUntil = now + config.caption_duration_ms + config.highlight_duration_ms;

      const file = anchor.file || "config/game_config.json";
      const currentFile = window.EduCodeViewer?.getCurrentFile?.() || "";
      if (window.EduWizard?.fetchWorkspaceFile && file !== currentFile) {
        try {
          if (file.startsWith("config/") || file.startsWith("core/")) {
            await window.EduWizard.fetchWorkspaceFile(file);
          } else if (window.EduWizard.fetchPreviewFile) {
            await window.EduWizard.fetchPreviewFile(file);
          }
        } catch (err) {
          const msg = err instanceof Error ? err.message : String(err);
          window.EduSession.log(`加载 ${file} 失败 · ${msg}`);
        }
      }

      if (window.EduCodeViewer) {
        window.EduCodeViewer.setActiveFile(file);
        const hit = window.EduCodeViewer.highlightLine(
          anchor.line,
          config.highlight_duration_ms
        );
        if (!hit) {
          console.warn(
            `EduCodeHighlight: 未高亮 ${file}:${anchor.line}（文件未加载或行号不存在）`
          );
        }
      }

      if (anchor.caption) this.showCaption(anchor.caption, priority);
    },

    /**
     * @param {string} text
     * @param {number} [priority]
     */
    showCaption(text, priority = 5) {
      const bubble = document.getElementById("captionBubble");
      if (!bubble) return;
      if (priority < presentationLockPriority && Date.now() < presentationLockUntil) return;
      if (captionTimer) {
        window.clearTimeout(captionTimer);
        captionTimer = null;
      }
      bubble.textContent = text;
      bubble.hidden = false;
      presentationLockPriority = Math.max(presentationLockPriority, priority);
      captionTimer = window.setTimeout(() => {
        bubble.hidden = true;
        captionTimer = null;
      }, config.caption_duration_ms);
    },

    /** 演示模式：无 Godot 桥时手动模拟 action */
    simulateAction(actionId) {
      void this.handleAction(actionId);
    },

    /**
     * @param {string} sessionId
     */
    startPolling(sessionId) {
      this.stopPolling();
      actionCursor = 0;
      presentationLockUntil = 0;
      presentationLockPriority = 0;
      pollTimer = window.setInterval(async () => {
        try {
          const data = await window.EduSession.api(
            `/sessions/${sessionId}/play/actions?since=${actionCursor}`
          );
          const actions = (data.actions || []).slice();
          actions.sort(
            (a, b) => actionPriority(b.action_id) - actionPriority(a.action_id)
          );
          for (const /** @type {{action_id:string,t_ms?:number,cursor?:number}} */ a of actions) {
            const eventMs = a.t_ms ?? a.cursor ?? 0;
            if (eventMs > 0) actionCursor = Math.max(actionCursor, eventMs);
            await this.handleAction(a.action_id);
          }
        } catch (_) {
          /* TODO: GET /sessions/{id}/play/actions 未就绪时静默 */
        }
      }, config.poll_interval_ms);
    },

    stopPolling() {
      if (pollTimer) {
        window.clearInterval(pollTimer);
        pollTimer = null;
      }
      if (captionTimer) {
        window.clearTimeout(captionTimer);
        captionTimer = null;
      }
    },
  };

  window.EduCodeHighlight = EduCodeHighlight;
})();
