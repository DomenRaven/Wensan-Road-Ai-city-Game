# survivor（割草肉鸽）R2 复刻经验手册 v1.0

> **日期**：2026-06-23  
> **品类**：`survivor` · 割草幸存者 / Vampire Survivors 类  
> **状态**：✅ Godot 可玩 · **用户验收通过** · `r2_done`  
> **模板**：`templates/survivor`  
> **秒哒参考**：`app-cikthp6wjz0h` · `秒哒游戏原型/割草肉鸽/app-cikthp6wjz0h/`  
> **注册表**：`config/miaoda_parity_r2_registry.json`

---

## 一、本手册用途

记录 **A 档深 R2** 从 L0 到用户验收的完整路径，重点覆盖：

- 大地图 + 相机跟随 + 视野缩放
- 实体不可见 / 灰块贴图 / 子弹残留等试玩坑
- Boss 全图激光、半血光球、受击反馈
- 玩家移动手感与碰撞扣血

**配套文档**：

| 文档 | 关系 |
|------|------|
| [`6.23_R2对齐执行规范手册_v1.0.md`](./6.23_R2对齐执行规范手册_v1.0.md) | 通用 R2 工序 |
| [`shmup_R2复刻经验手册_v1.0.md`](./shmup_R2复刻经验手册_v1.0.md) | 贴图 Image.load 方案同源 |
| [`platformer_R2复刻经验手册_v1.0.md`](./platformer_R2复刻经验手册_v1.0.md) | A 档首开对照 |

---

## 二、复刻目标与验收

### 2.1 秒哒 PRD 核心（P0）

| 机制 | Godot 落点 |
|------|------------|
| WASD 移动 + 自动射击 | `player_survivor.gd` · `auto_weapon.gd` |
| 鼠标左键改射击朝向 | `player_survivor._update_aim_from_mouse()` |
| 180s 倒计时 → Boss 战 | `survivor_arena.gd` · `game_manager.gd` |
| 6 类升级三选一 | `level_up_ui.gd` · 升级暂停 |
| Boss 升级回血 toast | `survivor_boss.full_heal()` · Boss 血条 |
| 开始 / 胜利 / 失败 UI | `main.tscn` · `game_manager.gd` |

### 2.2 验收结论（2026-06-23）

- ✅ 用户试玩验收通过
- ✅ `godot-mcp run_project` · `errors: []`
- ⚠️ 已知可接受：秒哒 top-down PNG 未落盘（Kenney 静帧）· 无行走动画 · 秒哒 H5 左右对照待展陈前补做

---

## 三、世界与相机

| 项 | 配置 / 文件 |
|----|-------------|
| 地图尺寸 | `tuning.world` 3000×3000 · `survivor_world.gd` |
| 刷怪环 | `spawn.ring_min/max` 520–680（屏外生成） |
| 相机 zoom | `world.camera_zoom` 0.58（扩大视野） |
| 跟随 | `arena_camera.gd` · **关闭** `position_smoothing`（避免拖滞） |

**教训**：勿用屏幕矩形 `clamp` 限制玩家；须 `SurvivorWorld.clamp_point()`。

---

## 四、显示与贴图（高频踩坑）

### 4.1 实体不可见但 HUD 正常

| 现象 | 根因 | 修复 |
|------|------|------|
| 角色/敌人看不见 | `ColorRect` 作 `Node2D` 子节点会盖住全部 Sprite | 背景改 `arena_background.gd` 的 `_draw()` 棋盘格 |
| 灰块敌人 | roguelike 地块当精灵 | 改 Kenney **topdown** 僵尸/机器人/士兵 |
| 贴图 load 失败 | 无 `.import` / 路径含特殊字符 | `survivor_sprite_util.gd` · `ResourceLoader` + `Image.load` 缓存 |

### 4.2 子弹残留

| 现象 | 根因 | 修复 |
|------|------|------|
| 弹道印在背景上 | 子节点坐标未随父节点清理 | `top_level=true` · `global_position` · 失活移出屏外 |

---

## 五、Boss 战

| 机制 | 实现 |
|------|------|
| 全图激光 + 瞄准线 | `survivor_boss.gd` · 方向锁定后延伸至地图对角线 1.25× |
| 激光受击 | `player.take_laser_hit()` · 击退 + 闪烁 + 粒子 + 震屏 |
| 半血光球环 | HP≤50% · 每 5s · 12 向 · 寿命 5s · 移速 0.7×玩家 |
| 光球扣血 | `boss_orb.gd` 外扩 52px 生成 + 距离判定 · `take_orb_hit()` |
| Boss 弹幕 | `hostile_projectile.gd` · 放大贴图 2.4× · 碰撞半径 11 |

**教训**：光球勿从 Boss 中心生成（与 Boss `Area2D` 重叠）；普通 `take_hit` 无敌帧会挡住光球，须独立 `take_orb_hit`。

---

## 六、玩家 UX

| 项 | 文件 |
|----|------|
| 底部生命血条 | `main.tscn` · `game_manager.update_hp()` |
| 面朝移动方向 | `SurvivorSpriteUtil.apply_facing_flip()` |
| 普通受击 | 闪红 · 缩放 · 击退 · 0.5s 无敌 |
| 升级悬停 | `level_up_ui.gd` · 绿底白字 |
| 连发夹角 | `weapon.spread_deg` = **12**（原 15−3°） |

---

## 七、移动手感（必查）

**现象**：WASD 卡顿、仅斜向能走。

**根因**：`if direction.length_squared() > 1.0` 时单轴输入长度恰为 1，不满足条件；受击改动后误把 `position +=` 放进该分支。

**修复**：

```gdscript
if input_dir.length_squared() > 0.001:
    move_velocity = input_dir.normalized() * _speed * _speed_multiplier
var total_velocity := move_velocity + _knockback
position += total_velocity * delta
```

---

## 八、核心文件索引

| 文件 | 职责 |
|------|------|
| `survivor_arena.gd` | 会话、Boss 召唤、XP、HUD 桥接 |
| `survivor_boss.gd` | 激光、弹幕、召唤、光球环 |
| `boss_orb.gd` | 半血光球 |
| `player_survivor.gd` | 移动、受击、升级数值 |
| `level_up_ui.gd` | 暂停选技能 |
| `horde_spawner.gd` | 环形刷怪 |
| `game_config.json` | tuning/theme 外置 |

---

## 九、给下一款 R2 的速查清单

- [ ] 背景勿用 `ColorRect` 挂在世界 `Node2D` 下
- [ ] 大地图 + `Camera2D` 跟随，玩家勿 screen-clamp
- [ ] 贴图统一走 `Image.load` 兜底
- [ ] 投射物 `top_level` + 池化失活移出世界
- [ ] 移动阈值用 `> 0.001`，勿用 `> 1.0`
- [ ] Boss 范围技：生成点外扩 + 距离判定双保险
- [ ] MCP `run_project` 无 ERROR 后再交用户试玩

---

*v1.0 · 2026-06-23 · 用户验收通过*
