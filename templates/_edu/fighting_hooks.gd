extends Node

## B7 fighting 操作钩子（workspace 专用，不改 templates/fighting/core 原件）
##
## 自动上报 action_id（与 config/code_anchors/fighting.json 对齐）：
## - light_punch：轻拳（ATTACK1 / p1_light）
## - heavy_punch：重拳（ATTACK2 / p1_heavy）
## - block：格挡（BLOCK / p1_block）
## - special：大招（ULTIMATE / p1_ultimate）

const ACTION_LIGHT_PUNCH: String = "light_punch"
const ACTION_HEAVY_PUNCH: String = "heavy_punch"
const ACTION_BLOCK: String = "block"
const ACTION_SPECIAL: String = "special"

const STATE_ATTACK1: int = 3
const STATE_ATTACK2: int = 4
const STATE_ULTIMATE: int = 5
const STATE_BLOCK: int = 6

const GAME_RESCAN_SEC: float = 0.45

var _player: CharacterBody2D = null
var _prev_state: int = -1
var _game_root: Node2D = null
var _rescan_timer: SceneTreeTimer = null
var _pending_rescan_count: int = 0
var _block_was_held: bool = false


func _ready() -> void:
	var main: Node = get_parent()
	if main == null:
		return
	_game_root = main.get_node_or_null("GameRoot") as Node2D
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


func _wire_player() -> void:
	var best: CharacterBody2D = null
	for node: Node in get_tree().get_nodes_in_group("player"):
		if not is_instance_valid(node) or node.is_queued_for_deletion():
			continue
		if not node is CharacterBody2D:
			continue
		var fighter: CharacterBody2D = node as CharacterBody2D
		if fighter.get("is_player_one") != true:
			continue
		best = fighter
	if best != _player:
		_player = best
		_prev_state = _read_action_state()
		_block_was_held = Input.is_action_pressed("p1_block")


func _physics_process(_delta: float) -> void:
	if _player == null or not is_instance_valid(_player) or _player.is_queued_for_deletion():
		_wire_player()
	_detect_input_edges()
	_detect_state_edges()


func _detect_input_edges() -> void:
	if _player == null or not is_instance_valid(_player):
		return
	if Input.is_action_just_pressed("p1_light"):
		_emit_action(ACTION_LIGHT_PUNCH)
	if Input.is_action_just_pressed("p1_heavy"):
		_emit_action(ACTION_HEAVY_PUNCH)
	if Input.is_action_just_pressed("p1_ultimate"):
		_emit_action(ACTION_SPECIAL)
	var block_held: bool = Input.is_action_pressed("p1_block")
	if block_held and not _block_was_held:
		_emit_action(ACTION_BLOCK)
	_block_was_held = block_held


func _detect_state_edges() -> void:
	if _player == null or not is_instance_valid(_player):
		return
	var state: int = _read_action_state()
	if state != _prev_state:
		match state:
			STATE_ATTACK1:
				_emit_action(ACTION_LIGHT_PUNCH)
			STATE_ATTACK2:
				_emit_action(ACTION_HEAVY_PUNCH)
			STATE_BLOCK:
				_emit_action(ACTION_BLOCK)
			STATE_ULTIMATE:
				_emit_action(ACTION_SPECIAL)
	_prev_state = state


func _read_action_state() -> int:
	if _player == null or not _player.has_method("get_action_state"):
		return -1
	return int(_player.call("get_action_state"))


func _emit_action(action_id: String) -> void:
	var bridge: Node = get_node_or_null("/root/EduActionBridge")
	if bridge == null:
		push_warning("FightingEduHooks: EduActionBridge missing · action=%s" % action_id)
		return
	if not bridge.has_method("emit_action"):
		return
	bridge.call("emit_action", action_id)
