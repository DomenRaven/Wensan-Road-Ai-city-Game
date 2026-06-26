/* B2 · 起名 · 推荐名芯片 */
(() => {
  "use strict";

  const EduB2Name = {
    /**
     * @param {string} name
     */
    sanitize(name) {
      return name.replace(/[^\u4e00-\u9fa5a-zA-Z0-9\s]/g, "").trim().slice(0, 20);
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
     * @param {{genre:string, displayName:string, genreLabel:string}} ctx
     * @param {string[]} suggestions
     */
    render(formEl, spec, ctx, suggestions) {
      const maxLen = spec.touch_constraints?.max_text_input_length || 20;
      const emoji = window.EduB1Intent?.emoji(ctx.genre) || "🎮";
      const preview = window.EduB1Intent?.previewUrl(ctx.genre) || "";
      formEl.innerHTML = `
        <div class="genre-confirm">
          <img src="${preview}" alt="" onerror="this.outerHTML='<span class=\\'emoji-fallback\\'>${emoji}</span>'" />
          <p>我知道了！我们一起制作一个<strong>【${ctx.genreLabel}】</strong>小游戏吧！</p>
        </div>
        <label for="nameInput">你希望它叫什么呢？</label>
        <input id="nameInput" class="text-input" maxlength="${maxLen}"
          value="${ctx.displayName || ""}" placeholder="给游戏起个名字…" />
        <div class="chip-row scroll-x" id="nameChips">
          ${suggestions
            .map((s) => `<button type="button" class="chip" data-name="${s}">${s}</button>`)
            .join("")}
        </div>
        <p class="hint">最多 ${maxLen} 个字 · 中英文和数字</p>
      `;

      formEl.querySelectorAll("#nameChips .chip").forEach((chip) => {
        chip.addEventListener("click", () => {
          const input = /** @type {HTMLInputElement} */ (formEl.querySelector("#nameInput"));
          input.value = chip.getAttribute("data-name") || "";
        });
      });
    },

    /**
     * @param {HTMLElement} formEl
     */
    getInput(formEl) {
      const input = /** @type {HTMLInputElement|null} */ (formEl.querySelector("#nameInput"));
      return this.sanitize(input?.value || "");
    },

    /** @param {string} name */
    isValid(name) {
      return name.length > 0;
    },
  };

  window.EduB2Name = EduB2Name;
})();
