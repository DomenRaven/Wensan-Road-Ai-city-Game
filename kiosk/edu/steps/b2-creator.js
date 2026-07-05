/* B2 · 子屏 A · 你的名字是？ */
(() => {
  "use strict";

  const MAX_LEN = 8;
  const VALID_PATTERN = /^[\u4e00-\u9fa5a-zA-Z0-9·]+$/;

  const EduB2Creator = {
    /**
     * @param {string} raw
     */
    normalizeText(raw) {
      return String(raw || "")
        .normalize("NFKC")
        .replace(/[\u200B-\u200D\uFEFF]/g, "")
        .replace(/[\uFF01-\uFF5E]/g, (ch) => String.fromCharCode(ch.charCodeAt(0) - 0xFEE0));
    },

    /**
     * @param {string} name
     */
    sanitize(name) {
      return this.normalizeText(name)
        .replace(/[^\u4e00-\u9fa5a-zA-Z0-9·]/g, "")
        .trim()
        .slice(0, MAX_LEN);
    },

    /**
     * @param {HTMLElement} formEl
     */
    commitComposition(formEl) {
      const input = /** @type {HTMLInputElement|null} */ (formEl.querySelector("#creatorInput"));
      if (!input) return;
      if (document.activeElement === input) {
        input.blur();
      }
    },

    /**
     * @param {HTMLElement} formEl
     * @param {Record<string, unknown>} _spec
     * @param {{ creatorName: string }} ctx
     */
    render(formEl, _spec, ctx) {
      formEl.innerHTML = `
        <div class="b2-creator-field">
          <input
            id="creatorInput"
            class="text-input b2-creator-input edu-touch-input"
            maxlength="${MAX_LEN}"
            value="${ctx.creatorName || ""}"
            placeholder="例如：小明"
            aria-label="你的名字"
            autocomplete="off"
            autocorrect="off"
            autocapitalize="off"
            spellcheck="false"
            inputmode="text"
          />
          <p class="hint" id="creatorHint">1–8 个字 · 中英文和数字</p>
        </div>
      `;
      const input = /** @type {HTMLInputElement|null} */ (formEl.querySelector("#creatorInput"));
      if (input) {
        input.addEventListener("compositionstart", () => {
          input.dataset.composing = "1";
        });
        input.addEventListener("compositionend", () => {
          delete input.dataset.composing;
          input.value = this.sanitize(input.value);
        });
        input.addEventListener("blur", () => {
          delete input.dataset.composing;
          input.value = this.sanitize(input.value);
        });
      }
      window.EduTouchKeyboard?.bind(formEl);
    },

    /**
     * @param {HTMLElement} formEl
     * @returns {boolean}
     */
    isComposing(formEl) {
      const input = /** @type {HTMLInputElement|null} */ (formEl.querySelector("#creatorInput"));
      return !!(input && (input.dataset.composing === "1" || input.isComposing));
    },

    /**
     * @param {HTMLElement} formEl
     * @param {string} [message]
     */
    showValidationError(formEl, message) {
      const hint = formEl.querySelector("#creatorHint");
      if (!hint) return;
      hint.classList.add("hint--error");
      hint.textContent = message || "请先填写你的名字（1–8 个字）";
    },

    /** @param {HTMLElement} formEl */
    clearValidationError(formEl) {
      const hint = formEl.querySelector("#creatorHint");
      if (!hint) return;
      hint.classList.remove("hint--error");
      hint.textContent = "1–8 个字 · 中英文和数字";
    },

    /**
     * @param {HTMLElement} formEl
     */
    getInput(formEl) {
      this.commitComposition(formEl);
      const input = /** @type {HTMLInputElement|null} */ (formEl.querySelector("#creatorInput"));
      return this.sanitize(input?.value || "");
    },

    /** @param {string} name */
    isValid(name) {
      const trimmed = this.sanitize(name);
      return trimmed.length >= 1 && trimmed.length <= MAX_LEN && VALID_PATTERN.test(trimmed);
    },
  };

  window.EduB2Creator = EduB2Creator;
})();
