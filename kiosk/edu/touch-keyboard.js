/* Kiosk · Windows TabTip 触控软键盘 · 点击输入即显 · 点外/导航即隐 · 零人为延迟 */
(() => {
  "use strict";

  /** @type {boolean} */
  let initialized = false;
  /** @type {"show"|"hide"|null} */
  let keyboardIntent = null;
  /** @type {AbortController|null} */
  let inflight = null;

  const SELECTOR = "input.edu-touch-input, textarea.edu-touch-input, [data-edu-keyboard]";

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

    fetch(url, options).catch(() => {
      /* 后端未启动时静默降级 */
    });
  }

  /**
   * @param {"show"|"hide"} action
   * @returns {void}
   */
  function postKeyboard(action) {
    keyboardIntent = action;
    if (action === "show") {
      showVirtualKeyboardApi();
    } else {
      hideVirtualKeyboardApi();
    }
    postKeyboardRequest(action);
  }

  /**
   * @param {HTMLElement|null|undefined} el
   * @returns {boolean}
   */
  function isTouchInput(el) {
    if (!(el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement)) {
      return false;
    }
    return el.matches(SELECTOR) || el.classList.contains("edu-touch-input");
  }

  /** @returns {void} */
  function blurActiveTouchInput() {
    const active = document.activeElement;
    if (isTouchInput(active)) {
      active.blur();
    }
  }

  /** @returns {void} */
  function showKeyboard() {
    postKeyboard("show");
  }

  /** @returns {void} */
  function hideKeyboard() {
    postKeyboard("hide");
  }

  /** @returns {void} */
  function dismissForNavigation() {
    blurActiveTouchInput();
    hideKeyboard();
  }

  /** @returns {void} */
  function dismiss() {
    dismissForNavigation();
  }

  /**
   * @param {HTMLElement} el
   * @returns {boolean}
   */
  function isInsideTouchInput(el) {
    return Boolean(el.closest(SELECTOR));
  }

  /**
   * @param {HTMLElement} el
   * @returns {boolean}
   */
  function isNavigationControl(el) {
    return Boolean(
      el.closest(
        "#btnNext, #btnPrev, #btnDualNext, #btnDualPrev, .btn-primary, .btn-secondary"
      )
    );
  }

  /**
   * @param {HTMLInputElement|HTMLTextAreaElement} target
   * @param {PointerEvent|Event} [ev]
   * @returns {void}
   */
  function activateInput(target, ev) {
    if (target.disabled) return;
    if (ev && "isComposing" in ev && ev.isComposing) return;

    target.removeAttribute("readonly");
    target.focus({ preventScroll: true });
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
    const target = targetFromEvent(ev);
    if (target) {
      activateInput(target, ev);
      return;
    }

    const el = ev.target;
    if (!(el instanceof Element)) return;
    if (isInsideTouchInput(el)) return;

    if (isNavigationControl(el) || keyboardIntent === "show" || isTouchInput(document.activeElement)) {
      blurActiveTouchInput();
      hideKeyboard();
    }
  }

  /**
   * @param {FocusEvent} ev
   * @returns {void}
   */
  function onFocusOut(ev) {
    const next = ev.relatedTarget;
    if (isTouchInput(next)) return;
    if (keyboardIntent !== "show") return;
    hideKeyboard();
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
        el.removeAttribute("readonly");
        el.style.touchAction = "manipulation";
      }
    });
  }

  window.EduTouchKeyboard = {
    init,
    bind,
    show: showKeyboard,
    hide: hideKeyboard,
    invoke: showKeyboard,
    dismiss,
    dismissForNavigation,
  };
})();
