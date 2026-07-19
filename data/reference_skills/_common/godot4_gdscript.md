# Reference · Godot 4 / GDScript（社区通识 × 本产品）

## 推荐写法

- 全部函数与关键变量**强类型**（产品硬约束）  
- 节点名 PascalCase；文件 snake_case  
- `@onready` 取子节点；生命周期在入树后访问节点  
- 改外观优先改 Sprite / `modulate`；玩家根保持可见与 `group=player`；闪烁只改 Sprite 并恢复  
- 改视觉 scale；碰撞体保持原大小以稳住判定  

## 产品安全边界（会话 GDScript）

- 可写范围：会话 workspace；桥 API 以契约列表为准  
- 同等效果用会话 GDScript 实现（不调用契约外钩子）  
- 面向单机触屏试玩（无联机 / 存档 / 内购 / 广告）  

## 本产品优先

- 用现有 `AiSandboxBridge` 与品类 hooks  
- 在会话内最小 targeted 编辑；templates 只读参考  
