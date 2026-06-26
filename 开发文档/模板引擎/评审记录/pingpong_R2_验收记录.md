# pingpong R2 · 用户验收记录

> **日期**：2026-06-23  
> **模板**：`templates/pingpong/`  
> **参考**：`秒哒游戏原型/乒乓球小游戏/app-cika5uyinqip`  
> **预览**：https://app-cika5uyinqip.appmiaoda.com

---

## 验收结论

| 项 | 结果 |
|----|------|
| 验收状态 | ✅ **通过** |
| 签字 | 用户 |
| 日期 | 2026-06-23 |
| MCP | `run_project` 无 ERROR |

---

## 本次试玩调优（验收前会话）

| 模块 | 改动 |
|------|------|
| 开始界面 | 仅保留球场背景 + START 启动图标 |
| 开局流程 | 3→2→1→开始 倒计时；`setup()` 先于 `add_child` 修复未显示 |
| 球拍 | 自绘竖直贴图 `assets/paddles/paddle_*.png`；显示/判定分离（`hit_width`/`hit_height`） |
| 球场范围 | `margin_top/bottom: 24` 对称；球与拍可顶到上下边并反弹 |
| 球阴影 | 程序化柔和椭圆 + 贴图兜底；置于球体下层 |
| 人机 | 可配置瞄准误差/反应线/远距追球比例；终值 `speed:118` · `aim_error:16` |

---

## P0 能力勾选

| 能力 | 状态 |
|------|------|
| ↑↓ 玩家球拍 | ✅ |
| AI 对战 · 5 分制 | ✅ |
| 球拍角度反弹 · 3 击加速 · 球速浮动 | ✅ |
| 开始 / 结束 UI（pong-football 素材） | ✅ |
| 得分 HUD · 回合发球 | ✅ |
| `game_config.json` 外置 tuning/theme/ai | ✅ |

---

## 已知可接受差距（非阻塞）

- 结束页秒哒 `Back.easeOut` 入场动画未 1:1 复刻
- 展陈前可与秒哒 H5 左右对照试玩回归 1 次
- 无 BGM（与多品类 L0/R2 一致，Kenney 撞击音保留）

---

## 终版 AI 参数（`tuning.ai`）

```json
{
  "speed": 118,
  "deadzone": 10,
  "aim_error": 16,
  "react_line_x": 340,
  "far_chase_scale": 0.62,
  "aim_refresh_sec": 0.15
}
```
