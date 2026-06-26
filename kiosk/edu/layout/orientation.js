/* B3+ 横竖屏方向检测 · body[data-orientation] · P3-2 */

(() => {

  "use strict";

  /** @type {number} */
  let breakpointPx = 900;

  /** @type {boolean} */
  let mounted = false;

  /** @type {number|null} */
  let debounceTimer = null;

  /** @type {150} */
  const DEBOUNCE_MS = 150;



  /**
   * @param {DOMRect} rect
   * @returns {{ x: number, y: number, w: number, h: number }}
   */
  function rectPayload(rect) {

    return {

      x: Math.round(rect.x),

      y: Math.round(rect.y),

      w: Math.round(rect.width),

      h: Math.round(rect.height),

    };

  }



  /**
   * @param {string} selector
   * @returns {{ x: number, y: number, w: number, h: number } | null}
   */

  function queryRect(selector) {

    const node = document.querySelector(selector);

    if (!node) return null;

    return rectPayload(node.getBoundingClientRect());

  }



  const EduOrientation = {

    /**
     * @param {{ orientation_breakpoint_px?: number }} [layout]
     */

    configure(layout) {

      if (layout?.orientation_breakpoint_px != null) {

        breakpointPx = layout.orientation_breakpoint_px;

      }

    },



    /** @returns {"landscape"|"portrait"} */

    getMode() {

      if (window.innerWidth < breakpointPx) return "portrait";

      if (window.matchMedia("(orientation: portrait)").matches) return "portrait";

      return "landscape";

    },



    /** 写入 body[data-orientation] */

    apply() {

      const mode = this.getMode();

      document.body.setAttribute("data-orientation", mode);

      return mode;

    },



    mount() {

      if (mounted) {

        this.apply();

        return;

      }

      mounted = true;

      const schedule = () => {

        if (debounceTimer != null) window.clearTimeout(debounceTimer);

        debounceTimer = window.setTimeout(() => {

          debounceTimer = null;

          EduOrientation.apply();

        }, DEBOUNCE_MS);

      };

      this.apply();

      window.addEventListener("resize", schedule, { passive: true });

      window.addEventListener("orientationchange", schedule, { passive: true });

    },



    /**
     * launch API 用 viewport 载荷（P3-3 消费）
     * @returns {{
     *   orientation: "landscape"|"portrait",
     *   client_viewport: {
     *     screen_x: number,
     *     screen_y: number,
     *     screen_w: number,
     *     screen_h: number,
     *     devicePixelRatio: number,
     *     kiosk_rect: { x: number, y: number, w: number, h: number } | null,
     *     godot_zone_rect: { x: number, y: number, w: number, h: number } | null
     *   }
     * }}
     */

    getViewportPayload() {

      const orientation = this.getMode();

      const kioskRect =

        queryRect("#dualPaneRoot")

        || queryRect(".dual-pane-root");

      const godotZoneRect =

        queryRect(".pane-right.godot-zone")

        || queryRect("#paneRightInner");

      return {

        orientation,

        client_viewport: {

          screen_x: window.screenX ?? window.screenLeft ?? 0,

          screen_y: window.screenY ?? window.screenTop ?? 0,

          screen_w: window.screen.width,

          screen_h: window.screen.height,

          devicePixelRatio: window.devicePixelRatio || 1,

          kiosk_rect: kioskRect,

          godot_zone_rect: godotZoneRect,

        },

      };

    },

  };



  window.EduOrientation = EduOrientation;

})();
