# AI 小游戏创作工坊 · 历史工作足迹 v1.3

> **项目**：GameForge K12 · 文三路 AI 教育区  
> **更新**：2026-06-22 · **真实状态：引擎 ✅ · 产品 UI / E2E ❌**

---

## 当前里程碑（2026-06-22）

```
#0  L0 + D6 polish     ██████████  ✅
#6–10 素材/预览/音效   ██████████  ✅
#11–12 Redis/压测     ████████░░  🔄  soak 未做
#1–#4 Kiosk + E2E     ██░░░░░░░░  ❌  灰盒 only · 个性化未通
双轨 A 展陈            ██░░░░░░░░  🔲
双轨 B 个性化          ░░░░░░░░░░  🔲
```

**D10 硬标准**：11 L0 ✅ · **Kiosk 产品 + E2E 🔲** · 10 并发脚本 ✅

### 2026-06-22 · 真实状态纠偏 + 双轨启动

| 项 | 说明 |
|----|------|
| **纠偏** | Kiosk 非产品 UI；S8 无 workspace；S9 仅 L0；E2E 未测 |
| **双轨计划** | [`D6-D10双轨并行计划_v1.0.md`](./模板引擎/D6-D10双轨并行计划_v1.0.md) |
| **约束 JSON** | `dual_track_registry` · `kiosk_ui_spec` · `wizard_payload_mapping` · `l1_e2e_acceptance` |
| **Cursor 规则** | `.cursor/rules/dual-track-kiosk.mdc` |

**当前应做（并行）**：
- **线 A**：产品 UI + L0 快速试玩 + LAN + soak
- **线 B**：`POST /generate` + config_builder + platformer `E2E-B-001`

### 2026-06-22 · 双轨（秒哒 + 素材）

| 完成项 | 产出 |
|--------|------|
| **秒哒竞品调研** | `03-背景与调研/秒哒竞品调研整合_v1.0.md` · 爬虫 561 条 |
| **11 品类提示词** | `秒哒11品类创作提示词_v1.0.md` · `config/miaoda_11_genre_prompts.json`（每类 ≥3 参考游戏） |
| **批次脚本** | `05-工具脚本/miaoda_batch_create.py` · API `tools/miaoda-skill/miaoda-app-builder/` |
| **批次进度** | **11/11 ✅** · 见 `data/秒哒11品类批次/batch_summary.jsonl` |
| **精选 7 项** | 成熟秒哒项目落盘 · `config/miaoda_reference_registry.json` · 转译手册 |
| **P1 素材 +3** | tiny-dungeon · roguelike-caves · 1-bit-pack → `assets/kenney/` · **29/29 OK** |
| **junction 刷新** | `wire_theme_sounds.py` · 11 类 impact/interface |

**双轨策略**：秒哒验证手感与 UX → 提取 tuning/theme → 只改 Godot `game_config.json`；**不迁代码、不替代 Kiosk/exe**。

**秒哒预览（已完成）**

| 品类 | 预览 URL |
|------|----------|
| platformer | https://app-cij488f80bup.appmiaoda.com |
| tower_defense | https://app-cijbpg71a0w1.appmiaoda.com |

**素材中央库**：`assets/kenney/{pack}/extracted/` · 清单 `assets/manifest.json` · 模板 junction `templates/{slug}/assets/kenney/`

### 2026-06-23 · 秒哒对齐 R2 立项

| 项 | 说明 |
|----|------|
| **用户决策** | 大幅度向秒哒对齐：交互逻辑、数值、美术；本地 L0 原型质量不足 |
| **v1 转译** | `miaoda_apply_translation.py` 7/7 已写 config · **不作为交付标准** |
| **R2 文档** | `秒哒对齐R2_立项说明_v1.0.md` · `config/miaoda_parity_r2_registry.json` |
| **开工方式** | 新会话 · 单品类 · 从 `platformer` 起 · 可改 core/scenes |

---

## 当前里程碑（2026-06-21）

