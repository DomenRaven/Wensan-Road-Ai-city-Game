/* B1 · 今天想玩什么？ · NLU 匹配品类 */

(() => {

  "use strict";



  /** 与 config/intent_genre_lexicon.json 同步 · API 不可用时的 fallback */

  const TIE_BREAK = [

    "platformer",

    "shmup",

    "survivor",

    "pingpong",

    "fighting",

    "parkour",

    "racing",

  ];



  const KEYWORD_MAP = [

    {

      genre: "platformer",

      words: ["马里奥", "闯关", "跳", "平台", "踩怪", "横版", "跳跃", "金币", "管道"],

    },

    {

      genre: "shmup",

      words: ["飞机", "射击", "雷霆", "弹幕", "打飞机", "飞行", "太空", "战机"],

    },

    {

      genre: "survivor",

      words: ["割草", "生存", "升级", "吸血鬼", "打怪变强", "幸存者", "肉鸽", "刷怪"],

    },

    {

      genre: "pingpong",

      words: ["乒乓球", "乒乓", "弹球", "球拍", "桌球", "对打", "双人", "球桌"],

    },

    {

      genre: "fighting",

      words: ["格斗", "拳击", "对战", "打架", "双人打", "拳脚", "擂台", "双人"],

    },

    {

      genre: "parkour",

      words: ["跑酷", "一直跑", "躲障碍", "无尽跑", "奔跑", "障碍", "滑铲", "冲刺"],

    },

    {

      genre: "racing",

      words: ["赛车", "开车", "竞速", "跑道", "漂移", "飙车", "车道", "超车"],

    },

  ];



  const DEFAULT_EXAMPLE_CHIPS = [

    "马里奥闯关",

    "我想打飞机",

    "割草打怪",

    "乒乓球",

    "格斗双人",

    "跑酷",

    "赛车",

  ];



  const GENRE_EMOJI = {

    platformer: "🌟",

    shmup: "🚀",

    survivor: "⚔️",

    pingpong: "🏓",

    fighting: "🥊",

    parkour: "🏃",

    racing: "🏎️",

  };



  /** 快捷 chip 文案 → 品类（优先于 KEYWORD_MAP，避免「格斗双人」误匹配乒乓球「双人」） */

  const CHIP_TEXT_GENRE = Object.freeze({

    "马里奥闯关": "platformer",

    "我想打飞机": "shmup",

    "割草打怪": "survivor",

    "乒乓球": "pingpong",

    "格斗双人": "fighting",

    "跑酷": "parkour",

    "赛车": "racing",

  });



  /**

   * @param {Record<string, unknown>} spec

   * @returns {string[]}

   */

  function exampleChips(spec) {

    const fromSpec = spec?.intent_example_chips;

    if (Array.isArray(fromSpec) && fromSpec.length > 0) {

      return fromSpec.map((v) => String(v));

    }

    return DEFAULT_EXAMPLE_CHIPS;

  }



  const BUBBLE_COLORS = [

    "#4ade80", "#60a5fa", "#e879f9", "#34d399", "#f87171", "#a78bfa", "#fb923c",

  ];



  /**

   * @param {HTMLElement} parent

   * @param {string[]} chips

   * @param {(text: string) => void} onSelect

   */

  function mountBubbleFallback(parent, chips, onSelect) {

    const host = document.createElement("div");

    host.id = "intentBubbleField";

    host.className = "intent-bubble-field intent-bubble-field--static";

    const grid = document.createElement("div");

    grid.className = "intent-bubble-static-grid";

    chips.forEach((text, index) => {

      const btn = document.createElement("button");

      btn.type = "button";

      btn.className = "intent-bubble-float";

      btn.style.setProperty("--bubble-color", BUBBLE_COLORS[index % BUBBLE_COLORS.length]);

      btn.style.setProperty("--bubble-rgb", "96, 165, 250");

      const shine = document.createElement("span");

      shine.className = "intent-bubble-shine";

      shine.setAttribute("aria-hidden", "true");

      const content = document.createElement("span");

      content.className = "intent-bubble-content";

      const slug = EduB1Intent?.chipGenre?.(text) || "platformer";

      const emoji = EduB1Intent?.emoji?.(slug) || "🎮";

      if (window.EduBubblePicker?.createMedal) {

        content.appendChild(window.EduBubblePicker.createMedal(emoji));

      } else {

        const glyph = document.createElement("span");

        glyph.className = "intent-bubble-emoji";

        glyph.textContent = emoji;

        content.appendChild(glyph);

      }

      const label = document.createElement("span");

      label.className = "intent-bubble-label";

      label.textContent = text;

      content.appendChild(label);

      btn.appendChild(shine);

      btn.appendChild(content);

      btn.addEventListener("click", () => onSelect(text));

      grid.appendChild(btn);

    });

    host.appendChild(grid);

    parent.appendChild(host);

  }



  const EduB1Intent = {

    /**

     * @param {HTMLElement} formEl

     * @param {Record<string, unknown>} spec

     * @param {{intentRaw:string, genre:string, replyText:string}} state

     */

    render(formEl, spec, state) {

      window.EduBubblePicker?.destroy();

      const chips = exampleChips(spec);



      formEl.innerHTML = `

        <div class="intent-b1-center">

          <textarea id="intentInput" class="text-input textarea intent-textarea intent-textarea--b1 edu-touch-input" maxlength="80"

            inputmode="text" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"

            aria-label="描述你想玩的游戏"

            placeholder="在这里输入，或点选、拖拽周围泡泡…">${state.intentRaw || ""}</textarea>

          <p class="hint intent-reply intent-reply--b1" id="intentReply">${state.replyText || ""}</p>

        </div>

      `;



      const input = /** @type {HTMLTextAreaElement|null} */ (formEl.querySelector("#intentInput"));
      window.EduTouchKeyboard?.bind(formEl);

      if (input && window.EduBubblePicker) {

        window.EduBubblePicker.mount(null, {

          chips,

          fullscreen: true,

          onSelect(text) {

            input.value = text;

          },

        });

      } else if (input) {

        mountBubbleFallback(document.body, chips, (text) => {

          input.value = text;

        });

      }

    },



    /** @returns {void} */

    destroy() {

      window.EduBubblePicker?.destroy();

    },



    /**

     * @param {HTMLElement} formEl

     */

    getInput(formEl) {

      const input = /** @type {HTMLTextAreaElement|null} */ (formEl.querySelector("#intentInput"));

      return (input?.value || "").trim();

    },



    /**

     * @param {string} text

     */

    fallbackMatch(text) {

      const lower = text.toLowerCase();

      const scores = new Map(

        TIE_BREAK.map((genre) => [genre, 0])

      );



      KEYWORD_MAP.forEach(({ genre, words }) => {

        let score = 0;

        words.forEach((w) => {

          if (lower.includes(w) || text.includes(w)) score += 1;

        });

        scores.set(genre, score);

      });



      let best = TIE_BREAK[0];

      let bestScore = -1;

      TIE_BREAK.forEach((genre) => {

        const score = scores.get(genre) || 0;

        if (score > bestScore) {

          bestScore = score;

          best = genre;

        }

      });



      const names = window.EduWizard?.spec?.genre_display_names || {};

      const label = names[best] || best;

      return {

        matched_genre: best,

        confidence: bestScore > 0 ? 0.75 : 0.4,

        reply_text: bestScore > 0 ? `听起来你想玩${label}！` : `我们先从${label}开始吧！`,

        candidates: [],

      };

    },



    /**

     * @param {string} text

     * @param {string} sessionId

     */

    async matchGenre(text, sessionId) {

      try {

        return await window.EduSession.api("/intent/match-genre", {

          method: "POST",

          body: JSON.stringify({ text, session_id: sessionId }),

        });

      } catch (_) {

        window.EduSession.log("POST /intent/match-genre 不可用 · 使用关键词 fallback");

        return this.fallbackMatch(text);

      }

    },



    /** @param {string} text */

    chipGenre(text) {

      const raw = String(text || "").trim();

      if (CHIP_TEXT_GENRE[raw]) return CHIP_TEXT_GENRE[raw];

      for (const row of KEYWORD_MAP) {

        if (row.words.some((w) => raw.includes(w))) return row.genre;

      }

      return TIE_BREAK[0];

    },



    /** @param {string} slug */

    emoji(slug) {

      return GENRE_EMOJI[slug] || "🎮";

    },



    /** @param {string} slug */

    previewUrl(slug) {

      return `../../assets/previews/${slug}.png`;

    },

  };



  window.EduB1Intent = EduB1Intent;

})();


