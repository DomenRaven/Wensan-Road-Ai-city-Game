extends Node

## B7 parkour 操作钩子（workspace 专用，不改 templates/parkour/core 原件）
##
## 自动上报 action_id（与 config/code_anchors/parkour.json 对齐）：
## - jump：玩家起跳（Input 边沿，与 player_runner 一致）
## - slide：玩家开始滑铲（蹲下过矮障 · Input 边沿 + 状态备用）
## - collect_coin：拾取金币
## - pickup_powerup：拾取无敌 / 双倍金币道具

const ACTION_JUMP: String = "jump"
const ACTION_SLIDE: String = "slide"
const ACTION_COIN: String = "collect_coin"
const ACTION_PICKUP: String = "pickup_powerup"

const COLLECTIBLE_KIND_COIN: int = 0

const GAME_RESCAN_SEC: float = 0.45

var _player: CharacterBody2D = null
var _was_sliding: bool = false
var _wired_spawner_id: int = 0
var _game_root: Node2D = null
var _rescan_timer: SceneTreeTimer = null
var _pending_rescan_count: int = 0


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
	_wire_collectible_spawner()


func _wire_player() -> void:
	var players: Array[Node] = get_tree().get_nodes_in_group("player")
	if players.is_empty():
		_player = null
		_was_sliding = false
		return
	var candidate: Node = players[0]
	if candidate is CharacterBody2D:
		if _player != candidate:
			_player = candidate as CharacterBody2D
			_was_sliding = _read_sliding()
	else:
		_player = null
		_was_sliding = false


func _wire_collectible_spawner() -> void:
	var spawner: Node = _find_collectible_spawner()
	if spawner == null:
		_wired_spawner_id = 0
		return
	var spawner_id: int = spawner.get_instance_id()
	if _wired_spawner_id == spawner_id:
		return
	_wired_spawner_id = spawner_id
	if not spawner.has_signal("collectible_collected"):
		return
	var callable := Callable(self, "_on_collectible_collected")
	if not spawner.is_connected("collectible_collected", callable):
		spawner.connect("collectible_collected", callable)


func _find_collectible_spawner() -> Node:
	if _game_root == null:
		return null
	for child: Node in _game_root.get_children():
		var spawner: Node = child.get_node_or_null("CollectibleSpawner")
		if spawner != null:
			return spawner
	return get_tree().root.find_child("CollectibleSpawner", true, false)


func _physics_process(_delta: float) -> void:
	if _player == null or not is_instance_valid(_player):
		_wire_player()
	_detect_jump()
	_detect_slide()


func _detect_jump() -> void:
	if _player == null or not is_instance_valid(_player):
		return
	if not _is_player_active():
		return
	if Input.is_action_just_pressed("jump"):
		_emit_action(ACTION_JUMP)


func _detect_slide() -> void:
	if _player == null or not is_instance_valid(_player):
		return
	if not _is_player_active():
		return
	var sliding: bool = _read_sliding()
	if Input.is_action_just_pressed("skill") and _player.is_on_floor() and not _was_sliding:
		_emit_action(ACTION_SLIDE)
	elif sliding and not _was_sliding:
		_emit_action(ACTION_SLIDE)
	_was_sliding = sliding


func _is_player_active() -> bool:
	if _player == null:
		return false
	if _player.has_method("is_playing"):
		return bool(_player.call("is_playing"))
	return true


func _read_sliding() -> bool:
	if _player == null or not _player.has_method("is_sliding"):
		return false
	return bool(_player.call("is_sliding"))


func _on_collectible_collected(kind: int) -> void:
	if kind == COLLECTIBLE_KIND_COIN:
		_emit_action(ACTION_COIN)
	else:
		_emit_action(ACTION_PICKUP)


func _emit_action(action_id: String) -> void:
	var bridge: Node = get_node_or_null("/root/EduActionBridge")
	if bridge == null:
		push_warning("ParkourEduHooks: EduActionBridge missing · action=%s" % action_id)
		return
	if not bridge.has_method("emit_action"):
		return
	bridge.call("emit_action", action_id)
