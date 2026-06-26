# Kenney 素材库说明

> **Kenney**（[kenney.nl](https://kenney.nl)）是荷兰独立开发者 **Kenney Vleugels** 维护的 **CC0 游戏素材** 站点。  
> **CC0** = 公共领域，可商用、可改、**无需署名**（仍建议在 about 页致谢）。

---

## 本项目为何用 Kenney

| 原因 | 说明 |
|------|------|
| 合规 | 展厅/K12 商用无版权风险 |
| 统一 | 2D 像素/卡通风格一致，11 品类可共用 UI 组件 |
| 快速 | 解压即用，配合 `theme.*.sprite_path` 换皮 |
| 规则 | 项目约束：素材仅用 `assets/kenney/` 与 `assets/` 内资源 |

Kenney **不是**游戏引擎，也 **不是** AI 工具——是 **现成的图片、音效、字体** 包（sprite sheets、UI、tileset 等）。

---

## 常用包（按品类）

| 包名 | 适用品类 |
|------|----------|
| Top-down Shooter / Space Shooter Redux | shooter, shmup |
| Platformer Pack / Jumper Pack | platformer, parkour, fighting |
| Tower Defense | tower_defense |
| Micro Roguelike / Tiny Dungeon | survivor |
| Racing Pack / Pixel Vehicle | racing, sports_race |
| Sports Pack | pingpong |
| Food Pack / Farm Pack | life_sim |

下载：[kenney.nl/assets](https://kenney.nl/assets) 或运行 **`python 05-工具脚本/download_assets.py`**（OpenGameArt 镜像）

## 本地清单（D1 已下载）

| 目录 | 适用品类 |
|------|----------|
| `platformer-pack-redux/` | platformer, parkour, fighting |
| `platformer-art-deluxe/` | platformer, parkour |
| `pixel-platformer/` | platformer, life_sim |
| `space-shooter-redux/` | shooter, shmup |
| `topdown-shooter/` | shooter, survivor |
| `tower-defense-topdown/` | tower_defense |
| `racing-pack/` | racing, sports_race |
| `sports-pack/` | pingpong, sports_race |
| `micro-roguelike/` | survivor |
| `ui-pack/` | 全品类 UI |
| `digital-audio/` · `rpg-sounds/` | 音效 |

字体：`assets/fonts/SourceHanSansCN-{Regular,Bold}.otf`

完整 manifest：`assets/manifest.json`

---

## 与 AI 生图的关系

- **Kenney** = 默认轨、快速、稳定（D10 保底）
- **AI 生图** = 可选轨，失败 **回退 Kenney**（见规格 §十四）

---

*项目内说明 · 2026-06-20*
