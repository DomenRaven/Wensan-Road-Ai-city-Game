extends Node

## B7 racing 操作钩子（workspace 专用，不改 templates/racing/core 原件）
##
## 自动上报 action_id（与 config/code_anchors/racing.json 对齐）：
## - hit_npc：撞上 NPC 车辆（HitArea ↔ npc_car）
## - hit_trap：撞上路障（HitArea ↔ road_obstacle）
## - lap_complete：跑完一圈（HUD 圈数增加）
## - steer：左右转向（首次按下，车速 > 阈值）· B7 最低优先级展示

const ACTION_HIT_NPC: String = "hit_npc"
const ACTION_HIT_TRAP: String = "hit_trap"
const ACTION_LAP_COMPLETE: String = "lap_complete"
const ACTION_STEER: String = "steer"

const GAME_RESCAN_SEC: float = 0.45
const MIN_SPEED_FOR_STEER: float = 20.0

var _player: Node2D = null
var _hit_area: Area2D = null
var _wired_hit_area_id: int = 0
var _prev_lap_count: int = 0
var _lap_label: Label = null
var _game_root: Node2D = null
var _rescan_timer: SceneTreeTimer = null
var _pending_rescan_count: int = 0
var _steer_left_was_pressed: bool = false
var _steer_right_was_pressed: bool = false


func _ready() -> void:
	var main: Node = get_parent()
	if main == null:
		return
	_lap_label = main.get_node_or_null(
		"GameHost/GameViewport/CanvasLayer/HUD/LapPanel/VBox/LapValue"
	) as Label
	_game_root = main.get_node_or_null("GameHost/GameViewport/GameRoot") as Node2D
	if _game_root != null:
		if not _game_root.is_connected("child_entered_tree", _on_game_child_entered):
			_game_root.child_entered_tree.connect(_on_game_child_entered)
		for child: Node in _game_root.get_children():
			_on_game_child_entered(child)
	call_deferred("_scan_scene")


func _on_game_child_entered(_child: Node) -> void:
	_pending_rescan_count = 3
	_schedule_game_rescan()


func _schedule_game_rescan() -> void:
	if _rescan_timer != null and _rescan_timer.time_left > 0.0:
		return
	_rescan_timer = get_tree().create_timer(GAME_RESCAN_SEC)
	_rescan_timer.timeout.connect(_on_rescan_timer)


func _on_rescan_timer() -> void:
	_scan_scene()
	if _pending_rescan_count > 0:
		_pending_rescan_count -= 1
		_rescan_timer = null
		_schedule_game_rescan()


func _scan_scene() -> void:
	_rescan_timer = null
	_wire_player()
	_reset_lap_tracking()


func _wire_player() -> void:
	var players: Array[Node] = get_tree().get_nodes_in_group("player")
	if players.is_empty():
		_player = null
		_hit_area = null
		_wired_hit_area_id = 0
		return
	var candidate: Node = players[0]
	if not candidate is Node2D:
		_player = null
		_hit_area = null
		_wired_hit_area_id = 0
		return
	if _player != candidate:
		_player = candidate as Node2D
		_hit_area = null
		_wired_hit_area_id = 0
	_wire_hit_area()


func _wire_hit_area() -> void:
	if _player == null or not is_instance_valid(_player):
		return
	var candidate: Node = _player.get_node_or_null("HitArea")
	if candidate == null or not candidate is Area2D:
		return
	var area: Area2D = candidate as Area2D
	var area_id: int = area.get_instance_id()
	if _wired_hit_area_id == area_id:
		return
	_hit_area = area
	_wired_hit_area_id = area_id
	var callable := Callable(self, "_on_hit_area_entered")
	if not _hit_area.is_connected("area_entered", callable):
		_hit_area.area_entered.connect(callable)


func _reset_lap_tracking() -> void:
	_prev_lap_count = _read_lap_count()
	_steer_left_was_pressed = false
	_steer_right_was_pressed = false


func _process(_delta: float) -> void:
	if _player == null or not is_instance_valid(_player):
		_wire_player()
	_detect_steer()
	_detect_lap_complete()


func _detect_steer() -> void:
	if _player == null or not is_instance_valid(_player):
		return
	var speed: float = _read_forward_speed()
	if speed < MIN_SPEED_FOR_STEER:
		_steer_left_was_pressed = Input.is_action_pressed("steer_left")
		_steer_right_was_pressed = Input.is_action_pressed("steer_right")
		return
	var left_pressed: bool = Input.is_action_pressed("steer_left")
	var right_pressed: bool = Input.is_action_pressed("steer_right")
	if left_pressed and not _steer_left_was_pressed:
		_emit_action(ACTION_STEER)
	elif right_pressed and not _steer_right_was_pressed:
		_emit_action(ACTION_STEER)
	_steer_left_was_pressed = left_pressed
	_steer_right_was_pressed = right_pressed


func _read_forward_speed() -> float:
	if _player == null or not is_instance_valid(_player):
		return 0.0
	if _player.has_method("get_forward_speed"):
		return float(_player.call("get_forward_speed"))
	return 0.0


func _on_hit_area_entered(area: Area2D) -> void:
	if area == null or not is_instance_valid(area):
		return
	if area.is_in_group("npc_car"):
		_emit_action(ACTION_HIT_NPC)
	elif area.is_in_group("road_obstacle"):
		_emit_action(ACTION_HIT_TRAP)


func _detect_lap_complete() -> void:
	var laps: int = _read_lap_count()
	if laps > _prev_lap_count and _prev_lap_count >= 0:
		_emit_action(ACTION_LAP_COMPLETE)
	_prev_lap_count = laps


func _read_lap_count() -> int:
	if _lap_label != null and is_instance_valid(_lap_label):
		return int(_lap_label.text.to_int())
	return 0


func _emit_action(action_id: String) -> void:
	var bridge: Node = get_node_or_null("/root/EduActionBridge")
	if bridge == null:
		push_warning("RacingEduHooks: EduActionBridge missing · action=%s" % action_id)
		return
	if not bridge.has_method("emit_action"):
		return
	bridge.call("emit_action", action_id)
