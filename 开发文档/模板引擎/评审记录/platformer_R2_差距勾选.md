# platformer R2 · 秒哒 vs Godot 差距勾选表

> **日期**：2026-06-23  
> **参考**：秒哒 PRD + `MainGame.ts` / `constants.ts` / `store.ts`  
> **目标**：`templates/platformer/`  
> **预览对照**：https://app-chu2c3e6u4g1.appmiaoda.com

---

## 1. 流程与 UI

| PRD 能力 | 秒哒 | Godot L0（改前） | R2 目标 |
|----------|------|------------------|---------|
| 开始界面 | React 覆盖层 + START | 无，进场景即玩 | ✅ 开始面板 |
| 游戏界面 HUD | 分数/命/关卡/金币 | 仅「星星 x/5」 | ✅ 四项 HUD |
| 游戏结束界面 | GAME OVER + 分数 + 重试/菜单 | 掉坑/碰怪临时 overlay | ✅ 结束面板 |
| 胜利界面 | LEVEL CLEARED + 下一关 | 收集 5 星即胜 | ✅ 通关旗胜利 |

---

## 2. 玩法与数值

| PRD 能力 | 秒哒 constants | Godot L0 | R2 目标 |
|----------|----------------|----------|---------|
| 初始生命 | 3 | 无限重开 | ✅ max_lives=3 |
| 侧面/下方碰敌 | 扣 1 命 + 无敌帧 1500ms | 碰怪即「死亡」重来 | ✅ 扣命 + 闪烁无敌 |
| 掉坑 | 扣 1 命 + 回起点 | 扣命式重来（无命数） | ✅ 扣命 + 回起点 |
| 踩头杀怪 | 消灭 + 弹跳 -300 + 100 分 | 无 | ✅ stomp 判定 |
| 金币 | +10 分，计数 | 星星收集无分 | ✅ 金币 +10 |
| 通关旗 | +500 分 | 无 | ✅ goal +500 |
| 胜利条件 | 到达终点旗 | 收集 5 颗星 | ✅ 终点旗 |
| 关卡宽度 | 视口 ×3 (800→2400) | 固定 ~640 | ✅ 640×3=1920 |
| 卷轴相机 | 跟随玩家，偏左 | 相机 limit 固定 | ✅ 跟随 + 边界 |

---

## 3. 关卡元素

| 元素 | 秒哒 MainGame | Godot L0 | R2 目标 |
|------|---------------|----------|---------|
| 地面 | 32px 平铺 | 5 段平台 | ✅ 全长地面条 |
| 砖块 | 随机 box + 顶出金币/碎裂 | 无 | ✅ 问号砖块 |
| 管道 | x=400/800 障碍 | 无 | ✅ 2 根管道 |
| 敌人 | 巡逻 velocity 50 | 短距 patrol | ✅ 全宽 bounce 巡逻 |
| 金币 | 旋转动画 cherries | Kenney 星星静帧 | ✅ 樱桃旋转 |
| 终点旗 | End idle/pressed | 无 | ✅ 旗杆 Area2D |

---

## 4. 操作与物理

| 项目 | 秒哒 | Godot L0 | R2 |
|------|------|----------|-----|
| 移动 | ←→ / AD | ←→ / AD | ✅ 已有 |
| 跳跃 | 空格 / ↑ | 空格 / ↑ | ✅ 已有 |
| 重力 | 800 | 980→config 800 | ✅ tuning |
| 玩家速度 | 200 | 200 | ✅ |
| 跳跃力 | -400 | -400 | ✅ |
| 二段跳 | 无 | 可选 skill | ✅ 默认关 |

---

## 5. 美术与动画

| 项目 | 秒哒 assets.ts | Godot L0 | R2 |
|------|----------------|----------|-----|
| 角色 | Pixel Adventure Mask_Dude 条 | Kenney p1_stand 单帧 | ✅ PA idle/run/jump/fall |
| 金币 | Cherries 544×32 | star.png | ✅ PA Cherries |
| 砖块 | Box1 动画 | 无 | ✅ PA Box1 |
| 终点 | End 动画 | 无 | ✅ PA End |
| 背景 | Blue 64×64 平铺 | Kenney bg | ✅ PA Blue |
| 敌人/管道/地面 | Boot 生成色块 | Kenney slime | ✅ PA 敌人条 + 色块管道/地 |

