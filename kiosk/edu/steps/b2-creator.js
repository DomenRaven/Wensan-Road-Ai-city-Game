/* B2 · 子屏 A · 你的名字是？ */
(() => {
  "use strict";

  const MAX_LEN = 8;
  const VALID_PATTERN = /^[\u4e00-\u9fa5a-zA-Z0-9·]+$/;

  /** 展厅预制称呼 · 点击即可填入（约 10 个） */
  const PRESET_NAMES = [
    "晶晶",
    "亮亮",
    "聪聪",
    "小军",
    "小雨",
    "乐乐",
    "朵朵",
    "浩浩",
    "安安",
    "天天",
  ];

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
     * @param {string} name
     */
    applyPreset(formEl, name) {
      const input = /** @type {HTMLInputElement|null} */ (formEl.querySelector("#creatorInput"));
      if (!input) return;
      input.value = this.sanitize(name);
      delete input.dataset.composing;
      this.clearValidationError(formEl);
      formEl.querySelectorAll(".b2-preset-chip").forEach((chip) => {
        chip.classList.toggle("is-selected", chip.getAttribute("data-name") === name);
      });
    },

    /**
     * @param {HTMLElement} formEl
     * @param {Record<string, unknown>} _spec
     * @param {{ creatorName: string }} ctx
     */
    render(formEl, _spec, ctx) {
      const selected = this.sanitize(ctx.creatorName || "");
      const chips = PRESET_NAMES.map((name) => {
        const active = name === selected ? " is-selected" : "";
        return `<button type="button" class="b2-preset-chip${active}" data-name="${name}">${name}</button>`;
      }).join("");

      formEl.innerHTML = `
        <div class="b2-creator-field">
          <input
            id="creatorInput"
            class="text-input b2-creator-input edu-touch-input"
            maxlength="${MAX_LEN}"
            value="${selected}"
            placeholder="例如：小明"
            aria-label="你的名字"
            autocomplete="off"
            autocorrect="off"
            autocapitalize="off"
            spellcheck="false"
            inputmode="text"
          />
          <p class="hint" id="creatorHint">1–8 个字 · 中英文和数字 · 也可点下方称呼</p>
          <div class="b2-preset-row" role="group" aria-label="预制称呼">
            ${chips}
          </div>
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
        input.addEventListener("input", () => {
          formEl.querySelectorAll(".b2-preset-chip").forEach((chip) => {
            chip.classList.toggle(
              "is-selected",
              chip.getAttribute("data-name") === this.sanitize(input.value)
            );
          });
        });
      }
      formEl.querySelectorAll(".b2-preset-chip").forEach((chip) => {
        chip.addEventListener("click", () => {
          const name = chip.getAttribute("data-name") || "";
          this.applyPreset(formEl, name);
        });
      });
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
      hint.textContent = "1–8 个字 · 中英文和数字 · 也可点下方称呼";
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
