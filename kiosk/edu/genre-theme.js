/* P4-C-3 · 品类主题 token · 仅数据查询，不切换页面 UI（背景统一蓝白基线） */

(() => {
  "use strict";

  /** @type {string[]} */
  const CSS_VARS = ["--genre-accent", "--genre-accent-light", "--genre-surface"];

  /**
   * @returns {Record<string, Record<string, string>>}
   */
  function getThemes() {
    const spec = window.EduSession?.spec || {};
    return /** @type {Record<string, Record<string, string>>} */ (spec.genre_themes || {});
  }

  /**
   * @param {string} slug
   * @returns {Record<string, string>|null}
   */
  function themeFor(slug) {
    if (!slug) return null;
    return getThemes()[slug] || null;
  }

  /** @param {string} _slug */
  function apply(_slug) {
    /* UI 背景保持统一蓝白 · 揭幕卡/烟花仍可读 spec.genre_themes */
  }

  function clear() {
    document.body.removeAttribute("data-genre-theme");
    document.body.removeAttribute("data-genre-pattern");
    CSS_VARS.forEach((name) => document.documentElement.style.removeProperty(name));
  }

  window.EduGenreTheme = { apply, clear, themeFor };
})();
