extends Node

## B7 survivor 操作钩子（workspace 专用，不改 templates/survivor/core 原件）
##
## 自动上报 action_id（与 config/code_anchors/survivor.json 对齐）：
## - move：玩家 WASD/方向键移动（首次输入）
## - kill_enemy：怪物被击败（horde_enemy.destroyed）
## - pickup_xp：拾取经验宝石（xp_gem.collected）
## - level_up：升级选项 UI 出现（LevelUpUI 变为可见）

const ACTION_MOVE: String = "move"
const ACTION_KILL_ENEMY: String = "kill_enemy"
const ACTION_PICKUP_XP: String = "pickup_xp"
const ACTION_LEVEL_UP: String = "level_up"

const MOVE_INPUT_THRESHOLD: float = 0.05

var _game_root: Node2D = null
var _gems_root: Node2D = null
var _level_up_ui: CanvasLayer = null
var _player: Area2D = null
var _wired_gems: Dictionary = {}
var _wired_enemies: Dictionary = {}
var _ui_was_visible: bool = false


func _ready() -> void:
	var main: Node = get_parent()
	if main != null:
		_game_root = main.get_node_or_null("GameRoot") as Node2D
		if _game_root != null:
			if not _game_root.is_connected("child_entered_tree", _on_game_root_child):
				_game_root.child_entered_tree.connect(_on_game_root_child)
	call_deferred("_scan_arena")


func _on_game_root_child(_child: Node) -> void:
	call_deferred("_scan_arena")


func _physics_process(_delta: float) -> void:
	if _gems_root == null or not is_instance_valid(_gems_root):
		_scan_arena()
	_detect_player_move()


func _scan_arena() -> void:
	_wire_gems_root()
	_wire_level_up_ui()
	_wire_player()
	_wire_enemies()


func _wire_gems_root() -> void:
	var candidate: Node = get_tree().root.find_child("XpGems", true, false)
	if candidate == null:
		return
	if _gems_root != candidate:
		_gems_root = candidate as Node2D
		_wired_gems.clear()
		if not _gems_root.is_connected("child_entered_tree", _on_gems_child_entered):
			_gems_root.child_entered_tree.connect(_on_gems_child_entered)
	for child: Node in _gems_root.get_children():
		_wire_gem(child)


func _on_gems_child_entered(child: Node) -> void:
	_wire_gem(child)


func _wire_gem(node: Node) -> void:
	var id: int = node.get_instance_id()
	if _wired_gems.has(id):
		return
	if not node.has_signal("collected"):
		return
	if not node.is_connected("collected", _on_gem_collected):
		node.connect("collected", _on_gem_collected)
	_wired_gems[id] = true


func _wire_level_up_ui() -> void:
	var candidate: Node = get_tree().root.find_child("LevelUpUI", true, false)
	if candidate == null:
		return
	if not candidate is CanvasLayer:
		return
	if _level_up_ui == candidate:
		return
	_level_up_ui = candidate as CanvasLayer
	_ui_was_visible = _level_up_ui.visible
	if not _level_up_ui.is_connected("visibility_changed", _on_level_up_visibility_changed):
		_level_up_ui.visibility_changed.connect(_on_level_up_visibility_changed)


func _wire_player() -> void:
	var players: Array[Node] = get_tree().get_nodes_in_group("player")
	if players.is_empty():
		_player = null
		return
	var candidate: Node = players[0]
	if candidate is Area2D:
		_player = candidate as Area2D
	else:
		_player = null


func _wire_enemies() -> void:
	var enemies_root: Node = get_tree().root.find_child("Enemies", true, false)
	if enemies_root == null:
		return
	if not enemies_root.is_connected("child_entered_tree", _on_enemies_child_entered):
		enemies_root.child_entered_tree.connect(_on_enemies_child_entered)
	for child: Node in enemies_root.get_children():
		_wire_enemy(child)


func _on_enemies_child_entered(child: Node) -> void:
	_wire_enemy(child)


func _wire_enemy(node: Node) -> void:
	var id: int = node.get_instance_id()
	if _wired_enemies.has(id):
		return
	if not node.has_signal("destroyed"):
		return
	if not node.is_connected("destroyed", _on_enemy_destroyed):
		node.connect("destroyed", _on_enemy_destroyed)
	_wired_enemies[id] = true


func _detect_player_move() -> void:
	var input_dir: Vector2 = Vector2(
		Input.get_action_strength("move_right") - Input.get_action_strength("move_left"),
		Input.get_action_strength("move_down") - Input.get_action_strength("move_up")
	)
	if input_dir.length_squared() <= MOVE_INPUT_THRESHOLD * MOVE_INPUT_THRESHOLD:
		return
	_emit_action(ACTION_MOVE)


func _on_gem_collected(_value: int) -> void:
	_emit_action(ACTION_PICKUP_XP)


func _on_enemy_destroyed(_enemy: Area2D, _xp_value: int) -> void:
	_emit_action(ACTION_KILL_ENEMY)


func _on_level_up_visibility_changed() -> void:
	if _level_up_ui == null or not is_instance_valid(_level_up_ui):
		return
	var now_visible: bool = _level_up_ui.visible
	if now_visible and not _ui_was_visible:
		_emit_action(ACTION_LEVEL_UP)
	_ui_was_visible = now_visible


func _emit_action(action_id: String) -> void:
	var bridge: Node = get_node_or_null("/root/EduActionBridge")
	if bridge == null:
		return
	if not bridge.has_method("emit_action"):
		return
	bridge.call("emit_action", action_id)