**素材来源**：OGA CC0 `Pixel Adventure 1.zip` → `assets/third_party/pixel-adventure-1/extracted/` → junction `templates/platformer/assets/pixel_adventure/`

---

## 6. game_config 外置项（R2）

| 键 | 秒哒来源 | 默认值 |
|----|----------|--------|
| tuning.player.move_speed | PLAYER_SPEED | 200 |
| tuning.player.jump_velocity | PLAYER_JUMP | -400 |
| tuning.physics.gravity | GRAVITY | 800 |
| tuning.enemy.patrol_speed | ENEMY_SPEED | 50 |
| tuning.enemy.bounce_on_stomp | BOUNCE_ON_ENEMY | -300 |
| tuning.scoring.coin | SCORE_COIN | 10 |
| tuning.scoring.enemy_stomp | SCORE_ENEMY | 100 |
| tuning.scoring.goal | SCORE_GOAL | 500 |
| tuning.lives.max | MAX_LIVES | 3 |
| tuning.lives.invincible_sec | INVINCIBLE_TIME | 1.5 |
| tuning.level.width_multiplier | GAME_WIDTH×3 | 3 |

---

## 7. 仍与秒哒有差距（已知可接受）

| 项 | 说明 |
|----|------|
| 多关卡递进 | 秒哒有 nextLevel；R2 实现胜利+重开，关卡号递增 UI，布局复用 |
| 砖块顶出随机 | 秒哒 50% 金币/碎裂；R2 简化：顶砖必出金币 |
| 敌人/管道美术 | 秒哒 Boot 亦为程序生成色块，非 PA 精美术 |
| 分辨率 | 秒哒 800×600 vs Godot 640×360（Kiosk 规格） |
| 音效 | PRD 本期不做；保留 Kenney impact/interface |

---

## 8. 勾选汇总（R2 交付）

- [x] 开始 → 游戏 → 结束/胜利界面
- [x] 3 命 + 侧面/下方碰敌 + 掉坑 + 无敌帧
- [x] 踩头杀怪 + 弹跳 + 100 分
- [x] 金币 +10、通关旗 +500
- [x] HUD：分数/生命/关卡/金币
- [x] 横版卷轴相机 + 3 倍关卡宽
- [x] 地面/砖块/管道/敌人/金币/终点旗
- [x] ←→/AD + 空格跳跃
- [x] Pixel Adventure 动画 + theme 路径
- [x] 数值写入 game_config.json

---

## 9. 深对齐迭代（2026-06-23 · 用户验收通过）

| 项 | 秒哒 / 需求 | Godot 落点 | 状态 |
|----|-------------|------------|------|
| 坐标系 | 800×600 · y 向下 | `_miaoda_x/y_to_godot` → 640×360 | ✅ |
| 地面 | Boot `#8B4513` 32px 平铺 | 动态 StaticBody2D · layer=2 | ✅ |
| 敌人外观 | Boot 绿色色块 | `#00aa00` ColorRect · 非 PA atlas 拉伸 | ✅ |
| 踩头判定 | 下落中接触顶面 | StompArea + `_was_falling_before_move` | ✅ |
| 同向侧面伤 | 玩家与敌同向不扣命 | HurtArea + slide collision | ✅ |
| 关卡差异 | 多关递进 | level profile + seed · 管道/砖/敌权重 | ✅ |
| 紫敌人 Lv4+ | 2 踩才死 · 1 踩眩晕 | `tough_enemy.gd` · 保底 ≥2 只 | ✅ |
| 橙敌人 Lv5+ | 慢速 + 跳跃 | `jumper_enemy.gd` · jump 0.8× 玩家 | ✅ |
| 红炮台 Lv5+ | 固定发射 | `turret_enemy.gd` + `enemy_orb.gd` | ✅ |
| 关卡号注入 | nextLevel 递增 | `configure_level(n)` **先于** `add_child` | ✅ |

**验收结论**：用户 2026-06-23 试玩通过 · MCP `errors: []` · 经验见 [`platformer_R2复刻经验手册_v1.0.md`](../platformer_R2复刻经验手册_v1.0.md)

---

*v1.1 · 2026-06-23 · 深对齐迭代 + 用户验收通过*
