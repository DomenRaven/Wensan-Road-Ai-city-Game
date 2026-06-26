/* B3/B4 右侧 · 品类 HTML 动画预览（替代静态 PNG） */
(() => {
  "use strict";

  /** @type {Record<string, {caption:string, scene:string}>} */
  const SCENES = {
    shmup: {
      caption: "驾驶小飞机，躲避弹幕、击毁敌机！",
      scene: `
        <div class="gs-layer gs-stars"></div>
        <div class="gs-ship gs-ship--player" aria-hidden="true"></div>
        <div class="gs-ship gs-ship--enemy gs-ship--enemy-a" aria-hidden="true"></div>
        <div class="gs-ship gs-ship--enemy gs-ship--enemy-b" aria-hidden="true"></div>
        <div class="gs-laser gs-laser--a" aria-hidden="true"></div>
        <div class="gs-laser gs-laser--b" aria-hidden="true"></div>
        <div class="gs-spark gs-spark--a" aria-hidden="true"></div>
      `,
    },
    platformer: {
      caption: "跳跃、踩怪、收集金币，一路闯关！",
      scene: `
        <div class="gs-ground" aria-hidden="true"></div>
        <div class="gs-platform gs-platform--a" aria-hidden="true"></div>
        <div class="gs-hero gs-hero--jump" aria-hidden="true"></div>
        <div class="gs-coin gs-coin--a" aria-hidden="true"></div>
        <div class="gs-coin gs-coin--b" aria-hidden="true"></div>
        <div class="gs-enemy gs-enemy--slime" aria-hidden="true"></div>
      `,
    },
    survivor: {
      caption: "走位躲怪，捡经验宝石，越打越强！",
      scene: `
        <div class="gs-hero gs-hero--survivor" aria-hidden="true"></div>
        <div class="gs-gem gs-gem--a" aria-hidden="true"></div>
        <div class="gs-gem gs-gem--b" aria-hidden="true"></div>
        <div class="gs-gem gs-gem--c" aria-hidden="true"></div>
        <div class="gs-mob gs-mob--a" aria-hidden="true"></div>
        <div class="gs-mob gs-mob--b" aria-hidden="true"></div>
        <div class="gs-mob gs-mob--c" aria-hidden="true"></div>
      `,
    },
    pingpong: {
      caption: "左右移动球拍，把乒乓球打回去！",
      scene: `
        <div class="gs-table" aria-hidden="true"></div>
        <div class="gs-net" aria-hidden="true"></div>
        <div class="gs-paddle gs-paddle--left" aria-hidden="true"></div>
        <div class="gs-paddle gs-paddle--right" aria-hidden="true"></div>
        <div class="gs-ball gs-ball--ping" aria-hidden="true"></div>
      `,
    },
    fighting: {
      caption: "轻拳、重拳、格挡，击败对手！",
      scene: `
        <div class="gs-arena-floor" aria-hidden="true"></div>
        <div class="gs-fighter gs-fighter--p1" aria-hidden="true"></div>
        <div class="gs-fighter gs-fighter--p2" aria-hidden="true"></div>
        <div class="gs-hitfx gs-hitfx--spark" aria-hidden="true"></div>
      `,
    },
    parkour: {
      caption: "自动奔跑，跳跃躲障，滑铲收金币！",
      scene: `
        <div class="gs-ground gs-ground--scroll" aria-hidden="true"></div>
        <div class="gs-runner" aria-hidden="true"></div>
        <div class="gs-obstacle gs-obstacle--a" aria-hidden="true"></div>
        <div class="gs-coin gs-coin--run" aria-hidden="true"></div>
      `,
    },
    racing: {
      caption: "握紧方向盘，弯道超车冲第一！",
      scene: `
        <div class="gs-road" aria-hidden="true"></div>
        <div class="gs-car gs-car--player" aria-hidden="true"></div>
        <div class="gs-car gs-car--npc" aria-hidden="true"></div>
        <div class="gs-road-line gs-road-line--a" aria-hidden="true"></div>
        <div class="gs-road-line gs-road-line--b" aria-hidden="true"></div>
      `,
    },
  };

  const DEFAULT_SCENE = {
    caption: "这就是你的游戏类型预览",
    scene: `
      <div class="gs-sparkle gs-sparkle--a" aria-hidden="true"></div>
      <div class="gs-sparkle gs-sparkle--b" aria-hidden="true"></div>
      <div class="gs-sparkle gs-sparkle--c" aria-hidden="true"></div>
      <div class="gs-orbit-icon" aria-hidden="true">✨</div>
    `,
  };

  const EduGenrePreview = {
    /**
     * @param {HTMLElement|null} container
     * @param {string} genre
     * @param {string} [label]
     */
    render(container, genre, label) {
      if (!container) return;
      const slug = String(genre || "").trim() || "platformer";
      const pack = SCENES[slug] || DEFAULT_SCENE;
      const title = label ? `${label}` : slug;
      container.innerHTML = `
        <div class="pane-right-preview-stage">
          <div class="genre-scene genre-scene--${slug}" role="img" aria-label="${title} 动画预览">
            ${pack.scene}
          </div>
          <p class="preview-placeholder genre-scene-caption">${pack.caption}</p>
        </div>
      `;
    },
  };

  window.EduGenrePreview = EduGenrePreview;
})();
