# 美术素材缺口分析 v1.1

> **日期**：2026-06-22（v1.1 回写 P0/P1 下载状态）  
> **现状**：本地 **29 包** · Kenney + 字体 + 音效 · 中央库 `assets/kenney/`  
> **结论**：P0 已全部自动化下载 ✅ · P1 部分完成 · 仍缺 BGM 音乐包

---

## 1. 十一品类覆盖矩阵

| 品类 | 已有 | 覆盖度 | 缺口说明 |
|------|------|--------|----------|
| **platformer** | platformer-pack-redux · deluxe · pixel | 🟢 足 | 可选 Jumper Pack 增障碍 ✅ |
| **parkour** | Jumper Pack + platformer | 🟢 足 | 2026-06-21 已 junction |
| **fighting** | abstract-platformer | 🟢 足 | 2026-06-21 已换 theme_paths |
| **shooter** | topdown-shooter · space-shooter | 🟢 足 | particle-pack ✅ |
| **shmup** | space-shooter-redux | 🟢 足 | 1-bit-pack 可补充 UI |
| **survivor** | topdown · micro-roguelike · **tiny-dungeon · roguelike-caves · 1-bit** | 🟢 足 | 2026-06-22 P1 已下 |
| **tower_defense** | td-topdown · td-kit-3d | 🟢 足 | — |
| **racing** | racing-pack · pixel-vehicle-pack | 🟢 足 | 2026-06-21 已换 |
| **sports_race** | sports-pack · racing | 🟢 足 | — |
| **pingpong** | sports-pack 球拍/球 | 🟢 足 | 2026-06-21 D6 polish |
| **life_sim** | food-kit · farm/food expansion | 🟢 足 | 2026-06-21 P0 已下 |

**全品类共用**

| 类型 | 状态 | 路径 |
|------|------|------|
| UI 按钮/进度条 | ✅ | `kenney/ui-pack` |
| 中文 UI 字体 | ✅ | `assets/fonts/` |
| Impact/Interface 音效 | ✅ | `kenney/impact-sounds` · `interface-sounds` · junction 11 类 |
| 粒子/VFX | ✅ | `kenney/particle-pack` |
| Input Prompts | ✅ | `kenney/input-prompts` |
| **BGM 音乐循环** | ❌ | Music Jingles / Digital Music — 待 itch 或 kenney.nl |
| Kenney Emotes | ❌ | 可选 |

---

## 2. 下载状态（2026-06-22）

### P0 · 已全部完成 ✅

| 包 | 路径 | 日期 |
|----|------|------|
| Food Kit · Food/Farm Expansion | `kenney/food-kit` 等 | 2026-06-21 |
| Jumper Pack | `kenney/jumper-pack` | 2026-06-21 |
| Pixel Vehicle Pack | `kenney/pixel-vehicle-pack` | 2026-06-21 |
| Particle · Impact · Interface | 对应目录 | 2026-06-21 |
| Abstract Platformer | `kenney/abstract-platformer` | 2026-06-21 |

### P1 · 部分完成

| # | 包名 | 状态 | 路径 |
|---|------|------|------|
| B1 | Music Jingles / Digital Music | ❌ 未下 | — |
| B2 | Roguelike Cave pack | ✅ | `kenney/roguelike-caves` |
| B3 | Tiny Dungeon | ✅ | `kenney/tiny-dungeon` |
| B4 | Abstract Platformer | ✅（P0） | — |
| B5 | Input Prompts | ✅（P0） | — |
| B6 | 1-Bit Pack | ✅ | `kenney/1-bit-pack`（OGA 1.1） |
| B7 | Ninja Adventure | ❌ | 待加 |

---

## 3. 存储路径与命令

**中央库**（所有模板共享）：

```
assets/kenney/{pack}/extracted/   ← 解压后 sprite/sheet
assets/manifest.json              ← 29 包清单
assets/fonts/                     ← 思源黑体等
```

**模板 junction**（音效，由脚本维护）：

```
templates/{slug}/assets/kenney/impact-sounds   → 中央库 impact-sounds/extracted
templates/{slug}/assets/kenney/interface-sounds → 中央库 interface-sounds/extracted
```

**自动化下载**：

```powershell
python 05-工具脚本/download_assets.py      # 29/29 OK
python 05-工具脚本/wire_theme_sounds.py    # 11 类 junction + game_config theme.sounds
```

**itch.io 免费包（需浏览器）** — 见 `assets/third_party/README.md` · 主要为 BGM

---

## 4. 与 D10 的关系

| 档位 | 素材要求 | 当前 |
|------|----------|------|
| **L0 preset** | 每类至少 1 角色 + 背景 + UI | ✅ 11/11 够用 |
| **L1 AI 换皮** | theme.style_pack 路径表 | 🔲 R3 |
| **向导预览** | 各品类缩略图 | ✅ `assets/previews/` 11/11 |

---

*v1.1 · 2026-06-22 · P0 全完成 · P1 +3 · 仍缺 BGM*
