# GameForge K12 · 本地工具安装目录
#
# | 组件   | 安装位置                          | 启动脚本 |
# |--------|-----------------------------------|----------|
# | Redis  | tools/redis/                      | 05-工具脚本/run_redis.ps1 |
# | Godot  | F:\Godot\... (系统级，见 .env)    | MCP / backend 试玩 API |
# | 素材   | assets/                           | 05-工具脚本/import_local_sfx.py |
# | 工作区 | workspace/{session_id}/ (运行时)  | L1 换皮后试玩 |

# 首次安装 Redis（便携版，约 12MB）：
#   .\05-工具脚本\install_redis.ps1

# 启动顺序（展厅联调）：
#   1. .\05-工具脚本\run_redis.ps1
#   2. .\05-工具脚本\run_backend.ps1
#   3. python -m http.server 8080  → http://127.0.0.1:8080/kiosk/
