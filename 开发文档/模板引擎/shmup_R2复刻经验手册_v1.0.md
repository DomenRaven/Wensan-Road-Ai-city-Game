# shmup（街机飞机射击）R2 复刻经验手册 v1.0

> **日期**：2026-06-23  
> **品类**：`shmup` · 街机飞机射击  
> **状态**：✅ Godot 可玩 · 用户试玩通过 · `r2_done`  
> **模板**：`templates/shmup`  
> **秒哒参考**：`app-chu7pw7h454x` · `秒哒游戏原型/街机飞机射击/app-chu7pw7h454x/`  
> **注册表**：`config/miaoda_parity_r2_registry.json`

---

## 一、本手册用途

记录 **platformer 之后第二款深 R2** 的完整复刻路径，以及试玩阶段暴露的 **卡死 / 黑屏 / 无实体** 等问题的根因与修复，供后续 **survivor、pingpong** 等品类复刻时对照，避免重复踩坑。

**配套文档**：

| 文档 | 关系 |
|------|------|
| [`6.23_R2对齐执行规范手册_v1.0.md`](./6.23_R2对齐执行规范手册_v1.0.md) | 通用 R2 工序 |
| [`6.23_七天交工工作清单_v1.0.md`](./6.23_七天交工工作清单_v1.0.md) | D1–D2 勾选 |
| [`秒哒转Godot_game_config_指导手册_v1.0.md`](./秒哒转Godot_game_config_指导手册_v1.0.md) | v1 config 层（非 R2 完成标准） |

---

## 二、复刻目标与验收

### 2.1 秒哒 PRD 核心（P0）

| 机制 | 秒哒实现 | Godot 落点 |
|------|----------|------------|
| 无尽得分 | Zustand `score` | `game_manager.gd` + HUD |
| 三类敌机 | NORMAL / FAST / HEAVY | `enemy_types` + `enemy_ship.gd` |
| Boss 循环 | 500 分首次，+1000 循环 | `enemy_spawner.gd` + `boss` tuning |
| 道具 | fireRate / doubleShot / shield | `powerup_pickup.gd` + `player_ship.gd` |
| 自动射击 + 拖拽 | Phaser pointer + timer | `player_ship.gd` |
| 开始 / 结束 UI | React 叠层 | `main.tscn` + `game_manager.gd` |
| 像素美术 | pixel-plane-shmup spritesheet | `shmup_sheet.gd` + `assets/` |

### 2.2 验收结论（2026-06-23）

| 项 | 结果 |
|----|------|
| `godot-mcp run_project` | ✅ errors: [] |
| 用户 Godot 试玩 | ✅ 可正常开局、移动、射击、敌机、Boss |
| 手感调优 | ✅ 敌机−10% · 弹速×0.7 · 120° 锁定弹 · Boss 血条 |
| **用户验收** | ✅ **通过**（2026-06-23 定稿） |
| 与秒哒 H5 左右对照 ≥10min | 🔲 展陈前可选（非阻塞） |
| 贴图偶发残留 | 🔲 已知项 · 清场补丁已回退（§九） |

---

## 三、复刻过程（按阶段）

### 阶段 0 · 读参考（勿跳过）

1. 读秒哒 `docs/prd.md`、`src/game/constants.ts`、`src/game/scenes/MainGame.ts`
2. 本地秒哒试玩：`npm install` → `npx vite`（**勿用** `npm run dev`，秒哒脚手架禁用）
3. 填 R2 规范手册附录 P0 勾选表

### 阶段 1 · 素材落盘

从秒哒导出目录复制到模板：

```
秒哒 …/Tilemap/*.png
  → templates/shmup/assets/pixel-plane-shmup/Tilemap/
```

**必须复制并重命名（见 §五.1）**：

| 原文件名（秒哒） | 模板内使用名 |
|------------------|--------------|
| `ships_packed (128x192)[frames=1].png` | `ships_packed.png` |
| `tiles_packed (192x160)[frames=1].png` | `tiles_packed.png` |
| `background.png` | `background.png`（无需改名） |

PowerShell 复制含方括号文件时用 **`-LiteralPath`**：

```powershell
Copy-Item -LiteralPath "…\ships_packed (128x192)[frames=1].png" -Destination "…\ships_packed.png" -Force
```

### 阶段 2 · 玩法 core 改造（由 L0 波次制 → 秒哒无尽制）

| 新增 / 重写 | 职责 |
|-------------|------|
| `core/shmup_sheet.gd` | spritesheet 切帧 |
| `core/enemy_spawner.gd` | 连续刷怪 + 难度爬坡 + Boss 触发 |
| `core/enemy_ship.gd` | 三类敌机 + Boss 入场/巡逻/扇形弹 |
| `core/player_ship.gd` | 自动射击、道具、护盾、鼠标/方向键 |
| `core/powerup_pickup.gd` | 掉落物 |
| `core/explosion_fx.gd` | 击毁特效 |
| `core/game_manager.gd` | START / PLAYING / GAMEOVER 流程 |
| `core/game_area.gd` | 场景内实体接线 |
| `core/scroll_background.gd` | 卷轴背景 |
| `config/game_config.json` | `enemy_types`、`boss`、`powerup_types`、`win.mode: endless` |

