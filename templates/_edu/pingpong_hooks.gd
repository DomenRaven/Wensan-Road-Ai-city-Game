extends Node

## B7 pingpong 操作钩子（workspace 专用，不改 templates/pingpong/core 原件）
##
## generate/v2 集成（与 edu_action_bridge.gd 头注释一致）：
## 1. copy `templates/_edu/` 下桥与钩子到 `workspace/{session_id}/core/`
## 2. 注册 EduActionBridge Autoload
## 3. 在 `scenes/main.tscn` 添加子节点：
##    `[node name="EduHooks" type="Node" parent="."]` + `pingpong_hooks.gd`
##
## 自动上报 action_id（与 config/code_anchors/pingpong.json 对齐）：
## - rally：拍子击中球（球水平速度反向）
## - score：一方得分（ball.scored 信号）
## - power_smash：大力扣杀技能激活

const PowerSmashSkill := preload("res://core/skills/power_smash.gd")

const ACTION_RALLY: String = "rally"
const ACTION_SCORE: String = "score"
const ACTION_POWER_SMASH: String = "power_smash"

const MIN_VELOCITY_X: float = 8.0

var _ball: Area2D = null
var _ball_wired: bool = false
var _prev_vel_x_sign: int = 0
var _prev_power_smash_armed: bool = false
var _game_root: Node2D = null
var _manager: Node = null
var _prev_playing: bool = false
var _run_complete_sent: bool = false
var _run_session_start_ms: int = 0
var _pending_run_stats: Dictionary = {}
var _match_finished_pending: bool = false


func _ready() -> void:
	_mute_exhibition_audio()
	var main: Node = get_parent()
	if main == null:
		return
	_manager = main
	_game_root = main.get_node_or_null("GameRoot") as Node2D
	if _game_root != null:
		_game_root.child_entered_tree.connect(_on_game_root_child_entered)
	call_deferred("_scan_scene")


func _mute_exhibition_audio() -> void:
	var master_idx: int = AudioServer.get_bus_index("Master")
	if master_idx < 0:
		return
	AudioServer.set_bus_mute(master_idx, true)


func _on_game_root_child_entered(_child: Node) -> void:
	call_deferred("_scan_scene")


func _scan_scene() -> void:
	_wire_ball()
	_prev_vel_x_sign = 0
	_prev_power_smash_armed = false


func _wire_ball() -> void:
	_ball_wired = false
	_ball = null
	if _game_root == null:
		return
	var game: Node = _game_root.get_node_or_null("Game")
	if game == null:
		return
	var candidate: Node = game.get_node_or_null("Ball")
	if candidate == null or not candidate is Area2D:
		return
	_ball = candidate as Area2D
	if _ball.has_signal("scored") and not _ball.is_connected("scored", _on_ball_scored):
		_ball.scored.connect(_on_ball_scored)
	_ball_wired = true


func _physics_process(_delta: float) -> void:
	_watch_run_complete()
	if not _ball_wired or _ball == null or not is_instance_valid(_ball):
		return
	_detect_rally()
	_detect_power_smash()


func _detect_rally() -> void:
	if not _ball.has_method("get_velocity"):
		return
	var vel: Vector2 = _ball.call("get_velocity") as Vector2
	if absf(vel.x) < MIN_VELOCITY_X:
		return
	var sign: int = 1 if vel.x > 0.0 else -1
	if _prev_vel_x_sign != 0 and sign != _prev_vel_x_sign:
		_emit_action(ACTION_RALLY)
	_prev_vel_x_sign = sign


func _detect_power_smash() -> void:
	if not PowerSmashSkill.is_enabled():
		return
	var armed: bool = bool(PowerSmashSkill._armed)
	if armed and not _prev_power_smash_armed:
		_emit_action(ACTION_POWER_SMASH)
	_prev_power_smash_armed = armed


func _on_ball_scored(_side: String) -> void:
	_emit_action(ACTION_SCORE)
	_prev_vel_x_sign = 0


func _emit_action(action_id: String) -> void:
	var bridge: Node = get_node_or_null("/root/EduActionBridge")
	if bridge == null:
		return
	if not bridge.has_method("emit_action"):
		return
	bridge.call("emit_action", action_id)


func _is_playing() -> bool:
	if _manager != null and _manager.has_method("is_playing"):
		return bool(_manager.call("is_playing"))
	return false


func _is_run_end_screen() -> bool:
	if _manager == null:
		return false
	var game_over: Node = _manager.get_node_or_null("CanvasLayer/GameOverScreen")
	return game_over != null and game_over.visible


func _is_start_screen() -> bool:
	if _manager == null:
		return false
	var start_screen: Node = _manager.get_node_or_null("CanvasLayer/StartScreen")
	return start_screen != null and start_screen.visible


func _read_player_score() -> int:
	if _manager == null:
		return 0
	if _is_run_end_screen():
		var final_label: Node = _manager.get_node_or_null("CanvasLayer/GameOverScreen/Panel/FinalScore")
		if final_label is Label:
			var parts: PackedStringArray = (final_label as Label).text.split("-")
			if not parts.is_empty():
				return int(parts[0].strip_edges())
	var label: Node = _manager.get_node_or_null("CanvasLayer/HUD/PlayerScore")
	if label is Label:
		return int((label as Label).text.to_int())
	return 0


func _build_run_stats(session_end: String) -> Dictionary:
	var elapsed_ms: int = 0
	if _run_session_start_ms > 0:
		elapsed_ms = maxi(0, Time.get_ticks_msec() - _run_session_start_ms)
	return {
		"score": _read_player_score(),
		"elapsed_ms": elapsed_ms,
		"metric": "score",
		"session_end": session_end,
	}


func _capture_finished_match() -> void:
	_pending_run_stats = _build_run_stats("game_over")
	_match_finished_pending = true


func _reset_run_session() -> void:
	_run_session_start_ms = Time.get_ticks_msec()
	_pending_run_stats = {}
	_match_finished_pending = false
	_run_complete_sent = false


func _try_flush_run_complete(session_end: String) -> void:
	if _run_complete_sent:
		return
	if _pending_run_stats.is_empty():
		if not _match_finished_pending and not _is_run_end_screen():
			return
		_pending_run_stats = _build_run_stats(session_end)
	if _pending_run_stats.is_empty():
		return
	var payload: Dictionary = _pending_run_stats.duplicate(true)
	payload["session_end"] = session_end
	_emit_run_complete(payload)
	_run_complete_sent = true
	_match_finished_pending = false
	_pending_run_stats = {}


func _watch_run_complete() -> void:
	var playing: bool = _is_playing()

	if playing and not _prev_playing:
		if _run_session_start_ms <= 0 or _is_run_end_screen():
			_reset_run_session()
		elif _match_finished_pending:
			_reset_run_session()

	if _prev_playing and not playing and _is_run_end_screen() and not _match_finished_pending:
		_capture_finished_match()

	if not playing and _is_start_screen() and _match_finished_pending:
		_try_flush_run_complete("menu_exit")

	_prev_playing = playing


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST:
		_try_flush_run_complete("window_close")


func _exit_tree() -> void:
	_try_flush_run_complete("window_close")


func _emit_run_complete(payload: Dictionary) -> void:
	var bridge: Node = get_node_or_null("/root/EduActionBridge")
	if bridge == null:
		return
	if bridge.has_method("emit_run_complete"):
		bridge.call("emit_run_complete", payload)
