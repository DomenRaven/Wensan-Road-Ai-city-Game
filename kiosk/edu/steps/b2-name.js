/* B2 · 起名 · 推荐名芯片 */
(() => {
  "use strict";

  const EduB2Name = {
    /**
     * @param {string} name
     */
    normalizeText(name) {
      return String(name || "")
        .normalize("NFKC")
        .replace(/[\u200B-\u200D\uFEFF]/g, "")
        .replace(/[\uFF01-\uFF5E]/g, (ch) => String.fromCharCode(ch.charCodeAt(0) - 0xFEE0));
    },

    /**
     * @param {string} name
     */
    /**
     * @param {string} name
     * @param {number} [maxLen]
     */
    sanitize(name, maxLen = 20) {
      const limit = Math.max(1, Number(maxLen) || 20);
      // 登录默认名含全角括号（），需保留
      return this.normalizeText(name)
        .replace(/[^\u4e00-\u9fa5a-zA-Z0-9\s（）()]/g, "")
        .trim()
        .slice(0, limit);
    },

    /**
     * @param {string} genre
     * @param {Record<string, unknown>} spec
     */
    async getSuggestions(genre, spec) {
      try {
        const data = await window.EduSession.api(
          `/creative/name-suggestions?genre=${encodeURIComponent(genre)}`
        );
        if (data.suggestions?.length >= 4) return data.suggestions;
        throw new Error(`suggestions 不足 4 条 (genre=${genre})`);
      } catch (err) {
        window.EduSession.log(
          `GET /creative/name-suggestions 失败 · 使用 spec fallback · ${err.message}`
        );
      }
      const fallback = spec.name_suggestions || {};
      const genreList = fallback[genre];
      if (Array.isArray(genreList) && genreList.length >= 4) return genreList;
      return Array.isArray(genreList) ? genreList : [];
    },

    /**
     * @param {HTMLElement} formEl
     * @param {Record<string, unknown>} spec
     * @param {{genre:string, displayName:string, genreLabel:string, creatorName?:string}} ctx
     * @param {string[]} suggestions
     */
    render(formEl, spec, ctx, suggestions) {
      const maxLen = Number(ctx.maxLen) || spec.touch_constraints?.max_text_input_length || 20;
      const escapedName = String(ctx.displayName || "")
        .replace(/&/g, "&amp;")
        .replace(/"/g, "&quot;")
        .replace(/</g, "&lt;");
      formEl.innerHTML = `
        <div class="genre-confirm genre-confirm--plain">
          <p class="genre-confirm-msg">让我们制作一个<strong>${ctx.genreLabel}</strong>小游戏吧！</p>
        </div>
        <label for="nameInput" class="b2-name-label">你想让它叫什么名字呢？</label>
        <input id="nameInput" class="text-input b2-name-input edu-touch-input" maxlength="${maxLen}"
          inputmode="text" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"
          value="${escapedName}" placeholder="输入游戏名字…" />
        <div class="chip-row scroll-x" id="nameChips">
          ${suggestions
            .map((s) => `<button type="button" class="chip" data-name="${s}">${s}</button>`)
            .join("")}
        </div>
        <p class="hint">最多 ${maxLen} 个字 · 中英文、数字与括号</p>
      `;

      formEl.querySelectorAll("#nameChips .chip").forEach((chip) => {
        chip.addEventListener("click", () => {
          const input = /** @type {HTMLInputElement} */ (formEl.querySelector("#nameInput"));
          input.value = chip.getAttribute("data-name") || "";
        });
      });
      window.EduTouchKeyboard?.bind(formEl);
    },

    /**
     * @param {HTMLElement} formEl
     */
    getInput(formEl) {
      const input = /** @type {HTMLInputElement|null} */ (formEl.querySelector("#nameInput"));
      if (input && document.activeElement === input) {
        input.blur();
      }
      const maxLen = input?.maxLength > 0 ? input.maxLength : 20;
      return this.sanitize(input?.value || "", maxLen);
    },

    /** @param {string} name */
    isValid(name) {
      return name.length > 0;
    },

    /**
     * @param {HTMLElement} formEl
     * @param {string} [message]
     */
    showValidationError(formEl, message) {
      const hint = formEl.querySelector(".hint");
      if (!hint) return;
      hint.classList.add("hint--error");
      hint.textContent = message || "请先输入游戏名字";
    },

    /** @param {HTMLElement} formEl */
    clearValidationError(formEl) {
      const hint = formEl.querySelector(".hint");
      const input = /** @type {HTMLInputElement|null} */ (formEl.querySelector("#nameInput"));
      if (!hint) return;
      hint.classList.remove("hint--error");
      const maxLen = input?.maxLength || 20;
      hint.textContent = `最多 ${maxLen} 个字 · 中英文和数字`;
    },
  };

  window.EduB2Name = EduB2Name;
})();