**废弃路径**：`enemy_wave.gd` 波次胜利逻辑不再走主流程（文件可保留，勿挂回场景）。

### 阶段 3 · 场景与 UI

- `scenes/main.tscn`：开始屏、Game Over、分数 HUD（绿/红街机风）
- `scenes/game.tscn`：Camera2D、背景、子弹池、刷怪器、玩家
- `scenes/player.tscn` / `enemy.tscn` / `bullet.tscn` / `powerup.tscn` / `explosion_fx.tscn`

### 阶段 4 · 验证

```text
godot-mcp run_project  →  templates/shmup
```

人工：开始 → 玩 3 分钟 → Boss（调试用 debug 加分或打到 500）→ 道具 → 死亡 → 重试。

---

## 四、秒哒 → Godot 架构对照

```text
秒哒                              Godot R2
────────────────────────────────────────────────────
React StartScreen / GameOver      main.tscn + game_manager.gd
Phaser MainGame scene             scenes/game.tscn + game_area.gd
Zustand score                     game_manager._score
physics groups                    Area2D + collision_layer/mask
ships/tiles spritesheet           shmup_sheet.gd (32×32 / 16×16)
ENEMY_TYPES / POWERUP_TYPES       game_config.tuning
```

**数值对齐源**：`constants.ts` 中 `PLAYER_SPEED`、`ENEMY_SPAWN_RATE`、`BOSS` hp/score 等 → 写入 `game_config.json` 的 `tuning`（±30% 规则仍适用）。

---

## 五、问题排查与修复（重点）

### 5.1 贴图文件名含 `[` `]` → 加载失败 / 卡死

**现象**

- 点击「开始游戏」后黑屏，无飞机敌机
- 窗口标题 **「未响应」**，开始界面可能仍可见
- `godot-mcp` 有时无 ERROR（卡死在导入阶段，不进脚本报错）

**根因**

1. Godot `res://` 路径中 **`[xxx]` 表示子资源**，秒哒素材名 `ships_packed (128x192)[frames=1].png` 会被错误解析  
2. `pixel-plane-shmup` 三张 PNG **无 `.import` 文件**；`preload(png)` 会在主线程 **同步导入**，点击开始时阻塞 UI

**修复（最终方案）**

1. 磁盘上复制为无方括号文件名：`ships_packed.png`、`tiles_packed.png`  
2. `shmup_sheet.gd` 使用 **`Image.load()` + `ImageTexture.create_from_image()`**，绕过导入管线  
3. 主菜单 `call_deferred("_warmup_assets")` 预热贴图  
4. **禁止**对无 `.import` 的秒哒 PNG 使用 `preload("res://…[frames=1].png")`

```gdscript
# shmup_sheet.gd · 推荐模式
static func _load_image_texture(res_path: String) -> Texture2D:
    var disk_path := ProjectSettings.globalize_path(res_path) if res_path.begins_with("res://") else res_path
    var img := Image.new()
    if img.load(disk_path) != OK:
        push_error("ShmupSheet: cannot load %s" % res_path)
        return null
    return ImageTexture.create_from_image(img)
```

**后续 R2 检查清单**

- [ ] 秒哒素材是否含 `[]`？→ 复制时改名  
- [ ] 新 PNG 是否有 `.import`？→ 无则 `Image.load` 或先跑 Godot 编辑器导入  
- [ ] 是否误用 `preload` 大贴图？→ 改懒加载 + 缓存

---

### 5.2 `configure()` 早于 `_ready()` → `@onready` 为 null

**现象**

```
Invalid assignment of property 'texture' on a base object of type 'Nil'
at shmup_sheet.gd → enemy_ship._apply_sprite
```

**根因**

`enemy_spawner` 在 `add_child` **之前** 调用 `enemy.configure()`，`@onready var _sprite` 尚未赋值。

**修复**

1. **先** `add_child(enemy)`，**再** `configure()`  
2. `_apply_sprite` 内用 `get_node_or_null("Sprite2D")` 兜底  
3. `game_manager` 对 `game_area.setup()` 使用 `call_deferred`

---

### 5.3 `game_area.setup()` 与 `@onready` 时序

**现象**

敌机不刷、`set_playing(false)` 一直生效，像「能进 HUD 但没玩法」。

**根因**

`setup()` 若在 `game_area._ready()` 之前同步调用，`_player` / `_spawner` 的 `@onready` 为 null，信号与 `set_spawning` 未接上。

**修复**

- `game_manager`：`call_deferred("setup", self)`  
- `game_area.setup`：用 `get_node_or_null("Player")` 而非仅依赖 `@onready`

---

### 5.4 点击开始主线程阻塞 → Windows「未响应」

**现象**

HUD 未切换或切换后卡死；任务管理器显示 Godot 未响应。

**叠加原因**

| 因素 | 处理 |
|------|------|
| 同步 `load("game.tscn")` 每次点击 | 改为 `const GAME_SCENE = preload(...)` |
| 128 子弹同帧 `instantiate` | 池大小降至 48，`call_deferred("_build_pool")` |
| 贴图同步导入 | `Image.load` + 主菜单预热 |
| `theme_sound.gd` 写 `const` 缓存 | 改为 `static var _stream_cache`（`const` 不可变） |

