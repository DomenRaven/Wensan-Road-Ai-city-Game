extends Node

## B7 操作上报桥 — Godot Autoload（教育版 workspace 专用）
##
## generate/v2 集成步骤：
## 1. copytree `templates/_edu/edu_action_bridge.gd` → `workspace/{session_id}/core/`
## 2. copytree `templates/_edu/platformer_hooks.gd` → `workspace/{session_id}/core/`
## 3. 在 `workspace/{session_id}/project.godot` [autoload] 追加：
##    `EduActionBridge="*res://core/edu_action_bridge.gd"`
## 4. 在 `workspace/{session_id}/scenes/main.tscn` 添加子节点 EduHooks（挂载 platformer_hooks.gd）
##
## 写入 workspace 根目录 append-only 日志：`.edu_actions.jsonl`
## 行格式：{"action_id":"jump","t_ms":<unix_ms>}
## 上报失败仅 push_warning，不阻塞游戏。

signal action_emitted(action_id: String)

const LOG_BASENAME: String = ".edu_actions.jsonl"
const DEBOUNCE_MS: int = 500
const DEBOUNCE_MS_BY_ACTION: Dictionary = {
	"kill_enemy": 280,
	"pickup": 400,
	"hit": 600,
	"hit_npc": 480,
	"hit_trap": 480,
	"lap_complete": 1200,
	"steer": 350,
	"jump": 400,
	"slide": 450,
	"collect_coin": 350,
	"pickup_powerup": 500,
	"stomp_enemy": 480,
	"light_punch": 380,
	"heavy_punch": 420,
	"block": 450,
	"special": 900,
}

var _last_emit_ms: Dictionary = {}


func emit_action(action_id: String) -> void:
	if action_id.is_empty():
		return
	var now_ms: int = int(Time.get_unix_time_from_system() * 1000.0)
	if _is_debounced(action_id, now_ms):
		return
	_last_emit_ms[action_id] = now_ms
	action_emitted.emit(action_id)
	_append_log_line(action_id, now_ms)


func _is_debounced(action_id: String, now_ms: int) -> bool:
	if not _last_emit_ms.has(action_id):
		return false
	var prev_ms: int = int(_last_emit_ms[action_id])
	var window_ms: int = int(DEBOUNCE_MS_BY_ACTION.get(action_id, DEBOUNCE_MS))
	return now_ms - prev_ms < window_ms


func _append_log_line(action_id: String, t_ms: int) -> void:
	var log_path: String = _resolve_log_path()
	if log_path.is_empty():
		return
	var payload: Dictionary = {"action_id": action_id, "t_ms": t_ms}
	var line: String = JSON.stringify(payload) + "\n"
	var file: FileAccess = null
	if FileAccess.file_exists(log_path):
		file = FileAccess.open(log_path, FileAccess.READ_WRITE)
	else:
		file = FileAccess.open(log_path, FileAccess.WRITE)
	if file == null:
		var err_code: int = FileAccess.get_open_error()
		push_warning("EduActionBridge: cannot write %s (err %d)" % [log_path, err_code])
		return
	file.seek_end()
	file.store_string(line)
	file.close()


func _resolve_log_path() -> String:
	var project_dir: String = ProjectSettings.globalize_path("res://")
	if project_dir.is_empty():
		push_warning("EduActionBridge: project directory unavailable")
		return ""
	return project_dir.path_join(LOG_BASENAME)