```
#0  L0 + D6 polish     ██████████  ✅
#1–#4 Kiosk + 试玩     █████████░  🔄  launch API ✅
#9–#10 音效/预览       ██████████  ✅ 含 Kenney theme.sounds
#11–#12 Redis/压测     ██████████  ✅
#5–#8 #13+            ░░░░░░░░░░  🔲
```

**D10 硬标准进度**：11 品类 L0 ✅ · Kiosk+试玩 🔄 · **10 并发 ✅**

### 2026-06-21 · 阶段 A/B 并行

| 完成项 | 产出 |
|--------|------|
| **Kiosk v0.2** | S0–S7 表单 · n/8 · ★R recap · S8/S9 占位 · `wizard.js` |
| **本地音效 #9** | `import_local_sfx.py` · 9 条 SFX · `assets/audio_paths.json` |
| **预览图 #10** | `generate_previews.py` · **11/11** `assets/previews/` |
| **theme_paths** | shooter/survivor/life_sim 预览路径修正 |

**音效库**：`D:\AAA学习\大一上\数字音视频\素材-音效`（数字音视频课程素材）

### 2026-06-21 · Redis + Godot 试玩 + 压测

| 完成项 | 产出 |
|--------|------|
| **Redis #11** | 便携版安装于 `tools/redis/` · `session_backend: redis` |
| **10 并发 #12** | `load_test_sessions.py` → 10/10 成功 · 第 11 个 429 |
| **Godot 试玩 #4** | `POST /sessions/{id}/play/launch` · Kiosk S9「启动试玩」按钮 |

**安装位置速查**

