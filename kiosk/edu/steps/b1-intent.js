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



  const EduB1Intent = {

    /**

     * @param {HTMLElement} formEl

     * @param {Record<string, unknown>} spec

     * @param {{intentRaw:string, genre:string, replyText:string}} state

     */

    render(formEl, spec, state) {

      const chips = exampleChips(spec);

      const chipHtml = chips

        .map((text) => `<button type="button" class="chip" data-text="${text}">${text}</button>`)

        .join("");



      formEl.innerHTML = `

        <div class="hint-banner">试试说：「我想玩马里奥闯关」「我想打飞机」</div>

        <label for="intentInput">今天你想玩什么游戏呢？</label>

        <textarea id="intentInput" class="text-input textarea" maxlength="80"

          placeholder="用一句话告诉我…">${state.intentRaw || ""}</textarea>

        <div class="chip-row" id="intentExamples" style="overflow-x:auto;flex-wrap:nowrap;padding-bottom:4px">

          ${chipHtml}

        </div>

        <p class="hint" id="intentReply">${state.replyText || ""}</p>

      `;



      formEl.querySelectorAll("#intentExamples .chip").forEach((chip) => {

        chip.addEventListener("click", () => {

          const input = /** @type {HTMLTextAreaElement} */ (formEl.querySelector("#intentInput"));

          input.value = chip.getAttribute("data-text") || "";

        });

      });

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