**UX 修复**

```gdscript
# 点击开始后先藏菜单、显 HUD，再 deferred 加载场景
func _begin_start_flow() -> void:
    _start_screen.visible = false
    _hud.visible = true
    call_deferred("_start_game")
```

---

### 5.5 背景不显示 / 纯黑屏

**原因**

- `ColorRect` 挂在 `Node2D` 下不符合 Godot 4 推荐用法  
- 贴图未加载时仅见 `#0a0a0c` 近黑底色  

**修复**

- 背景改为双 `Sprite2D`（`BgA` / `BgB`）无缝滚动  
- `Camera2D.current = true`  
- 在 `game_area.setup` 中 `camera.make_current()`

---

### 5.6 脚本级错误备忘

| 错误 | 修复 |
|------|------|
| `Integer division` 警告 | `int(floor(float(a) / float(b)))` |
| `Parser Error: Cannot assign to constant` | 音效缓存用 `static var` 非 `const` |
| PowerShell `Copy-Item` 方括号路径失败 | `-LiteralPath` |

---

## 六、关键文件速查

```text
templates/shmup/
├── config/game_config.json      # tuning / theme / enemy_types / boss
├── core/
│   ├── game_manager.gd          # 流程 + 预热 + preload 场景
│   ├── game_area.gd             # 场景接线
│   ├── shmup_sheet.gd           # ★ 贴图加载（Image.load）
│   ├── enemy_spawner.gd
│   ├── player_ship.gd
│   └── theme_sound.gd           # static var 缓存
├── scenes/main.tscn             # UI 壳
├── scenes/game.tscn             # 对局
└── assets/pixel-plane-shmup/Tilemap/
    ├── ships_packed.png         # ★ 无方括号
    ├── tiles_packed.png
    └── background.png
```

---

## 七、给下一款 R2（survivor / pingpong）的速查清单

**开工前**

- [ ] 读 PRD + constants，填 P0 表  
- [ ] 确认秒哒素材文件名，**批量去掉 `[]`** 或准备 `Image.load`  
- [ ] 检查目标 PNG 是否已有 `.import`  

**编码时**

- [ ] 动态实体：`add_child` 后再 `configure`  
- [ ] 场景 `setup`：用 `call_deferred` + `get_node`  
- [ ] 大场景：`preload` PackedScene，勿每次 `load()`  
- [ ] 对象池：分帧创建，单帧 < 50 实例  
- [ ] 贴图：静态缓存，避免每帧 `load()` / 新建 AtlasTexture  

**提测时**

- [ ] MCP `run_project` 无 ERROR  
- [ ] 点击开始 **3 秒内** 必须看到可控实体（否则先查 §5.1 / §5.3）  
- [ ] 任务管理器无「未响应」  
- [ ] 死亡 / Game Over / 回菜单后 **无贴图残留**（§5.7）  
- [ ] 与秒哒 H5 左右试玩记差距  

---

## 八、手感调优记录（2026-06-23 迭代）

用户试玩后二次调参，均落在 `game_config.json` + 少量 core 逻辑。

| 项 | 调整 | 配置 / 代码 |
|----|------|-------------|
| 敌机速度 | 全类型 **−10%** | `enemy_types.*.speed` |
| 敌弹速度 | **×0.7**（300→210） | `tuning.enemy.bullet_speed` |
| 追踪弹 | **发射时锁定倾角**，飞行中不转向 | `enemy_ship._compute_launch_direction` |
| 发射扇形 | 以正下方为轴 **120°** 内 | `tuning.enemy.aim_cone_deg` |
| Boss 血条 | HUD 红条 + `BOSS cur/max` 文字 | `main.tscn` + `game_manager.update_boss_hp` |

**追踪弹逻辑要点**：仅在 `spawn` 前读一次玩家坐标 → 与 `Vector2.DOWN` 夹角 clamp 到 ±60° → 直线飞行。勿再做飞行中 `homing`（易绕屏滞留）。

---

## 九、贴图残留（幽灵精灵）— 暂缓

> **2026-06-23 回退**：曾用 `_game_root.visible = (status==PLAYING)` 清场，但 `_begin_start_flow` 未走 `_show_screen`，导致开局 **GameRoot 一直隐藏、黑屏**。该补丁已撤销。

**若再修**：在 `_start_game` 显式 `_game_root.visible = true`，勿仅在 `_show_screen` 切换；或死亡时只 `hide_ship` + `clear_enemy_bullets`，不隐藏整层。

---

## 十、修订记录

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-06-23 | 首版：复刻过程 + 卡死/黑屏排查 |
| v1.1 | 2026-06-23 | §八 手感调优 · 用户确认可玩 |
| v1.2 | 2026-06-23 | §九 标注贴图残留补丁已回退 |
| v1.3 | 2026-06-23 | **用户验收通过** · 定稿交付状态 |

---

*维护：每完成一款深 R2，在 §七 追加品类特例一行；通用坑保留在 §五。*
