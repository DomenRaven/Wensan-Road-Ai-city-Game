/* Kiosk · 唤起 Windows 系统触控软键盘（中文 IME + TabTip）· 禁止自建模拟键位 */
(() => {
  "use strict";

  /** @type {boolean} */
  let initialized = false;
  /** @type {number} */
  let lastInvokeMs = 0;

  const SELECTOR = "input.edu-touch-input, textarea.edu-touch-input, [data-edu-keyboard]";
  const INVOKE_COOLDOWN_MS = 900;

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
  function showVirtualKeyboardApi() {
    try {
      if (navigator.virtualKeyboard) {
        navigator.virtualKeyboard.overlaysContent = true;
        navigator.virtualKeyboard.show();
      }
    } catch (_) {
      /* Chromium 旧版或无 VirtualKeyboard API */
    }
  }

  /** @returns {void} */
  function invokeOsKeyboard() {
    const now = Date.now();
    if (now - lastInvokeMs < INVOKE_COOLDOWN_MS) return;
    lastInvokeMs = now;

    showVirtualKeyboardApi();

    const url = `${apiBase()}/kiosk/touch-keyboard/show`;
    fetch(url, {
      method: "POST",
      keepalive: true,
      mode: "cors",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider: keyboardProvider() }),
    }).catch(() => {
      /* 后端未启动时静默降级 */
    });
  }

  /**
   * @param {HTMLInputElement|HTMLTextAreaElement} target
   * @returns {void}
   */
  function activateInput(target) {
    if (target.disabled) return;
    target.removeAttribute("readonly");
    if (document.activeElement !== target) {
      target.focus({ preventScroll: false });
    }
    invokeOsKeyboard();
    window.setTimeout(() => {
      if (document.activeElement === target) {
        target.scrollIntoView({ block: "center", behavior: "smooth" });
      }
    }, 80);
  }

  /**
   * @param {Event} ev
   * @returns {HTMLInputElement|HTMLTextAreaElement|null}
   */
  function targetFromEvent(ev) {
    const t = ev.target;
    if (t instanceof HTMLInputElement || t instanceof HTMLTextAreaElement) {
      return t.matches(SELECTOR) ? t : null;
    }
    return null;
  }

  /** @returns {void} */
  function init() {
    if (initialized) return;
    initialized = true;

    const onActivate = (ev) => {
      const target = targetFromEvent(ev);
      if (!target) return;
      activateInput(target);
    };

    /* 仅 pointerdown/touchstart · 避免 focusin 重复 Toggle 导致键盘闪退 */
    document.addEventListener("pointerdown", onActivate, true);
    document.addEventListener("touchstart", onActivate, { capture: true, passive: true });
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
    invoke: invokeOsKeyboard,
  };
})();
