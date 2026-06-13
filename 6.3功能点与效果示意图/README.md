# 功能点与效果示意图 · 说明

> 本目录：**汇报用示意图**（规划对齐 `1未来隧道部分/6.3功能点与效果示意图`）  
> 当前 v1.0 以 **Markdown + Mermaid** 交付于 `开发文档/架构/`；交互 JSX 在 Wave 2 建 frontend 后挂载。

---

## 一、当前可查看的图

| 图 | 路径 | 说明 |
|----|------|------|
| **软硬件架构图** | `开发文档/架构/系统架构说明_v1.0.md` §1 | 四层：交互→编排→制作→演示 |
| **架构 mermaid 源** | `开发文档/架构/静态图/system-architecture.mmd` | 可导出 SVG |
| **业务流程图** | `开发文档/架构/系统业务流程说明_v1.0.md` §1 | 六态状态机 |
| **业务 mermaid 源** | `开发文档/架构/静态图/business-flow.mmd` | 可导出 SVG |
| **空间布局** | `开发文档/AI生成小游戏_功能点明细与开发计划_v1.0.md` §1.2 | ASCII 平面 3.0×2.5m |

---

## 二、规划中的交互版（Wave 2+）

| 文件（待建） | 路由 | 说明 |
|--------------|------|------|
| `01_空间布局设计图.jsx` | `/diagrams/layout` | 体验岛 + 设备点位 |
| `02_体验流程动态Demo.jsx` | `/diagrams/experience` | 五步观众动画 |
| `03_软硬件架构图.jsx` | `/diagrams/arch` | 可点击节点 |
| `04_业务流程图.jsx` | `/diagrams/business` | 泳道 + 六态筛选 |

---

## 三、汇报演示顺序

1. `/diagrams/business` 或 业务流程 mermaid — 讲清 10 分钟闭环  
2. `/diagrams/arch` 或 架构 mermaid — 讲清 Cursor+Godot 分工  
3. 功能点明细 §1.2 — 体验岛平面  
4. Live：godot-mcp `get_godot_version` + 模板试玩（可选）

---

*6.3 功能点与效果示意图 · AI 小游戏创作工坊 v1.0*
