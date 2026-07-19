/* Kiosk · Windows TabTip 触控软键盘
 * 规则：只在点中 edu-touch-input 时唤起；点空白收起；短防抖避免 show/hide 互抢。
 */
(() => {
  "use strict";

  /** @type {boolean} */
  let initialized = false;
  /** @type {"show"|"hide"|null} */
  let keyboardIntent = null;
  /** @type {AbortController|null} */
  let inflight = null;
  /** @type {number} */
  let actionSeq = 0;
  /** @type {number} */
  let showGuardUntil = 0;
  /** @type {number} */
  let focusOutTimer = 0;
  /** @type {number} */
  let suppressShowUntil = 0;
  /** @type {HTMLInputElement|HTMLTextAreaElement|null} */
  let activeTouchInput = null;

  const SELECTOR = "input.edu-touch-input, textarea.edu-touch-input, [data-edu-keyboard]";
  /** 点这些区域不收起（随后会把焦点送回输入框） */
  const KEEP_OPEN_SELECTOR =
    ".edu-nlpatch-chip, [data-edu-keyboard-keep], label[for]";
  const SHOW_GUARD_MS = 400;
  const FOCUS_OUT_DELAY_MS = 120;
  /** 点发送/导航后短暂禁 show，避免 TabTip toggle 误开或 focus 回弹再唤起 */
  const SUPPRESS_SHOW_MS = 1200;

  /** @returns {string} */
  function apiBase() {
    return window.EduSession?.apiBase || "http://127.0.0.1:8000";
  }

  /** @returns {string} */
  function keyboardProvider() {
    const spec = window.EduSession?.spec;
    const provider = spec?.touch_keyboard?.provider;
    if (provider === "tabtip" || provider === "sogou_hand" || provider === "auto") {
      return provider;
    }
    return "auto";
  }

  /** @returns {void} */
  function hideVirtualKeyboardApi() {
    try {
      navigator.virtualKeyboard?.hide();
    } catch (_) {
      /* ignore */
    }
  }

  /** @returns {void} */
  function showVirtualKeyboardApi() {
    try {
      if (navigator.virtualKeyboard) {
        navigator.virtualKeyboard.overlaysContent = true;
        navigator.virtualKeyboard.show();
      }
    } catch (_) {
      /* ignore */
    }
  }

  /**
   * @param {"show"|"hide"} action
   * @returns {void}
   */
  function postKeyboardRequest(action) {
    inflight?.abort();
    inflight = new AbortController();
    const seq = ++actionSeq;

    const path = action === "show" ? "show" : "hide";
    const url = `${apiBase()}/kiosk/touch-keyboard/${path}`;
    const options = {
      method: "POST",
      keepalive: true,
      mode: "cors",
      headers: { "Content-Type": "application/json" },
      signal: inflight.signal,
    };
    if (action === "show") {
      options.body = JSON.stringify({ provider: keyboardProvider() });
    }

    fetch(url, options)
      .then(() => {
        if (seq !== actionSeq) return;
      })
      .catch(() => {
        /* 后端未启动时静默降级 */
      });
  }

  /**
   * @param {"show"|"hide"} action
   * @param {{ force?: boolean }} [opts]
   * @returns {void}
   */
  function postKeyboard(action, opts) {
    const force = !!opts?.force;
    if (action === "hide" && !force && Date.now() < showGuardUntil) {
      return;
    }
    if (action === "show" && keyboardIntent === "show" && Date.now() < showGuardUntil) {
      /* 刚唤起过：忽略重复 show，避免 TabTip 状态抖动 */
      return;
    }

    keyboardIntent = action;
    if (action === "show") {
      showGuardUntil = Date.now() + SHOW_GUARD_MS;
      showVirtualKeyboardApi();
    } else {
      hideVirtualKeyboardApi();
    }
    postKeyboardRequest(action);
  }

  /**
   * @param {EventTarget|null|undefined} el
   * @returns {boolean}
   */
  function isTouchInput(el) {
    if (!(el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement)) {
      return false;
    }
    return el.matches(SELECTOR) || el.classList.contains("edu-touch-input");
  }

  /** @returns {void} */
  function clearFocusOutTimer() {
    if (focusOutTimer) {
      window.clearTimeout(focusOutTimer);
      focusOutTimer = 0;
    }
  }

  /** @returns {void} */
  function blurActiveTouchInput() {
    const active = document.activeElement;
    if (isTouchInput(active)) {
      active.blur();
    }
    activeTouchInput = null;
  }

  /** @returns {void} */
  function showKeyboard() {
    if (Date.now() < suppressShowUntil) {
      return;
    }
    postKeyboard("show");
  }

  /**
   * @param {{ force?: boolean }} [opts]
   * @returns {void}
   */
  function hideKeyboard(opts) {
    postKeyboard("hide", opts);
  }

  /** @returns {void} */
  function dismissForNavigation() {
    clearFocusOutTimer();
    blurActiveTouchInput();
    suppressShowUntil = Date.now() + SUPPRESS_SHOW_MS;
    keyboardIntent = "hide";
    hideKeyboard({ force: true });
  }

  /** @returns {void} */
  function dismiss() {
    dismissForNavigation();
  }

  /**
   * @param {Element} el
   * @returns {boolean}
   */
  function isInsideTouchInput(el) {
    return Boolean(el.closest(SELECTOR));
  }

  /**
   * @param {Element} el
   * @returns {boolean}
   */
  function isKeepOpenZone(el) {
    return Boolean(el.closest(KEEP_OPEN_SELECTOR));
  }

  /**
   * @param {Element} el
   * @returns {boolean}
   */
  function isNavigationControl(el) {
    return Boolean(
      el.closest(
        "#btnNext, #btnPrev, #btnDualNext, #btnDualPrev, #btnReset, #btnCertSave, " +
          "#edu-nlpatch-submit, .edu-nlpatch-go, #edu-nlpatch-replay, #edu-nlpatch-done, " +
          ".btn-primary, .btn-secondary, .edu-nlpatch-close, [data-nlp-dismiss]"
      )
    );
  }

  /**
   * @param {HTMLInputElement|HTMLTextAreaElement} target
   * @param {Event} [ev]
   * @returns {void}
   */
  function activateInput(target, ev) {
    if (target.disabled || target.readOnly) return;
    if (ev && "isComposing" in ev && /** @type {{isComposing?:boolean}} */ (ev).isComposing) {
      return;
    }

    clearFocusOutTimer();
    activeTouchInput = target;
    target.removeAttribute("readonly");

    const alreadyFocused = document.activeElement === target;
    if (!alreadyFocused) {
      target.focus({ preventScroll: true });
    }

    /* 已聚焦且键盘意图为 show：只续期防抖，不再重复打 show（防第二次点击把 TabTip 关掉） */
    if (alreadyFocused && keyboardIntent === "show") {
      showGuardUntil = Date.now() + SHOW_GUARD_MS;
      return;
    }
    showKeyboard();
  }

  /**
   * @param {Event} ev
   * @returns {HTMLInputElement|HTMLTextAreaElement|null}
   */
  function targetFromEvent(ev) {
    const t = ev.target;
    if (!(t instanceof Element)) return null;
    if (t instanceof HTMLInputElement || t instanceof HTMLTextAreaElement) {
      return t.matches(SELECTOR) ? t : null;
    }
    const nested = t.closest(SELECTOR);
    if (nested instanceof HTMLInputElement || nested instanceof HTMLTextAreaElement) {
      return nested;
    }
    return null;
  }

  /**
   * @param {Event} ev
   * @returns {void}
   */
  function onPointerDown(ev) {
    /* 只响应主指针，忽略笔/额外按键带来的重复事件 */
    if ("button" in ev && /** @type {PointerEvent} */ (ev).button != null) {
      const pe = /** @type {PointerEvent} */ (ev);
      if (pe.button !== 0) return;
    }

    const target = targetFromEvent(ev);
    if (target) {
      activateInput(target, ev);
      return;
    }

    const el = ev.target;
    if (!(el instanceof Element)) return;
    if (isInsideTouchInput(el)) return;

    /* 快捷芯片等：不收起，等 click 把焦点送回输入框 */
    if (isKeepOpenZone(el)) {
      clearFocusOutTimer();
      return;
    }

    const shouldHide =
      isNavigationControl(el) ||
      keyboardIntent === "show" ||
      isTouchInput(document.activeElement) ||
      activeTouchInput != null;

    if (!shouldHide) return;

    clearFocusOutTimer();
    blurActiveTouchInput();
    hideKeyboard({ force: isNavigationControl(el) });
  }

  /**
   * @param {FocusEvent} ev
   * @returns {void}
   */
  function onFocusOut(ev) {
    const leaving = ev.target;
    if (!isTouchInput(leaving)) return;

    clearFocusOutTimer();
    focusOutTimer = window.setTimeout(() => {
      focusOutTimer = 0;
      if (isTouchInput(document.activeElement)) {
        activeTouchInput = /** @type {HTMLInputElement|HTMLTextAreaElement} */ (
          document.activeElement
        );
        return;
      }
      if (keyboardIntent !== "show") return;
      if (Date.now() < showGuardUntil) return;
      activeTouchInput = null;
      hideKeyboard();
    }, FOCUS_OUT_DELAY_MS);
  }

  /**
   * @param {FocusEvent} ev
   * @returns {void}
   */
  function onFocusIn(ev) {
    const el = ev.target;
    if (!isTouchInput(el)) return;
    clearFocusOutTimer();
    activeTouchInput = /** @type {HTMLInputElement|HTMLTextAreaElement} */ (el);
    /* 发送/导航后的 suppress 窗口内禁止再唤起（防误弹手写板） */
    if (Date.now() < suppressShowUntil) {
      return;
    }
    /* 程序化 focus（如芯片填词）也唤起；已 show 则被防抖吞掉 */
    showKeyboard();
  }

  /** @returns {void} */
  function warmKeyboard() {
    fetch(`${apiBase()}/kiosk/touch-keyboard/warm`, {
      method: "POST",
      keepalive: true,
      mode: "cors",
    }).catch(() => {});
  }

  /** @returns {void} */
  function init() {
    if (initialized) return;
    initialized = true;

    document.addEventListener("pointerdown", onPointerDown, true);
    document.addEventListener("focusout", onFocusOut, true);
    document.addEventListener("focusin", onFocusIn, true);
    warmKeyboard();
  }

  /**
   * @param {HTMLElement} root
   * @returns {void}
   */
  function bind(root) {
    root.querySelectorAll("input, textarea").forEach((el) => {
      if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
        el.classList.add("edu-touch-input");
        el.setAttribute("inputmode", "text");
        el.setAttribute("lang", "zh-CN");
        el.setAttribute("enterkeyhint", el.tagName === "TEXTAREA" ? "done" : "next");
        el.setAttribute("autocomplete", "off");
        el.setAttribute("autocapitalize", "off");
        el.removeAttribute("readonly");
        el.style.touchAction = "manipulation";
      }
    });
  }

  window.EduTouchKeyboard = {
    init,
    bind,
    show: showKeyboard,
    hide: () => hideKeyboard({ force: true }),
    invoke: showKeyboard,
    dismiss,
    dismissForNavigation,
  };
})();
