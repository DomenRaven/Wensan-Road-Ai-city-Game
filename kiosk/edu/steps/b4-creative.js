/* B4 · 完型填空创作模板 */

(() => {

  "use strict";



  const OPTIONAL_SKILLS_PATH = "../../config/optional_skills.json";



  /** @type {Record<string, Array<{id:string,label:string}>>|null} */

  let skillCatalog = null;



  /** @type {number} */

  let maxSkillsPerSession = 2;



  const EduB4Creative = {

    /** @type {Record<string, string | string[]>} */

    answers: {},



    /** @type {string|null} */

    loadError: null,



    async loadSkillCatalog() {

      if (skillCatalog) return skillCatalog;

      try {

        const res = await fetch(OPTIONAL_SKILLS_PATH);

        if (res.ok) {

          const data = await res.json();

          skillCatalog = data.catalog || {};

          if (typeof data.rules?.max_skills_per_session === "number") {

            maxSkillsPerSession = data.rules.max_skills_per_session;

          }

          return skillCatalog;

        }

      } catch (_) {

        window.EduSession.log("无法加载 optional_skills.json · 技能标签将显示 id");

      }

      skillCatalog = {};

      return skillCatalog;

    },



    /**

     * @param {Record<string, Array<{id:string,label:string}>>} catalog

     * @param {string} genre

     * @param {string} skillId

     */

    skillLabel(catalog, genre, skillId) {

      const list = catalog[genre] || [];

      const item = list.find((s) => s.id === skillId);

      return item?.label || skillId;

    },



    /**

     * @param {string} genre

     */

    async loadTemplate(genre) {

      this.loadError = null;

      try {

        const data = await window.EduSession.api(`/creative/templates/${genre}`);

        if (!data.questions?.length) {

          throw new Error(`模板无题目 (genre=${genre})`);

        }

        return data;

      } catch (err) {

        const msg = `无法加载创作模板 · GET /creative/templates/${genre} · ${err.message}`;

        this.loadError = msg;

        window.EduSession.log(msg);

        throw new Error(msg);

      }

    },



    /**

     * @param {{id:string,widget?:string,prompt:string,optional?:boolean,options?:Array<{id:string,label:string}>,skill_ids?:string[]}} q

     * @param {Record<string, Array<{id:string,label:string}>>} catalog

     * @param {string} genre

     * @param {Record<string, string | string[]>} existing

     */

    renderQuestionBlock(q, catalog, genre, existing) {

      const widget = q.widget || "single_choice";



      if (widget === "skill_pick") {

        const selected = Array.isArray(existing[q.id]) ? existing[q.id] : [];

        const skillIds = q.skill_ids || [];

        const optionalHint = q.optional ? ' <span class="hint">（可不选）</span>' : "";

        return `

          <div class="question-block" data-qid="${q.id}" data-widget="skill_pick">

            <p>${q.prompt}${optionalHint}</p>

            <div class="chip-row scroll-x skill-chip-row">

              ${skillIds

                .map((skillId) => {

                  const isSel = selected.includes(skillId);

                  const label = this.skillLabel(catalog, genre, skillId);

                  return `<button type="button" class="skill-chip ${isSel ? "selected" : ""}" data-skill="${skillId}">${label}</button>`;

                })

                .join("")}

            </div>

            <p class="hint skill-hint">最多选 ${maxSkillsPerSession} 个</p>

          </div>

        `;

      }



      const selected = typeof existing[q.id] === "string" ? existing[q.id] : "";

      return `

        <div class="question-block" data-qid="${q.id}" data-widget="single_choice">

          <p>${q.prompt}</p>

          <div class="option-cards">

            ${(q.options || [])

              .map(

                (opt) => `

              <label class="option-card ${selected === opt.id ? "selected" : ""}">

                <input type="radio" name="${q.id}" value="${opt.id}"

                  ${selected === opt.id ? "checked" : ""} />

                <span><strong>${opt.label}</strong></span>

              </label>

            `

              )

              .join("")}

          </div>

        </div>

      `;

    },



    /**

     * @param {HTMLElement} container

     * @param {{questions:Array<{id:string,widget?:string,prompt:string,optional?:boolean,options?:Array<{id:string,label:string}>,skill_ids?:string[]}>}} template

     * @param {Record<string, string | string[]>} existing

     * @param {string} genre

     */

    async render(container, template, existing, genre) {

      const catalog = await this.loadSkillCatalog();

      /** @type {Record<string, string | string[]>} */

      const nextAnswers = {};



      template.questions.forEach((q) => {

        const widget = q.widget || "single_choice";

        if (existing[q.id] !== undefined) {

          nextAnswers[q.id] = existing[q.id];

        } else if (widget === "skill_pick") {

          nextAnswers[q.id] = [];

        } else if (widget === "single_choice" && q.options?.[1]) {

          nextAnswers[q.id] = q.options[1].id;

        }

      });

      this.answers = nextAnswers;



      container.innerHTML = `

        <div class="creative-form-panel">

          <h3>填写你的创作配方</h3>

          ${template.questions

            .map((q) => this.renderQuestionBlock(q, catalog, genre, this.answers))

            .join("")}

        </div>

      `;



      container.querySelectorAll('.question-block[data-widget="single_choice"] .option-card').forEach((card) => {

        card.addEventListener("click", () => {

          const block = card.closest(".question-block");

          const qid = block?.getAttribute("data-qid") || "";

          block?.querySelectorAll(".option-card").forEach((c) => c.classList.remove("selected"));

          card.classList.add("selected");

          const radio = /** @type {HTMLInputElement|null} */ (card.querySelector("input"));

          if (radio) {

            radio.checked = true;

            this.answers[qid] = radio.value;

          }

        });

      });



      container.querySelectorAll('.question-block[data-widget="skill_pick"]').forEach((block) => {

        const qid = block.getAttribute("data-qid") || "";

        block.querySelectorAll(".skill-chip").forEach((chip) => {

          chip.addEventListener("click", () => {

            const skillId = chip.getAttribute("data-skill") || "";

            const current = Array.isArray(this.answers[qid]) ? [...this.answers[qid]] : [];

            const idx = current.indexOf(skillId);

            if (idx >= 0) {

              current.splice(idx, 1);

              chip.classList.remove("selected");

            } else if (current.length < maxSkillsPerSession) {

              current.push(skillId);

              chip.classList.add("selected");

            }

            this.answers[qid] = current;

          });

        });

      });

    },



    /**

     * @param {HTMLElement} container

     * @param {string} message

     */

    renderError(container, message) {

      container.innerHTML = `

        <div class="creative-form-panel creative-error-panel">

          <h3>无法加载创作配方</h3>

          <p class="launch-status err">${message}</p>

          <p class="hint">请确认后端已启动（uvicorn），并刷新页面重试。</p>

        </div>

      `;

    },



    /**

     * @param {{questions:Array<{id:string,widget?:string,optional?:boolean}>}} template

     */

    validate(template) {

      return template.questions.every((q) => {

        if (q.optional) return true;

        const ans = this.answers[q.id];

        const widget = q.widget || "single_choice";

        if (widget === "skill_pick") {

          return Array.isArray(ans) && ans.length > 0;

        }

        return typeof ans === "string" && ans.length > 0;

      });

    },



    /**

     * @param {string} sessionId

     * @param {Record<string, string | string[]>} answers

     */

    async submitAnswers(sessionId, answers) {

      return await window.EduSession.api(`/sessions/${sessionId}/creative/answers`, {

        method: "POST",

        body: JSON.stringify({ answers }),

      });

    },

  };



  window.EduB4Creative = EduB4Creative;

})();

