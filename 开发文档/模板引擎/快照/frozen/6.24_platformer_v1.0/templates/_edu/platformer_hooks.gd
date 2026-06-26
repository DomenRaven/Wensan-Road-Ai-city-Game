extends Node

## B7 platformer 操作钩子（workspace 专用，不改 templates/platformer/core 原件）
##
## 自动上报 action_id（与 config/code_anchors/platformer.json 对齐）：
## - jump：玩家起跳（Input 边沿）
## - stomp_enemy：踩死敌人（敌人状态边沿 · 仅当前关卡）
## - collect_coin：拾取金币（collectible.collected · 仅当前关卡）

const ACTION_JUMP: String = "jump"
const ACTION_STOMP: String = "stomp_enemy"
const ACTION_COIN: String = "collect_coin"

const LEVEL_RESCAN_SEC: float = 0.45

var _player: CharacterBody2D = null
var _enemy_alive: Dictionary = {}
var _wired_collectibles: Dictionary = {}
var _level_root: Node2D = null
var _rescan_timer: SceneTreeTimer = null
var _pending_rescan_count: int = 0


func _ready() -> void:
	var main: Node = get_parent()
	if main == null:
		return
	_level_root = main.get_node_or_null("LevelRoot") as Node2D
	if _level_root != null:
		if not _level_root.is_connected("child_entered_tree", _on_level_child_entered):
			_level_root.child_entered_tree.connect(_on_level_child_entered)
		for child: Node in _level_root.get_children():
			_on_level_child_entered(child)
	call_deferred("_scan_level")


func _on_level_child_entered(_child: Node) -> void:
	_wired_collectibles.clear()
	_pending_rescan_count = 4
	_schedule_level_rescan()


func _schedule_level_rescan() -> void:
	if _rescan_timer != null and _rescan_timer.time_left > 0.0:
		return
	_rescan_timer = get_tree().create_timer(LEVEL_RESCAN_SEC)
	_rescan_timer.timeout.connect(_on_rescan_timer)


func _on_rescan_timer() -> void:
	_scan_level()
	if _pending_rescan_count > 0:
		_pending_rescan_count -= 1
		_rescan_timer = null
		_schedule_level_rescan()


func _scan_level() -> void:
	_rescan_timer = null
	_wire_player()
	_wire_collectibles()
	_reset_enemy_tracking()


func _get_active_level() -> Node2D:
	if _level_root == null:
		return null
	var active: Node2D = null
	for child: Node in _level_root.get_children():
		if not child is Node2D:
			continue
		if not is_instance_valid(child) or child.is_queued_for_deletion():
			continue
		active = child as Node2D
	return active


func _wire_player() -> void:
	var best: CharacterBody2D = null
	for node: Node in get_tree().get_nodes_in_group("player"):
		if not is_instance_valid(node) or node.is_queued_for_deletion():
			continue
		if not node is CharacterBody2D:
			continue
		var body: CharacterBody2D = node as CharacterBody2D
		var level: Node2D = _get_active_level()
		if level != null and not level.is_ancestor_of(body):
			continue
		best = body
	if best != _player:
		_player = best


func _wire_collectibles() -> void:
	for node: Node in _find_collectible_nodes():
		if not is_instance_valid(node) or node.is_queued_for_deletion():
			continue
		var id: int = node.get_instance_id()
		if _wired_collectibles.has(id):
			continue
		if not node.has_signal("collected"):
			continue
		var callable := Callable(self, "_on_collectible_collected")
		if not node.is_connected("collected", callable):
			node.connect("collected", callable)
		_wired_collectibles[id] = true


func _find_collectible_nodes() -> Array[Node]:
	var found: Array[Node] = []
	var level: Node2D = _get_active_level()
	if level != null:
		var root: Node = level.get_node_or_null("Collectibles")
		if root != null:
			for child: Node in root.get_children():
				found.append(child)
			return found
	for node: Node in get_tree().get_nodes_in_group("collectible"):
		if is_instance_valid(node) and not node.is_queued_for_deletion():
			found.append(node)
	return found


func _reset_enemy_tracking() -> void:
	_enemy_alive.clear()
	var level: Node2D = _get_active_level()
	for node: Node in get_tree().get_nodes_in_group("enemy"):
		if not is_instance_valid(node) or node.is_queued_for_deletion():
			continue
		if level != null and not level.is_ancestor_of(node):
			continue
		if not node is CharacterBody2D:
			continue
		var enemy: CharacterBody2D = node as CharacterBody2D
		_enemy_alive[enemy.get_instance_id()] = _is_enemy_stompable(enemy)


func _physics_process(_delta: float) -> void:
	if _player == null or not is_instance_valid(_player) or _player.is_queued_for_deletion():
		_wire_player()
	_detect_jump()
	_track_enemy_stomps()


func _detect_jump() -> void:
	if _player == null or not is_instance_valid(_player):
		return
	if Input.is_action_just_pressed("jump"):
		_emit_action(ACTION_JUMP)


func _track_enemy_stomps() -> void:
	if _player == null or not is_instance_valid(_player):
		return
	var level: Node2D = _get_active_level()
	for node: Node in get_tree().get_nodes_in_group("enemy"):
		if not is_instance_valid(node) or node.is_queued_for_deletion():
			continue
		if level != null and not level.is_ancestor_of(node):
			continue
		if not node is CharacterBody2D:
			continue
		var enemy: CharacterBody2D = node as CharacterBody2D
		var id: int = enemy.get_instance_id()
		var alive: bool = _is_enemy_stompable(enemy)
		if _enemy_alive.has(id) and bool(_enemy_alive[id]) and not alive:
			_emit_action(ACTION_STOMP)
		_enemy_alive[id] = alive


func _is_enemy_stompable(enemy: CharacterBody2D) -> bool:
	if enemy.has_method("is_stompable"):
		return bool(enemy.call("is_stompable"))
	return enemy.is_inside_tree()


func _on_collectible_collected() -> void:
	_emit_action(ACTION_COIN)


func _emit_action(action_id: String) -> void:
	var bridge: Node = get_node_or_null("/root/EduActionBridge")
	if bridge == null:
		push_warning("PlatformerEduHooks: EduActionBridge missing · action=%s" % action_id)
		return
	if not bridge.has_method("emit_action"):
		return
	bridge.call("emit_action", action_id)
