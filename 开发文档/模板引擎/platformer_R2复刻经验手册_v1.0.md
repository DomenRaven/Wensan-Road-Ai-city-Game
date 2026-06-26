# platformer（横版闯关）R2 复刻经验手册 v1.0

> **日期**：2026-06-23  
> **品类**：`platformer` · 马里奥风格横版闯关  
> **状态**：✅ Godot 可玩 · 用户验收通过 · `r2_done`  
> **模板**：`templates/platformer`  
> **秒哒参考**：`app-chu2c3e6u4g1` · `秒哒游戏原型/横版闯关游戏/app-chu2c3e6u4g1/`  
> **注册表**：`config/miaoda_parity_r2_registry.json`

---

## 一、本手册用途

记录 **A 档首开深 R2** 从 L0 到用户验收的完整路径，重点覆盖：

- 秒哒 800×600 坐标 → Godot 640×360 映射
- 踩头 / 侧面扣命 / 同向接触判定
- 动态地形与敌人碰撞层
- Lv4+ 扩展敌人类与关卡号注入时序

**配套文档**：

| 文档 | 关系 |
|------|------|
| [`platformer_R2_差距勾选.md`](./评审记录/platformer_R2_差距勾选.md) | P0 勾选与已知差距 |
| [`6.23_R2对齐执行规范手册_v1.0.md`](./6.23_R2对齐执行规范手册_v1.0.md) | 通用 R2 工序 |
| [`shmup_R2复刻经验手册_v1.0.md`](./shmup_R2复刻经验手册_v1.0.md) | 第二款深 R2 对照 |

---

## 二、复刻目标与验收

### 2.1 秒哒 PRD 核心（P0）

| 机制 | 秒哒实现 | Godot 落点 |
|------|----------|------------|
| 3 命 + 无敌帧 | zustand lives + 1500ms | `game_manager.gd` + `player_platformer.gd` |
| 踩头杀怪 | 下落接触顶面 · bounce -300 · +100 | `StompArea` + `on_stomped()` |
| 侧面/下方碰敌 | 扣 1 命 | `HurtArea` + slide collision |
| 金币/旗杆 | +10 / +500 | `question_block.gd` · goal Area2D |
| 横版卷轴 | 视口×3 · 相机偏左 | `level_01.gd` · Camera2D |
| 关卡元素 | 地面/砖/管道/巡逻敌 | `level_01.gd` 程序化生成 |

### 2.2 验收结论（2026-06-23）

- ✅ 用户试玩通过：踩头、侧面扣命、同向不扣命、Lv4+ 新敌人可见
- ✅ `godot-mcp run_project` · `errors: []`
- ⚠️ 已知可接受：640×360 · 顶砖必出金币 · 多关 layout 复用+profile 变体 · 无 BGM

---

## 三、坐标与布局映射

秒哒 `MainGame.ts` 使用 **800×600**，Godot Kiosk 为 **640×360**。

```gdscript
# level_01.gd 核心换算（示意）
func _miaoda_x_to_godot(mx: float) -> float:
    return mx * (640.0 / 800.0)

func _miaoda_y_to_godot(my: float) -> float:
    return my * (360.0 / 600.0)
```

**教训**：

1. 不可直接照搬秒哒像素坐标，须按比例缩放。
2. 地面须 **32px 平铺色块**（Boot `#8B4513`），勿用 PA Terrain 整图拉伸。
3. 敌人/管道位置一律经换算函数写入，避免「看起来对、碰撞错位」。

---

## 四、碰撞与踩头（高频踩坑）

### 4.1 玩家/敌人穿地

| 现象 | 根因 | 修复 |
|------|------|------|
| 玩家/敌人掉穿地面 | 动态 `StaticBody2D` 未设 layer | `collision_layer = 2`（world） |
| 敌人碰不到玩家 | mask 仅 world | 敌人 `collision_mask` 含 player 层（2→3） |

### 4.2 踩头不生效

| 现象 | 根因 | 修复 |
|------|------|------|
| 站在敌头上不杀 | 用移动后 velocity 判 falling | **`_was_falling_before_move`** 在 `move_and_slide` 前记录 |
| 踩头无分 | 未等 `on_stomped()` 返回 true | 仅成功击杀时加分 |
| 侧面也触发踩头 | 单一 Area 混判 | 分离 **StompArea**（顶）与 **HurtArea**（侧/底） |

### 4.3 同向接触不扣命

秒哒：玩家与敌人同向移动时侧面接触不伤害。

- 实现：`HurtArea` + 相对速度/朝向检测 + slide collision  proximity
- 文件：`player_platformer.gd`

---

## 五、Lv4+ 扩展敌人

| 类型 | 颜色 | 脚本 | 行为 | 出现关卡 |
|------|------|------|------|----------|
| normal | 绿 | `patrol_enemy.gd` | 1 踩即死 | 全关 |
| tough | 紫 | `tough_enemy.gd` | 2 踩；第 1 踩 0.6s 眩晕+闪烁 | Lv4+ 保底 ≥2 |
| jumper | 橙 | `jumper_enemy.gd` | 0.5× 速 · 跳高 0.8× 玩家 | Lv5+ 保底 +2 |
| turret | 红 | `turret_enemy.gd` | 固定锚点 · 2.5s 发 orb | Lv5+ 管道/砖块上 |
| orb | 红弹 | `enemy_orb.gd` | 80px/s 左飞 · 5s 寿命 | turret 发射 |

**基类**：`enemy_patrol_base.gd` · 各子类覆写 `on_stomped()` / `_physics_process`

**config**：`game_config.json` → `tuning.enemy_types`

---

## 六、关卡号注入时序（Lv4–5 无新敌人根因）

**现象**：第 4–5 关仍只有绿色巡逻怪。

**根因**：

1. `level_01.gd` 在 `_ready` 时 `_level_num` 仍为默认 1
2. 新敌人权重过低，随机未命中

**修复**：

```gdscript
# game_manager.gd — 必须先 configure 再 add_child
level.configure_level(_level_num)
add_child(level)
```

并在 `level_01.gd` 对 Lv4/Lv5 做 **保底生成**（`_spawn_guaranteed_new_enemies`）。

---

## 七、关键文件索引

```
templates/platformer/
├── core/
│   ├── game_manager.gd      # 流程 · configure_level 调用
│   ├── player_platformer.gd # StompArea / HurtArea / 无敌帧
│   ├── level_01.gd          # 坐标映射 · 程序化关卡 · 敌人生成
│   ├── enemy_patrol_base.gd
│   ├── patrol_enemy.gd · tough_enemy.gd · jumper_enemy.gd
│   ├── turret_enemy.gd · enemy_orb.gd
│   └── question_block.gd
├── scenes/
│   ├── player.tscn          # StompArea + HurtArea 子节点
│   └── level_01.tscn        # Projectiles 容器（orb）
└── config/game_config.json
```

---

## 八、自检清单（后续 polish / 展陈前）

- [ ] 与秒哒 H5 左右试玩 1 次（非阻塞）
- [ ] 顶砖 50% 随机（若需更贴近秒哒）
- [ ] 多关独立 layout（若需超越 profile+seed）
- [ ] BGM（PRD 本期外）

---

*v1.0 · 2026-06-23 · platformer R2 用户验收通过会话产出*