| 组件 | 路径 |
|------|------|
| Redis | `tools/redis/server/` · 数据 `tools/redis/data/` |
| Godot | `F:\Godot\Godot_v4.6.3-stable_win64.exe\`（见 `backend/.env`） |
| 音效 | `assets/sfx/`（来源：数字音视频课程素材库） |
| Kenney 图 | `assets/kenney/` |
| 预览图 | `assets/previews/` |

**当前应做**：**L0 人工审核 #1–#11** · #5 exe 导出 · #13 tuning_mapper

### 2026-06-21 · L0 人工审核启动

| 完成项 | 产出 |
|--------|------|
| **l0_manual_audit.py** | 11 类 headless 预检 · 输出 `_audit_autocheck_latest.json` |
| **L0人工审核进度_v1.0.md** | 审核顺序 · 试玩清单 · #1 platformer R2 记录 |
| **platformer 修复** | ThemeSpriteUtil 消除 PNG import ERROR · H1 复测 PASS |

### 2026-06-21 · P0 素材八包下载 ✅

| 完成项 | 产出 |
|--------|------|
| **download_assets.py** | 新增 9 包（OGA + kenney.nl 直链）· 合计 **26 包** 全部 OK |
| **life_sim** | Food Kit · Food/Farm Expansion 像素块 · `theme_paths` 已换 |
| **fighting** | Abstract Platformer 角色 · `theme_paths` 已换 |
| **racing** | Pixel Vehicle Pack 赛车 · 保留 racing-pack 路面 |
| **音效库** | Impact Sounds 130 条 · Interface Sounds 100 条 · 本地 SFX 仍保留 |

**说明**：Kenney 官网已无独立 Farm Pack，用 **Pixel Platformer Farm Expansion** 替代 A3。

### 2026-06-21 · theme.sounds 配置 + 游戏内播放 ✅

| 完成项 | 产出 |
|--------|------|
| **wire_theme_sounds.py** | 11 品类 junction + `theme.sounds` 写入 `game_config.json` |
| **theme_sound.gd** | 各模板 `core/` · 从 theme 读 OGG 路径并播放 |
| **事件钩子** | platformer 跳/收集/撞 · fighting 拳/格挡 · shooter/shmup/survivor 射/命中 · 等 |
| **interface 键** | click · confirm · back · error · select（config 已写，HUD 待接） |

---

## 时间线

### 2026-06-13 · 立项

Git 入库 v1.1 文档 · 调研爬虫 · RAG 初建 · 技术评审 71.74 分

### 2026-06-19 · D1 启动

| 完成项 | 产出 |
|--------|------|
| 排期 | D1=6/19 · 上线=6/30 |
| 素材 | Kenney 12 包 + 字体 + 音效 · `download_assets.py` |
| 环境 | Godot MCP smoke PASS · RAG 1399 chunks |
| 后端 | FastAPI · Session≤10 · wizard API · memory 回退 |

### 2026-06-20 · D2–D3 · 批次 A + 工作流

| 完成项 | 产出 |
|--------|------|
| **platformer L0** | MCP PASS · 88/100 |
| **tower_defense L0** | MCP PASS · 86/100 |
| **shmup L0** | MCP PASS · 84/100 |
| 工作流 | `品类L0核心工程搭建工作流_v1.0.md`（已批准） |
| 配置 | `theme_paths.json` · `_examples/*.json` |

### 2026-06-20 · D4 · 批次 B

| 完成项 | 产出 |
|--------|------|
| **shooter** · **survivor** | 88 · 87 分 |
| **fighting** · **parkour** | 86 · 85 分（parkour R2 theme_sprite） |
| 评审 | `评审记录/shooter_L0.md` 等 4 份 |

### 2026-06-20 · D5 · 批次 C

| 完成项 | 产出 |
|--------|------|
| **life_sim** · **sports_race** | 87 · 87 分 |
| **pingpong** · **racing** | 97 · 87 分 |
| 里程碑 | **11/11 L0 全部 MCP PASS** |

### 2026-06-20 · 补齐轮次 + 对接

| 完成项 | 产出 |
|--------|------|
| **game_config.schema** | `templates/_schema/game_config.schema.json` |
| **td polish** | 卖塔 50% · path_validator BFS |
| **跨品类** | tuning clamp（platformer/td/survivor）· shmup 代码星空 · survivor 对象池 |
| **Kiosk 灰盒** | `kiosk/index.html` v0.1 |
| **文档** | `GameForge_K12_对接与交接_v1.0.md` · `工作状态记录_v1.0.md` |

### 2026-06-21 · D6 polish + 执行清单

| 完成项 | 产出 |
|--------|------|
| **6 类 theme/tuning** | pingpong · racing · sports_race · parkour · survivor · life_sim |
| **JumperPack** | OGA 下载 · parkour junction |
| **文档对齐** | [`D6-D10执行工作清单_v1.0.md`](./模板引擎/D6-D10执行工作清单_v1.0.md) |

---

### 2026-06-23 · R2 立项 + shmup 参考源 + 七天交工

| 完成项 | 产出 |
|--------|------|
| **R2 立项** | `秒哒对齐R2_立项说明_v1.0.md` · `miaoda_parity_r2_registry.json` |
| **platformer R2** | `templates/platformer` · registry `r2_done` |
| **shmup 完整导出** | `秒哒游戏原型/街机飞机射击/app-chu7pw7h454x/` · 本地 `npx vite` 可运行 |
| **架构梳理** | 秒哒 React+Phaser vs Godot 双轨分工 |
| **racing R2** | `templates/racing` · 90s 俯视角圈数竞速 · cars-racing 素材 · 用户审查通过 |
| **七天策略** | `6.23_七天交工工作清单_v1.0.md` · `6.23_R2对齐执行规范手册_v1.0.md` |

| 决策 | 内容 |
|------|------|
| 交付本体 | Godot + Kiosk + Windows exe |
| 秒哒角色 | 参考答案，非主程序 |
| 7 天 scope | **精选 7 款 A 深 R2 全部完成**（racing 2026-06-23 审查通过）+ 11 类流水线 |

---

## 十一品类 L0 一览

| 批次 | slug | 分 | MCP |
|------|------|-----|-----|
| D3 A | platformer | 88 | ✅ |
| D3 A | tower_defense | 86 | ✅ |
| D3 A | shmup | 84 | ✅ |
| D4 B | shooter | 88 | ✅ |
| D4 B | survivor | 87 | ✅ |
| D4 B | fighting | 86 | ✅ |
| D4 B | parkour | 85 | ✅ |
| D5 C | life_sim | 87 | ✅ |
| D5 C | sports_race | 87 | ✅ |
| D5 C | pingpong | 97 | ✅ |
| D5 C | racing | 87 | ✅ |

目录：`templates/{slug}/` · 示例：`templates/_examples/{slug}_game_config.json`

---

## 关键决策

| 日期 | 决策 |
|------|------|
| 6/19 | D10 = 11 类 L0 preset，非全 AI 定制 |
| 6/20 | 玩法子模式 S2 · 技能 S7 最多 2 个 · core 预制 |
| 6/19 | 服务器 OS / 终端形态 TBD，不阻塞 |
| 6/20 | 素材「有包」≠ 够展陈 → P0 再补 8 包 |
| 6/20 | theme 运行时加载 + 色块 fallback（禁 .tscn 嵌 PNG） |

---

| 6/23 | 七天交工三档策略 · 秒哒参考/Godot交付 · 不翻译 TS |
| 6/23 | shmup R2 完成 · 战机 Godot 复刻可玩 |
| 6/23 | 贴图无 `.import` + 文件名方括号 → 主线程卡死；统一 `Image.load` 方案 |
| 6/23 | shmup 手感：敌机减速、120° 锁定弹、Boss 血条 |
| 6/23 | **shmup 用户验收通过** · A 档第二款深 R2 定稿 |
| 6/23 | **pingpong 用户验收通过** · 经典 Pong · 倒计时/球拍判定/球场边距/阴影/人机 |
| 6/23 | **精选 7 款 A 深 R2 全部 r2_done** · 7/7 用户人工验收闭环 |
| 6/23 | **fighting 用户验收通过** · 1v1 格斗：模式/选角/MP大招/双人对战 P2 小键盘 |
| 6/23 | **parkour 用户验收通过** · 地面碰撞/滑铲/UI 文字 · canvas_items 显示 |
| 6/23 | **survivor 用户验收通过** · 3000×3000 大地图 · Boss 全图激光/半血光球 · 受击震屏 · 底部血条 |
| 6/23 | survivor 手感：WASD `>1.0` 单轴不动 · 光球 `take_orb_hit` · 相机关闭 smoothing |
| 6/23 | 经验手册：[`survivor_R2复刻经验手册_v1.0.md`](./模板引擎/survivor_R2复刻经验手册_v1.0.md) |
| 6/23 | **platformer 用户验收通过** · 深对齐秒哒坐标/地面色块 · 踩头 StompArea · Lv4+ 三色新敌人 |
| 6/23 | platformer 关卡号注入 `configure_level` · 动态 StaticBody2D 须 collision_layer=2 |
| 6/23 | 经验手册：[`platformer_R2复刻经验手册_v1.0.md`](./模板引擎/platformer_R2复刻经验手册_v1.0.md) |

| 6/24 | **6.24 B 链教育版** 需求规格评审通过 · P0 platformer **E2E-B-EDU-001 16/16** |
| 6/24 | P1 **窗1–6** 六款 creative · anchors · theater · `_edu` hooks 并行交付 |
| 6/24 | P1 **窗7 集成**：`GENRE_HOOKS` 7/7 · `validate` 7/7 · 校准表 |
| 6/24 | P1 **窗8 E2E/MCP**：`e2e_b_edu_batch.py` **6/6 PASS** · MCP shmup+racing `errors: []` |
| 6/24 | P1 进度 **8/12** · **P1-R 收工启动**：快照 · 手册 · 窗9–13 提示词 · Cursor 约束 |

---

## 下一步

→ **[`6.24_P1-R_附录A_完整窗口提示词_v1.0.md`](./模板引擎/6.24_P1-R_附录A_完整窗口提示词_v1.0.md)**（P1-R 窗9–13）  
→ **[`6.24_整合任务清单_v1.0.md`](./模板引擎/6.24_整合任务清单_v1.0.md)**  
→ **[`6.23_七天交工工作清单_v1.0.md`](./模板引擎/6.23_七天交工工作清单_v1.0.md)**（D6–D7 并行）

1. ~~D1–D5 精选 7 款 A 深 R2~~ ✅  
2. ~~6.24 P0 platformer B 链教育切片~~ ✅  
3. ~~6.24 P1 窗1–8 配置+集成+E2E~~ ✅（后端链路）  
4. **P1-R 窗9–13** [`6.24_P1-R_附录A`](./模板引擎/6.24_P1-R_附录A_完整窗口提示词_v1.0.md) 前端+联调收工  
5. D6 Kiosk 11 类联调 · D7 exe 导出 + 彩排  
6. E17 platformer 人工展厅 · ≥1 款非 platformer 试玩 ≥120s

---

## 文档索引

| 文档 | 用途 |
|------|------|
| [`6.23_七天交工工作清单_v1.0.md`](./模板引擎/6.23_七天交工工作清单_v1.0.md) | ★ D10 前按日勾选 |
| [`6.23_R2对齐执行规范手册_v1.0.md`](./模板引擎/6.23_R2对齐执行规范手册_v1.0.md) | ★ R2/B 档工序与验收 |
| [`shmup_R2复刻经验手册_v1.0.md`](./模板引擎/shmup_R2复刻经验手册_v1.0.md) | ★ 战机复刻 · 问题排查 |
| [`survivor_R2复刻经验手册_v1.0.md`](./模板引擎/survivor_R2复刻经验手册_v1.0.md) | ★ 割草肉鸽 · 大地图/Boss/受击 |
| [`platformer_R2复刻经验手册_v1.0.md`](./模板引擎/platformer_R2复刻经验手册_v1.0.md) | ★ 横版闯关 · 踩头/坐标/新敌人 |
| [`GameForge_K12_对接与交接_v1.0.md`](./GameForge_K12_对接与交接_v1.0.md) | ★ 对接 + Prompt |
| [`AI生成小游戏_会话交接手册_v1.0.md`](./AI生成小游戏_会话交接手册_v1.0.md) | 速览交接 |
| [`6.24_P1_六款并行施工手册_v1.0.md`](./模板引擎/6.24_P1_六款并行施工手册_v1.0.md) | P1 八窗并行 · 验收标准 |
| [`6.24_P1-R_总控对接与启动_v1.0.md`](./模板引擎/6.24_P1-R_总控对接与启动_v1.0.md) | ★ **新开总控窗** 首读 |
| [`6.24_P1-R_前端与联调收工手册_v1.0.md`](./模板引擎/6.24_P1-R_前端与联调收工手册_v1.0.md) | ★ P1 剩余 4 项收工 |
| [`6.24_P1-R_附录A_完整窗口提示词_v1.0.md`](./模板引擎/6.24_P1-R_附录A_完整窗口提示词_v1.0.md) | 窗9–13 复制即用 |
| [`评审记录/6.24_P1_窗8_施工自查总结.md`](./模板引擎/评审记录/6.24_P1_窗8_施工自查总结.md) | 窗8 签字与缺口 |
| [`模板引擎/工作状态记录_v1.0.md`](./模板引擎/工作状态记录_v1.0.md) | 里程碑回写 |
| [`D6-D10执行工作清单_v1.0.md`](./模板引擎/D6-D10执行工作清单_v1.0.md) | ★ 按序执行 |
| [`模板引擎/L0模板待完善清单_v1.0.md`](./模板引擎/L0模板待完善清单_v1.0.md) | 已知缺口 |

| [`秒哒竞品调研整合_v1.0.md`](../03-背景与调研/秒哒竞品调研整合_v1.0.md) | 竞品架构 · 双轨依据 |
| [`秒哒11品类创作提示词_v1.0.md`](../03-背景与调研/秒哒11品类创作提示词_v1.0.md) | 秒哒批次提示词 |

---

*v2.0 · 2026-06-24 · 6.24 P1 窗1–8 闭环 · E2E-B-EDU-BATCH 6/6*
